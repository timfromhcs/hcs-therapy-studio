"""Numerics: calibration, confidence and conformal abstention."""

from __future__ import annotations

import math

import pytest

from hcs_therapy.numerics.calibration import (
    apply_platt,
    apply_temperature,
    brier_score,
    conformal_coverage,
    conformal_threshold,
    expected_calibration_error,
    fit_platt,
    fit_temperature,
    negative_log_likelihood,
    reliability_curve,
    should_abstain,
)


def test_brier_of_a_perfect_forecast_is_zero() -> None:
    assert brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == pytest.approx(0.0)


def test_brier_of_a_coin_flip_forecast_is_a_quarter() -> None:
    """Always predicting 0.5 gives (0.5)² per item = 0.25."""
    assert brier_score([0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0]) == pytest.approx(0.25)


def test_nll_of_a_perfect_forecast_is_near_zero() -> None:
    assert negative_log_likelihood([1.0, 0.0], [1, 0]) < 1e-9


def test_nll_of_a_coin_flip_is_log_two() -> None:
    assert negative_log_likelihood([0.5, 0.5], [1, 0]) == pytest.approx(math.log(2))


def test_calibration_error_is_zero_for_a_perfectly_calibrated_set() -> None:
    """Ten confidence levels, each with exactly that hit rate.

    Equal-mass binning puts one level per bin, so accuracy equals confidence and
    the error is zero. This is the identity that makes ECE readable.
    """
    probabilities: list[float] = []
    labels: list[int] = []
    for step in range(1, 11):
        confidence = step / 10
        hits = round(confidence * 10)
        probabilities.extend([confidence] * 10)
        labels.extend([1] * hits + [0] * (10 - hits))
    assert expected_calibration_error(probabilities, labels, bins=10) == pytest.approx(
        0.0, abs=1e-12
    )


def test_calibration_error_detects_overconfidence() -> None:
    """Says 0.95, is right half the time → ECE = |0.5 − 0.95| = 0.45.

    The labels are interleaved so every equal-mass bin sees the same hit rate;
    with the ones first, binning would just describe the ordering.
    """
    probabilities = [0.95] * 100
    labels = [1, 0] * 50
    assert expected_calibration_error(probabilities, labels, bins=10) == pytest.approx(
        0.45, abs=1e-9
    )


def test_reliability_curve_bins_carry_their_own_counts() -> None:
    curve = reliability_curve([0.1, 0.2, 0.9, 0.95], [0, 0, 1, 1], bins=2)
    assert len(curve) == 2
    assert sum(bucket["count"] for bucket in curve) == 4


def test_temperature_scaling_detects_overconfidence() -> None:
    """A model that is wrong half the time while claiming 98 % must get T > 1."""
    logits = [4.0, 4.0, -4.0, -4.0]
    labels = [1, 0, 0, 1]
    temperature = fit_temperature(logits, labels)
    assert temperature > 1.0


def test_temperature_scaling_reduces_the_nll_it_optimises() -> None:
    """Temperature scaling is fitted on NLL, so NLL must not get worse.

    ECE is *not* guaranteed to improve — it is not a proper scoring rule — which
    is exactly why the claim made here is the one that is true.
    """
    logits = [3.0] * 100
    labels = ([1] * 7 + [0] * 3) * 10
    temperature = fit_temperature(logits, labels)
    before = negative_log_likelihood(apply_temperature(logits, 1.0), labels)
    after = negative_log_likelihood(apply_temperature(logits, temperature), labels)
    assert after <= before + 1e-12


def test_temperature_scaling_repairs_a_badly_calibrated_set() -> None:
    """70 % correct while claiming 95 %: after fitting, confidence ≈ accuracy."""
    logits = [3.0] * 100
    labels = ([1] * 7 + [0] * 3) * 10
    before = expected_calibration_error(apply_temperature(logits, 1.0), labels, bins=10)
    temperature = fit_temperature(logits, labels)
    after = expected_calibration_error(
        apply_temperature(logits, temperature), labels, bins=10
    )
    assert after < before / 2.0, (before, after, temperature)


def test_temperature_fit_is_deterministic() -> None:
    logits = [2.0, -1.0, 0.5, -3.0, 1.5]
    labels = [1, 0, 1, 0, 1]
    assert fit_temperature(logits, labels) == fit_temperature(logits, labels)


def test_temperature_fit_refuses_a_single_class() -> None:
    """No calibration estimate exists when every label is identical."""
    assert fit_temperature([1.0, 2.0, 3.0], [1, 1, 1]) == 1.0


def test_temperature_requires_a_positive_value() -> None:
    with pytest.raises(ValueError):
        apply_temperature([1.0], 0.0)


def test_platt_scaling_recovers_a_separable_signal() -> None:
    scores = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    labels = [0, 0, 0, 0, 1, 1, 1]
    a, b = fit_platt(scores, labels)
    assert a > 0
    fitted = apply_platt(scores, a, b)
    assert fitted[0] < 0.5 < fitted[-1]
    assert negative_log_likelihood(fitted, labels) < negative_log_likelihood(
        [0.5] * len(scores), labels
    )


def test_platt_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        fit_platt([0.1, 0.2], [1])


def test_conformal_threshold_uses_the_finite_sample_rank() -> None:
    """n=9, alpha=0.1 → rank = ceil(10·0.9) = 9, so the loosest score sets q.

    q = 0.9 means "accept anything with confidence ≥ 0.1", which covers the true
    answer 90 % of the time on exchangeable data. A tighter-looking threshold
    here would be a misreading of the guarantee.
    """
    confidences = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    assert conformal_threshold(confidences, alpha=0.1) == pytest.approx(0.9)


def test_conformal_threshold_tightens_as_alpha_grows() -> None:
    """Smaller error budget ⇒ stricter acceptance."""
    confidences = sorted((index + 1) / 100 for index in range(100))
    loose = conformal_threshold(confidences, alpha=0.3)
    strict = conformal_threshold(confidences, alpha=0.02)
    assert strict > loose


def test_conformal_threshold_fails_closed_with_too_few_samples() -> None:
    """n=5, alpha=0.01 → rank = ceil(6·0.99) = 6 > n → never accept."""
    assert conformal_threshold([0.9] * 5, alpha=0.01) == float("inf")


def test_conformal_abstention_decision_is_monotone() -> None:
    threshold = conformal_threshold([0.9] * 9, alpha=0.1)
    assert not should_abstain(0.95, threshold)
    assert should_abstain(0.5, threshold)


def test_conformal_coverage_meets_the_guarantee_on_synthetic_data() -> None:
    """Marginal coverage must be at least 1−α on exchangeable data."""
    import numpy as np

    rng = np.random.default_rng(11)
    calibration = rng.uniform(0.0, 1.0, size=800)
    test = rng.uniform(0.0, 1.0, size=2000)
    coverage = conformal_coverage(calibration, test, alpha=0.2)
    assert coverage >= 0.78, f"coverage {coverage} violated the 1-alpha floor"
    assert coverage <= 0.85, f"coverage {coverage} is far above the target"


def test_conformal_rejects_an_impossible_alpha() -> None:
    with pytest.raises(ValueError):
        conformal_threshold([0.5], alpha=0.0)
    with pytest.raises(ValueError):
        conformal_threshold([], alpha=0.1)


def test_calibration_validation_rejects_out_of_range_probabilities() -> None:
    with pytest.raises(ValueError):
        brier_score([1.5], [1])
    with pytest.raises(ValueError):
        brier_score([0.5], [2])
    with pytest.raises(ValueError):
        brier_score([], [])
