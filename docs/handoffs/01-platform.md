# Handoff — Agent 1 (Platform & Architecture)

## Current status
**Milestone 1 (Document Management) is complete and integrated.** All three agents have finished
their Milestone 1 work and Agent 1 has performed the final integration, quality review, and Git
consolidation. The repository is on `main` (single branch, single worktree, no remote, nothing
pushed).

Milestone 1 delivers: PDF upload + validation + text extraction + local persistence on the backend,
and a professional document-management UI on the frontend (upload, collection table with status
badges, loading/empty/success/error states).

**Milestone 2 (Advanced RAG Infrastructure) — platform + backend complete; frontend search UI
pending.** Agent 1 delivered the platform layer (dependencies, shared config, the retrieval contract,
the Milestone 2 API endpoints, ADRs 0007/0008, deterministic integration tests, Docker/data-isolation
updates). Agent 2 has since implemented the backend (chunking, BM25, embedded-Chroma vector store,
hybrid retriever, and the three Milestone 2 endpoints) against `docs/contracts/retrieval.md` — see
`docs/handoffs/02-backend.md`. The system runs in **lexical-only mode** with **no real model
endpoints or API keys**. Frontend Agent 3 still needs to build the index/status + search UI against
the Milestone 2 endpoints in `docs/contracts/api.md`. See the coordination log entry below.

## Coordination log

### 2026-11-14 — Milestone 2 platform foundation (Agent 1)
Delivered the platform layer for Advanced RAG Infrastructure. **No real model endpoints or API keys;
the system runs in lexical-only mode by default.**
- **Dependencies:** added `chromadb>=1.0` and `rank-bm25>=0.2` to `pyproject.toml` runtime deps.
  Regenerated `uv.lock` with the real resolver (`uv lock`, 103 packages).
- **`httpx2` conflict fix:** `chromadb → huggingface-hub 2.x → httpx2` shadowed `httpx`, breaking
  Starlette's TestClient (it does `try: import httpx2 as httpx`). Added
  `[tool.uv] constraint-dependencies = ["huggingface-hub<1"]` to pin `huggingface-hub 0.36.2` and
  remove `httpx2`/`httpcore2`. Chroma remains fully functional; real `httpx 0.28.1` is intact.
- **Config:** extended `core/config.py` with `vector_store_path`, `chroma_collection`,
  `chroma_distance_fn`, `retrieval_mode` (lexical|vector|hybrid), `rrf_k`, `retrieval_top_k`,
  `rerank_enabled`, `chunk_size_tokens`, `chunk_overlap_tokens`, and optional
  `embedding_base_url` / `embedding_api_key` (default `None`). All have safe defaults; no model key
  required to start.
- **Contracts:** new `docs/contracts/retrieval.md` (Chunk model, chunk metadata schema, index
  lifecycle, BM25/vector/hybrid-RRF/rerank interfaces, search-result + citation schemas, lexical-only
  guarantee, deterministic testing requirements). Extended `docs/contracts/api.md` with Milestone 2
  endpoints (`POST /documents/{id}/index`, `GET /index/status`, `POST /search`) + exact request/response
  schemas.
- **Decisions:** ADR 0007 (embedded ChromaDB, not a dedicated container) and ADR 0008 (hybrid
  retrieval with BM25 + Reciprocal Rank Fusion, provider-abstracted, no LangChain).
- **Docker/data isolation:** the existing `vector-data` named volume at `/app/.data` already covers
  `.data/vector-store` (Chroma persist dir) and `.data/documents`; updated the `compose.yaml` comment
  and `.env.example` accordingly. `.gitignore`/`.dockerignore` already exclude all runtime data.
- **Tests:** new `tests/integration/test_retrieval_infrastructure.py` (13 deterministic tests):
  Chroma init/persistence/collection lifecycle, metadata contract round-trip, RRF exact-value math,
  BM25 determinism, no-provider lexical-only guarantee, and a deterministic embedding double.
- **Docs:** updated `docs/architecture/overview.md` (RAG data flow, provider abstraction, embedded
  Chroma persistence), `docs/roadmap.md` (Milestone 2 platform-complete / impl-pending), and
  `docs/development.md` (vector-store persistence note, `httpx2` troubleshooting row, lexical-only
  note).
- **Validation (executed this machine, Windows):** `uv sync --locked` clean; `uv run ruff check .`
  passed; `uv run ruff format --check .` passed; `uv run pytest` **200 passed** (106 backend, 80
  frontend, 14 integration); `docker compose config` valid.
- **No commit made:** Agent 3 has uncommitted frontend work in the working tree, so per the
  multi-agent protocol Agent 1 did not commit. Commit on `main` once the tree is clear.

