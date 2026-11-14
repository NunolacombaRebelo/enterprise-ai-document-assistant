"""Document management endpoints (Milestone 1).

Thin HTTP layer over :class:`DocumentService`. Route handlers contain no business logic; they
translate between HTTP and the service and map service exceptions to HTTP status codes.

Endpoints (see ``docs/contracts/api.md`` Milestone 1 addition):
- ``POST /documents`` — upload and process one PDF (multipart field ``file``).
- ``GET /documents`` — list documents.
- ``GET /documents/{document_id}`` — retrieve one document's metadata and status.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from enterprise_ai_document_assistant.core.config import Settings, get_settings
from enterprise_ai_document_assistant.services.documents.models import (
    DocumentListResponse,
    DocumentMetadata,
)
from enterprise_ai_document_assistant.services.documents.service import DocumentService
from enterprise_ai_document_assistant.services.documents.storage import DocumentNotFoundError
from enterprise_ai_document_assistant.services.documents.validation import UploadValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:  # noqa: B008
    """Build the document service from application settings (dependency injection)."""
    return DocumentService(settings)


@router.post(
    "",
    response_model=DocumentMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process one PDF",
)
async def upload_document(
    file: UploadFile = File(...),  # noqa: B008
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentMetadata:
    """Accept a PDF upload, validate it, extract text, and store it.

    Returns ``201`` with the document metadata. Returns ``400`` for invalid uploads (wrong type,
    empty, oversized). Encrypted or malformed PDFs are stored as ``error`` documents and returned
    with a reason.
    """
    data = await file.read()
    try:
        return service.upload(file.filename, data)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=DocumentListResponse, summary="List documents")
def list_documents(
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentListResponse:
    """Return all stored documents, most recent first."""
    return service.list_documents()


@router.get("/{document_id}", response_model=DocumentMetadata, summary="Get a document")
def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentMetadata:
    """Return one document's metadata and processing status.

    Returns ``404`` if the document does not exist.
    """
    try:
        return service.get_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
