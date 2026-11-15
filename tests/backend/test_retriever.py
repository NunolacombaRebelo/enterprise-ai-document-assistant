"""Tests for the Retriever orchestration (Milestone 2).

Covers lexical-only mode, vector/hybrid degradation to lexical when no vectors are present, the
no-provider guarantee, and source attribution. No network, no models.
"""

from __future__ import annotations

from enterprise_ai_document_assistant.core.config import Settings
from enterprise_ai_document_assistant.services.retrieval.bm25 import BM25Index
from enterprise_ai_document_assistant.services.retrieval.models import Chunk
from enterprise_ai_document_assistant.services.retrieval.retriever import Retriever
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore


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


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def _bm25(chunks: list[Chunk]) -> BM25Index:
    idx = BM25Index()
    idx.build(chunks)
    return idx


def test_lexical_mode_no_provider_returns_results() -> None:
    """The no-provider guarantee: vector=None, embedder=None, lexical mode returns BM25 results."""
    retriever = Retriever(_settings(retrieval_mode="lexical"), _bm25(_corpus()), vector=None)
    results, mode = retriever.search("refund policy", top_k=5)
    assert mode == "lexical"
    assert results
    assert results[0].chunk_id == "doc-a:0"
    assert results[0].sources == ("bm25",)


def test_hybrid_mode_without_vectors_degrades_to_lexical() -> None:
    retriever = Retriever(_settings(retrieval_mode="hybrid"), _bm25(_corpus()), vector=None)
    results, mode = retriever.search("password reset", top_k=5)
    assert mode == "lexical"
    assert results
    assert results[0].chunk_id == "doc-b:0"
    assert results[0].sources == ("bm25",)


def test_vector_mode_without_vectors_degrades_to_lexical() -> None:
    retriever = Retriever(_settings(retrieval_mode="vector"), _bm25(_corpus()), vector=None)
    results, mode = retriever.search("refund", top_k=5)
    assert mode == "lexical"
    assert results


def test_hybrid_mode_with_vector_store_but_no_vectors_degrades(tmp_path) -> None:
    """A vector store exists but has no real vectors -> hybrid degrades to lexical."""
    vector = VectorStore(path=str(tmp_path / "vector-store"), collection_name="documents")
    retriever = Retriever(
        _settings(retrieval_mode="hybrid"), _bm25(_corpus()), vector=vector, embedder=object()
    )
    results, mode = retriever.search("refund", top_k=5)
    assert mode == "lexical"
    assert results
    assert results[0].sources == ("bm25",)


def test_empty_query_returns_empty_results() -> None:
    retriever = Retriever(_settings(retrieval_mode="lexical"), _bm25(_corpus()), vector=None)
    results, mode = retriever.search("", top_k=5)
    assert mode == "lexical"
    assert results == []


def test_empty_corpus_returns_empty_results() -> None:
    retriever = Retriever(_settings(retrieval_mode="lexical"), _bm25([]), vector=None)
    results, _mode = retriever.search("anything", top_k=5)
    assert results == []


def test_top_k_limits_results() -> None:
    retriever = Retriever(_settings(retrieval_mode="lexical"), _bm25(_corpus()), vector=None)
    results, _ = retriever.search("refund shipping password policy", top_k=2)
    assert len(results) <= 2


def test_results_carry_source_metadata() -> None:
    retriever = Retriever(_settings(retrieval_mode="lexical"), _bm25(_corpus()), vector=None)
    results, _ = retriever.search("refund", top_k=5)
    r = results[0]
    assert r.document_id == "doc-a"
    assert r.filename == "doc-a.pdf"
    assert r.page == 1
    assert r.chunk_index == 0
    assert r.text.startswith("Our refund")
