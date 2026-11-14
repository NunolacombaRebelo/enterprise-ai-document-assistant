"""Tests for the Phase 0 health endpoint contract.

Verifies that the FastAPI app exposes ``GET /health`` returning ``{"status": "ok"}``, per
``docs/contracts/api.md``. Uses FastAPI's in-memory TestClient — no network, no credentials.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from enterprise_ai_document_assistant.api.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_is_fastapi_instance() -> None:
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
