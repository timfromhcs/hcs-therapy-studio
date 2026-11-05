"""Weight-space merging arithmetic on plain arrays.

Sources
-------

* Task vectors — Ilharco et al. (2022): ``τ = θ_finetuned − θ_base``.
* SLERP — Shoemake (1985). Spherical linear interpolation on the unit sphere:
  ``sin((1−t)Ω)/sinΩ · a + sin(tΩ)/sinΩ · b`` with ``Ω = arccos(â·b̂)``.
* TIES-Merging — Yadav et al., NeurIPS 2023: trim to the top-``k``% magnitudes,
  elect one sign per coordinate by summed magnitude, then average only the
  values that agree with the elected sign (disjoint mean).
* DARE — Yu et al. (2024): randomly drop delta parameters with probability
  ``p`` and rescale the survivors by ``1/(1−p)``, which preserves the expected
  value while removing redundancy.

Everything here is element-wise and numpy-only, so it can be unit-tested against
hand-computed vectors without loading a model. The product never merges weights
it has not hashed: see ``AGENTS.md`` §6.7.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

__all__ = [
    "dare_merge",
    "linear_merge",
    "slerp",
    "task_vector",
    "ties_merge",
]


def _flat(array: np.ndarray) -> np.ndarray:
    return np.asarray(array, dtype=np.float64).reshape(-1)


def slerp(a: np.ndarray, b: np.ndarray, t: float, *, eps: float = 1e-8) -> np.ndarray:
    """Spherical interpolation between two arrays.

    ``t = 0`` returns ``a`` and ``t = 1`` returns ``b`` exactly, which is the
    property the test suite asserts. Nearly parallel vectors fall back to linear
    interpolation because ``sin Ω`` in the denominator collapses; nearly
    anti-parallel vectors have no unique geodesic, so a linear blend is returned
    instead of a numerical explosion.
    """
    if not 0.0 <= t <= 1.0:
        raise ValueError("t must be within [0, 1]")
    left = _flat(a)
    right = _flat(b)
    if left.shape != right.shape:
        raise ValueError("arrays must have the same shape")
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm < eps or right_norm < eps:
        return ((1.0 - t) * left + t * right).reshape(np.shape(a))
    cosine = float(np.dot(left, right) / (left_norm * right_norm))
    cosine = max(-1.0, min(1.0, cosine))
    if cosine > 1.0 - eps:
        return ((1.0 - t) * left + t * right).reshape(np.shape(a))
    if cosine < -1.0 + eps:
        return ((1.0 - t) * left + t * right).reshape(np.shape(a))
    omega = float(np.arccos(cosine))
    sin_omega = float(np.sin(omega))
    blend = (
        np.sin((1.0 - t) * omega) / sin_omega * left
        + np.sin(t * omega) / sin_omega * right
    )
    return blend.reshape(np.shape(a))


def task_vector(base: np.ndarray, finetuned: np.ndarray) -> np.ndarray:
    """``τ = θ_ft − θ_base``. Shape mismatch is an error, never a broadcast."""
    left = _flat(base)
    right = _flat(finetuned)
    if left.shape != right.shape:
        raise ValueError("base and finetuned must have the same shape")
    return (right - left).reshape(np.shape(base))


def linear_merge(deltas: Sequence[np.ndarray], weights: Sequence[float] | None = None) -> np.ndarray:
    """Weighted mean of task vectors."""
    if not deltas:
        raise ValueError("need at least one task vector")
    arrays = [_flat(delta) for delta in deltas]
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("all task vectors must have the same shape")
    if weights is None:
        weights = [1.0] * len(arrays)
    if len(weights) != len(arrays):
        raise ValueError("weights must match the number of task vectors")
    stacked = np.vstack(arrays)
    total = float(np.sum(np.abs(weights)))
    if total == 0:
        raise ValueError("weights must not sum to zero")
    blended = np.tensordot(np.asarray(weights, dtype=np.float64), stacked, axes=1) / total
    return blended.reshape(np.shape(deltas[0]))


def ties_merge(
    deltas: Sequence[np.ndarray], *, density: float = 0.2, weights: Sequence[float] | None = None
) -> np.ndarray:
    """TIES: trim, elect sign, disjoint mean.

    ``density`` is the fraction of each task vector kept per coordinate after
    trimming. 0.2 is the value from the paper's default recipe; it keeps the
    largest 20 % of magnitudes, which is what removes the interference between
    independently trained adapters.
    """
    if not deltas:
        raise ValueError("need at least one task vector")
    if not 0.0 < density <= 1.0:
        raise ValueError("density must be within (0, 1]")
    arrays = [_flat(delta) for delta in deltas]
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("all task vectors must have the same shape")
    if weights is None:
        weights = [1.0] * len(arrays)
    if len(weights) != len(arrays):
        raise ValueError("weights must match the number of task vectors")

    stacked = np.vstack(arrays)
    magnitudes = np.abs(stacked)
    trimmed = np.zeros_like(stacked)
    for row in range(stacked.shape[0]):
        if density >= 1.0:
            trimmed[row] = stacked[row]
            continue
        threshold = np.quantile(magnitudes[row], 1.0 - density)
        keep = magnitudes[row] >= threshold
        trimmed[row] = np.where(keep, stacked[row], 0.0)

    # Sign election: weighted mass per coordinate, ties resolved by the largest
    # single magnitude so the result is deterministic.
    weight_array = np.asarray(weights, dtype=np.float64)[:, None]
    mass = np.sum(trimmed * weight_array, axis=0)
    elected = np.sign(mass)
    dominant = np.argmax(magnitudes * weight_array, axis=0)
    fallback = np.sign(stacked[dominant, np.arange(stacked.shape[1])])
    elected = np.where(elected == 0, fallback, elected)

    agrees = np.sign(trimmed) == elected
    signed = np.where(agrees, trimmed * weight_array, 0.0)
    counts = np.count_nonzero(agrees, axis=0)
    merged = np.where(counts > 0, np.sum(signed, axis=0) / np.maximum(counts, 1), 0.0)
    return merged.reshape(np.shape(deltas[0]))


def dare_merge(
    deltas: Sequence[np.ndarray],
    *,
    drop_rate: float = 0.9,
    seed: int = 0,
    weights: Sequence[float] | None = None,
) -> np.ndarray:
    """DARE: drop, rescale, then linearly merge.

    Each element survives with probability ``1 − drop_rate`` and is divided by
    ``1 − drop_rate``, so the expectation of the merged vector is unchanged
    while the variance of the interference term drops.
    """
    if not deltas:
        raise ValueError("need at least one task vector")
    if not 0.0 <= drop_rate < 1.0:
        raise ValueError("drop_rate must be within [0, 1)")
    generator = np.random.default_rng(seed)
    pruned: list[np.ndarray] = []
    for delta in deltas:
        array = _flat(delta)
        if drop_rate == 0.0:
            pruned.append(array)
            continue
        keep = generator.random(array.shape) >= drop_rate
        pruned.append(np.where(keep, array, 0.0) / (1.0 - drop_rate))
    return linear_merge(pruned, weights)
