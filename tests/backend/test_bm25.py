"""Tests for the BM25 lexical index (Milestone 2).

Covers determinism, ranking correctness, non-negative scores, empty corpus, no-match queries, and
tokenization. No network, no models.
"""

from __future__ import annotations

from enterprise_ai_document_assistant.services.retrieval.bm25 import BM25Index, tokenize
from enterprise_ai_document_assistant.services.retrieval.models import Chunk


def _chunk(doc_id: str, index: int, text: str, page: int = 1) -> Chunk:
    return Chunk(
        id=f"{doc_id}:{index}",
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        page=page,
        chunk_index=index,
        text=text,
        char_start=0,
        char_end=len(text),
        created_at="2026-11-15T00:00:00+00:00",
    )


def _corpus() -> list[Chunk]:
    return [
        _chunk("doc-a", 0, "Our refund policy allows returns within thirty days."),
        _chunk("doc-a", 1, "Shipping is free for orders over fifty dollars."),
        _chunk("doc-b", 0, "To reset your password use the link on the login page."),
    ]


def test_tokenize_is_deterministic_and_lowercase() -> None:
    assert tokenize("Hello, World! hello") == ["hello", "world", "hello"]
    assert tokenize("  a  b  ") == ["a", "b"]
    assert tokenize("") == []


def test_search_ranks_relevant_chunk_first() -> None:
    idx = BM25Index()
    idx.build(_corpus())
    results = idx.search("refund policy", top_k=3)
    assert results
    assert results[0][0] == "doc-a:0"
    assert all(score >= 0 for _, score in results)


def test_search_is_deterministic() -> None:
    idx1 = BM25Index()
    idx1.build(_corpus())
    idx2 = BM25Index()
    idx2.build(_corpus())
    assert idx1.search("password reset", top_k=3) == idx2.search("password reset", top_k=3)


def test_search_order_independent_of_insertion() -> None:
    corpus = _corpus()
    idx1 = BM25Index()
    idx1.build(corpus)
    idx2 = BM25Index()
    idx2.build(list(reversed(corpus)))
    assert idx1.search("refund", top_k=3) == idx2.search("refund", top_k=3)


def test_empty_corpus_returns_empty() -> None:
    idx = BM25Index()
    idx.build([])
    assert idx.search("anything", top_k=5) == []


def test_no_match_query_returns_empty() -> None:
    idx = BM25Index()
    idx.build(_corpus())
    assert idx.search("zzzqqqxyzzy", top_k=5) == []


def test_empty_query_returns_empty() -> None:
    idx = BM25Index()
    idx.build(_corpus())
    assert idx.search("", top_k=5) == []
    assert idx.search("   ", top_k=5) == []


def test_top_k_limits_results() -> None:
    idx = BM25Index()
    idx.build(_corpus())
    results = idx.search("policy shipping password refund", top_k=2)
    assert len(results) <= 2


def test_scores_are_non_negative() -> None:
    idx = BM25Index()
    idx.build(_corpus())
    for query in ["refund", "shipping", "password", "policy"]:
        for _, score in idx.search(query, top_k=3):
            assert score >= 0


def test_get_returns_chunk_or_none() -> None:
    idx = BM25Index()
    idx.build(_corpus())
    assert idx.get("doc-a:0") is not None
    assert idx.get("doc-a:0").text.startswith("Our refund")
    assert idx.get("does-not-exist") is None


def test_len_reflects_corpus_size() -> None:
    idx = BM25Index()
    idx.build(_corpus())
    assert len(idx) == 3
