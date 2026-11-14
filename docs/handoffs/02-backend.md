# Handoff — Agent 2 (Backend Engineering)

## Current status
**Not started.** Phase 0 provides the foundation; Agent 2 begins backend work from here.

## Starting points
- Read `AGENTS.md`, `docs/contracts/api.md`, and `docs/contracts/ownership.md` first.
- The FastAPI app object is `app` in `src/enterprise_ai_document_assistant/api/main.py`.
- `GET /health → {"status":"ok"}` is already implemented and is part of the contract — keep it.
- Configuration lives in `src/enterprise_ai_document_assistant/core/config.py`.
- Backend tests live in `tests/backend/`.

## Owned paths
- `src/enterprise_ai_document_assistant/`
- `tests/backend/`
- `docs/backend.md`
- `docs/handoffs/02-backend.md` (this file)

## Conventions
- Type hints on all new functions/public APIs; module-level `logger = logging.getLogger(__name__)`.
- No speculative RAG/provider code before its phase (see `docs/roadmap.md`).
- New dependencies only via Agent 1 coordination (`pyproject.toml` / `uv.lock`).

## Update this file after each substantial change: what changed, what was validated, limitations,
remaining tasks, and anything Agent 1/3 must know.
