"""Lexical retrieval: BM25, reciprocal rank fusion, maximal marginal relevance.

Sources
-------

* BM25 — Robertson & Walker, *On Relevance Weights with Little Relevance
  Information* (1994); the Okapi variant used everywhere since:

      IDF(q)  = ln(1 + (N - n(q) + 0.5) / (n(q) + 0.5))
      score   = Σ_q IDF(q) · tf(q,D)·(k1+1) / (tf(q,D) + k1·(1 - b + b·|D|/avgdl))

* Reciprocal Rank Fusion — Cormack, Clarke & Büttcher, SIGIR 2009:

      RRF(d) = Σ_rankers 1 / (k + rank_r(d))        k = 60 by convention
      (benchmarks land in k ∈ [40, 80]; 60 is the published default)

* Maximal Marginal Relevance — Carbonell & Goldstein, SIGIR 1998:

      MMR = argmax_{d ∈ R\\S} [ λ·sim(d,q) − (1−λ)·max_{s∈S} sim(d,s) ]

Honest naming: this module is **lexical**. It is not a dense/vector retriever and
does not pretend to be. Two *real* scorers are fused — BM25 over words and BM25
over character trigrams — which is what makes the fusion meaningful for German
compound words ("Versagensangst" vs "Angst") without an embedding model.
"""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "BM25Index",
    "Scored",
    "dedupe",
    "fold_umlauts",
    "maximal_marginal_relevance",
    "reciprocal_rank_fusion",
    "tokenize",
    "trigrams",
]

# German text written on a phone keyboard, plus the "ss" convention that is
# standard in Swiss usage and common in informal writing.
_FOLDS = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def fold_umlauts(text: str) -> str:
    """Fold German umlauts so ``Angst`` and ``Ängste`` share a stem."""
    out = []
    for char in text.lower():
        out.append(_FOLDS.get(char, char))
    return "".join(out)


def tokenize(text: str, *, min_length: int = 2) -> list[str]:
    """Unicode-aware word tokeniser with light German folding.

    NFKC first (so ``ﬁ`` and composed umlauts agree), then keep letters and
    digits, then fold. No stemming: a bad stemmer is worse than none, and the
    trigram scorer absorbs the morphology anyway.
    """
    normalised = unicodedata.normalize("NFKC", text).lower()
    normalised = fold_umlauts(normalised)
    tokens: list[str] = []
    current: list[str] = []
    for char in normalised:
        if char.isalnum():
            current.append(char)
        elif current:
            token = "".join(current)
            if len(token) >= min_length:
                tokens.append(token)
            current = []
    if current:
        token = "".join(current)
        if len(token) >= min_length:
            tokens.append(token)
    return tokens


def trigrams(text: str, *, n: int = 3) -> list[str]:
    """Character n-grams with word boundaries.

    Boundary padding (``#wort#``) is what lets "Angst" match inside
    "Versagensangst": the inner trigrams are shared. That is the whole reason
    this scorer is fused with word BM25 instead of replacing it.
    """
    grams: list[str] = []
    for word in tokenize(text, min_length=1):
        padded = f"#{word}#"
        if len(padded) <= n:
            grams.append(padded)
            continue
        for index in range(len(padded) - n + 1):
            grams.append(padded[index : index + n])
    return grams


@dataclass(frozen=True)
class Scored:
    doc_id: str
    score: float

    def as_dict(self) -> dict[str, object]:
        return {"id": self.doc_id, "score": round(self.score, 6)}


