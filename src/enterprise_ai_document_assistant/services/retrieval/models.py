"""Retrieval data models (Milestone 2).

Implements the data models defined in ``docs/contracts/retrieval.md``: :class:`Chunk` (the indexed
unit), :class:`SearchResult`, and :class:`Citation`. These are plain frozen dataclasses so they can
be used by both the service layer and the API layer without a framework dependency.

The chunk metadata schema stored in Chroma is exactly the five keys documented in the contract
(``document_id``, ``filename``, ``page``, ``chunk_index``, ``created_at``); see
:func:`chunk_metadata`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """A contiguous passage of a document's extracted text (the indexed unit).

    ``id`` is ``f"{document_id}:{chunk_index}"`` — globally unique across the collection and stable
    across reindexing of the same document version, so reindex can upsert rather than duplicate.
    ``embedding`` is populated only when real embeddings exist (Milestone 3+); it is ``None`` in
    lexical-only mode and must never be a placeholder presented as a semantic result.
    """

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


def chunk_metadata(chunk: Chunk) -> dict:
    """Return the exact metadata dict the contract requires to be stored in Chroma.

    Keys: ``document_id`` (str), ``filename`` (str), ``page`` (int), ``chunk_index`` (int),
    ``created_at`` (str). Numeric values are stored as numbers so they round-trip.
    """
    return {
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "page": chunk.page,
        "chunk_index": chunk.chunk_index,
        "created_at": chunk.created_at,
    }


@dataclass(frozen=True)
class SearchResult:
    """A ranked retrieval result with citation-ready source metadata."""

    chunk_id: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    text: str
    score: float
    sources: tuple[str, ...]


@dataclass(frozen=True)
class Citation:
    """A source citation derived from a result's chunk metadata (never from model output)."""

    document_id: str
    filename: str
    page: int
    chunk_index: int
    excerpt: str


def citation_from_result(result: SearchResult, excerpt_length: int = 200) -> Citation:
    """Build a :class:`Citation` from a :class:`SearchResult`'s metadata and text.

    The excerpt is the first ``excerpt_length`` characters of the chunk text, trimmed. This is
    derived purely from chunk metadata/text, so the system never invents a source.
    """
    excerpt = result.text.strip()
    if len(excerpt) > excerpt_length:
        excerpt = excerpt[:excerpt_length].rstrip()
    return Citation(
        document_id=result.document_id,
        filename=result.filename,
        page=result.page,
        chunk_index=result.chunk_index,
        excerpt=excerpt,
    )