### 2026-11-14 — Frontend `ModuleNotFoundError: No module named 'frontend'` (Docker + native)
**Root cause:** the frontend imports itself as a package (`from frontend.api.client import ...`), but
Streamlit adds only the *script's* directory (`frontend/`) to `sys.path`, not the repository root. So
`import frontend` fails both in the Docker image (WORKDIR `/app`, script at `/app/frontend/app.py`)
and when running `uv run streamlit run frontend/app.py` natively from the repo root. The tests passed
only because `tests/frontend/conftest.py` inserts the repo root into `sys.path`.
**Fix (Platform-owned, no Agent 3 source changes):**
- Added `docker/frontend-launch.sh` — a launcher that `cd /app` and runs `/app/.venv/bin/streamlit run
  frontend/app.py`; combined with `PYTHONPATH=/app` this makes `frontend` importable.
- `docker/frontend.Dockerfile`: set `PYTHONPATH=/app`, copy+chmod the launcher while still root, and
  use it as `CMD`.
- Documented the native equivalent in `README.md` and `docs/development.md`: set `PYTHONPATH` to the
  repo root before `streamlit run frontend/app.py`.
**Validation:** rebuilt the frontend image; container healthy; AppTest render inside the container =
0 exceptions, title rendered, "Backend connected"; frontend→backend over internal net OK; healthcheck
negative test confirms it reports `unhealthy` when Streamlit is not serving. Native launch verified on
Windows with `PYTHONPATH` set. `ruff check` / `ruff format --check` / `pytest` (87) all pass.

### 2026-11-14 — Milestone 1 final integration (Agent 1)
Two integration defects were found during end-to-end validation and fixed within Agent 1 ownership:
- **`httpx` was a dev-only dependency but the frontend client imports it at runtime.** A production
  (`--no-dev`) install did not include it, so the Docker frontend image would crash on import.
  Moved `httpx>=0.27` to runtime dependencies in `pyproject.toml`, re-locked (`uv lock`, 57
  packages), and verified it survives a `--no-dev` install and is present in the built frontend image.
- **Docker api container could not write to the mounted data volume.** The named volume at
  `/app/.data` is initialised root-owned, but the container runs as non-root `appuser`. Added
  `docker/api-entrypoint.sh` (runs as root, chowns the volume, then drops to `appuser` via `gosu`)
  and updated `docker/api.Dockerfile` (installs `gosu`, sets the entrypoint). Verified upload/list/get
  and persistence in the volume over the Dockerized API.
Both fixes are in Agent 1-owned files only (`pyproject.toml`, `uv.lock`, `docker/`). No Agent 2/3
files were modified for these fixes.

### 2026-11-14 — Milestone 1: `pypdf` dependency + API contract (Agent 2 request)
- **Dependency:** added `pypdf>=4` to `pyproject.toml` runtime dependencies; regenerated
  `uv.lock` with the real resolver (`uv lock`, now 57 packages, `pypdf 7.1.0` locked with hash).
  Verified reproducible install with `uv sync --locked` and a clean `import pypdf`.
- **Contract:** updated `docs/contracts/api.md` with the Milestone 1 document endpoints
  (`POST /documents`, `GET /documents`, `GET /documents/{document_id}`), the `DocumentMetadata` /
  `DocumentListResponse` models, status codes, and error behaviour — verified against the actual
  implementation and an end-to-end smoke test.
- **Validation run by Agent 1:** `uv run ruff check src tests/backend tests/integration` (passed),
  `uv run ruff format --check src tests/backend tests/integration` (passed, 18 files),
  `uv run pytest tests/backend tests/integration` (**35 passed**), app import + OpenAPI path check
  (all four endpoints present), end-to-end TestClient smoke test (201/200/404/400 + `/health`).
- **Status for Agent 2:** the blocking item is resolved. Re-sync with `uv sync --locked`; CI will now
  include `pypdf`. No commit was made (Agents 2/3 have uncommitted changes).

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
- 0007 Embedded ChromaDB for vector storage (Milestone 2)
- 0008 Hybrid retrieval with BM25 + Reciprocal Rank Fusion, provider-abstracted (Milestone 2)

## Validation results (Milestone 2, executed on this machine, Windows)
- `uv sync --locked` — clean install from the lockfile.
- `uv run ruff check .` — **passed**. `uv run ruff format --check .` — **passed**.
- `uv run pytest` — **200 passed** (106 backend, 80 frontend, 14 integration).
- `docker compose config` — **valid**.
- App starts with no embedding provider configured (`EMBEDDING_API_KEY` unset → `None`) and runs in
  lexical-only mode; `chromadb 1.5.9` + `rank_bm25` import cleanly; real `httpx 0.28.1` intact
  (`httpx2` removed by the `huggingface-hub<1` constraint).

## Validation results (Milestone 1 integration, executed on this machine, Windows)
Dependency / environment:
- `uv sync --locked` — clean install from the lockfile (57 packages).
- `uv run ruff check .` — **passed**. `uv run ruff format --check .` — **passed** (58 files).
- `uv run pytest` — **87 passed** (backend + frontend + integration).
- App starts without LLM credentials (`OPENAI_API_KEY` unset → `None`).
- Production (`--no-dev`) venv verified to include `httpx`, `pypdf`, `streamlit`, `fastapi`.

