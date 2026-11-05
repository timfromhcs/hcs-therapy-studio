"""Numerics: retrieval primitives.

Each test anchors on a hand-computed or analytically known value rather than on
the implementation's own output.
"""

from __future__ import annotations

import math

import pytest

from hcs_therapy.numerics.retrieval import (
    BM25Index,
    dedupe,
    fold_umlauts,
    maximal_marginal_relevance,
    reciprocal_rank_fusion,
    tokenize,
    trigrams,
)


def test_tokenize_folds_umlauts_and_keeps_digits() -> None:
    assert tokenize("Ängste und Sorgen 2026") == ["aengste", "und", "sorgen", "2026"]


def test_fold_umlauts_covers_sharp_s() -> None:
    assert fold_umlauts("Straße") == "strasse"


def test_tokenize_drops_single_letters_by_default() -> None:
    assert tokenize("a b cde") == ["cde"]
    assert tokenize("a b cde", min_length=1) == ["a", "b", "cde"]


def test_trigrams_share_inner_grams_across_compounds() -> None:
    """The reason a trigram scorer is fused with word BM25 at all.

    Boundary n-grams differ by construction (``#an`` vs ``#ve``); the *inner*
    grams are what let "Angst" match inside "Versagensangst".
    """
    compound = trigrams("Versagensangst")
    stem = trigrams("Angst")
    shared = set(stem) & set(compound)
    assert shared == {"ang", "ngs", "gst", "st#"}
    # And the word-level tokeniser cannot do this at all:
    assert set(tokenize("Versagensangst")) & set(tokenize("Angst")) == set()


def test_bm25_idf_is_always_positive_on_a_tiny_corpus() -> None:
    """The 1+ form of IDF cannot go negative; the classic form does at N=3."""
    index = BM25Index({"a": "angst angst", "b": "angst", "c": "angst"})
    assert index.idf("angst") > 0


def test_bm25_ranks_the_concentrated_document_first() -> None:
    index = BM25Index(
        {
            "focused": "panikattacke nachts herzrasen",
            "diluted": "heute war ein ruhiger tag mit spaziergang und kaffee und panikattacke",
            "other": "einkaufsliste milch brot kaese",
        }
    )
    ranked = index.search("panikattacke")
    assert [hit.doc_id for hit in ranked] == ["focused", "diluted"]


def test_bm25_score_matches_the_formula_by_hand() -> None:
    """N=2, one document contains the term twice, the other once.

    avgdl = (2 + 1) / 2 = 1.5. For the length-2 document:
      length_norm = 1.5 * (1 - 0.75 + 0.75 * 2/1.5) = 1.5 * (0.25 + 1.0) = 1.875
      tf part     = 2 * 2.5 / (2 + 1.875) = 5 / 3.875
      idf         = ln(1 + (2 - 2 + 0.5) / (2 + 0.5)) = ln(1.2)
    """
    index = BM25Index({"long": "angst angst", "short": "angst"}, k1=1.5, b=0.75)
    expected = math.log(1.2) * (2 * 2.5) / (2 + 1.875)
    hit = next(s for s in index.score("angst") if s.doc_id == "long")
    assert hit.score == pytest.approx(expected, rel=1e-12)


def test_bm25_b_zero_disables_length_normalisation() -> None:
    index = BM25Index({"long": "angst " * 10, "short": "angst"}, b=0.0)
    scores = {hit.doc_id: hit.score for hit in index.score("angst")}
    # With b=0 the only difference left is term frequency.
    assert scores["long"] > scores["short"]


def test_bm25_empty_query_and_empty_corpus() -> None:
    index = BM25Index({"a": "angst"})
    assert index.search("") == []
    assert index.search("   ") == []
    empty = BM25Index({})
    assert empty.search("angst") == []
    assert empty.idf("angst") == 0.0


def test_bm25_rejects_impossible_parameters() -> None:
    with pytest.raises(ValueError):
        BM25Index({"a": "x"}, k1=-1)
    with pytest.raises(ValueError):
        BM25Index({"a": "x"}, b=1.5)


