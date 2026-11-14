"""Tests for the frontend API client (``frontend/api/client.py``).

These tests use a fake ``httpx`` transport (see ``conftest.py``) so they verify request
construction and response handling without a real backend, network, or credentials.
"""

from __future__ import annotations

import httpx
import pytest
from frontend.api.client import (
    BackendUnavailableError,
    DocumentAPIClient,
    HTTPStatusError,
    RequestTimeoutError,
    UnexpectedResponseError,
)
from tests.frontend.conftest import json_response, make_transport


class TestHealth:
    def test_health_ok(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(200, {"status": "ok"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        assert client.health() is True

    def test_health_unhealthy_body(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(200, {"status": "degraded"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        assert client.health() is False

    def test_health_non_200(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(503, {"status": "unavailable"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        assert client.health() is False

    def test_health_offline_raises_unavailable(self, base_url: str) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        transport = make_transport(handler)
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(BackendUnavailableError):
            client.health()

    def test_health_timeout_raises(self, base_url: str) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        transport = make_transport(handler)
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(RequestTimeoutError):
            client.health()


class TestRequestConstruction:
    def test_health_hits_health_path(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(200, {"status": "ok"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        client.health()
        assert transport.requests[0].method == "GET"
        assert transport.requests[0].url.path == "/health"

    def test_upload_hits_documents_path_with_multipart(self, base_url: str) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            return json_response(201, {"id": "d1", "filename": "a.pdf", "status": "processed"})

        transport = make_transport(handler)
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        client.upload_document("a.pdf", b"%PDF-1.4 fake")

        req = transport.requests[0]
        assert req.method == "POST"
        assert req.url.path == "/documents"
        # Multipart body must carry the file field.
        assert req.headers["content-type"].startswith("multipart/form-data")
        req.read()
        body = req.content.decode("utf-8", errors="replace")
        assert 'name="file"' in body
        assert "a.pdf" in body

    def test_list_hits_documents_path(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(200, {"documents": []}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        client.list_documents()
        assert transport.requests[0].method == "GET"
        assert transport.requests[0].url.path == "/documents"

    def test_get_hits_document_detail_path(self, base_url: str) -> None:
        transport = make_transport(
            lambda req: json_response(200, {"id": "d1", "filename": "a.pdf", "status": "processed"})
        )
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        client.get_document("d1")
        assert transport.requests[0].method == "GET"
        assert transport.requests[0].url.path == "/documents/d1"

    def test_base_url_trailing_slash_normalised(self) -> None:
        transport = make_transport(lambda req: json_response(200, {"documents": []}))
        client = DocumentAPIClient(base_url="http://testserver/", transport=transport)
        client.list_documents()
        assert transport.requests[0].url.path == "/documents"


class TestUpload:
    def test_upload_success_returns_document(self, base_url: str) -> None:
        payload = {
            "id": "d1",
            "filename": "report.pdf",
            "status": "processed",
            "page_count": 12,
            "created_at": "2026-11-14T10:00:00Z",
        }
        transport = make_transport(lambda req: json_response(201, payload))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        doc = client.upload_document("report.pdf", b"%PDF-1.4 fake")
        assert doc.id == "d1"
        assert doc.filename == "report.pdf"
        assert doc.status == "processed"
        assert doc.page_count == 12
        assert doc.created_at is not None

    def test_upload_400_raises_http_status_error(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(400, {"detail": "invalid file"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(HTTPStatusError) as exc:
            client.upload_document("bad.pdf", b"not a pdf")
        assert exc.value.status_code == 400
        assert "invalid file" in exc.value.detail

    def test_upload_413_is_too_large(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(413, {"detail": "file too large"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(HTTPStatusError) as exc:
            client.upload_document("big.pdf", b"x")
        assert exc.value.status_code == 413

    def test_upload_500_is_server_error(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(500, {"detail": "boom"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(HTTPStatusError) as exc:
            client.upload_document("a.pdf", b"%PDF")
        assert exc.value.status_code == 500

    def test_upload_unexpected_body_raises(self, base_url: str) -> None:
        # 201 but the body is not a valid document object.
        transport = make_transport(lambda req: json_response(201, {"unexpected": True}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(UnexpectedResponseError):
            client.upload_document("a.pdf", b"%PDF")

    def test_upload_offline_raises_unavailable(self, base_url: str) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route")

        transport = make_transport(handler)
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(BackendUnavailableError):
            client.upload_document("a.pdf", b"%PDF")

    def test_upload_timeout_raises(self, base_url: str) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow")

        transport = make_transport(handler)
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(RequestTimeoutError):
            client.upload_document("a.pdf", b"%PDF")


class TestListDocuments:
    def test_list_success_parses_documents(self, base_url: str) -> None:
        payload = {
            "documents": [
                {"id": "d1", "filename": "a.pdf", "status": "processed", "page_count": 3},
                {"id": "d2", "filename": "b.pdf", "status": "error", "error": "bad pdf"},
            ]
        }
        transport = make_transport(lambda req: json_response(200, payload))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        docs = client.list_documents()
        assert [d.id for d in docs] == ["d1", "d2"]
        assert docs[0].page_count == 3
        assert docs[1].page_count is None

    def test_list_empty_collection(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(200, {"documents": []}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        assert client.list_documents() == []

    def test_list_404_raises_http_status_error(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(404, {"detail": "not found"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(HTTPStatusError) as exc:
            client.list_documents()
        assert exc.value.status_code == 404

    def test_list_bad_shape_raises(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(200, {"no_documents": True}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(UnexpectedResponseError):
            client.list_documents()

    def test_list_offline_raises_unavailable(self, base_url: str) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline")

        transport = make_transport(handler)
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(BackendUnavailableError):
            client.list_documents()


class TestGetDocument:
    def test_get_success(self, base_url: str) -> None:
        payload = {"id": "d1", "filename": "a.pdf", "status": "processed", "page_count": 5}
        transport = make_transport(lambda req: json_response(200, payload))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        doc = client.get_document("d1")
        assert doc.id == "d1"
        assert doc.status == "processed"

    def test_get_404_raises(self, base_url: str) -> None:
        transport = make_transport(lambda req: json_response(404, {"detail": "not found"}))
        client = DocumentAPIClient(base_url=base_url, transport=transport)
        with pytest.raises(HTTPStatusError) as exc:
            client.get_document("missing")
        assert exc.value.status_code == 404


class TestAgainstRealBackend:
    """Validate the frontend client against the actual FastAPI backend contract.

    Uses FastAPI's TestClient as the httpx transport, so the real request/response shapes (status
    codes, JSON fields, multipart field name) are exercised without a running server, network, or
    credentials. This is the closest thing to a real end-to-end check available in the frontend
    suite; it confirms the frontend client matches the backend contract.
    """

    @pytest.fixture
    def real_transport(self):
        from fastapi.testclient import TestClient

        from enterprise_ai_document_assistant.api.main import app

        # TestClient exposes its ASGI transport as ``_transport``; reuse it so the frontend
        # client hits the real backend app in-process.
        return TestClient(app)._transport

    def test_health(self, real_transport) -> None:
        client = DocumentAPIClient(base_url="http://testserver", transport=real_transport)
        assert client.health() is True

    def test_upload_then_list(self, real_transport, tmp_path) -> None:
        # A minimal but valid PDF (header + EOF marker) so the backend accepts it.
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF"
        client = DocumentAPIClient(base_url="http://testserver", transport=real_transport)

        doc = client.upload_document("contract.pdf", pdf_bytes)
        assert doc.id
        assert doc.filename == "contract.pdf"
        assert doc.status in ("processed", "error")
        assert doc.created_at is not None

        docs = client.list_documents()
        assert any(d.id == doc.id for d in docs)

    def test_get_missing_404(self, real_transport) -> None:
        client = DocumentAPIClient(base_url="http://testserver", transport=real_transport)
        with pytest.raises(HTTPStatusError) as exc:
            client.get_document("does-not-exist")
        assert exc.value.status_code == 404

    def test_upload_non_pdf_rejected(self, real_transport) -> None:
        client = DocumentAPIClient(base_url="http://testserver", transport=real_transport)
        with pytest.raises(HTTPStatusError) as exc:
            client.upload_document("not-a-pdf.pdf", b"this is not a pdf at all")
        assert exc.value.status_code == 400
