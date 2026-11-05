"""Preference-optimisation losses and group advantages.

Sources
-------

Let ``Δ_chosen = log π_θ(y_w|x) − log π_ref(y_w|x)`` and
``Δ_rejected = log π_θ(y_l|x) − log π_ref(y_l|x)``.

* DPO — Rafailov et al. (2023):
  ``L = −log σ(β·(Δ_chosen − Δ_rejected))``
* IPO — Azar et al. (2024):
  ``L = (Δ_chosen − Δ_rejected − 1/(2β))²``
* ORPO — Hong et al. (2024): ``L = L_SFT + λ·(−log σ(log odds_w − log odds_l))``
* SimPO — Meng et al. (2024): reference-free with a target margin γ:
  ``L = −log σ(β·(log π_θ(y_w|x) − log π_θ(y_l|x)) − γ)``
* CPO — Xu et al. (2024): ``L = L_SFT + λ·(−log σ(β·(log π_θ(y_w|x) − log π_θ(y_l|x))))``
* GRPO — Shao et al. (2024) group-relative advantage:
  ``Â_i = (r_i − mean(r)) / std(r)``

Why this module exists at all: `AGENTS.md` §6.6 forbids starting with DPO
before SFT is stable, and forbids optimising adherence or session length. What
it does not forbid is knowing exactly what the loss would be, with a tested
implementation, so the decision can be made against numbers instead of vibes.
None of this is used in a training run by this project yet.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = [
    "cpo_loss",
    "dpo_loss",
    "grpo_advantage",
    "ipo_loss",
    "orpo_loss",
    "simpo_loss",
]


def _pair(first: Tensor, second: Tensor, label: str) -> None:
    if first.shape != second.shape:
        raise ValueError(f"{label} must have the same shape as its reference")
    if first.numel() == 0:
        raise ValueError(f"{label} must not be empty")


def dpo_loss(
    policy_chosen_logps: Tensor,
    policy_rejected_logps: Tensor,
    ref_chosen_logps: Tensor,
    ref_rejected_logps: Tensor,
    *,
    beta: float = 0.1,
) -> tuple[Tensor, Tensor, Tensor]:
    """Returns ``(loss, chosen_reward, rejected_reward)``.

    At exact, symmetric preference (log-ratios equal) the loss is ``log 2``,
    which the test suite asserts — that is the sanity anchor, because an
    off-by-one in the sign convention still trains and still looks plausible.
    """
    _pair(policy_chosen_logps, ref_chosen_logps, "policy/reference chosen")
    _pair(policy_rejected_logps, ref_rejected_logps, "policy/reference rejected")
    _pair(policy_chosen_logps, policy_rejected_logps, "chosen/rejected")
    if beta <= 0:
        raise ValueError("beta must be positive")
    chosen_reward = beta * (policy_chosen_logps - ref_chosen_logps)
    rejected_reward = beta * (policy_rejected_logps - ref_rejected_logps)
    logits = chosen_reward - rejected_reward
    loss = -torch.nn.functional.logsigmoid(logits).mean()
    return loss, chosen_reward.detach(), rejected_reward.detach()


def ipo_loss(
    policy_chosen_logps: Tensor,
    policy_rejected_logps: Tensor,
    ref_chosen_logps: Tensor,
    ref_rejected_logps: Tensor,
    *,
    beta: float = 0.1,
) -> tuple[Tensor, Tensor, Tensor]:
    """IPO: regression to a fixed margin instead of a sigmoid.

    This makes the loss bounded, which is the paper's answer to DPO's tendency
    to over-optimise when the preference signal is nearly deterministic.
    """
    _pair(policy_chosen_logps, ref_chosen_logps, "policy/reference chosen")
    _pair(policy_rejected_logps, ref_rejected_logps, "policy/reference rejected")
    if beta <= 0:
        raise ValueError("beta must be positive")
    chosen_reward = beta * (policy_chosen_logps - ref_chosen_logps)
    rejected_reward = beta * (policy_rejected_logps - ref_rejected_logps)
    margin = chosen_reward - rejected_reward - 0.5 / beta
    loss = (margin**2).mean()
    return loss, chosen_reward.detach(), rejected_reward.detach()


def simpo_loss(
    policy_chosen_logps: Tensor,
    policy_rejected_logps: Tensor,
    *,
    beta: float = 2.0,
    gamma: float = 0.5,
) -> Tensor:
    """SimPO: no reference model, so no second forward pass and no memory for it."""
    _pair(policy_chosen_logps, policy_rejected_logps, "chosen/rejected")
    if beta <= 0:
        raise ValueError("beta must be positive")
    if gamma < 0:
        raise ValueError("gamma must be non-negative")
    margin = beta * (policy_chosen_logps - policy_rejected_logps) - gamma
    return -torch.nn.functional.logsigmoid(margin).mean()


def orpo_loss(
    sft_loss: Tensor,
    chosen_logps: Tensor,
    rejected_logps: Tensor,
    *,
    lam: float = 0.1,
) -> tuple[Tensor, Tensor]:
    """ORPO: SFT plus an odds-ratio penalty, in one stage.

    The true ORPO penalty uses the odds ``p/(1−p)`` of each completion, which
    needs the normaliser ``log Z``. It is accepted here as an optional argument
    so the caller can supply an exact value; otherwise the log-probability
    difference is used, which is the common approximate form and is documented
    as such rather than presented as the exact paper loss.
    """
    _pair(chosen_logps, rejected_logps, "chosen/rejected")
    if lam < 0:
        raise ValueError("lam must be non-negative")
    log_odds = chosen_logps - rejected_logps
    penalty = -torch.nn.functional.logsigmoid(log_odds).mean()
    return sft_loss + lam * penalty, penalty.detach()


def cpo_loss(
    sft_loss: Tensor,
    chosen_logps: Tensor,
    rejected_logps: Tensor,
    *,
    beta: float = 0.1,
    lam: float = 0.1,
) -> tuple[Tensor, Tensor]:
    """CPO: SFT plus a bounded contrastive preference term."""
    _pair(chosen_logps, rejected_logps, "chosen/rejected")
    if beta <= 0:
        raise ValueError("beta must be positive")
    if lam < 0:
        raise ValueError("lam must be non-negative")
    preference = -torch.nn.functional.logsigmoid(beta * (chosen_logps - rejected_logps)).mean()
    return sft_loss + lam * preference, preference.detach()


def grpo_advantage(rewards: Tensor, *, group_size: int | None = None, eps: float = 1e-4) -> Tensor:
    """Group-relative advantage, normalised inside each group.

    A single-sample group has zero variance and therefore zero advantage; that
    is returned as zeros rather than NaN, because a silent NaN in a training
    loop is indistinguishable from a working one for several hours.
    """
    flat = rewards.reshape(-1)
    if flat.numel() == 0:
        raise ValueError("rewards must not be empty")
    size = group_size or flat.numel()
    if size <= 0:
        raise ValueError("group_size must be positive")
    if flat.numel() % size != 0:
        raise ValueError("rewards must be divisible by group_size")
    groups = flat.view(-1, size)
    if size == 1:
        return torch.zeros_like(flat)
    mean = groups.mean(dim=1, keepdim=True)
    std = groups.std(dim=1, keepdim=True, unbiased=False)
    advantage = (groups - mean) / (std + eps)
    return advantage.reshape(flat.shape)
