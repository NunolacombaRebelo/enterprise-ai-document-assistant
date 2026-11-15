"""Pydantic models for the document management API (Milestone 1).

These are the request/response shapes agreed for Milestone 1. They are the single source of truth
for the document endpoints' JSON so the API layer and the service layer cannot drift. See
``docs/contracts/api.md`` (Milestone 1 addition) and ``docs/backend.md``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    """Processing status of a document.

    - ``processed``: the PDF was accepted, validated, and text was extracted successfully.
    - ``error``: the document was accepted and stored but could not be processed (e.g. encrypted,
      malformed, or scanned with no extractable text). The reason is in ``error``.
    """

    PROCESSED = "processed"
    ERROR = "error"


class DocumentMetadata(BaseModel):
    """Metadata and processing status for a single document.

    Returned by ``POST /documents`` (on success), ``GET /documents/{id}``, and as each element of
    the ``GET /documents`` list.
    """

    id: str = Field(description="Stable, unique document identifier (UUIDv4).")
    filename: str = Field(description="Original uploaded filename (sanitized).")
    status: DocumentStatus = Field(description="Processing status.")
    page_count: int | None = Field(
        default=None,
        description="Number of pages, when extraction succeeded; null otherwise.",
    )
    created_at: datetime = Field(description="UTC timestamp when the document was uploaded.")
    error: str | None = Field(
        default=None,
        description="Human-readable reason when status is 'error'; null otherwise.",
    )


class DocumentListResponse(BaseModel):
    """Response body for ``GET /documents``."""

    documents: list[DocumentMetadata] = Field(
        default_factory=list,
        description="All stored documents, most recent first.",
    )
