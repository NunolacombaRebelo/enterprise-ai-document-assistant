# Handoff — Agent 1 (Platform & Architecture) — Phase 0

## Current status
Phase 0 (Repository foundation) is **complete**. The repository is initialized on `main`, the
engineering foundation is in place, and Agents 2 and 3 can begin work without restructuring the
repository. No remote is configured and nothing has been pushed.

## Completed work
- Git repository initialized on `main` with a local identity (no remote, no push).
- Python project configured: `pyproject.toml`, `.python-version` (3.12), generated `uv.lock`
  (real resolver, 56 packages), `uv sync --locked` verified.
- Package structure created (`src/enterprise_ai_document_assistant/`): `api/`, `core/`, `services/`,
  `rag/`, `providers/`. Minimal `api/main.py` exposes `GET /health → {"status":"ok"}`;
  `core/config.py` provides env-based settings via pydantic-settings.
- Frontend placeholder `frontend/app.py` (Streamlit) for Agent 3 to build on.
- Configuration/security: `.env.example`, `.gitignore`, `.dockerignore`, `.editorconfig`.
- Agent instructions: `AGENTS.md`, five `.kilo/rules/*.md`, `kilo.jsonc`, two skills
  (`implement-feature`, `review-change`).
- Integration contracts: `docs/contracts/api.md`, `docs/contracts/ownership.md`.
- Docker: `docker/api.Dockerfile`, `docker/frontend.Dockerfile`, `compose.yaml` (api:8000,
  frontend:8501, internal net, named volume for future vector store).
- CI: `.github/workflows/ci.yml` (uv setup, locked install, ruff lint, ruff format check, pytest).
- Documentation: `README.md`, `docs/architecture/overview.md`, `docs/development.md`,
  `docs/roadmap.md`, six ADRs in `docs/decisions/`.
- Minimal tests: backend health + config, integration health contract, frontend placeholder.

## Architecture decisions
See `docs/decisions/`:
- 0001 Python 3.12 + FastAPI
- 0002 Streamlit
- 0003 uv
- 0004 Docker Compose
- 0005 Modular monolith
- 0006 AI-agent development rules and multi-agent ownership

## Validation results
Executed on this machine (Windows):
- `uv lock` — resolved 56 packages.
- `uv sync --locked` — installed 55 packages into `.venv/`.
- Import + `GET /health` via TestClient — returned `200 {"status":"ok"}`.
- `uv run ruff check .` — passed. `uv run ruff format --check .` — passed (37 files).
  `uv run pytest` — **8 passed**.
- `docker compose config` — valid.
- `docker compose build` — both images (`api`, `frontend`) built successfully.
- `docker compose up -d` (on alternate host ports to avoid a port clash with other local
  containers) — both containers reached **healthy**; `GET /health` → `{"status":"ok"}`; frontend
  `/_stcore/health` → `ok`, root → HTTP 200. Stack torn down after verification.

## Known limitations
- Cross-platform (Linux) validation was not executed here; the repo is designed to be portable but
  Linux runs are documented, not tested, on this machine.
- The frontend is a placeholder only; no real UI logic exists yet.
- Docker runtime was verified on alternate host ports (18000/18501) because ports 8000/8501 were
  already in use by unrelated containers on this machine; the default ports in `compose.yaml` are
  unchanged and correct for a clean machine.

## Remaining tasks (for later phases)
- Phase 1+: backend endpoints, services, RAG, providers (Agent 2); real frontend (Agent 3).
- Add LangChain/ChromaDB/OpenAI dependencies only when their phase begins, via Agent 1 coordination.
- Expand integration tests as cross-service behavior lands.

## Instructions for Agents 2 and 3
1. Read `AGENTS.md` first, then `docs/contracts/api.md` and `docs/contracts/ownership.md`.
2. Work only within your owned paths (see the ownership table). Do not edit shared config files;
   request changes through Agent 1.
3. Use `uv sync --locked` to install; never hand-edit `pyproject.toml` or `uv.lock`.
4. Follow the coding conventions (type hints, logging, config from `core/config.py`).
5. Add meaningful tests in your owned test directory; run `ruff check`, `ruff format --check`, and
   `pytest` before declaring done.
6. Update your handoff file after each substantial change.
7. Inspect `git status` before changes; stage only your own files; no destructive git commands.

### Agent 2 (Backend) starting points
- Extend `src/enterprise_ai_document_assistant/api/main.py` (keep `app` as the app object).
- Add endpoints under `api/`; business logic in `services/`; RAG in `rag/`; providers in
  `providers/`.
- Backend-specific settings can be added to `core/config.py` through coordination if they affect
  shared behavior.
- Keep `GET /health` working; it is part of the contract.

### Agent 3 (Frontend) starting points
- Build the real UI in `frontend/app.py` (replace the placeholder).
- Talk to the backend over HTTP using `API_BASE_URL` (native `http://localhost:8000`, Docker
  `http://api:8000`). Never import backend internals.
- Frontend tests go in `tests/frontend/`.
