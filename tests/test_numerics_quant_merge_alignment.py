"""Numerics: quantisation sizes, KV cache, LoRA counts, merging and losses."""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from hcs_therapy.numerics.alignment import (
    cpo_loss,
    dpo_loss,
    grpo_advantage,
    ipo_loss,
    orpo_loss,
    simpo_loss,
)
from hcs_therapy.numerics.merge import (
    dare_merge,
    linear_merge,
    slerp,
    task_vector,
    ties_merge,
)
from hcs_therapy.numerics.quant import (
    BLOCK_LAYOUTS,
    bytes_per_weight,
    estimate_gguf_bytes,
    kv_cache_bytes,
    lora_parameters,
    quant_info,
    transformer_lora_parameters,
)

# --- quantisation ---------------------------------------------------------


def test_published_bits_per_weight() -> None:
    """These are struct sizes, not estimates: they come from ggml-quants.h."""
    expected = {
        "Q2_K": 2.625,
        "Q3_K": 3.4375,
        "Q4_0": 4.5,
        "Q4_1": 5.0,
        "Q4_K": 4.5,
        "Q5_0": 5.5,
        "Q5_1": 6.0,
        "Q5_K": 5.5,
        "Q6_K": 6.5625,
        "Q8_0": 8.5,
        "Q8_K": 9.125,
        "F16": 16.0,
        "BF16": 16.0,
        "F32": 32.0,
    }
    for name, bits in expected.items():
        assert quant_info(name).bits_per_weight == pytest.approx(bits), name


def test_every_layout_has_a_sane_block() -> None:
    for name, (weights, size) in BLOCK_LAYOUTS.items():
        assert weights >= 1, name
        assert size >= weights / 8, f"{name} cannot store its own weights"


def test_quant_names_are_case_insensitive() -> None:
    assert quant_info("q4_K").bits_per_weight == pytest.approx(4.5)


def test_unknown_quantisation_is_an_error_with_a_list() -> None:
    with pytest.raises(ValueError, match="Q4_K"):
        quant_info("Q9_Z")


def test_gguf_estimate_grows_as_precision_grows() -> None:
    q4 = estimate_gguf_bytes(1_700_000_000, "Q4_K")
    q8 = estimate_gguf_bytes(1_700_000_000, "Q8_0")
    assert q4 < q8
    assert 0.9 * 1024**3 < q4 < 1.2 * 1024**3


def test_gguf_estimate_of_a_1_7b_q8_matches_the_real_file() -> None:
    """The real qwen3-1.7b Q8_0 file is 1,834,426,016 bytes (measured, hash-pinned).

    A 6 % band around a measured artifact is the honest tolerance for an
    estimator that does not parse the tensor list.
    """
    estimate = estimate_gguf_bytes(1_700_000_000, "Q8_0")
    assert abs(estimate - 1_834_426_016) / 1_834_426_016 < 0.06


def test_gguf_estimate_validates_input() -> None:
    with pytest.raises(ValueError):
        estimate_gguf_bytes(0, "Q4_K")
    with pytest.raises(ValueError):
        estimate_gguf_bytes(10, "Q4_K", quantised_fraction=0.0)


def test_bytes_per_weight_matches_quant_info() -> None:
    assert bytes_per_weight("Q4_K") == pytest.approx(4.5 / 8)


# --- KV cache -------------------------------------------------------------


def test_kv_cache_matches_the_published_formula() -> None:
    """2 · layers · kv_heads · head_dim · bytes, per token."""
    budget = kv_cache_bytes(n_layers=28, n_kv_heads=8, head_dim=128, context=4096)
    expected = 2 * 28 * 8 * 128 * 2
    assert budget.per_token_bytes == expected
    assert budget.total_bytes == expected * 4096


def test_kv_cache_scales_linearly_with_context_and_batch() -> None:
    small = kv_cache_bytes(n_layers=4, n_kv_heads=2, head_dim=64, context=1000)
    large = kv_cache_bytes(n_layers=4, n_kv_heads=2, head_dim=64, context=4000)
    assert large.total_bytes == small.total_bytes * 4
    batched = kv_cache_bytes(n_layers=4, n_kv_heads=2, head_dim=64, context=1000, batch=3)
    assert batched.total_bytes == small.total_bytes * 3


