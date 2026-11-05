"""Numerics: scoring metrics."""

from __future__ import annotations

import pytest

from hcs_therapy.numerics.metrics import (
    cohens_kappa,
    fleiss_kappa,
    macro_f1,
    mean_reciprocal_rank,
    ndcg_at_k,
    pass_at_k,
)


def test_cohens_kappa_perfect_agreement_is_one() -> None:
    assert cohens_kappa(["a", "b", "a"], ["a", "b", "a"]) == pytest.approx(1.0)


def test_cohens_kappa_pure_chance_is_zero() -> None:
    """Two raters on a balanced binary task agreeing 50 % of the time."""
    first = ["a", "a", "b", "b"]
    second = ["a", "b", "a", "b"]
    assert cohens_kappa(first, second) == pytest.approx(0.0)


def test_cohens_kappa_is_negative_for_systematic_disagreement() -> None:
    first = ["a", "a", "a", "b", "b", "b"]
    second = ["b", "b", "b", "a", "a", "a"]
    assert cohens_kappa(first, second) == pytest.approx(-1.0)


def test_cohens_kappa_rejects_misaligned_raters() -> None:
    with pytest.raises(ValueError):
        cohens_kappa(["a"], ["a", "b"])
    with pytest.raises(ValueError):
        cohens_kappa([], [])


def test_fleiss_kappa_perfect_agreement_is_one() -> None:
    # Two raters, two categories, both agree on every item.
    assert fleiss_kappa([[2, 0], [0, 2], [2, 0]]) == pytest.approx(1.0)


def test_fleiss_kappa_chance_is_zero() -> None:
    """Half the items agreed on, coin-flip marginals → exactly chance."""
    assert fleiss_kappa([[2, 0], [1, 1], [1, 1], [0, 2]]) == pytest.approx(0.0)


def test_fleiss_kappa_supports_more_than_two_raters() -> None:
    value = fleiss_kappa([[3, 0], [2, 1], [0, 3], [1, 2]])
    assert -1.0 <= value <= 1.0
    assert value > 0.0


def test_fleiss_kappa_validates_the_table() -> None:
    with pytest.raises(ValueError):
        fleiss_kappa([[1, 0], [2, 0]])
    with pytest.raises(ValueError):
        fleiss_kappa([[1]])
    with pytest.raises(ValueError):
        fleiss_kappa([])


def test_macro_f1_perfect_prediction_is_one() -> None:
    labels = ["crisis", "normal", "normal"]
    assert macro_f1(labels, labels) == pytest.approx(1.0)


def test_macro_f1_punishes_a_missed_class() -> None:
    truth = ["a", "a", "b", "b"]
    predicted = ["a", "a", "a", "a"]
    # class a: p=0.5, r=1.0 → F1=0.667; class b: p=0, r=0 → F1=0.
    assert macro_f1(truth, predicted) == pytest.approx((2 * 0.5 * 1.0 / 1.5) / 2)


def test_macro_f1_skips_classes_absent_from_both_lists() -> None:
    assert macro_f1(["a"], ["a"], labels=["a", "z"]) == pytest.approx(1.0)


def test_mrr_counts_the_first_relevant_hit() -> None:
    rankings = [["x", "y", "a"], ["b", "q"]]
    relevant = [{"a"}, {"b"}]
    # 1/3 + 1/1 averaged.
    assert mean_reciprocal_rank(rankings, relevant) == pytest.approx((1 / 3 + 1.0) / 2)


def test_mrr_gives_zero_for_a_query_with_no_hit() -> None:
    assert mean_reciprocal_rank([["x", "y"]], [{"a"}]) == pytest.approx(0.0)


def test_mrr_requires_aligned_inputs() -> None:
    with pytest.raises(ValueError):
        mean_reciprocal_rank([["a"]], [])
    with pytest.raises(ValueError):
        mean_reciprocal_rank([], [])


def test_ndcg_is_one_for_the_ideal_order() -> None:
    grades = {"a": 3.0, "b": 2.0, "c": 1.0}
    assert ndcg_at_k(["a", "b", "c"], grades) == pytest.approx(1.0)


def test_ndcg_is_less_than_one_for_a_reversed_order() -> None:
    grades = {"a": 3.0, "b": 2.0, "c": 1.0}
    assert ndcg_at_k(["c", "b", "a"], grades) < 0.8


def test_ndcg_is_zero_without_a_positive_grade() -> None:
    assert ndcg_at_k(["a"], {"a": 0.0}) == pytest.approx(0.0)
    assert ndcg_at_k([], {"a": 1.0}) == pytest.approx(0.0)


def test_ndcg_cutoff_is_respected() -> None:
    grades = {"a": 0.0, "b": 3.0}
    assert ndcg_at_k(["a", "b"], grades, k=1) == pytest.approx(0.0)


def test_pass_at_k_matches_the_closed_form() -> None:
    """n=10, c=2, k=1 → 0.2. The naive 1−(1−c/n)^k agrees for k=1."""
    assert pass_at_k(10, 2, 1) == pytest.approx(0.2)


def test_pass_at_k_is_one_when_enough_samples_are_correct() -> None:
    assert pass_at_k(5, 3, 3) == pytest.approx(1.0)


def test_pass_at_k_differs_from_the_naive_estimate() -> None:
    """The naive 1−(1−c/n)^k under-estimates; the Codex estimator is unbiased.

    pass@5 for n=10, c=2 is exactly 1 − C(8,5)/C(10,5) = 1 − 56/252 ≈ 0.7778,
    while the naive form gives 1 − 0.8⁵ ≈ 0.6723.
    """
    naive = 1.0 - (1.0 - 2 / 10) ** 5
    assert pass_at_k(10, 2, 5) == pytest.approx(1.0 - 56 / 252)
    assert pass_at_k(10, 2, 5) > naive


def test_pass_at_k_validates_its_inputs() -> None:
    with pytest.raises(ValueError):
        pass_at_k(0, 0, 1)
    with pytest.raises(ValueError):
        pass_at_k(5, 6, 1)
    with pytest.raises(ValueError):
        pass_at_k(5, 1, 0)