def test_rrf_matches_hand_computation() -> None:
    """k=60: rank 2 contributes 1/62, rank 3 contributes 1/63."""
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "c"]], k=60)
    scores = {hit.doc_id: hit.score for hit in fused}
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["a"] == pytest.approx(1 / 61)
    assert scores["c"] == pytest.approx(1 / 62)
    assert [hit.doc_id for hit in fused] == ["b", "a", "c"]


def test_rrf_default_k_is_the_published_60() -> None:
    a = reciprocal_rank_fusion([["x"]])
    b = reciprocal_rank_fusion([["x"]], k=60)
    assert a[0].score == b[0].score == pytest.approx(1 / 61)


def test_rrf_weights_scale_contributions() -> None:
    fused = reciprocal_rank_fusion([["a"], ["b"]], weights=[2.0, 1.0])
    scores = {hit.doc_id: hit.score for hit in fused}
    assert scores["a"] == pytest.approx(2.0 / 61)
    assert scores["b"] == pytest.approx(1.0 / 61)


def test_rrf_rejects_bad_k_and_mismatched_weights() -> None:
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=0)
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"], ["b"]], weights=[1.0])


def test_rrf_is_order_stable_on_ties() -> None:
    fused = reciprocal_rank_fusion([["b"], ["a"]])
    assert [hit.doc_id for hit in fused] == ["a", "b"]


def test_mmr_prefers_relevance_when_lambda_is_one() -> None:
    relevance = {"strong": 1.0, "weak": 0.2}
    chosen = maximal_marginal_relevance(
        relevance, lambda a, b: 1.0, lam=1.0, k=2
    )
    assert [c.doc_id for c in chosen] == ["strong", "weak"]


def test_mmr_suppresses_a_near_duplicate() -> None:
    """With lam=0.4 the second slot goes to the dissimilar document.

    Hand computation for the second round:
      a2: 0.4·0.98 − 0.6·1.0 = −0.208
      c : 0.4·0.50 − 0.6·0.0 =  0.200   → c wins
    """
    relevance = {"a": 1.0, "a2": 0.98, "c": 0.5}
    similarity = {"a|a2": 1.0, "a|c": 0.0, "a2|c": 0.0}

    chosen = maximal_marginal_relevance(
        relevance, lambda x, y: similarity["|".join(sorted((x, y)))], lam=0.4, k=2
    )
    assert [c.doc_id for c in chosen] == ["a", "c"]


def test_mmr_keeps_the_duplicate_when_lambda_favours_relevance() -> None:
    relevance = {"a": 1.0, "a2": 0.98, "c": 0.5}
    similarity = {"a|a2": 1.0, "a|c": 0.0, "a2|c": 0.0}

    chosen = maximal_marginal_relevance(
        relevance, lambda x, y: similarity["|".join(sorted((x, y)))], lam=1.0, k=2
    )
    assert [c.doc_id for c in chosen] == ["a", "a2"]


def test_mmr_validates_lambda_and_k() -> None:
    with pytest.raises(ValueError):
        maximal_marginal_relevance({"a": 1.0}, lambda x, y: 0.0, lam=1.5)
    assert maximal_marginal_relevance({"a": 1.0}, lambda x, y: 0.0, k=0) == []


def test_dedupe_drops_a_restatement() -> None:
    snippets = [
        "Panikattacken treten oft nachts auf und fühlen sich wie Herzrasen an.",
        "Panikattacken treten oft nachts auf und fühlen sich wie Herzrasen an!",
        "Ein Spaziergang an der frischen Luft hilft beim Runterkommen.",
    ]
    assert dedupe(snippets) == [0, 2]


def test_dedupe_keeps_everything_when_nothing_overlaps() -> None:
    snippets = ["eins zwei drei", "vier fünf sechs", "sieben acht neun"]
    assert dedupe(snippets) == [0, 1, 2]