Integration (real HTTP, synthetic PDFs only):
- Live uvicorn backend + frontend `DocumentAPIClient`: health, upload valid 2-page PDF → `processed`
  (`page_count=2`), list, get-by-id, unknown id → `404`, non-PDF → `400`, encrypted PDF → stored as
  `error` with reason, persistence (`.pdf` + `.json`), frontend offline state → typed error. **13/13**.
- Real Streamlit server started; health endpoint `ok`; frontend client reports "Backend connected"
  against a live backend.

Docker:
- `docker compose config` — valid. `docker compose build` — both images built.
- `docker compose up -d` (alternate host ports 18000/18501 to avoid a clash with unrelated local
  containers) — both containers **healthy**. Upload/list/get through the Dockerized API all correct;
  non-PDF → `400`. Persistence in the named volume confirmed (files owned by `appuser`). Frontend
  reaches the backend over the internal network (`http://api:8000/health` → `{"status":"ok"}`).
  Stack torn down after verification; only resources created for this check were removed.

## Known limitations
- **ChromaDB auto-embeds on `add`.** Chroma requires a `documents` field on `add` and applies its
  default *local* embedding function (no model download) when no custom embedding function is given.
  In lexical-only mode this is harmless — retrieval uses BM25, not Chroma vector queries — and
  Milestone 3 upserts real provider vectors over the placeholder. Agent 2 should be aware of this
  when implementing `VectorStore.add`; see the note in `docs/contracts/retrieval.md`.
- Cross-platform (Linux) validation was not executed here; the repo is designed to be portable but
  Linux runs are documented, not tested, on this machine.
- Browser-based manual verification of the Streamlit UI was **not** performed in this environment;
  the UI was validated via Streamlit's `AppTest` (in-process render) and by confirming the live
  frontend server + client connectivity. A human should click through the UI once for final sign-off.
- Document deletion is not exposed (no `DELETE /documents/{id}` endpoint in the contract yet).
- Scanned/image-only PDFs are classified `processed` with empty text (OCR is out of scope).
- Docker runtime was verified on alternate host ports because 8000/8501 were occupied by unrelated
  containers; the documented defaults in `compose.yaml` are unchanged and correct for a clean machine.

## Remaining tasks
### Milestone 2 — frontend search UI (Agent 3; platform + backend done)
- **Agent 2 (backend): complete.** Chunking, BM25, embedded-Chroma `VectorStore`, `Retriever` with
  lexical/vector/hybrid modes + RRF, and the `POST /documents/{id}/index`, `GET /index/status`,
  `POST /search` endpoints are implemented and tested (see `docs/handoffs/02-backend.md`).
- **Agent 3 (frontend, pending):** index/status UI + a search panel consuming `POST /search`,
  rendering results with filename/page/score and metadata-derived citations. The "Ask" page is
  currently a placeholder; the frontend does not yet call the Milestone 2 endpoints.
- **Agent 1:** review the Milestone 2 implementation at integration time; add any needed dependency
  or config changes via coordination.

### Later milestones (NOT started)
- Milestone 3: concrete OpenAI-compatible embedding provider (real vectors upserted over
  placeholders), vector/hybrid retrieval active, optional reranking, RAG orchestration + grounded
  answer generation with an OpenAI-compatible LLM.
- Milestone 4: source citations attached to generated answers; polished UI/UX.
- Add document deletion once the backend exposes it.

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
- **Milestone 2:** read `docs/contracts/retrieval.md` first — it defines the Chunk model, chunk
  metadata schema, index lifecycle, BM25/vector/hybrid-RRF/rerank interfaces, and the lexical-only
  guarantee. Implement chunking + `BM25Index` (rank-bm25) + embedded-Chroma `VectorStore` +
  `Retriever`, and the three Milestone 2 endpoints from `docs/contracts/api.md`. Embeddings are
  interface-only here (no concrete provider). See ADRs 0007/0008.
- Extend `src/enterprise_ai_document_assistant/api/main.py` (keep `app` as the app object).
- Add endpoints under `api/`; business logic in `services/`; RAG in `rag/`; providers in
  `providers/`.
- Backend-specific settings can be added to `core/config.py` through coordination if they affect
  shared behavior. The Milestone 2 Chroma/retrieval settings are already present.
- Keep `GET /health` working; it is part of the contract.

### Agent 3 (Frontend) starting points
- Build the real UI in `frontend/app.py` (replace the placeholder).
- Talk to the backend over HTTP using `API_BASE_URL` (native `http://localhost:8000`, Docker
  `http://api:8000`). Never import backend internals.
- Frontend tests go in `tests/frontend/`.
