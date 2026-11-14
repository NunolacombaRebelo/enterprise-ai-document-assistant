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