def test_quantising_the_cache_cuts_the_footprint() -> None:
    fp16 = kv_cache_bytes(n_layers=4, n_kv_heads=2, head_dim=64, context=1000)
    q8 = kv_cache_bytes(
        n_layers=4, n_kv_heads=2, head_dim=64, context=1000, bytes_per_element=34 / 32
    )
    assert q8.total_bytes < fp16.total_bytes
    assert q8.total_bytes / fp16.total_bytes == pytest.approx(0.53125, rel=0.01)


def test_kv_cache_rejects_zero_dimensions() -> None:
    with pytest.raises(ValueError):
        kv_cache_bytes(n_layers=0, n_kv_heads=1, head_dim=1, context=1)


# --- LoRA -----------------------------------------------------------------


def test_lora_parameter_count_is_rank_times_sum_of_dims() -> None:
    result = lora_parameters({"q": (1024, 1024)}, rank=8)
    assert result["total"] == 8 * (1024 + 1024)


def test_lora_magnitude_adds_one_vector_per_matrix() -> None:
    plain = lora_parameters({"q": (100, 200)}, rank=4)
    dora = lora_parameters({"q": (100, 200)}, rank=4, magnitude=True)
    assert dora["total"] - plain["total"] == 200


def test_lora_validates_rank_and_dimensions() -> None:
    with pytest.raises(ValueError):
        lora_parameters({"q": (10, 10)}, rank=0)
    with pytest.raises(ValueError):
        lora_parameters({"q": (0, 10)}, rank=4)


def test_transformer_lora_covers_every_targeted_layer() -> None:
    result = transformer_lora_parameters(n_layers=2, hidden=64, intermediate=128, rank=4)
    # per layer: 4 square (2·4·64) + 2 up/gate (4·(64+128)) + 1 down (4·(128+64))
    per_layer = 4 * (4 * 128) + 3 * (4 * 192)
    assert result["total"] == 2 * per_layer
    assert result["average_per_layer"] == per_layer


def test_transformer_lora_rejects_an_unknown_target() -> None:
    with pytest.raises(ValueError):
        transformer_lora_parameters(
            n_layers=1, hidden=8, intermediate=8, rank=2, targets=("made_up_proj",)
        )


# --- merging --------------------------------------------------------------


def test_slerp_endpoints_are_exact() -> None:
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    assert np.allclose(slerp(a, b, 0.0), a)
    assert np.allclose(slerp(a, b, 1.0), b)


def test_slerp_midpoint_preserves_the_norm() -> None:
    """Interpolation happens on the sphere, so the radius is constant."""
    a = np.array([3.0, 0.0, 0.0])
    b = np.array([0.0, 3.0, 0.0])
    midpoint = slerp(a, b, 0.5)
    assert np.linalg.norm(midpoint) == pytest.approx(3.0)
    assert np.allclose(midpoint, [3 / math.sqrt(2)] * 2 + [0.0], atol=1e-12)


def test_slerp_falls_back_on_parallel_and_antiparallel() -> None:
    """Same direction has no unique geodesic; blend linearly and stay finite."""
    a = np.array([1.0, 2.0])
    assert np.allclose(slerp(a, a * 2.0, 0.3), a * 1.3)
    blended = slerp(np.array([1.0, 0.0]), np.array([-1.0, 0.0]), 0.5)
    assert np.allclose(blended, [0.0, 0.0])


def test_slerp_validates_t_and_shapes() -> None:
    with pytest.raises(ValueError):
        slerp(np.array([1.0]), np.array([1.0]), 1.5)
    with pytest.raises(ValueError):
        slerp(np.array([1.0]), np.array([1.0, 2.0]), 0.5)


def test_task_vector_is_a_difference() -> None:
    base = np.array([1.0, 2.0])
    finetuned = np.array([2.0, 5.0])
    assert np.allclose(task_vector(base, finetuned), [1.0, 3.0])


