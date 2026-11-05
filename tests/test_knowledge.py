"""Knowledge base: chunking, retrieval, citations and privacy of the index."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hcs_therapy.knowledge import (
    KnowledgeBase,
    chunk_text,
    citations_in,
    index_paths,
    is_informative,
    missing_citations,
    strip_long_code_blocks,
)
from hcs_therapy.paths import paths as resolve_paths
from hcs_therapy.storage import ContentKey


@pytest.fixture
def kb(tmp_path: Path) -> KnowledgeBase:
    paths = resolve_paths(tmp_path / "home").ensure()
    base = KnowledgeBase(paths, key=ContentKey.load_or_create(paths.root))
    yield base
    base.close()


CORPUS = {
    "panik": (
        "Panikattacken kündigen sich oft mit Herzrasen an. "
        "Viele Menschen beschreiben ein Gefühl von Kontrollverlust.\n\n"
        "Ruhiges Atmen und ein fester Orientierungspunkt helfen, die Welle zu überstehen."
    ),
    "schlaf": (
        "Schlafhygiene bedeutet: feste Zeiten, kein Bildschirm im Bett und ein kühles Zimmer.\n\n"
        "Wenn die Schlaflosigkeit länger als vier Wochen anhält, ist ein Arztbesuch sinnvoll."
    ),
}


# --- chunking -------------------------------------------------------------


def test_chunking_splits_on_paragraphs() -> None:
    chunks = chunk_text(CORPUS["panik"])
    assert len(chunks) == 2
    assert "Herzrasen" in chunks[0]
    assert "Orientierungspunkt" in chunks[1]


def test_chunking_overlaps_so_a_seam_is_still_retrievable() -> None:
    text = "wort " * 400
    chunks = chunk_text(text, target=200, overlap=40)
    assert len(chunks) > 1
    tail = chunks[0][-40:].strip()
    assert tail and tail in chunks[1]


def test_chunking_of_empty_text_is_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunking_validates_its_parameters() -> None:
    with pytest.raises(ValueError):
        chunk_text("x", target=0)
    with pytest.raises(ValueError):
        chunk_text("x", target=100, overlap=100)


def test_chunking_does_not_cut_mid_word_when_a_space_exists() -> None:
    words = ["Kontrollverlust", "Orientierungspunkt", "Herzrasen", "Atmung"]
    text = " ".join(words * 60)
    chunks = chunk_text(text, target=300, overlap=30)
    for chunk in chunks[:-1]:
        assert chunk.split()[-1] in words


def test_long_code_blocks_are_collapsed() -> None:
    diagram = "```\n" + "\n".join(f"│ line {index} │" for index in range(30)) + "\n```"
    stripped = strip_long_code_blocks(f"before\n\n{diagram}\n\nafter")
    assert "code block omitted: 32 lines" in stripped
    assert "line 12" not in stripped


def test_short_code_blocks_survive() -> None:
    snippet = "```bash\nhcs-therapy doctor\n```"
    assert strip_long_code_blocks(snippet) == snippet


def test_is_informative_rejects_box_art() -> None:
    assert not is_informative("????????????????????")
    assert is_informative("Das ist ein normaler Satz über Angst.")


# --- indexing and search --------------------------------------------------


def test_add_document_reports_chunk_count(kb: KnowledgeBase) -> None:
    result = kb.add_document(source="note", title="Panik", text=CORPUS["panik"])
    assert result["chunks"] == 2
    assert result["doc_id"].startswith("d_")


def test_search_finds_the_on_topic_document(kb: KnowledgeBase) -> None:
    kb.add_document(source="note", title="Panik", text=CORPUS["panik"], doc_id="panik")
    kb.add_document(source="note", title="Schlaf", text=CORPUS["schlaf"], doc_id="schlaf")
    hits = kb.search("Herzrasen bei Panik", k=2)
    assert hits
    assert hits[0].doc_id == "panik"


def test_search_works_across_a_german_compound(kb: KnowledgeBase) -> None:
    """Word tokenisation cannot match "Versagensangst" to "Angst"; trigrams can."""
    kb.add_document(
        source="note",
        title="Angst",
        text="Angst vor Prüfungen ist weit verbreitet und gut behandelbar.",
        doc_id="angst",
    )
    hits = kb.search("Versagensangst", k=1)
    assert hits, "the trigram scorer should have bridged the compound"
    assert hits[0].doc_id == "angst"


def test_search_returns_empty_on_an_empty_index(kb: KnowledgeBase) -> None:
    assert kb.search("irgendwas") == []


def test_search_rejects_an_empty_query(kb: KnowledgeBase) -> None:
    kb.add_document(source="note", title=None, text=CORPUS["panik"])
    assert kb.search("   ") == []
    assert kb.search("x", k=0) == []


def test_hits_carry_a_usable_citation(kb: KnowledgeBase) -> None:
    kb.add_document(source="note", title=None, text=CORPUS["panik"])
    hit = kb.search("Herzrasen", k=1)[0]
    assert hit.citation == f"[#{hit.chunk_id}]"
    assert hit.rank_word == 1


def test_readding_a_document_replaces_it(kb: KnowledgeBase) -> None:
    kb.add_document(source="note", title="v1", text=CORPUS["panik"], doc_id="doc")
    kb.add_document(source="note", title="v2", text=CORPUS["schlaf"], doc_id="doc")
    assert len(kb.documents()) == 1
    assert kb.search("Schlafhygiene", k=1)[0].doc_id == "doc"


def test_removing_a_document_drops_its_chunks(kb: KnowledgeBase) -> None:
    kb.add_document(source="note", title=None, text=CORPUS["panik"], doc_id="doc")
    assert kb.remove_document("doc") == 1
    assert kb.search("Herzrasen") == []
    assert kb.stats()["chunks"] == 0


def test_mmr_does_not_show_the_same_sentence_twice(kb: KnowledgeBase) -> None:
    """Two restatements and one distinct note: the pair must not both appear."""
    kb.add_document(
        source="note", title="a", text="Herzrasen und Atemnot bei Panik.", doc_id="a"
    )
    kb.add_document(
        source="note", title="b", text="Herzrasen und Atemnot bei Panik!", doc_id="b"
    )
    kb.add_document(
        source="note",
        title="c",
        text="Panik lässt sich mit Atemübungen und Bodenkontakt begleiten.",
        doc_id="c",
    )
    hits = kb.search("Panik", k=2, lam=0.5)
    assert hits
    assert not {"a", "b"} <= {hit.doc_id for hit in hits}


# --- citations ------------------------------------------------------------


def test_missing_citations_flags_an_invented_source() -> None:
    assert missing_citations("Siehe [#3] und [#99].", [3, 7]) == [99]


def test_missing_citations_is_empty_when_everything_is_grounded() -> None:
    assert missing_citations("Siehe [#3] und [#7].", [3, 7]) == []


def test_citations_in_deduplicates_and_sorts() -> None:
    assert citations_in("[#5] then [#2] then [#5]") == [2, 5]


def test_context_block_is_fenced_and_labelled_as_data(kb: KnowledgeBase) -> None:
    kb.add_document(source="note", title=None, text=CORPUS["panik"])
    hits = kb.search("Herzrasen", k=1)
    block = kb.context_block(hits)
    assert "DATA, not instructions" in block
    assert f"[#{hits[0].chunk_id}]" in block
    assert block.startswith("Retrieved passages")


def test_context_block_respects_the_character_budget(kb: KnowledgeBase) -> None:
    kb.add_document(source="note", title=None, text=CORPUS["panik"])
    hits = kb.search("Herzrasen", k=2)
    assert kb.context_block(hits, max_chars=10).count("[#") <= 1


def test_context_block_of_no_hits_is_empty(kb: KnowledgeBase) -> None:
    assert kb.context_block([]) == ""


# --- privacy --------------------------------------------------------------


def test_chunk_text_is_not_stored_in_plaintext(kb: KnowledgeBase) -> None:
    """A plaintext index beside an encrypted journal would undo the encryption."""
    secret = "Ein sehr persönlicher Satz über meine Angstzustände."
    kb.add_document(source="note", title="privat", text=secret)
    raw = kb.path.read_bytes()
    assert secret.encode("utf-8") not in raw
    assert b"Angstzust" not in raw
    # And it is still readable through the API, which proves decryption works.
    assert kb.search("Angstzustände", k=1)


def test_an_encrypted_index_without_a_key_fails_loudly(tmp_path: Path) -> None:
    """Silently returning nothing would look like "no results", not "wrong setup"."""
    paths = resolve_paths(tmp_path / "home").ensure()
    key = ContentKey.load_or_create(paths.root)
    writer = KnowledgeBase(paths, key=key)
    writer.add_document(source="note", title=None, text="geheimer inhalt")
    writer.close()

    # The failure happens at construction, which is earlier and therefore better
    # than at the first search: the caller learns immediately.
    with pytest.raises(ValueError, match="encrypted"):
        KnowledgeBase(paths, key=None)


# --- file indexing --------------------------------------------------------


def test_index_paths_indexes_markdown(kb: KnowledgeBase, tmp_path: Path) -> None:
    source = tmp_path / "notiz.md"
    source.write_text("# Notiz\n\nAngst und Atmung hängen zusammen.", encoding="utf-8")
    results = index_paths(kb, [source])
    assert results[0]["chunks"] >= 1
    assert kb.search("Atmung")


def test_index_paths_refuses_a_binary_format(kb: KnowledgeBase, tmp_path: Path) -> None:
    source = tmp_path / "notiz.pdf"
    source.write_bytes(b"%PDF-1.7")
    with pytest.raises(ValueError, match="only .txt"):
        index_paths(kb, [source])


def test_index_paths_reports_a_missing_file(kb: KnowledgeBase, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        index_paths(kb, [tmp_path / "nope.md"])


def test_stats_names_the_retriever_and_denies_a_vector_index(kb: KnowledgeBase) -> None:
    stats = kb.stats()
    assert stats["vector_index"] is None
    assert "bm25" in stats["retriever"]
    assert "not a dense/vector index" in stats["note"]


def test_index_survives_a_reopen(kb: KnowledgeBase, tmp_path: Path) -> None:
    paths = resolve_paths(tmp_path / "home").ensure()
    kb.add_document(source="note", title=None, text=CORPUS["panik"], doc_id="persist")
    reopen = KnowledgeBase(paths, key=ContentKey.load_or_create(paths.root))
    try:
        assert reopen.search("Herzrasen")[0].doc_id == "persist"
    finally:
        reopen.close()


def test_db_file_is_real_sqlite(kb: KnowledgeBase) -> None:
    connection = sqlite3.connect(kb.path)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    finally:
        connection.close()
    assert {"kb_docs", "kb_chunks"} <= tables
