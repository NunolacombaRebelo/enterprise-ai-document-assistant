"""Milestone 2 integration tests (Agent 1-owned).

Deterministic, no network, no real models. These validate the *infrastructure* and *contracts*
for Advanced RAG (docs/contracts/retrieval.md) that Backend Agent 2 implements against:

- embedded ChromaDB initialization, persistence, and collection lifecycle (ADR 0007);
- the chunk metadata contract stored in Chroma;
- Reciprocal Rank Fusion math (exact values);
- BM25 lexical determinism;
- the no-provider guarantee: retrieval works in lexical-only mode with no embedding provider.

The retrieval *interfaces* (BM25Index / VectorStore / Retriever) are implemented by Agent 2. To keep
these tests meaningful without depending on Agent 2's not-yet-written code, we exercise the same
algorithms and storage directly against the pinned dependencies (chromadb, rank-bm25) using small
reference implementations that mirror the contract signatures. If Agent 2's implementations match
the contract, these same assertions apply to them.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
import pytest
from rank_bm25 import BM25Okapi

# --- Reference models mirroring docs/contracts/retrieval.md -----------------


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    created_at: str
    embedding: list[float] | None = None


def _metadata(chunk: Chunk) -> dict:
    """The exact metadata dict the contract requires to be stored in Chroma."""
    return {
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "page": chunk.page,
        "chunk_index": chunk.chunk_index,
        "created_at": chunk.created_at,
    }


def _tokenize(text: str) -> list[str]:
    """Deterministic tokenizer per the contract: lowercase, split on non-alphanumerics."""
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


@dataclass
class Bm25Index:
    """Reference BM25 index mirroring the contract's BM25Index interface."""

    chunks: dict[str, Chunk] = field(default_factory=dict)
    _bm25: BM25Okapi | None = None

    def build(self, chunks: Sequence[Chunk]) -> None:
        # Keep insertion order so BM25Okapi's score array aligns with chunk ids.
        self.order: list[str] = [c.id for c in chunks]
        self.chunks = {c.id: c for c in chunks}
        corpus = [_tokenize(c.text) for c in chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if self._bm25 is None or not self.chunks:
            return []
        scores = self._bm25.get_scores(_tokenize(query))  # aligned with self.order
        # Rank by score descending; ties broken by chunk id ascending (deterministic).
        indexed = sorted(range(len(self.order)), key=lambda i: (-float(scores[i]), self.order[i]))
        return [(self.order[i], float(scores[i])) for i in indexed[:top_k]]


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Reference RRF exactly as specified in docs/contracts/retrieval.md."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture()
def sample_chunks() -> list[Chunk]:
    now = "2026-11-14T00:00:00Z"
    return [
        Chunk(
            "doc-a:0",
            "doc-a",
            "policy.pdf",
            1,
            0,
            "Our refund policy allows returns within 30 days of purchase.",
            0,
            62,
            now,
        ),
        Chunk(
            "doc-a:1",
            "doc-a",
            "policy.pdf",
            1,
            1,
            "Shipping is free for orders over fifty dollars.",
            62,
            110,
            now,
        ),
        Chunk(
            "doc-b:0",
            "doc-b",
            "faq.pdf",
            2,
            0,
            "To reset your password use the link on the login page.",
            0,
            58,
            now,
        ),
    ]


@pytest.fixture()
def chroma_dir(tmp_path: Path) -> Path:
    return tmp_path / "vector-store"


# --- ChromaDB: initialization, persistence, collection lifecycle -------------


@pytest.mark.integration
def test_chroma_persistent_client_initializes_and_persists(chroma_dir: Path) -> None:
    """ADR 0007: embedded ChromaDB persists to a local dir and survives reopen (no external svc)."""
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection("documents")
    col.add(ids=["c1"], documents=["hello world"], metadatas=[{"document_id": "d1"}])
    assert col.count() == 1
    del client

    reopened = chromadb.PersistentClient(path=str(chroma_dir))
    col2 = reopened.get_or_create_collection("documents")
    assert col2.count() == 1
    got = col2.get(ids=["c1"])
    assert got["documents"] == ["hello world"]
    assert got["metadatas"][0]["document_id"] == "d1"


@pytest.mark.integration
def test_chroma_collection_lifecycle_upsert_delete_count(chroma_dir: Path) -> None:
    """Create, upsert (idempotent by id), delete-by-document, count."""
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection("documents")
    col.add(
        ids=["d1:0", "d1:1"],
        documents=["a", "b"],
        metadatas=[{"document_id": "d1"}, {"document_id": "d1"}],
    )
    assert col.count() == 2
    # Upsert the same id does not duplicate.
    col.upsert(ids=["d1:0"], documents=["a-updated"], metadatas=[{"document_id": "d1"}])
    assert col.count() == 2
    got = col.get(ids=["d1:0"])
    assert got["documents"] == ["a-updated"]
    # Delete all chunks of one document.
    col.delete(where={"document_id": "d1"})
    assert col.count() == 0


@pytest.mark.integration
def test_chroma_empty_collection_query_is_safe(chroma_dir: Path) -> None:
    """Querying an empty collection must not raise."""
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection("empty")
    assert col.count() == 0
    # get on an empty collection returns empty structures, not an error.
    res = col.get()
    assert res["ids"] == []


# --- Metadata contract -------------------------------------------------------


@pytest.mark.integration
def test_chunk_metadata_contract_round_trips(chroma_dir: Path, sample_chunks) -> None:
    """A stored chunk's metadata contains exactly the documented keys with correct types."""
    expected_keys = {"document_id", "filename", "page", "chunk_index", "created_at"}
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection("documents")
    for c in sample_chunks:
        col.add(ids=[c.id], documents=[c.text], metadatas=[_metadata(c)])
    for c in sample_chunks:
        got = col.get(ids=[c.id])
        meta = got["metadatas"][0]
        assert set(meta.keys()) == expected_keys
        assert isinstance(meta["document_id"], str)
        assert isinstance(meta["filename"], str)
        assert isinstance(meta["page"], int)
        assert isinstance(meta["chunk_index"], int)
        assert isinstance(meta["created_at"], str)
        assert meta["document_id"] == c.document_id
        assert meta["page"] == c.page


@pytest.mark.integration
def test_chunk_stores_text_and_metadata_for_lexical_mode(chroma_dir: Path, sample_chunks) -> None:
    """Lexical-only mode: chunk text + metadata are stored and retrievable from Chroma.

    Chroma requires a document field on add and applies its default (local) embedding function;
    it does NOT download a model. In lexical-only mode retrieval uses BM25, not Chroma vector
    queries, so this placeholder vector is harmless. Milestone 3 upserts real embeddings over it
    (see docs/contracts/retrieval.md, "Index lifecycle"). The guarantee tested here is that the
    *text and citation metadata* survive round-trip so citations resolve correctly.
    """
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection("documents")
    for c in sample_chunks:
        col.add(ids=[c.id], documents=[c.text], metadatas=[_metadata(c)])
    got = col.get(include=["documents", "metadatas"])
    assert len(got["ids"]) == len(sample_chunks)
    by_id = dict(zip(got["ids"], got["metadatas"], strict=True))
    doc_text = dict(zip(got["ids"], got["documents"], strict=True))
    for c in sample_chunks:
        assert doc_text[c.id] == c.text
        assert by_id[c.id]["document_id"] == c.document_id
        assert by_id[c.id]["page"] == c.page


# --- RRF math (exact values) -------------------------------------------------


@pytest.mark.integration
def test_rrf_exact_values_single_and_fused() -> None:
    """RRF score(c) = sum 1/(k+rank). Assert exact fused values for a known example."""
    k = 60
    # One list only: rank 1 -> 1/61, rank 2 -> 1/62.
    single = reciprocal_rank_fusion([["x", "y"]], k=k)
    assert single[0][0] == "x"
    assert single[1][0] == "y"
    assert single[0][1] == pytest.approx(1 / 61)
    assert single[1][1] == pytest.approx(1 / 62)

    # Two identical lists: x is rank 1 in both -> 1/61 + 1/61; y is rank 2 in both -> 1/62 + 1/62.
    fused = reciprocal_rank_fusion([["x", "y"], ["x", "y"]], k=k)
    assert fused[0][0] == "x"
    assert fused[0][1] == pytest.approx(2 / 61)
    y_score = dict(fused)["y"]
    assert y_score == pytest.approx(2 / 62)

    # Cross-list example: x rank 1 in list A, rank 2 in list B -> 1/61 + 1/62.
    cross = reciprocal_rank_fusion([["x", "z"], ["z", "x"]], k=k)
    x_score = dict(cross)["x"]
    assert x_score == pytest.approx(1 / 61 + 1 / 62)


@pytest.mark.integration
def test_rrf_deterministic_tie_break_by_chunk_id() -> None:
    """Ties in fused score are broken by chunk id ascending (determinism requirement)."""
    k = 60
    # b and a get identical fused scores (each appears once at rank 1 in a separate list).
    result = reciprocal_rank_fusion([["b"], ["a"]], k=k)
    assert [cid for cid, _ in result] == ["a", "b"]
    assert result[0][1] == pytest.approx(result[1][1])


@pytest.mark.integration
def test_rrf_empty_input_returns_empty() -> None:
    assert reciprocal_rank_fusion([], k=60) == []
    assert reciprocal_rank_fusion([[], []], k=60) == []


# --- BM25 determinism --------------------------------------------------------


@pytest.mark.integration
def test_bm25_is_deterministic(sample_chunks) -> None:
    """Same corpus + query -> same ranked ids/scores, every run."""
    idx1 = Bm25Index()
    idx1.build(sample_chunks)
    idx2 = Bm25Index()
    idx2.build(sample_chunks)
    r1 = idx1.search("refund policy", top_k=3)
    r2 = idx2.search("refund policy", top_k=3)
    assert r1 == r2
    # The refund-policy chunk must rank first for that query.
    assert r1[0][0] == "doc-a:0"
    assert all(score >= 0 for _, score in r1)


@pytest.mark.integration
def test_bm25_empty_corpus_returns_empty() -> None:
    idx = Bm25Index()
    idx.build([])
    assert idx.search("anything", top_k=5) == []


# --- No-provider (lexical-only) guarantee ------------------------------------


@dataclass
class Retriever:
    """Reference retriever mirroring the contract: works with vector=None, embedder=None."""

    settings_mode: str
    bm25: Bm25Index
    vector: object | None = None
    embedder: object | None = None

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        lexical = self.bm25.search(query, top_k=top_k)
        if self.settings_mode == "lexical" or self.vector is None or self.embedder is None:
            # vector/hybrid with no vectors present degrades to lexical (no dummy results).
            return lexical
        raise AssertionError("vector path requires vectors; not exercised in lexical-only tests")


@pytest.mark.integration
def test_retriever_works_with_no_provider_in_lexical_mode(sample_chunks) -> None:
    """No embedding provider + no vector store -> lexical search still returns correct results."""
    bm25 = Bm25Index()
    bm25.build(sample_chunks)
    retr = Retriever(settings_mode="lexical", bm25=bm25, vector=None, embedder=None)
    results = retr.search("refund", top_k=5)
    assert results, "lexical-only mode must return results"
    assert results[0][0] == "doc-a:0"


@pytest.mark.integration
def test_retriever_hybrid_degrades_to_lexical_without_vectors(sample_chunks) -> None:
    """hybrid mode with no vectors present degrades to lexical (no crash, no dummy results)."""
    bm25 = Bm25Index()
    bm25.build(sample_chunks)
    retr = Retriever(settings_mode="hybrid", bm25=bm25, vector=None, embedder=None)
    results = retr.search("password reset", top_k=5)
    assert results
    assert results[0][0] == "doc-b:0"


# --- Deterministic embedding double ------------------------------------------


def deterministic_embed(texts: Sequence[str], dim: int = 8) -> list[list[float]]:
    """Hash-based fixed-dimension vectors: stable across runs, no model, no network."""
    import hashlib

    out = []
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        vec = [b / 255.0 for b in h[:dim]]
        out.append(vec)
    return out


@pytest.mark.integration
def test_deterministic_embedding_double_is_stable() -> None:
    v1 = deterministic_embed(["alpha", "beta"])
    v2 = deterministic_embed(["alpha", "beta"])
    assert v1 == v2
    assert len(v1[0]) == 8
    # Different texts produce different vectors.
    assert deterministic_embed(["alpha"])[0] != deterministic_embed(["gamma"])[0]
