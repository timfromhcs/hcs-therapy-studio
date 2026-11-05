"""Numerics: sampling, penalties and perplexity."""

from __future__ import annotations

import math

import numpy as np
import pytest

from hcs_therapy.numerics.sampling import (
    SamplingConfig,
    apply_penalties,
    entropy,
    perplexity,
    sample_token,
    softmax,
    transform_logits,
)


def test_softmax_sums_to_one_and_handles_neg_inf() -> None:
    probs = softmax([0.0, math.log(3.0), -np.inf])
    assert probs.sum() == pytest.approx(1.0)
    assert probs[0] == pytest.approx(0.25)
    assert probs[1] == pytest.approx(0.75)
    assert probs[2] == 0.0


def test_softmax_is_shift_invariant() -> None:
    a = softmax([1.0, 2.0, 3.0])
    b = softmax([101.0, 102.0, 103.0])
    assert np.allclose(a, b)


def test_softmax_rejects_all_negative_infinity() -> None:
    with pytest.raises(ValueError):
        softmax([-np.inf, -np.inf])
    with pytest.raises(ValueError):
        softmax([])


def test_entropy_of_a_uniform_distribution_is_log_v() -> None:
    assert entropy([0.25] * 4) == pytest.approx(math.log(4))


def test_entropy_of_a_point_mass_is_zero() -> None:
    assert entropy([1.0, 0.0, 0.0]) == pytest.approx(0.0)


def test_perplexity_of_uniform_is_the_vocabulary_size() -> None:
    """PPL = exp(-mean(log p)); uniform p = 1/V ⇒ PPL = V exactly."""
    vocab = 32000
    log_probs = [-math.log(vocab)] * 7
    assert perplexity(log_probs) == pytest.approx(vocab, rel=1e-12)


def test_perplexity_rejects_a_positive_log_probability() -> None:
    with pytest.raises(ValueError):
        perplexity([0.5])


def test_perplexity_is_monotone_in_confidence() -> None:
    confident = perplexity([-0.1, -0.2, -0.15])
    unsure = perplexity([-4.0, -3.8, -4.2])
    assert confident < unsure


def test_top_k_keeps_exactly_k_tokens() -> None:
    logits = [0.0, 1.0, 2.0, 3.0, 4.0]
    kept = transform_logits(logits, SamplingConfig(temperature=1.0, top_k=2, top_p=None))
    assert np.isfinite(kept).sum() == 2
    assert np.argmax(kept) == 4


def test_top_p_keeps_the_smallest_prefix_reaching_p() -> None:
    """Uniform over 4 tokens: p = 0.25 each, cumulative 0.25/0.50/0.75/1.0.

    top_p=0.50 needs two tokens, top_p=0.75 needs three. Exact binary fractions,
    so the assertion is not at the mercy of floating-point rounding.
    """
    logits = [0.0, 0.0, 0.0, 0.0]
    two = transform_logits(logits, SamplingConfig(temperature=1.0, top_k=None, top_p=0.5))
    three = transform_logits(logits, SamplingConfig(temperature=1.0, top_k=None, top_p=0.75))
    assert np.isfinite(two).sum() == 2
    assert np.isfinite(three).sum() == 3


def test_top_p_always_keeps_at_least_one_token() -> None:
    logits = [0.0, 1.0, 2.0]
    kept = transform_logits(logits, SamplingConfig(temperature=1.0, top_k=None, top_p=1e-9))
    assert np.isfinite(kept).sum() == 1
    assert np.argmax(kept) == 2


def test_min_p_threshold_is_relative_to_the_maximum() -> None:
    """logits [2,0,0] → p ≈ [0.787, 0.107, 0.107]; min_p=0.5 keeps only the mode."""
    logits = [2.0, 0.0, 0.0]
    kept = transform_logits(
        logits, SamplingConfig(temperature=1.0, top_k=None, top_p=None, min_p=0.5)
    )
    assert np.isfinite(kept).sum() == 1
    assert np.argmax(kept) == 0


def test_min_p_keeps_a_tie_at_the_threshold() -> None:
    logits = [math.log(0.5), math.log(0.5)]
    kept = transform_logits(
        logits, SamplingConfig(temperature=1.0, top_k=None, top_p=None, min_p=0.9)
    )
    assert np.isfinite(kept).sum() == 2


