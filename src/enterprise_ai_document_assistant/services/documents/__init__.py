"""Document management service (Milestone 1).

Owned by Agent 2 (Backend Engineering). Responsibilities:
- Secure PDF upload validation (type, size, magic bytes, safe filename).
- PDF text extraction and page count (via ``pypdf``).
- Local development persistence of documents and metadata.
- Document listing and status retrieval.

Business logic lives here; the API layer (``api/documents.py``) is a thin HTTP wrapper.
"""

from enterprise_ai_document_assistant.services.documents.models import (
    DocumentListResponse,
    DocumentMetadata,
    DocumentStatus,
)
from enterprise_ai_document_assistant.services.documents.service import DocumentService

__all__ = [
    "DocumentListResponse",
    "DocumentMetadata",
    "DocumentService",
    "DocumentStatus",
]