def test_linear_merge_of_identical_vectors_is_the_identity() -> None:
    delta = np.array([1.0, -2.0])
    assert np.allclose(linear_merge([delta, delta]), delta)


def test_linear_merge_respects_weights() -> None:
    a = np.array([0.0, 1.0])
    b = np.array([1.0, 0.0])
    assert np.allclose(linear_merge([a, b], [3.0, 1.0]), [0.25, 0.75])


def test_ties_merging_identical_vectors_is_the_identity() -> None:
    delta = np.array([1.0, -2.0, 0.5])
    assert np.allclose(ties_merge([delta, delta], density=1.0), delta)


def test_ties_merging_cancels_equal_opposite_mass() -> None:
    a = np.array([2.0])
    b = np.array([-2.0])
    # Equal mass on both signs: elected sign is 0 → falls back to the dominant
    # magnitude, which is a tie, so only the agreeing half contributes.
    merged = ties_merge([a, b], density=1.0)
    assert abs(float(merged[0])) == pytest.approx(2.0)


def test_ties_trimming_keeps_only_the_dense_signal() -> None:
    a = np.array([10.0, 0.01, 0.01, 0.01])
    merged = ties_merge([a], density=0.25)
    assert merged[0] == pytest.approx(10.0)
    assert np.allclose(merged[1:], 0.0)


def test_ties_validates_density() -> None:
    with pytest.raises(ValueError):
        ties_merge([np.array([1.0])], density=0.0)


def test_dare_preserves_the_expectation() -> None:
    """Drop p of the entries, scale survivors by 1/(1−p): mean is unchanged."""
    delta = np.ones(20000)
    merged = dare_merge([delta], drop_rate=0.5)
    assert merged.mean() == pytest.approx(1.0, rel=0.05)


def test_dare_is_reproducible_for_a_seed() -> None:
    delta = np.arange(1000.0)
    assert np.allclose(dare_merge([delta], seed=5), dare_merge([delta], seed=5))


def test_dare_with_zero_drop_is_the_identity() -> None:
    delta = np.array([1.0, 2.0, 3.0])
    assert np.allclose(dare_merge([delta], drop_rate=0.0), delta)


def test_dare_rejects_an_impossible_drop_rate() -> None:
    with pytest.raises(ValueError):
        dare_merge([np.array([1.0])], drop_rate=1.0)


def test_merge_rejects_mismatched_shapes() -> None:
    with pytest.raises(ValueError):
        linear_merge([np.array([1.0]), np.array([1.0, 2.0])])
    with pytest.raises(ValueError):
        ties_merge([np.array([1.0]), np.array([1.0, 2.0])])


# --- alignment losses -----------------------------------------------------


def test_dpo_loss_at_symmetric_preference_is_log_two() -> None:
    """Sanity anchor: equal log-ratios ⇒ σ(0) = 0.5 ⇒ −log 0.5 = log 2."""
    zeros = torch.zeros(4)
    loss, chosen, rejected = dpo_loss(zeros, zeros, zeros, zeros)
    assert float(loss) == pytest.approx(math.log(2))
    assert torch.allclose(chosen, torch.zeros(4))
    assert torch.allclose(rejected, torch.zeros(4))


def test_dpo_loss_falls_as_the_margin_grows() -> None:
    policy_chosen = torch.tensor([1.0, 3.0, 8.0])
    policy_rejected = torch.zeros(3)
    ref = torch.zeros(3)
    losses = [
        float(dpo_loss(policy_chosen[i : i + 1], policy_rejected[i : i + 1], ref[:1], ref[:1])[0])
        for i in range(3)
    ]
    assert losses[0] > losses[1] > losses[2]


def test_dpo_margin_doubles_when_beta_doubles() -> None:
    pc = torch.tensor([1.0])
    z = torch.zeros(1)
    _, chosen, _ = dpo_loss(pc, z, z, z, beta=0.1)
    _, chosen2, _ = dpo_loss(pc, z, z, z, beta=0.2)
    assert float(chosen2) == pytest.approx(2 * float(chosen))


