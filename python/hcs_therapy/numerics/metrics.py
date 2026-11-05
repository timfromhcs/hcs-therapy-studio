"""Scoring metrics with a published definition each.

Sources
-------

* Cohen's κ — Cohen (1960). Agreement between two raters, chance-corrected.
* Fleiss' κ — Fleiss (1971). The many-rater generalisation.
* MRR / NDCG — standard IR measures (Järvelin & Kekäläinen 2002 for NDCG).
* pass@k — Chen et al., *Evaluating Large Language Models Trained on Code*
  (2021): the unbiased estimator ``1 − C(n−c, k)/C(n, k)``, not the naive
  ``1 − (1 − c/n)^k``.

Chance-corrected agreement is the only way a clinician-review claim means
anything: two raters who agree 80 % on a 50/50 task have agreed by luck.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence

__all__ = [
    "cohens_kappa",
    "fleiss_kappa",
    "macro_f1",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "pass_at_k",
]


def cohens_kappa(first: Sequence[object], second: Sequence[object]) -> float:
    """Chance-corrected agreement between two raters.

    1.0 is perfect, 0.0 is chance. Negative values mean systematic disagreement.
    """
    if len(first) != len(second):
        raise ValueError("raters must label the same number of items")
    if not first:
        raise ValueError("need at least one item")
    total = len(first)
    observed = sum(1 for a, b in zip(first, second, strict=False) if a == b) / total
    first_counts = Counter(first)
    second_counts = Counter(second)
    categories = set(first_counts) | set(second_counts)
    expected = sum(
        (first_counts[category] / total) * (second_counts[category] / total)
        for category in categories
    )
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1.0 - expected)


def fleiss_kappa(ratings: Sequence[Sequence[int]]) -> float:
    """Fleiss' κ for ``n`` raters per item, given as per-category counts."""
    if not ratings:
        raise ValueError("need at least one item")
    n_raters = sum(ratings[0])
    if n_raters < 2:
        raise ValueError("Fleiss' kappa needs at least two ratings per item")
    for row in ratings:
        if len(row) != len(ratings[0]):
            raise ValueError("every item needs the same number of categories")
        if sum(row) != n_raters:
            raise ValueError("every item needs the same number of ratings")
    items = len(ratings)
    categories = len(ratings[0])
    agreement = [
        (sum(count * count for count in row) - n_raters) / (n_raters * (n_raters - 1))
        for row in ratings
    ]
    mean_agreement = sum(agreement) / items
    category_totals = [sum(row[j] for row in ratings) for j in range(categories)]
    expected = sum((total / (items * n_raters)) ** 2 for total in category_totals)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(mean_agreement, 1.0) else 0.0
    return (mean_agreement - expected) / (1.0 - expected)


def macro_f1(
    truth: Sequence[object], predicted: Sequence[object], *, labels: Sequence[object] | None = None
) -> float:
    """Unweighted mean of per-class F1. Classes absent from both lists are skipped."""
    if len(truth) != len(predicted):
        raise ValueError("truth and prediction must have equal length")
    if not truth:
        raise ValueError("need at least one item")
    classes = list(labels) if labels is not None else sorted(set(truth) | set(predicted), key=str)
    scores: list[float] = []
    for label in classes:
        true_positive = sum(1 for t, p in zip(truth, predicted, strict=False) if t == label and p == label)
        false_positive = sum(1 for t, p in zip(truth, predicted, strict=False) if t != label and p == label)
        false_negative = sum(1 for t, p in zip(truth, predicted, strict=False) if t == label and p != label)
        if true_positive + false_positive + false_negative == 0:
            continue
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        denominator = precision + recall
        scores.append(2 * precision * recall / denominator if denominator else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def mean_reciprocal_rank(
    rankings: Sequence[Sequence[str]], relevant: Sequence[set[str]]
) -> float:
    """MRR over ranked id lists. A query with no relevant hit contributes 0."""
    if len(rankings) != len(relevant):
        raise ValueError("rankings and relevance sets must align")
    if not rankings:
        raise ValueError("need at least one ranking")
    total = 0.0
    for ranking, wanted in zip(rankings, relevant, strict=False):
        for position, doc_id in enumerate(ranking, start=1):
            if doc_id in wanted:
                total += 1.0 / position
                break
    return total / len(rankings)


def ndcg_at_k(
    ranking: Sequence[str], grades: Mapping[str, float], *, k: int = 10
) -> float:
    """Graded NDCG with the 2^rel − 1 gain convention.

    Returns 0.0 when no document has a positive grade, and 1.0 when the ranking
    matches the ideal ordering, which makes it readable as "fraction of the
    achievable value that was realised".
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if not ranking:
        return 0.0

    def gain(grade: float) -> float:
        return float(2.0**grade - 1.0)

    dcg = 0.0
    for position, doc_id in enumerate(ranking[:k], start=1):
        dcg += gain(grades.get(doc_id, 0.0)) / math.log2(position + 1)

    ideal_ranked = sorted(grades.values(), reverse=True)[:k]
    idcg = 0.0
    for position, grade in enumerate(ideal_ranked, start=1):
        idcg += gain(grade) / math.log2(position + 1)
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k estimator for ``n`` samples with ``c`` correct.

    ``1 − C(n−c, k)/C(n, k)`` computed with exact integer binomials, so there is
    no floating-point cancellation for large ``n``.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= c <= n:
        raise ValueError("c must be within [0, n]")
    if k <= 0:
        raise ValueError("k must be positive")
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)