def test_temperature_flattens_and_sharpens() -> None:
    logits = [0.0, 1.0, 2.0]
    cold = softmax(transform_logits(logits, SamplingConfig(temperature=0.5)))
    hot = softmax(transform_logits(logits, SamplingConfig(temperature=2.0)))
    assert cold.max() > hot.max()


def test_typical_filter_keeps_the_token_near_the_entropy() -> None:
    """A flat distribution has entropy ~log V, so all tokens are typical."""
    logits = [0.0, 0.0, 0.0]
    kept = transform_logits(
        logits, SamplingConfig(temperature=1.0, top_k=None, top_p=None, typical_p=0.99)
    )
    assert np.isfinite(kept).sum() == 3


def test_repetition_penalty_pushes_a_positive_logit_down() -> None:
    logits = [4.0, 0.0]
    penalised = apply_penalties(logits, [0], SamplingConfig(repetition_penalty=2.0))
    assert penalised[0] == pytest.approx(2.0)


def test_repetition_penalty_moves_a_negative_logit_further_down() -> None:
    """A plain multiplication would raise a negative logit and encourage it."""
    logits = [-4.0, 0.0]
    penalised = apply_penalties(logits, [0], SamplingConfig(repetition_penalty=2.0))
    assert penalised[0] == pytest.approx(-8.0)


def test_frequency_and_presence_penalties_follow_the_convention() -> None:
    logits = [10.0, 10.0]
    history = [0, 0, 0]
    penalised = apply_penalties(
        logits, history, SamplingConfig(frequency_penalty=0.5, presence_penalty=0.25)
    )
    assert penalised[0] == pytest.approx(10.0 - 1.5 - 0.25)
    assert penalised[1] == pytest.approx(10.0)


def test_dry_penalises_the_token_that_continued_a_repeated_ngram() -> None:
    """History 1,2,3,1,2,3 → the n-gram "1 2 3" repeated, so 1 is penalised."""
    logits = [0.0] * 6
    history = [1, 2, 3, 1, 2, 3]
    penalised = apply_penalties(
        logits,
        history,
        SamplingConfig(dry_multiplier=2.0, dry_base=1.75, dry_allowed_length=2),
    )
    assert penalised[1] < 0.0
    assert penalised[4] == pytest.approx(0.0)


def test_dry_does_no_harm_without_a_repeat() -> None:
    logits = [0.0] * 8
    penalised = apply_penalties(
        logits, [1, 2, 3, 4, 5, 6], SamplingConfig(dry_multiplier=2.0)
    )
    assert np.allclose(penalised, 0.0)


def test_greedy_is_deterministic_regardless_of_seed() -> None:
    config = SamplingConfig(temperature=0.0, seed=1)
    first = sample_token([0.1, 5.0, 0.2], config)
    second = sample_token([0.1, 5.0, 0.2], SamplingConfig(temperature=0.0, seed=99))
    assert first == second == 1


def test_sampling_is_reproducible_with_a_seed() -> None:
    config = SamplingConfig(temperature=1.0, top_k=None, top_p=None, seed=7)
    logits = [0.0, 0.0, 0.0, 0.0]
    first = [sample_token(logits, config) for _ in range(20)]
    second = [sample_token(logits, config) for _ in range(20)]
    assert first == second


def test_sampling_follows_the_probability_order() -> None:
    """A near-deterministic distribution must almost always pick the mode."""
    config = SamplingConfig(temperature=0.1, top_k=None, top_p=None, seed=3)
    logits = [0.0, 10.0, 0.0]
    picks = [sample_token(logits, config) for _ in range(200)]
    assert picks.count(1) > 195


def test_invalid_filter_parameters_are_rejected() -> None:
    with pytest.raises(ValueError):
        transform_logits([0.0], SamplingConfig(top_p=0.0))
    with pytest.raises(ValueError):
        transform_logits([0.0], SamplingConfig(min_p=2.0))
    with pytest.raises(ValueError):
        transform_logits([0.0], SamplingConfig(typical_p=0.0))
    with pytest.raises(ValueError):
        apply_penalties([0.0], [0], SamplingConfig(repetition_penalty=0.0))
