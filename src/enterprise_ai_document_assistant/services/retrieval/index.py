"""Indexing lifecycle and status (Milestone 2).

Orchestrates the document indexing lifecycle: chunking, persistence of chunks (the single source of
truth), rebuilding the BM25 index, and upserting into Chroma. The existing document storage
(Milestone 1) is the authoritative source for uploaded PDFs and metadata; the retrieval index is a
derived representation.

Indexing is **idempotent**: reindexing the same document replaces its chunks (upsert by
``Chunk.id``) rather than duplicating them. The original uploaded document is always preserved;
indexing never deletes user data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from enterprise_ai_document_assistant.core.config import Settings
from enterprise_ai_document_assistant.services.documents.extraction import extract_pdf_pages
from enterprise_ai_document_assistant.services.documents.models import DocumentStatus
from enterprise_ai_document_assistant.services.documents.storage import DocumentStore
from enterprise_ai_document_assistant.services.retrieval.bm25 import BM25Index
from enterprise_ai_document_assistant.services.retrieval.chunk_store import ChunkStore
from enterprise_ai_document_assistant.services.retrieval.chunking import (
    ChunkingConfig,
    chunk_pages,
)
from enterprise_ai_document_assistant.services.retrieval.retriever import Retriever
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentNotIndexableError(Exception):
    """Raised when a document has no extractable text to index (e.g. status ``error``)."""


@dataclass(frozen=True)
class IndexResult:
    """Outcome of indexing one document."""

    document_id: str
    chunks_indexed: int
    vectors_added: int


@dataclass(frozen=True)
class IndexStatus:
    """Snapshot of the index state for ``GET /index/status``."""

    documents_indexed: int
    chunks_indexed: int
    vectors_present: bool
    retrieval_mode: str
    collection: str


class IndexService:
    """High-level indexing and retrieval operations."""

    def __init__(
        self,
        settings: Settings,
        document_store: DocumentStore,
        chunk_store: ChunkStore | None = None,
        vector_store: VectorStore | None = None,
        bm25: BM25Index | None = None,
    ) -> None:
        self._settings = settings
        self._document_store = document_store
        # Chunk store lives alongside documents under .data (git-ignored); the single source of
        # truth for the retrieval index.
        self._chunk_store = chunk_store or ChunkStore(_chunks_dir(settings))
        self._vector_store = vector_store
        self._bm25 = bm25 or BM25Index()
        self._retriever = Retriever(
            settings,
            self._bm25,
            vector=self._vector_store,
            embedder=None,  # interface-only in Milestone 2; no concrete provider wired up.
        )
        # Rebuild the BM25 index from persisted chunks so it survives restarts.
        self._rebuild_bm25()

    @property
    def bm25(self) -> BM25Index:
        return self._bm25

    @property
    def store(self) -> DocumentStore:
        """The authoritative document store (Milestone 1) that holds uploaded PDFs/metadata."""
        return self._document_store

    @property
    def vector_store(self) -> VectorStore | None:
        return self._vector_store

    def _rebuild_bm25(self) -> None:
        self._bm25.build(self._chunk_store.all_chunks())

    def index_document(self, document_id: str) -> IndexResult:
        """Index (or reindex) one document. Idempotent.

        Raises :class:`DocumentNotIndexableError` if the document's status is ``error`` (no
        extractable text). Re-extracts from the stored PDF, chunks it, persists the chunks, rebuilds
        the BM25 index, and upserts into Chroma (vectors only if available).
        """
        metadata = self._document_store.get(document_id)
        if metadata.status is not DocumentStatus.PROCESSED:
            raise DocumentNotIndexableError(
                f"Document '{document_id}' has no extractable text to index (status: "
                f"{metadata.status.value})."
            )

        pdf_path = self._document_store.root / f"{document_id}.pdf"
        data = pdf_path.read_bytes()
        pages = extract_pdf_pages(data)

        config = ChunkingConfig(
            target_size_tokens=self._settings.chunk_size_tokens,
            overlap_tokens=self._settings.chunk_overlap_tokens,
        )
        # created_at is stable per document so reindexing produces stable chunk metadata.
        created_at = metadata.created_at.isoformat()
        chunks = chunk_pages(
            pages,
            document_id=document_id,
            filename=metadata.filename,
            created_at=created_at,
            config=config,
        )

        # Persist chunks (single source of truth) and rebuild BM25.
        self._chunk_store.save_document(document_id, chunks)
        self._rebuild_bm25()

        # Upsert into Chroma (text + metadata; vectors only if available).
        vectors_added = 0
        if self._vector_store is not None:
            self._vector_store.add(chunks)
            vectors_added = sum(1 for c in chunks if c.embedding is not None)

        logger.info(
            "Indexed document %s: %d chunk(s), %d vector(s) added",
            document_id,
            len(chunks),
            vectors_added,
        )
        return IndexResult(
            document_id=document_id, chunks_indexed=len(chunks), vectors_added=vectors_added
        )

    def remove_document(self, document_id: str) -> None:
        """Remove a document's chunks from the index (and Chroma). Does not delete the PDF."""
        self._chunk_store.delete_document(document_id)
        if self._vector_store is not None:
            self._vector_store.delete_document(document_id)
        self._rebuild_bm25()
        logger.info("Removed document %s from the index", document_id)

    def status(self) -> IndexStatus:
        """Return the current index status snapshot."""
        documents = self._chunk_store.all_documents()
        chunks = self._chunk_store.all_chunks()
        vectors_present = bool(self._vector_store and self._vector_store.vectors_present)
        return IndexStatus(
            documents_indexed=len(documents),
            chunks_indexed=len(chunks),
            vectors_present=vectors_present,
            retrieval_mode=self._settings.retrieval_mode,
            collection=self._settings.chroma_collection,
        )

    def search(self, query: str, top_k: int | None = None) -> tuple[list, str]:
        """Run a search in the configured mode. Returns ``(results, effective_mode)``."""
        return self._retriever.search(query, top_k=top_k)


def _chunks_dir(settings: Settings) -> str:
    """Derive the chunk store directory from the configured documents directory.

    Chunks are stored alongside documents under ``.data`` (git-ignored) so all runtime data is
    isolated together.
    """
    from pathlib import Path

    base = Path(settings.documents_dir).parent
    return str(base / "chunks")
