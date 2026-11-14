"""API tests for document management (Milestone 1).

Uses FastAPI's in-memory TestClient with a temporary documents directory (via dependency override),
so no runtime data is written into the repo. No network, no credentials.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from enterprise_ai_document_assistant.api.documents import get_document_service
from enterprise_ai_document_assistant.api.main import app
from enterprise_ai_document_assistant.core.config import Settings
from enterprise_ai_document_assistant.services.documents.service import DocumentService

from .pdf_factory import (
    make_empty_pdf_bytes,
    make_encrypted_pdf_bytes,
    make_non_pdf_bytes,
    make_pdf_bytes,
)


@pytest.fixture()
def client(tmp_path) -> TestClient:
    """TestClient with the document service pointed at a temp directory."""
    settings = Settings(_env_file=None, documents_dir=str(tmp_path / "documents"))

    def override() -> DocumentService:
        return DocumentService(settings)

    app.dependency_overrides[get_document_service] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_still_works(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_valid_pdf_returns_201(client: TestClient) -> None:
    response = client.post(
        "/documents",
        files={"file": ("report.pdf", make_pdf_bytes(3), "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "processed"
    assert body["page_count"] == 3
    assert body["filename"] == "report.pdf"
    assert body["id"]
    assert body["created_at"]
    assert body["error"] is None


def test_upload_lists_document(client: TestClient) -> None:
    upload = client.post(
        "/documents",
        files={"file": ("a.pdf", make_pdf_bytes(1), "application/pdf")},
    )
    doc_id = upload.json()["id"]

    listing = client.get("/documents")
    assert listing.status_code == 200
    docs = listing.json()["documents"]
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id


def test_get_document_returns_metadata(client: TestClient) -> None:
    upload = client.post(
        "/documents",
        files={"file": ("b.pdf", make_pdf_bytes(2), "application/pdf")},
    )
    doc_id = upload.json()["id"]

    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == doc_id
    assert body["page_count"] == 2
    assert body["status"] == "processed"


def test_get_unknown_document_returns_404(client: TestClient) -> None:
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404


def test_upload_empty_returns_400(client: TestClient) -> None:
    response = client.post(
        "/documents",
        files={"file": ("empty.pdf", make_empty_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_non_pdf_returns_400(client: TestClient) -> None:
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", make_non_pdf_bytes(), "text/plain")},
    )
    assert response.status_code == 400


def test_upload_encrypted_pdf_stored_as_error(client: TestClient) -> None:
    response = client.post(
        "/documents",
        files={"file": ("locked.pdf", make_encrypted_pdf_bytes(), "application/pdf")},
    )
    # The document is accepted and stored, but flagged as an error with a reason.
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "error"
    assert body["page_count"] is None
    assert body["error"]


def test_upload_sanitizes_filename(client: TestClient) -> None:
    response = client.post(
        "/documents",
        files={"file": ("../../evil.pdf", make_pdf_bytes(1), "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "evil.pdf"


def test_oversized_upload_returns_400(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        documents_dir=str(tmp_path / "documents"),
        max_upload_bytes=100,
    )

    def override() -> DocumentService:
        return DocumentService(settings)

    app.dependency_overrides[get_document_service] = override
    try:
        with TestClient(app) as c:
            big = make_pdf_bytes(1) + b"x" * 1000
            response = c.post(
                "/documents",
                files={"file": ("big.pdf", big, "application/pdf")},
            )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