class BM25Index:
    """Okapi BM25 over an in-memory corpus.

    ``k1`` controls term-frequency saturation, ``b`` the length normalisation.
    The published defaults (1.5, 0.75) are kept as defaults and exposed because
    short German chat messages and long journal entries want different ``b``.
    """

    def __init__(
        self,
        documents: Mapping[str, str] | Iterable[tuple[str, str]],
        *,
        k1: float = 1.5,
        b: float = 0.75,
        tokenizer: Callable[[str], list[str]] = tokenize,
    ) -> None:
        items = list(documents.items() if isinstance(documents, Mapping) else documents)
        if k1 < 0:
            raise ValueError("k1 must be >= 0")
        if not 0 <= b <= 1:
            raise ValueError("b must be within [0, 1]")
        self.k1 = float(k1)
        self.b = float(b)
        self._tokenizer = tokenizer
        self._ids: list[str] = []
        self._terms: list[Counter[str]] = []
        self._lengths: list[int] = []
        self._df: Counter[str] = Counter()
        for doc_id, text in items:
            terms = Counter(self._tokenizer(text))
            self._ids.append(doc_id)
            self._terms.append(terms)
            self._lengths.append(sum(terms.values()))
            self._df.update(terms.keys())
        self.n_docs = len(self._ids)
        total = sum(self._lengths)
        self.avg_length = (total / self.n_docs) if self.n_docs else 0.0

    # -- inspection --------------------------------------------------------
    @property
    def document_ids(self) -> list[str]:
        return list(self._ids)

    def idf(self, term: str) -> float:
        """Robertson/Sparck-Jones IDF, always positive.

        The ``1 +`` form is the one that cannot go negative on a small corpus,
        which matters here: a knowledge base of 12 journal entries would
        otherwise give a term that appears in 11 of them a negative weight and
        actively penalise the correct document.
        """
        if not self.n_docs:
            return 0.0
        df = self._df.get(term, 0)
        return math.log(1.0 + (self.n_docs - df + 0.5) / (df + 0.5))

    def score(self, query: str) -> list[Scored]:
        """Rank every document that shares at least one term with the query."""
        query_terms = self._tokenizer(query)
        if not query_terms or not self.n_docs:
            return []
        results: list[Scored] = []
        for index, terms in enumerate(self._terms):
            if not terms:
                continue
            length_norm = self.k1 * (
                1.0 - self.b + self.b * (self._lengths[index] / (self.avg_length or 1.0))
            )
            total = 0.0
            matched = False
            for term in query_terms:
                tf = terms.get(term, 0)
                if not tf:
                    continue
                matched = True
                total += self.idf(term) * (tf * (self.k1 + 1.0)) / (tf + length_norm)
            if matched and total > 0.0:
                results.append(Scored(self._ids[index], total))
        results.sort(key=lambda item: (-item.score, item.doc_id))
        return results

    def search(self, query: str, *, k: int = 5) -> list[Scored]:
        return self.score(query)[: max(k, 0)]


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]],
    *,
    k: int = 60,
    weights: Sequence[float] | None = None,
) -> list[Scored]:
    """Fuse ranked id lists by rank, never by raw score.

    Rank-based fusion is the correct choice here because BM25 over words and
    BM25 over trigrams produce scores on incomparable scales; normalising them
    would invent a calibration that does not exist.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights must match the number of rankings")
    totals: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights, strict=False):
        for rank, doc_id in enumerate(ranking, start=1):
            totals[doc_id] = totals.get(doc_id, 0.0) + weight / (k + rank)
    results = [Scored(doc_id, score) for doc_id, score in totals.items()]
    results.sort(key=lambda item: (-item.score, item.doc_id))
    return results


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    a, b = set(left), set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedupe(
    snippets: Sequence[str],
    *,
    threshold: float = 0.85,
    tokenizer: Callable[[str], list[str]] = tokenize,
) -> list[int]:
    """Return indices of snippets that are not near-duplicates of an earlier one.

    Retrieval over overlapping chunks returns the same paragraph twice; showing
    it twice wastes context and makes the assistant look confused.
    """
    kept: list[int] = []
    kept_tokens: list[list[str]] = []
    for index, snippet in enumerate(snippets):
        tokens = tokenizer(snippet)
        if any(_jaccard(tokens, other) >= threshold for other in kept_tokens):
            continue
        kept.append(index)
        kept_tokens.append(tokens)
    return kept


def maximal_marginal_relevance(
    relevance: Mapping[str, float],
    similarity: Callable[[str, str], float],
    *,
    lam: float = 0.7,
    k: int = 5,
) -> list[Scored]:
    """Greedy MMR selection.

    ``lam = 1.0`` is pure relevance; ``lam = 0.0`` is pure diversity. The
    default 0.7 favours relevance while still suppressing near-duplicates, which
    is the behaviour a citation list needs.
    """
    if not 0.0 <= lam <= 1.0:
        raise ValueError("lam must be within [0, 1]")
    if k <= 0:
        return []
    remaining = dict(relevance)
    selected: list[Scored] = []
    while remaining and len(selected) < k:
        best_id = ""
        best_value = -math.inf
        for doc_id, score in remaining.items():
            penalty = 0.0
            if selected:
                penalty = max(similarity(doc_id, chosen.doc_id) for chosen in selected)
            value = lam * score - (1.0 - lam) * penalty
            if value > best_value or (value == best_value and doc_id < best_id):
                best_value = value
                best_id = doc_id
        selected.append(Scored(best_id, best_value))
        remaining.pop(best_id, None)
    return selected
