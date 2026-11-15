"""Document management orchestration (Milestone 1).

Coordinates validation, extraction, and persistence. The API layer calls this service; it contains
the business logic so route handlers stay thin.

Behaviour:
- ``upload`` validates the upload (HTTP 400 on failure), generates a stable UUID, extracts text,
  and persists the document. Extraction failures (encrypted / malformed) are stored as documents
  with status ``error`` and a reason, rather than rejected, so the user can see what happened.
- ``list_documents`` and ``get_document`` read from the store.
"""

from __future__ import annotations

import logging
import uuid

from enterprise_ai_document_assistant.core.config import Settings
from enterprise_ai_document_assistant.services.documents.extraction import (
    EncryptedPdfError,
    ExtractionError,
    MalformedPdfError,
    extract_pdf,
)
from enterprise_ai_document_assistant.services.documents.models import (
    DocumentListResponse,
    DocumentMetadata,
    DocumentStatus,
)
from enterprise_ai_document_assistant.services.documents.storage import (
    DocumentStore,
    build_metadata,
)
from enterprise_ai_document_assistant.services.documents.validation import (
    validate_pdf_upload,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """High-level document management operations."""

    def __init__(self, settings: Settings, store: DocumentStore | None = None) -> None:
        self._settings = settings
        self._store = store or DocumentStore(settings.documents_dir)

    @property
    def store(self) -> DocumentStore:
        return self._store

    def upload(self, filename: str | None, data: bytes) -> DocumentMetadata:
        """Validate, extract, and persist an uploaded PDF.

        Raises :class:`UploadValidationError` (HTTP 400) for invalid uploads. Extraction failures
        are stored as ``error`` documents and returned (not raised).
        """
        validated = validate_pdf_upload(filename, data, self._settings.max_upload_bytes)
        document_id = str(uuid.uuid4())

        try:
            extracted = extract_pdf(validated.data)
            metadata = build_metadata(
                document_id,
                validated.filename,
                DocumentStatus.PROCESSED,
                page_count=extracted.page_count,
            )
        except EncryptedPdfError as exc:
            metadata = build_metadata(
                document_id, validated.filename, DocumentStatus.ERROR, None, str(exc)
            )
        except MalformedPdfError as exc:
            metadata = build_metadata(
                document_id, validated.filename, DocumentStatus.ERROR, None, str(exc)
            )
        except ExtractionError as exc:
            metadata = build_metadata(
                document_id, validated.filename, DocumentStatus.ERROR, None, str(exc)
            )

        self._store.save(document_id, validated.data, metadata)
        logger.info(
            "Uploaded document %s (filename=%s, status=%s)",
            document_id,
            validated.filename,
            metadata.status.value,
        )
        return metadata

    def list_documents(self) -> DocumentListResponse:
        """Return all documents, most recent first."""
        return DocumentListResponse(documents=self._store.list())

    def get_document(self, document_id: str) -> DocumentMetadata:
        """Return one document's metadata, or raise :class:`DocumentNotFoundError`."""
        return self._store.get(document_id)
