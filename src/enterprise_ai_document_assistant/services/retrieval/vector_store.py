"""Embedded ChromaDB vector store (Milestone 2).

Implements the ``VectorStore`` interface from ``docs/contracts/retrieval.md`` using **embedded
ChromaDB** (ADR 0007). It persists to ``vector_store_path`` (git-ignored, volume-backed in Docker)
and requires no external service.

**Chroma safety (critical requirement).** Chroma requires a ``documents`` field on ``add`` and, if
no custom embedding function is supplied, applies its default *local* embedding function (which runs
an ONNX model — no download, but a real computation). To honor "no automatic embedding model
execution in production paths," this store supplies a **zero-vector no-op embedding function** that
returns a fixed zero vector without running any model. The zero vector is a storage placeholder only
and is **never** used for ranking:
- Retrieval in Milestone 2 is lexical (BM25) only; the Chroma collection is never queried for
  similarity in lexical-only mode.
- ``vectors_present`` tracks whether any chunk actually carries a real embedding. ``query`` raises
  if called when no real vectors are present, so placeholder vectors are never presented as semantic
  results.
- When real embeddings land (Milestone 3), ``upsert`` writes the provider's vectors over the
  placeholder by ``Chunk.id`` (verified: upsert replaces the stored vector without duplicating).

The store is safe to call when the collection is empty (returns ``[]``).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import chromadb
import numpy as np
from chromadb.api.types import EmbeddingFunction

from enterprise_ai_document_assistant.services.retrieval.models import Chunk, chunk_metadata

logger = logging.getLogger(__name__)

#: Dimension of the zero placeholder vector. Chroma requires a fixed dimension per collection; this
#: matches the default local model's output dimension so real embeddings (Milestone 3) can be
#: upserted over it without re-creating the collection.
_PLACEHOLDER_DIM = 384


class _ZeroEmbeddingFunction(EmbeddingFunction):
    """No-op embedding function that returns a fixed zero vector (no model, no download).

    This satisfies Chroma's add-time embedding requirement without running any embedding model. The
    zero vector is a storage placeholder and is never used for ranking (see module docstring).

    It implements the full ``EmbeddingFunction`` interface (``name``, ``get_config``,
    ``build_from_config``, ``validate_config``) so Chroma does not emit deprecation warnings for a
    future required interface.
    """

    def __init__(self, dim: int = _PLACEHOLDER_DIM) -> None:
        self._dim = dim

    @staticmethod
    def name() -> str:
        """A stable identifier for this embedding function (Chroma calls ``name()``)."""
        return "zero-placeholder"

    def get_config(self) -> dict:
        """Return a serializable configuration (Chroma requires ``get_config()``)."""
        return {"dim": self._dim}

    @staticmethod
    def build_from_config(config: dict) -> _ZeroEmbeddingFunction:
        """Reconstruct the function from its config (Chroma requires ``build_from_config()``)."""
        return _ZeroEmbeddingFunction(dim=int(config.get("dim", _PLACEHOLDER_DIM)))

    @staticmethod
    def validate_config(config: dict) -> None:
        """Validate the config (Chroma requires ``validate_config()``)."""
        dim = config.get("dim", _PLACEHOLDER_DIM)
        if not isinstance(dim, int) or dim < 1:
            raise ValueError("dim must be a positive integer")

    def __call__(self, input):
        return [np.zeros(self._dim, dtype="float32") for _ in input]


class VectorStore:
    """Embedded ChromaDB-backed store for chunk text, metadata, and (future) embeddings."""

    def __init__(
        self,
        path: str,
        collection_name: str,
        distance_fn: str = "cosine",
    ) -> None:
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=_ZeroEmbeddingFunction(),
            metadata={"hnsw:space": distance_fn},
        )
        self._vectors_present = False
        logger.info(
            "Opened Chroma collection '%s' at %s (distance=%s)",
            collection_name,
            path,
            distance_fn,
        )

    @property
    def vectors_present(self) -> bool:
        """Whether any chunk currently carries a real (non-placeholder) embedding."""
        return self._vectors_present

    def add(self, chunks: Sequence[Chunk]) -> None:
        """Upsert chunks into Chroma.

        Chunks with ``embedding=None`` are stored WITHOUT a real vector (the zero placeholder is
        written to satisfy Chroma's add-time requirement but is never used for ranking). Chunks with
        a real embedding are upserted with that vector.
        """
        if not chunks:
            return
        ids = [c.id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [chunk_metadata(c) for c in chunks]
        # Only chunks that carry a real embedding contribute a vector; the rest use the placeholder.
        embeddings = [c.embedding if c.embedding is not None else None for c in chunks]
        has_real = any(c.embedding is not None for c in chunks)
        if has_real:
            # Upsert with explicit embeddings (real vectors for the chunks that have them).
            placeholder = np.zeros(_PLACEHOLDER_DIM, dtype="float32")
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=[e if e is not None else placeholder for e in embeddings],
            )
            self._vectors_present = True
        else:
            # Lexical-only: store text + metadata with the zero placeholder (no model runs).
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        logger.info("Upserted %d chunk(s) into Chroma", len(chunks))

    def query(self, embedding: list[float], top_k: int) -> list[tuple[str, float]]:
        """Return ``[(chunk_id, similarity_score)]`` best-first using the configured distance fn.

        Raises :class:`ValueError` if no real vectors are present, so placeholder vectors are never
        presented as semantic results. Returns ``[]`` for an empty collection.
        """
        if not self._vectors_present:
            raise ValueError(
                "No real vectors are present; vector search is unavailable in lexical-only mode."
            )
        if self._collection.count() == 0 or top_k <= 0:
            return []
        result = self._collection.query(query_embeddings=[embedding], n_results=top_k)
        ids = result["ids"][0] if result["ids"] else []
        distances = result["distances"][0] if result["distances"] else []
        # Convert distance to a similarity score (higher = better). For cosine, distance in [0,2];
        # we return 1 - distance/2 so higher is better and matches the "higher = better" contract.
        scores = [1.0 - float(d) / 2.0 for d in distances]
        return list(zip(ids, scores, strict=True))

    def delete_document(self, document_id: str) -> None:
        """Remove all chunks for a document from the collection."""
        self._collection.delete(where={"document_id": document_id})
        logger.info("Deleted Chroma chunks for document %s", document_id)

    def count(self) -> int:
        """Return the number of chunks in the collection."""
        return self._collection.count()

    def get_chunk(self, chunk_id: str) -> dict | None:
        """Return the stored document/metadata for a chunk id, or ``None``."""
        result = self._collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        return {
            "id": result["ids"][0],
            "document": result["documents"][0] if result["documents"] else None,
            "metadata": result["metadatas"][0] if result["metadatas"] else None,
        }
