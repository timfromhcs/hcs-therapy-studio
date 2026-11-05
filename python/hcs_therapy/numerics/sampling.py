"""Token sampling, logit post-processing and perplexity.

Sources
-------

* top-k — Fan, Lewis & Dauphin, *Hierarchical Neural Story Generation* (2018)
* nucleus / top-p — Holtzman et al., *The Curious Case of Neural Text
  Degeneration* (2019): smallest set V_p with Σ_{x∈V_p} p(x) ≥ p
* min-p — Nguyen et al., *Turning Up the Heat: Min-p Sampling* (2024):
  keep every token with p(x) ≥ p_min · max_x p(x)
* typical decoding — Meister et al., *Typical Decoding for Natural Language
  Generation* (2022): keep tokens whose surprisal is near the distribution
  entropy, measured by |−log p(x) − H(p)|
* repetition penalty — Keskar et al., CTRL (2019); frequency/presence variants
  follow the OpenAI logit-bias convention
* DRY — the don't-repeat-n-gram sampler shipped in llama.cpp, which is what
  actually stops a 1.7B model from looping
* perplexity — PPL = exp(−(1/N) Σ log p(x_i | x_<i))

Everything here operates on a 1-D logit vector for a single step. That keeps it
unit-testable without a model, and it is the same arithmetic the server does.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

__all__ = [
    "SamplingConfig",
    "apply_penalties",
    "entropy",
    "perplexity",
    "sample_token",
    "softmax",
    "transform_logits",
]

_NEG_INF = -np.inf


@dataclass(frozen=True)
class SamplingConfig:
    """Sampler settings. Defaults follow small-model practice: low temperature,
    a wide top-k and top-p, and no min-p (it is opt-in because it interacts
    badly with very flat distributions)."""

    temperature: float = 0.8
    top_k: int | None = 40
    top_p: float | None = 0.95
    min_p: float | None = None
    typical_p: float | None = None
    repetition_penalty: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    dry_multiplier: float = 0.0
    dry_base: float = 1.75
    dry_allowed_length: int = 2
    seed: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "min_p": self.min_p,
            "typical_p": self.typical_p,
            "repetition_penalty": self.repetition_penalty,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "dry_multiplier": self.dry_multiplier,
        }


def _as_array(logits: Sequence[float]) -> np.ndarray:
    array = np.asarray(logits, dtype=np.float64).reshape(-1)
    if array.size == 0:
        raise ValueError("logits must not be empty")
    return array


def softmax(logits: Sequence[float]) -> np.ndarray:
    """Numerically stable softmax. ``-inf`` entries become probability 0."""
    array = _as_array(logits)
    finite = np.isfinite(array)
    if not finite.any():
        raise ValueError("at least one logit must be finite")
    shifted = np.where(finite, array, _NEG_INF)
    peak = shifted[finite].max()
    exponents = np.where(finite, np.exp(shifted - peak), 0.0)
    total = exponents.sum()
    if total <= 0:
        raise ValueError("softmax denominator underflowed")
    return exponents / total


def entropy(probabilities: Sequence[float]) -> float:
    """Shannon entropy in nats."""
    probs = np.asarray(probabilities, dtype=np.float64)
    probs = probs[probs > 0]
    if probs.size == 0:
        return 0.0
    return float(-np.sum(probs * np.log(probs)))


def perplexity(log_probabilities: Sequence[float]) -> float:
    """Perplexity from per-token natural-log probabilities.

    A uniform distribution over V tokens has log-probability −log V everywhere,
    so the result is exactly V. The test suite asserts that identity, which is
    why this function is trustworthy as a quantisation-damage measure.
    """
    values = np.asarray(list(log_probabilities), dtype=np.float64)
    if values.size == 0:
        raise ValueError("need at least one log-probability")
    if np.any(values > 1e-9):
        raise ValueError("log-probabilities must be <= 0")
    return float(np.exp(-values.mean()))


def apply_penalties(
    logits: Sequence[float],
    history: Sequence[int],
    config: SamplingConfig,
) -> np.ndarray:
    """Repetition, frequency, presence and DRY, in that order.

    The repetition penalty is the CTRL sign-aware form: divide a positive logit,
    multiply a negative one. A plain multiplication would push negative logits
    *up* and actively encourage the repeated token.
    """
    array = _as_array(logits).copy()
    if not history:
        return array
    counts = Counter(int(token) for token in history)
    vocab = array.size

    if config.repetition_penalty != 1.0:
        penalty = float(config.repetition_penalty)
        if penalty <= 0:
            raise ValueError("repetition_penalty must be positive")
        for token in counts:
            if 0 <= token < vocab:
                value = array[token]
                array[token] = value / penalty if value > 0 else value * penalty

    if config.frequency_penalty:
        for token, count in counts.items():
            if 0 <= token < vocab:
                array[token] -= config.frequency_penalty * count

    if config.presence_penalty:
        for token in counts:
            if 0 <= token < vocab:
                array[token] -= config.presence_penalty

    if config.dry_multiplier:
        for length, follower in _dry_followers(history, config.dry_allowed_length):
            if 0 <= follower < vocab and np.isfinite(array[follower]):
                penalty = config.dry_multiplier * (
                    config.dry_base ** (length - config.dry_allowed_length)
                )
                array[follower] -= penalty
    return array


def _dry_followers(history: Sequence[int], minimum: int) -> list[tuple[int, int]]:
    """``(length, follower)`` for every suffix of ``history`` seen earlier.

    DRY penalises the token that *followed* the previous occurrence of the
    repeated n-gram. Getting this wrong is easy: the follower belongs to the
    earlier occurrence, not to the suffix itself.
    """
    total = len(history)
    found: list[tuple[int, int]] = []
    for length in range(minimum, total):
        suffix = list(history[total - length :])
        for start in range(0, total - length):
            if list(history[start : start + length]) == suffix:
                found.append((length, history[start + length]))
                break
    return found


def _filter_top_k(array: np.ndarray, k: int | None) -> np.ndarray:
    if k is None or k <= 0 or k >= array.size:
        return array
    keep = np.argpartition(array, -k)[-k:]
    mask = np.full(array.size, False)
    mask[keep] = True
    return np.where(mask, array, _NEG_INF)


def _filter_top_p(array: np.ndarray, p: float | None) -> np.ndarray:
    if p is None or p >= 1.0:
        if p is not None and p <= 0:
            raise ValueError("top_p must be in (0, 1]")
        return array
    if p <= 0:
        raise ValueError("top_p must be in (0, 1]")
    probs = softmax(array)
    order = np.argsort(-probs, kind="stable")
    cumulative = np.cumsum(probs[order])
    # Smallest prefix whose cumulative mass reaches p; always at least one token.
    cutoff = int(np.searchsorted(cumulative, p, side="left")) + 1
    cutoff = min(max(cutoff, 1), array.size)
    keep = order[:cutoff]
    mask = np.full(array.size, False)
    mask[keep] = True
    return np.where(mask, array, _NEG_INF)


def _filter_min_p(array: np.ndarray, p: float | None) -> np.ndarray:
    if p is None or p <= 0:
        return array
    if p > 1:
        raise ValueError("min_p must be in (0, 1]")
    probs = softmax(array)
    threshold = p * probs.max()
    mask = probs >= threshold
    # The argmax always survives (threshold <= max probability).
    return np.where(mask, array, _NEG_INF)


def _filter_typical(array: np.ndarray, p: float | None) -> np.ndarray:
    if p is None or p >= 1.0:
        return array
    if p <= 0:
        raise ValueError("typical_p must be in (0, 1]")
    probs = softmax(array)
    h = entropy(probs)
    with np.errstate(divide="ignore"):
        surprisal = -np.log(probs)
    distance = np.abs(surprisal - h)
    order = np.argsort(distance, kind="stable")
    cumulative = np.cumsum(probs[order])
    cutoff = int(np.searchsorted(cumulative, p, side="left")) + 1
    cutoff = min(max(cutoff, 1), array.size)
    mask = np.full(array.size, False)
    mask[order[:cutoff]] = True
    return np.where(mask, array, _NEG_INF)


def transform_logits(
    logits: Sequence[float],
    config: SamplingConfig,
    *,
    history: Sequence[int] = (),
) -> np.ndarray:
    """Full post-processing chain, in the order a server applies it.

    penalties → temperature → top-k → top-p → min-p → typical.
    Applying temperature after penalties matters: the CTRL penalty is defined on
    raw logits, and scaling first would change its effective strength.
    """
    array = apply_penalties(logits, history, config)
    # temperature <= 0 means greedy: leave the logits alone, argmax decides.
    array = (
        array
        if config.temperature <= 0
        else array / float(config.temperature)
    )
    array = _filter_top_k(array, config.top_k)
    array = _filter_top_p(array, config.top_p)
    array = _filter_min_p(array, config.min_p)
    array = _filter_typical(array, config.typical_p)
    return array


def sample_token(
    logits: Sequence[float],
    config: SamplingConfig,
    *,
    history: Sequence[int] = (),
    rng: np.random.Generator | None = None,
) -> int:
    """Sample one token id. ``temperature <= 0`` degenerates to argmax."""
    processed = transform_logits(logits, config, history=history)
    if config.temperature <= 0:
        return int(np.argmax(processed))
    probs = softmax(processed)
    generator = rng if rng is not None else np.random.default_rng(config.seed)
    return int(generator.choice(probs.size, p=probs))
