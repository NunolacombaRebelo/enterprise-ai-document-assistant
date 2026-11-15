"""API tests for the Milestone 2 retrieval endpoints (and Milestone 1 regression).

Uses FastAPI's in-memory TestClient with temp dirs (via dependency overrides) so no runtime data is
written into the repo. No network, no credentials, no models.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from enterprise_ai_document_assistant.api.documents import get_document_service
from enterprise_ai_document_assistant.api.main import app
from enterprise_ai_document_assistant.api.retrieval import _index_service
from enterprise_ai_document_assistant.core.config import Settings
from enterprise_ai_document_assistant.services.documents.service import DocumentService
from enterprise_ai_document_assistant.services.documents.storage import DocumentStore
from enterprise_ai_document_assistant.services.retrieval.index import IndexService
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore

from .pdf_factory import make_pdf_bytes


@pytest.fixture()
def client(tmp_path) -> TestClient:
    settings = Settings(
        _env_file=None,
        documents_dir=str(tmp_path / "documents"),
        vector_store_path=str(tmp_path / "vector-store"),
    )

    def doc_service() -> DocumentService:
        return DocumentService(settings)

    def index_service() -> IndexService:
        return IndexService(
            settings=settings,
            document_store=DocumentStore(settings.documents_dir),
            vector_store=VectorStore(path=settings.vector_store_path, collection_name="documents"),
        )

    app.dependency_overrides[get_document_service] = doc_service
    app.dependency_overrides[_index_service] = index_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _upload(client: TestClient, filename: str, pages: int = 2) -> str:
    response = client.post(
        "/documents", files={"file": (filename, make_pdf_bytes(pages), "application/pdf")}
    )
    assert response.status_code == 201
    return response.json()["id"]


# --- Milestone 1 regression --------------------------------------------------


def test_health_still_works(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_milestone1_document_endpoints_still_work(client: TestClient) -> None:
    document_id = _upload(client, "a.pdf", pages=1)
    assert client.get("/documents").json()["documents"][0]["id"] == document_id
    assert client.get(f"/documents/{document_id}").status_code == 200
    assert client.get("/documents/unknown").status_code == 404


# --- Milestone 2: index ------------------------------------------------------


def test_index_document_returns_200(client: TestClient) -> None:
    document_id = _upload(client, "policy.pdf", pages=2)
    response = client.post(f"/documents/{document_id}/index")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["chunks_indexed"] >= 1
    assert body["vectors_added"] == 0


def test_index_unknown_document_returns_404(client: TestClient) -> None:
    assert client.post("/documents/does-not-exist/index").status_code == 404


def test_index_error_document_returns_409(client: TestClient) -> None:
    # Upload a non-PDF is rejected (400), so create an error document via an encrypted PDF.
    from .pdf_factory import make_encrypted_pdf_bytes

    response = client.post(
        "/documents", files={"file": ("locked.pdf", make_encrypted_pdf_bytes(), "application/pdf")}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "error"
    document_id = response.json()["id"]
    assert client.post(f"/documents/{document_id}/index").status_code == 409


def test_index_is_idempotent(client: TestClient) -> None:
    document_id = _upload(client, "policy.pdf", pages=2)
    first = client.post(f"/documents/{document_id}/index").json()
    second = client.post(f"/documents/{document_id}/index").json()
    assert first["chunks_indexed"] == second["chunks_indexed"]
    status = client.get("/index/status").json()
    assert status["documents_indexed"] == 1
    assert status["chunks_indexed"] == first["chunks_indexed"]


# --- Milestone 2: status -----------------------------------------------------


def test_index_status_empty(client: TestClient) -> None:
    response = client.get("/index/status")
    assert response.status_code == 200
    body = response.json()
    assert body["documents_indexed"] == 0
    assert body["chunks_indexed"] == 0
    assert body["vectors_present"] is False
    assert body["retrieval_mode"] == "lexical"
    assert body["collection"] == "documents"


def test_index_status_after_indexing(client: TestClient) -> None:
    document_id = _upload(client, "policy.pdf", pages=2)
    client.post(f"/documents/{document_id}/index")
    body = client.get("/index/status").json()
    assert body["documents_indexed"] == 1
    assert body["chunks_indexed"] >= 1


# --- Milestone 2: search -----------------------------------------------------


def test_search_returns_results_with_citations(client: TestClient) -> None:
    document_id = _upload(client, "policy.pdf", pages=4)
    client.post(f"/documents/{document_id}/index")
    # The synthetic PDF text is "Page N synthetic content"; "Page 1" discriminates chunk 0.
    response = client.post("/search", json={"query": "Page 1", "top_k": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Page 1"
    assert body["mode"] == "lexical"
    assert len(body["results"]) >= 1
    top = body["results"][0]
    assert top["document_id"] == document_id
    assert top["filename"] == "policy.pdf"
    assert top["sources"] == ["bm25"]
    assert top["score"] >= 0
    # The top result should be the page-1 chunk (chunk_index 0).
    assert top["chunk_index"] == 0
    # Citations mirror results.
    assert len(body["citations"]) == len(body["results"])
    citation = body["citations"][0]
    assert citation["document_id"] == document_id
    assert citation["filename"] == "policy.pdf"
    assert citation["page"] >= 1
    assert citation["excerpt"]


def test_search_no_match_returns_empty_results(client: TestClient) -> None:
    document_id = _upload(client, "policy.pdf", pages=2)
    client.post(f"/documents/{document_id}/index")
    response = client.post("/search", json={"query": "zzzqqqxyzzy", "top_k": 5})
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["citations"] == []


def test_search_empty_query_returns_422(client: TestClient) -> None:
    assert client.post("/search", json={"query": ""}).status_code == 422
    assert client.post("/search", json={}).status_code == 422


def test_search_invalid_top_k_returns_422(client: TestClient) -> None:
    assert client.post("/search", json={"query": "x", "top_k": 0}).status_code == 422
    assert client.post("/search", json={"query": "x", "top_k": -1}).status_code == 422


def test_search_respects_top_k(client: TestClient) -> None:
    document_id = _upload(client, "policy.pdf", pages=4)
    client.post(f"/documents/{document_id}/index")
    response = client.post("/search", json={"query": "Page 1", "top_k": 1})
    assert response.status_code == 200
    assert len(response.json()["results"]) <= 1


def test_search_before_indexing_returns_empty(client: TestClient) -> None:
    # A document exists but is not indexed -> nothing to search.
    _upload(client, "policy.pdf", pages=4)
    response = client.post("/search", json={"query": "Page 1", "top_k": 5})
    assert response.status_code == 200
    assert response.json()["results"] == []
