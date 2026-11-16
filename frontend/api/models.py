"""Data models for the frontend API client.

These mirror the backend document metadata contract (see ``docs/contracts/api.md`` and the
Milestone 1 endpoint proposal). Parsing is defensive: unexpected or missing fields never crash the
UI; they are surfaced as a clean error instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class DocumentStatus:
    """Document processing status values.

    These mirror the backend ``DocumentStatus`` enum (see
    ``src/enterprise_ai_document_assistant/services/documents/models.py``). The backend is the
    source of truth for status strings; this class documents the values the frontend understands
    and renders. Unknown values are displayed verbatim rather than dropped.
    """

    PROCESSED = "processed"
    ERROR = "error"


# Statuses the frontend treats as "still in flight" (none in Milestone 1 — processing is
# synchronous on the backend, so a document is either ``processed`` or ``error`` when returned).
ACTIVE_STATUSES = frozenset()


@dataclass(frozen=True)
class Document:
    """A document in the collection, as returned by the backend."""

    id: str
    filename: str
    status: str
    page_count: int | None = None
    created_at: datetime | None = None
    error: str | None = None

    @property
    def is_active(self) -> bool:
        """Return ``True`` while the document is still being processed."""
        return self.status in ACTIVE_STATUSES

    @property
    def is_error(self) -> bool:
        """Return ``True`` when the document could not be processed."""
        return self.status == DocumentStatus.ERROR


def _parse_datetime(value: object) -> datetime | None:
    """Parse an ISO-8601 datetime string, returning ``None`` when absent or invalid."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_document(payload: object) -> Document:
    """Parse a single document object from a backend response.

    Raises :class:`ValueError` when the payload is not a mapping or lacks required fields, so the
    caller can present a clean error instead of crashing.
    """
    if not isinstance(payload, dict):
        raise ValueError("Document payload is not an object.")

    document_id = payload.get("id")
    filename = payload.get("filename")
    if not isinstance(document_id, str) or not document_id:
        raise ValueError("Document payload is missing a valid 'id'.")
    if not isinstance(filename, str) or not filename:
        raise ValueError("Document payload is missing a valid 'filename'.")

    status = payload.get("status")
    if not isinstance(status, str) or not status:
        raise ValueError("Document payload is missing a valid 'status'.")

    page_count = payload.get("page_count")
    if page_count is not None and not isinstance(page_count, int):
        raise ValueError("Document payload has an invalid 'page_count'.")

    error = payload.get("error")
    if error is not None and not isinstance(error, str):
        raise ValueError("Document payload has an invalid 'error'.")

    return Document(
        id=document_id,
        filename=filename,
        status=status,
        page_count=page_count,
        created_at=_parse_datetime(payload.get("created_at")),
        error=error,
    )


def parse_document_list(payload: object) -> list[Document]:
    """Parse a document collection response (``{"documents": [...]}``).

    Raises :class:`ValueError` when the payload is not the expected shape.
    """
    if not isinstance(payload, dict):
        raise ValueError("Document list response is not an object.")
    items = payload.get("documents")
    if not isinstance(items, list):
        raise ValueError("Document list response is missing a 'documents' array.")
    return [parse_document(item) for item in items]


# ---------------------------------------------------------------------------
# Milestone 2 — retrieval (search / index) models
#
# These mirror the backend contract in ``docs/contracts/api.md`` (Milestone 2) and
# ``docs/contracts/retrieval.md``. Parsing is defensive: unexpected or missing fields
# raise a clean :class:`ValueError` that the client maps to a typed error.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SearchResult:
    """A single ranked retrieval result with citation-ready source metadata."""

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


@dataclass(frozen=True)
class SearchResponse:
    """The full ``POST /search`` response."""

    query: str
    mode: str
    results: tuple[SearchResult, ...]
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class IndexStatus:
    """The ``GET /index/status`` response."""

    documents_indexed: int
    chunks_indexed: int
    vectors_present: bool
    retrieval_mode: str
    collection: str


@dataclass(frozen=True)
class IndexResult:
    """The ``POST /documents/{id}/index`` response."""

    document_id: str
    chunks_indexed: int
    vectors_added: int


def _as_int(value: object, field: str) -> int:
    """Coerce a JSON value to ``int`` or raise a clean :class:`ValueError`."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Field '{field}' is not an integer.")
    return value


def _as_float(value: object, field: str) -> float:
    """Coerce a JSON value to ``float`` or raise a clean :class:`ValueError`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Field '{field}' is not a number.")
    return float(value)


