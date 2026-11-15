"""Tests for the embedded ChromaDB vector store (Milestone 2).

Covers the critical Chroma safety requirements: no implicit embedding model execution, no
production placeholder vectors presented as semantic results, persistence across restarts,
metadata contract, and the upsert path for future real embeddings. Uses a temp dir (no external
service). No real model endpoints or API keys.
"""

from __future__ import annotations

import numpy as np
import pytest

from enterprise_ai_document_assistant.services.retrieval.models import Chunk, chunk_metadata
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore


def _chunk(doc_id: str, index: int, text: str, embedding: list[float] | None = None) -> Chunk:
    return Chunk(
        id=f"{doc_id}:{index}",
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        page=1,
        chunk_index=index,
        text=text,
        char_start=0,
        char_end=len(text),
        created_at="2026-11-15T00:00:00+00:00",
        embedding=embedding,
    )


@pytest.fixture()
def store(tmp_path) -> VectorStore:
    return VectorStore(path=str(tmp_path / "vector-store"), collection_name="documents")


def test_add_without_embeddings_stores_text_and_metadata(store: VectorStore) -> None:
    chunks = [_chunk("d1", 0, "hello world"), _chunk("d1", 1, "refund policy")]
    store.add(chunks)
    assert store.count() == 2
    # No real vectors were added, so vectors_present must be False.
    assert store.vectors_present is False
    got = store.get_chunk("d1:0")
    assert got is not None
    assert got["document"] == "hello world"
    assert got["metadata"]["document_id"] == "d1"


def test_no_implicit_embedding_model_runs(store: VectorStore) -> None:
    """Adding chunks with embedding=None must not run a real embedding model.

    The store uses a zero-vector no-op embedding function, so the stored vector is all zeros (a
    placeholder), never a real semantic embedding.
    """
    store.add([_chunk("d1", 0, "some text to embed")])
    # The placeholder vector is all zeros (verified by inspecting the raw collection).
    result = store._collection.get(ids=["d1:0"], include=["embeddings"])
    vec = np.asarray(result["embeddings"][0])
    assert vec.shape[0] > 0
    assert bool(np.all(vec == 0)), "placeholder vector must be all zeros, not a real embedding"


def test_query_without_vectors_raises(store: VectorStore) -> None:
    """Querying when no real vectors are present must raise (no fake semantic results)."""
    store.add([_chunk("d1", 0, "some text")])
    with pytest.raises(ValueError):
        store.query([0.1, 0.2], top_k=5)


def test_persistence_across_restart(tmp_path) -> None:
    path = str(tmp_path / "vector-store")
    s1 = VectorStore(path=path, collection_name="documents")
    s1.add([_chunk("d1", 0, "persisted text")])
    del s1

    s2 = VectorStore(path=path, collection_name="documents")
    assert s2.count() == 1
    got = s2.get_chunk("d1:0")
    assert got is not None
    assert got["document"] == "persisted text"


def test_metadata_contract_round_trips(store: VectorStore) -> None:
    chunk = _chunk("d1", 0, "metadata test")
    store.add([chunk])
    got = store.get_chunk("d1:0")
    meta = got["metadata"]
    assert set(meta.keys()) == {"document_id", "filename", "page", "chunk_index", "created_at"}
    assert meta == chunk_metadata(chunk)
    assert isinstance(meta["page"], int)
    assert isinstance(meta["chunk_index"], int)


def test_upsert_is_idempotent_by_id(store: VectorStore) -> None:
    store.add([_chunk("d1", 0, "original")])
    store.add([_chunk("d1", 0, "updated")])
    assert store.count() == 1  # upsert by id, no duplication
    assert store.get_chunk("d1:0")["document"] == "updated"


def test_delete_document_removes_chunks(store: VectorStore) -> None:
    store.add([_chunk("d1", 0, "a"), _chunk("d1", 1, "b"), _chunk("d2", 0, "c")])
    assert store.count() == 3
    store.delete_document("d1")
    assert store.count() == 1
    assert store.get_chunk("d1:0") is None
    assert store.get_chunk("d2:0") is not None


def test_empty_collection_query_is_safe(store: VectorStore) -> None:
    assert store.count() == 0
    # get on an empty collection returns None (no error).
    assert store.get_chunk("missing") is None


def test_real_embedding_upsert_sets_vectors_present(tmp_path) -> None:
    """When a chunk carries a real embedding, vectors_present becomes True and query works."""
    store = VectorStore(path=str(tmp_path / "vector-store"), collection_name="documents")
    # A real (non-zero) embedding.
    real = [1.0] * 384
    store.add([_chunk("d1", 0, "text", embedding=real)])
    assert store.vectors_present is True
    # Query with a similar vector returns the chunk.
    results = store.query([1.0] * 384, top_k=5)
    assert results
    assert results[0][0] == "d1:0"
    assert results[0][1] >= 0
