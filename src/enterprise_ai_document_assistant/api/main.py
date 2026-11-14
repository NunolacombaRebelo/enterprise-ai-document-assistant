"""FastAPI application.

Phase 0 exposes a single ``GET /health`` endpoint used for infrastructure validation. The full
backend (endpoints, services, RAG, providers) is owned by Agent 2 and will be built on top of this
module. See ``docs/contracts/api.md`` for the contract and ``docs/handoffs/02-backend.md`` for the
handoff to Agent 2.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from enterprise_ai_document_assistant.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())

app = FastAPI(
    title="Enterprise AI Document Assistant",
    version="0.1.0",
    description=(
        "AI document assistant for small businesses. Phase 0 exposes the health endpoint only."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns ``{"status": "ok"}`` per the Phase 0 API contract."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