def parse_search_result(payload: object) -> SearchResult:
    """Parse one ``SearchResult`` object from a backend response."""
    if not isinstance(payload, dict):
        raise ValueError("Search result is not an object.")

    chunk_id = payload.get("chunk_id")
    document_id = payload.get("document_id")
    filename = payload.get("filename")
    text = payload.get("text")
    if not isinstance(chunk_id, str) or not chunk_id:
        raise ValueError("Search result is missing a valid 'chunk_id'.")
    if not isinstance(document_id, str) or not document_id:
        raise ValueError("Search result is missing a valid 'document_id'.")
    if not isinstance(filename, str):
        raise ValueError("Search result is missing a valid 'filename'.")
    if not isinstance(text, str):
        raise ValueError("Search result is missing a valid 'text'.")

    sources = payload.get("sources")
    if sources is None:
        sources = ()
    elif isinstance(sources, (list, tuple)):
        sources = tuple(str(s) for s in sources)
    else:
        raise ValueError("Search result 'sources' is not a list.")

    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        filename=filename,
        page=_as_int(payload.get("page"), "page"),
        chunk_index=_as_int(payload.get("chunk_index"), "chunk_index"),
        text=text,
        score=_as_float(payload.get("score"), "score"),
        sources=sources,
    )


def parse_citation(payload: object) -> Citation:
    """Parse one ``Citation`` object from a backend response."""
    if not isinstance(payload, dict):
        raise ValueError("Citation is not an object.")

    document_id = payload.get("document_id")
    filename = payload.get("filename")
    excerpt = payload.get("excerpt")
    if not isinstance(document_id, str) or not document_id:
        raise ValueError("Citation is missing a valid 'document_id'.")
    if not isinstance(filename, str):
        raise ValueError("Citation is missing a valid 'filename'.")
    if not isinstance(excerpt, str):
        raise ValueError("Citation is missing a valid 'excerpt'.")

    return Citation(
        document_id=document_id,
        filename=filename,
        page=_as_int(payload.get("page"), "page"),
        chunk_index=_as_int(payload.get("chunk_index"), "chunk_index"),
        excerpt=excerpt,
    )


def parse_search_response(payload: object) -> SearchResponse:
    """Parse a ``POST /search`` response.

    An empty ``results`` array is a valid "no matches" state and parses to an empty tuple.
    """
    if not isinstance(payload, dict):
        raise ValueError("Search response is not an object.")

    query = payload.get("query")
    mode = payload.get("mode")
    if not isinstance(query, str):
        raise ValueError("Search response is missing a valid 'query'.")
    if not isinstance(mode, str):
        raise ValueError("Search response is missing a valid 'mode'.")

    results = payload.get("results")
    if results is None:
        results = []
    if not isinstance(results, list):
        raise ValueError("Search response 'results' is not a list.")

    citations = payload.get("citations")
    if citations is None:
        citations = []
    if not isinstance(citations, list):
        raise ValueError("Search response 'citations' is not a list.")

    return SearchResponse(
        query=query,
        mode=mode,
        results=tuple(parse_search_result(r) for r in results),
        citations=tuple(parse_citation(c) for c in citations),
    )


def parse_index_status(payload: object) -> IndexStatus:
    """Parse a ``GET /index/status`` response."""
    if not isinstance(payload, dict):
        raise ValueError("Index status response is not an object.")

    vectors_present = payload.get("vectors_present")
    retrieval_mode = payload.get("retrieval_mode")
    collection = payload.get("collection")
    if not isinstance(vectors_present, bool):
        raise ValueError("Index status 'vectors_present' is not a boolean.")
    if not isinstance(retrieval_mode, str) or not retrieval_mode:
        raise ValueError("Index status is missing a valid 'retrieval_mode'.")
    if not isinstance(collection, str):
        raise ValueError("Index status is missing a valid 'collection'.")

    return IndexStatus(
        documents_indexed=_as_int(payload.get("documents_indexed"), "documents_indexed"),
        chunks_indexed=_as_int(payload.get("chunks_indexed"), "chunks_indexed"),
        vectors_present=vectors_present,
        retrieval_mode=retrieval_mode,
        collection=collection,
    )


def parse_index_result(payload: object) -> IndexResult:
    """Parse a ``POST /documents/{id}/index`` response."""
    if not isinstance(payload, dict):
        raise ValueError("Index response is not an object.")

    document_id = payload.get("document_id")
    if not isinstance(document_id, str) or not document_id:
        raise ValueError("Index response is missing a valid 'document_id'.")

    return IndexResult(
        document_id=document_id,
        chunks_indexed=_as_int(payload.get("chunks_indexed"), "chunks_indexed"),
        vectors_added=_as_int(payload.get("vectors_added"), "vectors_added"),
    )
