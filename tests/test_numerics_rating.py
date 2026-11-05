"""Numerics: ranking, bootstrap intervals and paired significance."""

from __future__ import annotations

import math

import pytest

from hcs_therapy.numerics.rating import (
    bootstrap_ci,
    bradley_terry,
    elo_update,
    expected_score,
    paired_bootstrap_pvalue,
    rank_from_matches,
)


def test_bradley_terry_recovers_a_planted_order() -> None:
    """A beats B twice as often as B beats A ⇒ strength ratio ≈ 2."""
    matches = [("a", "b")] * 20 + [("b", "a")] * 10
    strengths = bradley_terry(matches)
    assert strengths["a"] > strengths["b"]
    assert strengths["a"] / strengths["b"] == pytest.approx(2.0, rel=0.15)


def test_bradley_terry_recovers_three_players_in_order() -> None:
    matches = [("a", "b")] * 30 + [("b", "c")] * 30 + [("a", "c")] * 40
    order = [name for name, _ in rank_from_matches(matches)]
    assert order == ["a", "b", "c"]


def test_bradley_terry_is_scale_normalised() -> None:
    matches = [("x", "y")] * 5 + [("y", "z")] * 5
    strengths = bradley_terry(matches)
    geometric = math.exp(sum(math.log(value) for value in strengths.values()) / len(strengths))
    assert geometric == pytest.approx(1.0, rel=1e-6)


def test_bradley_terry_needs_matches_and_rejects_self_play() -> None:
    with pytest.raises(ValueError):
        bradley_terry([])
    with pytest.raises(ValueError):
        bradley_terry([("a", "a")])


def test_bradley_terry_keeps_a_winless_player_positive() -> None:
    matches = [("a", "b")] * 10
    strengths = bradley_terry(matches)
    assert strengths["b"] > 0.0


def test_elo_expected_score_is_half_for_equal_ratings() -> None:
    assert expected_score(1500.0, 1500.0) == pytest.approx(0.5)
    assert expected_score(1900.0, 1500.0) > 0.9


def test_elo_update_is_zero_sum() -> None:
    new_a, new_b = elo_update(1500.0, 1500.0, 1.0, k=32)
    assert new_a == pytest.approx(1516.0)
    assert new_b == pytest.approx(1484.0)
    assert new_a + new_b == pytest.approx(3000.0)


def test_elo_draw_between_equals_changes_nothing() -> None:
    assert elo_update(1500.0, 1500.0, 0.5) == (1500.0, 1500.0)


def test_elo_rejects_an_impossible_score() -> None:
    with pytest.raises(ValueError):
        elo_update(1500.0, 1500.0, 0.75)


def test_bootstrap_ci_brackets_the_mean() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    interval = bootstrap_ci(values, resamples=500, seed=3)
    assert interval is not None
    low, high = interval
    assert low <= 4.5 <= high


def test_bootstrap_ci_refuses_a_tiny_sample() -> None:
    """Four points do not support an interval; returning None is the honest answer."""
    assert bootstrap_ci([1.0, 2.0, 3.0, 4.0]) is None


def test_bootstrap_ci_narrows_as_n_grows() -> None:
    import numpy as np

    rng = np.random.default_rng(5)
    small = bootstrap_ci(rng.normal(size=30), resamples=500, seed=1)
    large = bootstrap_ci(rng.normal(size=3000), resamples=500, seed=1)
    assert small is not None and large is not None
    assert (large[1] - large[0]) < (small[1] - small[0])


def test_bootstrap_ci_is_reproducible_for_a_seed() -> None:
    values = [0.1, 0.4, 0.35, 0.8, 0.5, 0.2]
    assert bootstrap_ci(values, seed=42) == bootstrap_ci(values, seed=42)


def test_paired_bootstrap_detects_a_clear_improvement() -> None:
    baseline = [0.5] * 40
    candidate = [0.9] * 40
    assert paired_bootstrap_pvalue(candidate, baseline) < 0.01


def test_paired_bootstrap_does_not_invent_a_difference() -> None:
    values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    assert paired_bootstrap_pvalue(values, values) == pytest.approx(1.0)


def test_paired_bootstrap_needs_alignment() -> None:
    with pytest.raises(ValueError):
        paired_bootstrap_pvalue([1.0, 2.0], [1.0])
    with pytest.raises(ValueError):
        paired_bootstrap_pvalue([], [])
