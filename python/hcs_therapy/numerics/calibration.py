"""Calibration, confidence and abstention.

Sources
-------

* Expected Calibration Error — Naeini et al. (2015), popularised by Guo et al.,
  *On Calibration of Modern Neural Networks* (2017). Equal-mass bins, because
  equal-width bins collapse on a concentrated score distribution.
* Brier score — Brier (1950). Mean squared error of a probability forecast.
* Temperature scaling — Guo et al. (2017). One scalar T minimising NLL:
  ``p = σ(logit / T)``. T > 1 softens an over-confident model.
* Platt scaling — Platt (1999). ``p = σ(a·s + b)`` fitted by gradient descent.
* Split conformal prediction — Papadopoulos et al. (2002); Angelopoulos & Bates,
  *A Gentle Introduction to Conformal Prediction* (2023). Take the
  ⌈(n+1)(1−α)⌉-th smallest nonconformity score as the threshold; the abstention
  rule then has a **finite-sample** marginal coverage guarantee, with no
  distributional assumption beyond exchangeability.

Why abstention matters for this product: a wellbeing assistant that says
"ich bin hier nicht sicher" is useful. One that guesses confidently is harmful.
Conformal prediction is the mechanism that turns "confidence" into a decision
with a guarantee attached.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

__all__ = [
    "apply_platt",
    "apply_temperature",
    "brier_score",
    "conformal_coverage",
    "conformal_threshold",
    "expected_calibration_error",
    "fit_platt",
    "fit_temperature",
    "negative_log_likelihood",
    "reliability_curve",
    "should_abstain",
]

_EPS = 1e-12


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp = math.exp(value)
    return exp / (1.0 + exp)


def _logit(probability: float) -> float:
    clipped = min(max(probability, _EPS), 1.0 - _EPS)
    return math.log(clipped / (1.0 - clipped))


def _validate(probabilities: Sequence[float], labels: Sequence[int]) -> tuple[list[float], list[int]]:
    probs = [float(p) for p in probabilities]
    labs = [int(label) for label in labels]
    if len(probs) != len(labs):
        raise ValueError("probabilities and labels must have equal length")
    if not probs:
        raise ValueError("need at least one example")
    for value in probs:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"probability out of range: {value}")
    for label in labs:
        if label not in (0, 1):
            raise ValueError("labels must be 0 or 1")
    return probs, labs


def brier_score(probabilities: Sequence[float], labels: Sequence[int]) -> float:
    """Mean squared error of the forecast. Lower is better; 0.25 is a coin flip."""
    probs, labs = _validate(probabilities, labels)
    return sum((p - y) ** 2 for p, y in zip(probs, labs, strict=False)) / len(probs)


def negative_log_likelihood(
    probabilities: Sequence[float], labels: Sequence[int], *, eps: float = _EPS
) -> float:
    probs, labs = _validate(probabilities, labels)
    total = 0.0
    for p, y in zip(probs, labs, strict=False):
        clipped = min(max(p, eps), 1.0 - eps)
        total += -math.log(clipped) if y == 1 else -math.log(1.0 - clipped)
    return total / len(probs)


def reliability_curve(
    probabilities: Sequence[float], labels: Sequence[int], *, bins: int = 10
) -> list[dict[str, float]]:
    """Equal-mass reliability bins, returned as data so the UI can draw them."""
    probs, labs = _validate(probabilities, labels)
    if bins <= 0:
        raise ValueError("bins must be positive")
    order = sorted(range(len(probs)), key=lambda index: probs[index])
    size = len(order)
    curve: list[dict[str, float]] = []
    bin_size = max(1, math.ceil(size / bins))
    for start in range(0, size, bin_size):
        chunk = order[start : start + bin_size]
        if not chunk:
            continue
        confidence = sum(probs[i] for i in chunk) / len(chunk)
        accuracy = sum(labs[i] for i in chunk) / len(chunk)
        curve.append(
            {
                "count": float(len(chunk)),
                "confidence": confidence,
                "accuracy": accuracy,
                "gap": abs(accuracy - confidence),
            }
        )
    return curve


def expected_calibration_error(
    probabilities: Sequence[float], labels: Sequence[int], *, bins: int = 10
) -> float:
    """ECE = Σ_b (n_b / n) · |acc_b − conf_b| over equal-mass bins."""
    probs, _ = _validate(probabilities, labels)
    curve = reliability_curve(probs, labels, bins=bins)
    total = 0.0
    for bucket in curve:
        weight = bucket["count"] / len(probs)
        total += weight * bucket["gap"]
    return total


def apply_temperature(logits: Sequence[float], temperature: float) -> list[float]:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    return [_sigmoid(float(value) / temperature) for value in logits]


def fit_temperature(logits: Sequence[float], labels: Sequence[int]) -> float:
    """Fit T by minimising NLL. Coarse log-grid, then golden-section refine.

    Deterministic and dependency-free on purpose: an optimiser that needs scipy
    is an optimiser that silently changes behaviour between environments. The
    objective is unimodal in log T for a one-parameter temperature, so the grid
    plus a bounded refine is sufficient and reproducible.
    """
    values = [float(v) for v in logits]
    labs = [int(label) for label in labels]
    if len(values) != len(labs):
        raise ValueError("logits and labels must have equal length")
    if not values:
        raise ValueError("need at least one example")
    if len(set(labs)) == 1:
        # Degenerate: one class only, NLL is minimised by driving T to an
        # extreme, which is not a calibration estimate. Refuse to pretend.
        return 1.0

    def objective(temperature: float) -> float:
        probs = apply_temperature(values, temperature)
        return negative_log_likelihood(probs, labs)

    import numpy as np

    grid = np.exp(np.linspace(math.log(0.05), math.log(20.0), 200))
    scored = [(objective(float(t)), float(t)) for t in grid]
    best_value, best_t = min(scored)

    # Golden-section refinement around the best grid point.
    index = [t for _, t in scored].index(best_t)
    low = float(grid[max(index - 1, 0)])
    high = float(grid[min(index + 1, len(grid) - 1)])
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    for _ in range(60):
        if high - low < 1e-6:
            break
        left = high - inv_phi * (high - low)
        right = low + inv_phi * (high - low)
        if objective(left) < objective(right):
            high = right
        else:
            low = left
    refined = (low + high) / 2.0
    refined_value = objective(refined)
    return round(refined if refined_value <= best_value else best_t, 6)


def fit_platt(
    scores: Sequence[float], labels: Sequence[int], *, iterations: int = 2000, rate: float = 0.1
) -> tuple[float, float]:
    """Fit ``p = σ(a·s + b)`` by full-batch gradient descent on NLL.

    Scores are standardised first so one learning rate works for raw logits and
    for [0, 1] probabilities alike; the returned ``a``/``b`` are already mapped
    back to the original scale.
    """
    values = [float(v) for v in scores]
    labs = [int(label) for label in labels]
    if len(values) != len(labs):
        raise ValueError("scores and labels must have equal length")
    if not values:
        raise ValueError("need at least one example")
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    scale = math.sqrt(variance) or 1.0
    standardised = [(v - mean) / scale for v in values]
    if len(set(labs)) == 1:
        return (0.0, _logit(sum(labs) / len(labs)))

    a, b = 1.0, 0.0
    n = len(values)
    for _ in range(iterations):
        grad_a = 0.0
        grad_b = 0.0
        for x, y in zip(standardised, labs, strict=False):
            p = _sigmoid(a * x + b)
            error = p - y
            grad_a += error * x
            grad_b += error
        a -= rate * grad_a / n
        b -= rate * grad_b / n
    return (a / scale, b - a * mean / scale)


def apply_platt(scores: Sequence[float], a: float, b: float) -> list[float]:
    return [_sigmoid(a * float(value) + b) for value in scores]


def conformal_threshold(confidences: Sequence[float], *, alpha: float = 0.1) -> float:
    """Split-conformal confidence threshold.

    ``confidences`` are the model's probability that its answer is acceptable,
    measured on a held-out calibration set. A new answer is accepted when its
    confidence is at least the returned threshold, and otherwise the assistant
    abstains. The guarantee: P(accepted | answer is acceptable) ≥ 1 − α in the
    exchangeable case — which is why the calibration set must not be the
    evaluation set.
    """
    values = sorted(float(v) for v in confidences)
    if not values:
        raise ValueError("need at least one calibration score")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be within (0, 1)")
    n = len(values)
    rank = math.ceil((n + 1) * (1.0 - alpha))
    if rank > n:
        # Not enough calibration data for this alpha: never accept. Failing
        # closed is the only defensible choice for a safety-relevant gate.
        return float("inf")
    # Nonconformity is 1 − confidence, so its ascending order is the reverse of
    # the confidence order: the rank-th smallest nonconformity is the
    # (n − rank)-th smallest confidence.
    return 1.0 - values[n - rank]


def should_abstain(confidence: float, threshold: float) -> bool:
    """``threshold`` is the nonconformity cutoff returned above."""
    return (1.0 - float(confidence)) > threshold


def conformal_coverage(
    calibration: Sequence[float], test: Sequence[float], *, alpha: float = 0.1
) -> float:
    """Empirical acceptance rate on ``test`` for the threshold fitted on ``calibration``."""
    threshold = conformal_threshold(calibration, alpha=alpha)
    values = [float(value) for value in test]
    if not values:
        return 0.0
    accepted = sum(1 for value in values if not should_abstain(value, threshold))
    return accepted / len(values)