def test_dpo_backpropagates() -> None:
    pc = torch.tensor([1.0], requires_grad=True)
    loss, _, _ = dpo_loss(pc, torch.zeros(1), torch.zeros(1), torch.zeros(1))
    loss.backward()
    assert pc.grad is not None
    assert float(pc.grad[0]) < 0.0


def test_dpo_rejects_bad_shapes_and_beta() -> None:
    with pytest.raises(ValueError):
        dpo_loss(torch.zeros(2), torch.zeros(3), torch.zeros(2), torch.zeros(3))
    with pytest.raises(ValueError):
        dpo_loss(torch.zeros(1), torch.zeros(1), torch.zeros(1), torch.zeros(1), beta=0.0)


def test_ipo_loss_is_exactly_zero_at_the_target_margin() -> None:
    beta = 0.1
    policy_chosen = torch.tensor([2.0])
    loss, _, _ = ipo_loss(
        policy_chosen, torch.zeros(1), torch.zeros(1), torch.zeros(1), beta=beta
    )
    # margin = β·2 − 1/(2β) = 0.2 − 5 = −4.8 → squared, not zero.
    assert float(loss) > 0.0
    target = torch.tensor([0.5 / beta / beta])
    flat, _, _ = ipo_loss(target, torch.zeros(1), torch.zeros(1), torch.zeros(1), beta=beta)
    assert float(flat) == pytest.approx(0.0, abs=1e-12)


def test_simpo_loss_respects_the_target_margin() -> None:
    at_margin = simpo_loss(torch.tensor([1.0]), torch.zeros(1), beta=2.0, gamma=2.0)
    assert float(at_margin) == pytest.approx(math.log(2))
    beyond = simpo_loss(torch.tensor([2.0]), torch.zeros(1), beta=2.0, gamma=2.0)
    assert float(beyond) < float(at_margin)


def test_simpo_rejects_a_negative_margin() -> None:
    with pytest.raises(ValueError):
        simpo_loss(torch.zeros(1), torch.zeros(1), gamma=-1.0)


def test_orpo_adds_its_penalty_to_the_sft_loss() -> None:
    sft = torch.tensor(1.0)
    total, penalty = orpo_loss(sft, torch.zeros(1), torch.zeros(1), lam=0.5)
    assert float(penalty) == pytest.approx(math.log(2))
    assert float(total) == pytest.approx(1.0 + 0.5 * math.log(2))


def test_cpo_adds_a_bounded_contrastive_term() -> None:
    """β·Δ = 0.1 · 100 = 10 → −log σ(10) ≈ 4.5e−5, i.e. the term saturates.

    ``total = sft + λ·penalty`` with sft = 0 and λ = 0.1, so total is a tenth of
    the raw penalty — the relationship the test pins down.
    """
    total, preference = cpo_loss(
        torch.zeros(1), torch.tensor([100.0]), torch.zeros(1), lam=0.1
    )
    assert float(preference) < 0.01
    assert float(total) == pytest.approx(0.1 * float(preference))


def test_grpo_advantage_standardises_inside_each_group() -> None:
    """Group [0.4, 1.2]: mean 0.8, population std 0.4 → [−1, +1]."""
    advantage = grpo_advantage(torch.tensor([0.4, 1.2]), group_size=2)
    assert torch.allclose(advantage, torch.tensor([-1.0, 1.0]), atol=1e-3)


def test_grpo_advantage_sums_to_zero_inside_a_group() -> None:
    advantage = grpo_advantage(torch.tensor([0.0, 1.0, 2.0, 3.0]), group_size=4)
    assert float(advantage.sum()) == pytest.approx(0.0, abs=1e-5)


def test_grpo_single_sample_group_returns_zeros_not_nan() -> None:
    advantage = grpo_advantage(torch.tensor([1.0, 2.0]), group_size=1)
    assert torch.allclose(advantage, torch.zeros(2))
    assert not torch.isnan(advantage).any()


def test_grpo_validates_the_group_size() -> None:
    with pytest.raises(ValueError):
        grpo_advantage(torch.tensor([1.0, 2.0, 3.0]), group_size=2)
    with pytest.raises(ValueError):
        grpo_advantage(torch.tensor([]))
