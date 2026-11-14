"""Integration tests (Agent 1-owned).

Phase 0 contains a minimal placeholder that validates the backend health contract end-to-end via
the in-memory TestClient. Full cross-service integration tests (frontend ↔ backend over HTTP,
Docker Compose) are added by Agent 1 as later phases land.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from enterprise_ai_document_assistant.api.main import app


@pytest.mark.integration
def test_backend_health_contract() -> None:
    """The backend satisfies the Phase 0 health contract (docs/contracts/api.md)."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
