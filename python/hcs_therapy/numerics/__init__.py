"""Small, pure, testable numerics that the rest of the project reasons with.

Why this package exists
-----------------------

The project makes claims about retrieval quality, quantisation size, KV-cache
footprint, calibration and preference optimisation. A claim without an
implementation that can be run and checked is a guess. Every module here is:

* **pure** — no network, no model, no GPU, no global state;
* **deterministic** — seeded where randomness is involved;
* **anchored to a published formula** — each module names its source, and each
  test compares against an analytically known value rather than against the
  implementation's own output.

Nothing in this package is trained, sampled from a model, or downloaded.
"""

from __future__ import annotations

from .retrieval import (
    BM25Index,
    Scored,
    dedupe,
    maximal_marginal_relevance,
    reciprocal_rank_fusion,
    tokenize,
    trigrams,
)
from .sampling import (
    SamplingConfig,
    entropy,
    perplexity,
    sample_token,
    transform_logits,
)

__all__ = [
    "BM25Index",
    "SamplingConfig",
    "Scored",
    "dedupe",
    "entropy",
    "maximal_marginal_relevance",
    "perplexity",
    "reciprocal_rank_fusion",
    "sample_token",
    "tokenize",
    "transform_logits",
    "trigrams",
]
