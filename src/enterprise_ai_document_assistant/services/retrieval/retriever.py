"""Retrieval orchestration (Milestone 2).

Implements the ``Retriever`` from ``docs/contracts/retrieval.md``. It runs the configured
``retrieval_mode`` and returns :class:`SearchResult` objects:

- ``lexical``: BM25 only (always available, no embeddings needed).
- ``vector``: Chroma similarity only; requires real vectors present, else degrades to lexical.
- ``hybrid``: BM25 + vector (if vectors present) fused via Reciprocal Rank Fusion; with no vectors,
  lexical only.

The **no-provider guarantee**: with ``vector=None`` and ``embedder=None`` in ``lexical`` mode, the
retriever returns correct BM25 results. ``vector``/``hybrid`` with no vectors degrade gracefully to
lexical (logging a warning) rather than returning dummy semantic results.
"""

from __future__ import annotations

import logging

from enterprise_ai_document_assistant.core.config import Settings
from enterprise_ai_document_assistant.services.retrieval.bm25 import BM25Index
from enterprise_ai_document_assistant.services.retrieval.fusion import (
    reciprocal_rank_fusion,
    rerank,
)
from enterprise_ai_document_assistant.services.retrieval.models import SearchResult
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Mode-driven retrieval over a BM25 index and (optional) vector store."""

    def __init__(
        self,
        settings: Settings,
        bm25: BM25Index,
        vector: VectorStore | None = None,
        embedder: object | None = None,
    ) -> None:
        self._settings = settings
        self._bm25 = bm25
        self._vector = vector
        self._embedder = embedder

    def _lexical(self, query: str, top_k: int) -> list[SearchResult]:
        scored = self._bm25.search(query, top_k=top_k)
        results: list[SearchResult] = []
        for chunk_id, score in scored:
            chunk = self._bm25.get(chunk_id)
            if chunk is None:
                continue
            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    page=chunk.page,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    score=score,
                    sources=("bm25",),
                )
            )
        return results

    def _vector_results(self, query: str, top_k: int) -> list[SearchResult] | None:
        """Return vector results, or ``None`` if vector search is unavailable (no real vectors)."""
        if self._vector is None or self._embedder is None:
            return None
        if not self._vector.vectors_present:
            return None
        # Embed the query with the provider, then query Chroma. (Milestone 3 path.)
        query_vectors = self._embedder.embed([query])  # type: ignore[union-attr]
        if not query_vectors:
            return None
        scored = self._vector.query(query_vectors[0], top_k=top_k)
        results: list[SearchResult] = []
        for chunk_id, score in scored:
            stored = self._vector.get_chunk(chunk_id)
            if stored is None or stored.get("metadata") is None:
                continue
            meta = stored["metadata"]
            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=str(meta.get("document_id", "")),
                    filename=str(meta.get("filename", "")),
                    page=int(meta.get("page", 0)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    text=stored.get("document") or "",
                    score=score,
                    sources=("vector",),
                )
            )
        return results

    def search(self, query: str, top_k: int | None = None) -> tuple[list[SearchResult], str]:
        """Run the configured mode and return ``(results, effective_mode)``.

        ``effective_mode`` is the mode actually used (may be ``lexical`` even if ``hybrid`` is
        configured but no vectors are present). Results are best-first by score.
        """
        k = top_k if top_k is not None else self._settings.retrieval_top_k
        mode = self._settings.retrieval_mode

        if mode == "lexical":
            return self._lexical(query, k), "lexical"

        vector_results = self._vector_results(query, k)

        if mode == "vector":
            if vector_results is None:
                logger.warning(
                    "Vector mode requested but no vectors present; degrading to lexical."
                )
                return self._lexical(query, k), "lexical"
            return vector_results, "vector"

        # mode == "hybrid"
        lexical = self._lexical(query, k)
        if vector_results is None:
            logger.warning("Hybrid mode requested but no vectors present; using lexical only.")
            return lexical, "lexical"

        # Fuse the two ranked lists (each truncated to k) via RRF.
        lexical_ids = [r.chunk_id for r in lexical]
        vector_ids = [r.chunk_id for r in vector_results]
        fused = reciprocal_rank_fusion([lexical_ids, vector_ids], k=self._settings.rrf_k)

        by_id = {r.chunk_id: r for r in lexical}
        by_id.update({r.chunk_id: r for r in vector_results})
        fused_results: list[SearchResult] = []
        for chunk_id, fused_score in fused:
            base = by_id.get(chunk_id)
            if base is None:
                continue
            # Mark which retrievers contributed.
            sources = set()
            if chunk_id in lexical_ids:
                sources.add("bm25")
            if chunk_id in vector_ids:
                sources.add("vector")
            fused_results.append(
                SearchResult(
                    chunk_id=base.chunk_id,
                    document_id=base.document_id,
                    filename=base.filename,
                    page=base.page,
                    chunk_index=base.chunk_index,
                    text=base.text,
                    score=fused_score,
                    sources=tuple(sorted(sources)),
                )
            )
        fused_results = fused_results[:k]
        if self._settings.rerank_enabled:
            fused_results = rerank(query, fused_results)
        return fused_results, "hybrid"
