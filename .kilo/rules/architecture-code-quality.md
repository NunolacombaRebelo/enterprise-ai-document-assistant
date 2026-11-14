# Architecture and code quality

Guardrails for the modular monolith. The architecture rationale lives in
`docs/architecture/overview.md` and the ADRs in `docs/decisions/`.

## Architecture boundaries
- **Modular monolith** — one Python package, one FastAPI app, one Streamlit frontend. No
  microservices, no message brokers, no external databases in Phase 0–2.
- Package layout (`src/enterprise_ai_document_assistant/`):
  - `api/` — FastAPI app + endpoints (Agent 2). `main.py` holds the `app` object.
  - `core/` — shared configuration/utilities (Agent 1 owns config; Agent 2 may add shared core
    utilities through coordination).
  - `services/` — backend services: ingestion, extraction, chunking, embedding, retrieval (Agent 2).
  - `rag/` — RAG orchestration (Agent 2, future).
  - `providers/` — LLM / embedding / vector-store provider abstractions (Agent 2, future).
- **Frontend** (`frontend/`) — Streamlit app; talks to the backend over HTTP using `API_BASE_URL`
  (Agent 3). It must not import backend internals directly.
- **Communication** — frontend → backend is HTTP only. Do not introduce shared in-process state
  between the two.

## Code quality
- Type hints on all new functions and public APIs.
- Consistent logging via the standard `logging` module (module-level `logger =
  logging.getLogger(__name__)`). Never log secrets or full API keys.
- Configuration comes from `core/config.py` (`pydantic-settings`), not from hard-coded values or
  scattered `os.environ` reads. Add new settings there through coordination.
- Keep modules small and single-purpose. Avoid speculative abstractions for features that are not
  yet implemented (Phase 0 must not pre-build RAG/providers logic).
- Follow Ruff rules as configured in `pyproject.toml` (lint + format). Run both before committing.
- No dead code, no commented-out blocks, no TODO-only stubs that claim to be implemented.

## Dependency discipline
- No unnecessary dependencies. Do not add LangChain / ChromaDB / OpenAI SDKs until their phase
  begins (see `docs/roadmap.md`).
- Only Agent 1 modifies `pyproject.toml` and `uv.lock`. Others request changes via
  `docs/contracts/ownership.md`.
