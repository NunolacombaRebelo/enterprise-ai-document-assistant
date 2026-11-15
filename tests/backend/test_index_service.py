"""Tests for the indexing lifecycle (Milestone 2).

Covers initial indexing, reindexing (idempotency), duplicate prevention, status, persistence across
restarts, and the not-indexable (status error) case. Uses temp dirs; no network, no models.
"""

from __future__ import annotations

import pytest

from enterprise_ai_document_assistant.core.config import Settings
from enterprise_ai_document_assistant.services.documents.models import DocumentStatus
from enterprise_ai_document_assistant.services.documents.storage import (
    DocumentStore,
    build_metadata,
)
from enterprise_ai_document_assistant.services.retrieval.chunk_store import ChunkStore
from enterprise_ai_document_assistant.services.retrieval.index import (
    DocumentNotIndexableError,
    IndexService,
)
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore

from .pdf_factory import make_pdf_bytes


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        documents_dir=str(tmp_path / "documents"),
        vector_store_path=str(tmp_path / "vector-store"),
    )


def _make_service(tmp_path, settings: Settings | None = None) -> IndexService:
    settings = settings or _settings(tmp_path)
    return IndexService(
        settings=settings,
        document_store=DocumentStore(settings.documents_dir),
        vector_store=VectorStore(path=settings.vector_store_path, collection_name="documents"),
    )


def _upload_processed_pdf(service: IndexService, filename: str, pages: int = 2) -> str:
    """Upload a processed PDF via the document store and return its id."""
    import uuid

    document_id = str(uuid.uuid4())
    metadata = build_metadata(document_id, filename, DocumentStatus.PROCESSED, page_count=pages)
    service.store.save(document_id, make_pdf_bytes(pages), metadata)
    return document_id


def test_index_document_creates_chunks(tmp_path) -> None:
    service = _make_service(tmp_path)
    document_id = _upload_processed_pdf(service, "policy.pdf", pages=2)
    result = service.index_document(document_id)
    assert result.document_id == document_id
    assert result.chunks_indexed >= 1
    assert result.vectors_added == 0  # lexical-only mode


def test_reindex_is_idempotent(tmp_path) -> None:
    service = _make_service(tmp_path)
    document_id = _upload_processed_pdf(service, "policy.pdf", pages=2)
    first = service.index_document(document_id)
    second = service.index_document(document_id)
    # Reindexing replaces chunks (no duplication).
    assert first.chunks_indexed == second.chunks_indexed
    status = service.status()
    assert status.documents_indexed == 1
    assert status.chunks_indexed == first.chunks_indexed


def test_index_multiple_documents_no_cross_contamination(tmp_path) -> None:
    service = _make_service(tmp_path)
    d1 = _upload_processed_pdf(service, "a.pdf", pages=1)
    d2 = _upload_processed_pdf(service, "b.pdf", pages=1)
    service.index_document(d1)
    service.index_document(d2)
    status = service.status()
    assert status.documents_indexed == 2
    # Chunk ids are unique across documents.
    chunks = service._chunk_store.all_chunks()
    assert len(chunks) == len({c.id for c in chunks})


def test_index_error_document_raises(tmp_path) -> None:
    service = _make_service(tmp_path)
    import uuid

    document_id = str(uuid.uuid4())
    metadata = build_metadata(document_id, "bad.pdf", DocumentStatus.ERROR, None, "encrypted")
    service.store.save(document_id, make_pdf_bytes(1), metadata)
    with pytest.raises(DocumentNotIndexableError):
        service.index_document(document_id)


def test_status_empty_index(tmp_path) -> None:
    service = _make_service(tmp_path)
    status = service.status()
    assert status.documents_indexed == 0
    assert status.chunks_indexed == 0
    assert status.vectors_present is False
    assert status.retrieval_mode == "lexical"
    assert status.collection == "documents"


def test_persistence_across_restart(tmp_path) -> None:
    """Chunks persist to disk; a new IndexService rebuilds the BM25 index from them."""
    settings = _settings(tmp_path)
    service1 = _make_service(tmp_path, settings)
    document_id = _upload_processed_pdf(service1, "policy.pdf", pages=4)
    service1.index_document(document_id)
    indexed_chunks = service1.status().chunks_indexed
    assert indexed_chunks >= 1

    # Simulate a restart: a brand-new IndexService over the same dirs.
    service2 = _make_service(tmp_path, settings)
    status2 = service2.status()
    assert status2.chunks_indexed == indexed_chunks
    assert status2.documents_indexed == 1
    # The rebuilt BM25 index can still search.
    results, mode = service2.search("Page 1", top_k=5)
    assert mode == "lexical"
    # The synthetic PDF text is "Page N synthetic content"; "Page 1" discriminates chunk 0.
    assert results
    assert results[0].chunk_index == 0


def test_remove_document_from_index(tmp_path) -> None:
    service = _make_service(tmp_path)
    d1 = _upload_processed_pdf(service, "a.pdf", pages=1)
    d2 = _upload_processed_pdf(service, "b.pdf", pages=1)
    service.index_document(d1)
    service.index_document(d2)
    assert service.status().documents_indexed == 2
    service.remove_document(d1)
    status = service.status()
    assert status.documents_indexed == 1
    # d1's chunks are gone from the chunk store.
    assert service._chunk_store.get_document(d1) == []
    # The original PDF is preserved (indexing never deletes user data).
    assert (service.store.root / f"{d1}.pdf").exists()


def test_chunk_store_round_trip(tmp_path) -> None:
    store = ChunkStore(tmp_path / "chunks")
    from enterprise_ai_document_assistant.services.retrieval.chunking import chunk_text

    chunks = chunk_text("Hello world. A test.", "d1", "a.pdf", "2026-11-15T00:00:00+00:00")
    store.save_document("d1", chunks)
    loaded = store.get_document("d1")
    assert [c.id for c in loaded] == [c.id for c in chunks]
    assert [c.text for c in loaded] == [c.text for c in chunks]
    assert [c.page for c in loaded] == [c.page for c in chunks]
