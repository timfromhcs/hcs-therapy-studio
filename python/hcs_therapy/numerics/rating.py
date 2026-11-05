"""Ranking models and comparing them without lying about noise.

Sources
-------

* Bradley–Terry — Bradley & Terry (1952). ``P(i beats j) = p_i / (p_i + p_j)``,
  fitted by the MM algorithm of Hunter (2004):
  ``p_i ← W_i / Σ_{j≠i} n_ij / (p_i + p_j)``.
* Elo — Elo (1978). ``E_a = 1 / (1 + 10^((r_b − r_a)/400))``.
* Bootstrap — Efron (1979). Percentile intervals need no distributional
  assumption and are honest about small samples because they widen.
* Paired bootstrap — the standard way to ask "is this A/B difference real",
  resampling *per-item* differences rather than the two arms independently.

The rule this module enforces in the product: never report a difference between
two candidates without a sample size and an interval next to it.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence

import numpy as np

__all__ = [
    "bootstrap_ci",
    "bradley_terry",
    "elo_update",
    "expected_score",
    "paired_bootstrap_pvalue",
    "rank_from_matches",
]

_MIN_INTERVAL_N = 5


def _pair_counts(
    matches: Sequence[tuple[str, str]] | Mapping[tuple[str, str], int],
) -> tuple[list[str], dict[tuple[str, str], int]]:
    if isinstance(matches, Mapping):
        counts = {key: int(value) for key, value in matches.items() if int(value) > 0}
    else:
        counts: dict[tuple[str, str], int] = {}
        for winner, loser in matches:
            if winner == loser:
                raise ValueError("a player cannot beat itself")
            counts[(winner, loser)] = counts.get((winner, loser), 0) + 1
    players = sorted({name for pair in counts for name in pair})
    if not players:
        raise ValueError("no matches supplied")
    return players, counts


def bradley_terry(
    matches: Sequence[tuple[str, str]] | Mapping[tuple[str, str], int],
    *,
    max_iterations: int = 1000,
    tolerance: float = 1e-10,
) -> dict[str, float]:
    """Fit Bradley–Terry strengths, normalised to a geometric mean of 1.

    A player with no wins still gets a small positive strength rather than zero,
    because a zero makes every future comparison undefined; the MM update uses a
    floor of one pseudo-win for that reason.
    """
    players, counts = _pair_counts(matches)
    index = {name: position for position, name in enumerate(players)}
    size = len(players)
    wins = np.zeros(size, dtype=np.float64)
    games = np.zeros((size, size), dtype=np.float64)
    for (winner, loser), value in counts.items():
        wins[index[winner]] += value
        games[index[winner], index[loser]] += value
        games[index[loser], index[winner]] += value

    strength = np.ones(size, dtype=np.float64) / size
    for _ in range(max_iterations):
        denominator = np.zeros(size, dtype=np.float64)
        for i in range(size):
            for j in range(size):
                if i == j or games[i, j] == 0:
                    continue
                denominator[i] += games[i, j] / max(strength[i] + strength[j], 1e-12)
        updated = np.where(denominator > 0, np.maximum(wins, 1e-9) / np.maximum(denominator, 1e-12), strength)
        # Normalise by geometric mean: the likelihood is invariant to a common
        # scale, so the constraint only removes an unidentifiable degree of freedom.
        geometric = math.exp(float(np.mean(np.log(np.maximum(updated, 1e-300)))))
        updated = updated / geometric
        if float(np.max(np.abs(updated - strength))) < tolerance:
            strength = updated
            break
        strength = updated
    return {name: float(strength[index[name]]) for name in players}


def rank_from_matches(
    matches: Sequence[tuple[str, str]] | Mapping[tuple[str, str], int],
) -> list[tuple[str, float]]:
    """Convenience: strengths sorted strongest first."""
    strengths = bradley_terry(matches)
    ordered = sorted(strengths.items(), key=lambda item: (-item[1], item[0]))
    return ordered


def expected_score(rating_a: float, rating_b: float) -> float:
    """Elo expectation that ``a`` beats ``b``."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def elo_update(
    rating_a: float, rating_b: float, score_a: float, *, k: float = 32.0
) -> tuple[float, float]:
    """Online Elo update. ``score_a`` is 1 for a win, 0.5 a draw, 0 a loss."""
    if score_a not in (0.0, 0.5, 1.0):
        raise ValueError("score_a must be 0, 0.5 or 1")
    if k <= 0:
        raise ValueError("k must be positive")
    expected = expected_score(rating_a, rating_b)
    delta = k * (score_a - expected)
    return (rating_a + delta, rating_b - delta)


def bootstrap_ci(
    values: Sequence[float],
    *,
    statistic: Callable[[np.ndarray], float] = lambda sample: float(np.mean(sample)),
    resamples: int = 1000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float] | None:
    """Percentile bootstrap interval.

    Returns ``None`` below five observations. A bootstrap interval over three
    points is a decoration that invites a false conclusion, so the product shows
    "n too small" instead.
    """
    data = np.asarray(list(values), dtype=np.float64)
    if data.size == 0:
        raise ValueError("need at least one value")
    if data.size < _MIN_INTERVAL_N:
        return None
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be within (0, 1)")
    generator = np.random.default_rng(seed)
    indices = generator.integers(0, data.size, size=(resamples, data.size))
    samples = data[indices]
    statistics = np.apply_along_axis(statistic, 1, samples)
    lower = float(np.quantile(statistics, alpha / 2.0))
    upper = float(np.quantile(statistics, 1.0 - alpha / 2.0))
    return (lower, upper)


def paired_bootstrap_pvalue(
    candidate: Sequence[float],
    baseline: Sequence[float],
    *,
    resamples: int = 2000,
    seed: int = 0,
) -> float:
    """Two-sided paired bootstrap p-value for ``mean(candidate) − mean(baseline)``.

    Pairs must be aligned (same item, same prompt). One-sided resampling of the
    difference is what makes this a *paired* test; resampling each arm
    separately would throw away the correlation and overstate the p-value.
    """
    a = np.asarray(list(candidate), dtype=np.float64)
    b = np.asarray(list(baseline), dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("paired samples must have equal length")
    if a.size == 0:
        raise ValueError("need at least one pair")
    differences = a - b
    observed = float(differences.mean())
    if np.allclose(differences, 0.0):
        return 1.0
    generator = np.random.default_rng(seed)
    indices = generator.integers(0, differences.size, size=(resamples, differences.size))
    means = differences[indices].mean(axis=1)
    # Centre under the null, then count how often the resampled mean is at least
    # as extreme as the observed one.
    centred = means - observed
    extreme = np.abs(centred) >= abs(observed)
    return float((np.count_nonzero(extreme) + 1) / (resamples + 1))
