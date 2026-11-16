# Handoff — Agent 1 (Platform & Architecture)

## Current status
**Milestones 1 and 2 are complete and fully integrated.** All three agents have finished their work
and Agent 1 has performed the final integration, quality review, and Git consolidation. The
repository is on `main`, in sync with `origin/main`
(`https://github.com/NunolacombaRebelo/enterprise-ai-document-assistant.git`).

Milestone 1 delivers: PDF upload + validation + text extraction + local persistence on the backend,
and a professional document-management UI on the frontend (upload, collection table with status
badges, loading/empty/success/error states).

**Milestone 2 (Advanced RAG Infrastructure) — complete.** Agent 1 delivered the platform layer
(dependencies, shared config, the retrieval contract, the Milestone 2 API endpoints, ADRs 0007/0008,
deterministic integration tests, Docker/data-isolation updates). Agent 2 implemented the backend
(chunking, BM25, embedded-Chroma vector store, hybrid retriever, and the three Milestone 2 endpoints)
against `docs/contracts/retrieval.md` — see `docs/handoffs/02-backend.md`. Agent 3 implemented the
frontend search experience (functional BM25 search on the Ask page, auto-index on upload on the
Documents page) against `docs/contracts/api.md` — see `docs/handoffs/03-frontend.md`. The Ask page
was later refined into a **conversational** interface (chat composer + message history) while the
Documents page was simplified (index panel removed, auto-index on upload) — see the 2026-11-16
coordination log entry. The system runs in **lexical-only mode** with **no real model endpoints or
API keys**.

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

### 2026-11-16 — Milestone 2 final integration + Git consolidation (Agent 1)
Full integration review of the complete Milestone 2 implementation (Agent 2 backend + Agent 3
frontend) was performed and the repository was consolidated on `main`.
- **`.gitignore` source-tracking bug (RESOLVED).** The rule is now `/documents/` (root-anchored),
  so it no longer matches the source package `src/.../services/documents/`. Verified via
  `git check-ignore` (exit 1 = not ignored) that all `services/documents/` and `services/retrieval/`
  source files are tracked (`git ls-files` confirms). Runtime paths (`.data/`, `uploads/`) remain
  correctly ignored. No further action needed.
- **ChromaDB zero-vector embedding assessment (no code change; documented).** The
  `_ZeroEmbeddingFunction` returns a fixed 384-dim zero vector — no ONNX model runs, no download.
  `vectors_present` gates `query()` so placeholder vectors are never used for ranking; in
  lexical-only mode Chroma is never queried for similarity. **The "separation of lexical chunk
  storage from Chroma" already exists:** `ChunkStore` (`.data/chunks/*.json`) is the single source
  of truth for chunks and BM25 is rebuilt from it on startup; Chroma is a derived store. No
  refactor is warranted in Milestone 2. **Milestone 3 caveat (coordination note for Agent 2):**
  `_PLACEHOLDER_DIM = 384` is hardcoded to match the default local model's output dimension. If the
  Milestone 3 embedding model has a different output dimension (e.g. `text-embedding-3-small` =
  1536), the collection's fixed dimension will conflict on upsert. Recommend deriving the
  placeholder dimension from the configured embedding model (or creating the collection lazily on
  first real-embedding upsert) when real embeddings land.
- **Frontend Milestone 2 search UI (Agent 3) — verified.** `frontend/api/client.py` now exposes
  `search()`, `index_document()`, and `index_status()` in addition to the Milestone 1 methods.
  `chat.py` is a functional BM25 search workspace (mode indicator, search form, ranked result cards
  with source citations, distinct empty/error states). `documents.py` has a search-index panel
  (global index status + idempotent per-document Index action). The frontend correctly consumes the
  three Milestone 2 endpoints per `docs/contracts/api.md`.
- **End-to-end workflow verified (Dockerized API, port 18000):** upload 4-page PDF → `201`
  `processed`; `POST /documents/{id}/index` → `200` `chunks_indexed=4`, `vectors_added=0`;
  `GET /index/status` → `vectors_present=false`, `retrieval_mode=lexical`; `POST /search`
  "Page 3" → ranked results with correct page attribution, `sources=["bm25"]`, citations present;
  no-match query → `results: []`; empty query → `422`; reindex idempotent (no chunk duplication).
- **Persistence across restart verified:** a fresh `IndexService` over the same dirs rebuilds the
  BM25 index from persisted chunks; the Docker `vector-data` named volume survives container
  recreation (`documents_indexed` and `chunks_indexed` persist across `docker compose up`).
- **No embedding model downloaded/executed in lexical-only mode:** 0 ONNX model files in the vector
  store after indexing; `vectors_added=0`; `vectors_present=false`; mode stays `lexical`.
- **Validation (executed this machine, Windows):** `uv sync --locked` clean (103 packages);
  `uv run ruff check .` passed; `uv run ruff format --check .` passed (92 files); `uv run pytest`
  **221 passed** (106 backend, 101 frontend, 14 integration) in 29.3s; `docker compose config`
  valid. The single pytest warning is the expected Starlette `httpx` deprecation note (harmless —
  `httpx2` is intentionally removed by the `huggingface-hub<1` constraint).
- **Docker (executed this machine, Windows):** `docker compose build` rebuilt both images
  (`enterprise-ai-document-assistant-api:0.1.0`, `enterprise-ai-document-assistant-frontend:0.1.0`);
  `docker compose up -d` (host ports 18000/18501) recreated both containers — both **healthy**.
  Frontend reaches backend over internal network (`http://api:8000/health` → 200). Unrelated
  containers (`ead-web`, `open-webui`, `hp_product_backend`, `hp_warranty_postgres`, `docker-*`,
  `dify-*`) were not touched.
- **Portability/security checks:** no runtime data, `.env`, `.venv`, PDFs, or vector-store files are
  tracked (106 files); no machine-specific absolute paths (`C:\Users\...`, `/home/...`) in any
  tracked file; `.dockerignore` correctly excludes runtime data and secrets.
- **Commit:** consolidated commit on `main` (see below). No push performed.

### 2026-11-16 — Frontend UX iteration integration (Agent 3 conversational Ask + simplified Documents)
Agent 3 delivered a focused frontend refinement on top of the Milestone 2 search UI. Agent 1
performed the integration review, functional validation, quality checks, Docker validation, and Git
consolidation. **Scope verified: only Agent 3's owned files changed** (`frontend/`, `tests/frontend/`,
`docs/frontend.md`, `docs/handoffs/03-frontend.md`) — no Agent 1/2 files touched.
- **Changes reviewed (8 files, +512/−493):**
  - `chat.py` — the Ask page is now a **conversational** interface: bottom-anchored `st.chat_input`
    composer, message history held in session state (`KEY_CONVERSATION`), user/assistant/error
    bubbles, ranked result cards with source citations, suggestion chips in the empty state.
    Clearly labelled "BM25 · keyword retrieval" with a "semantic/AI answers arrive in a later
    milestone" note — **no fabricated LLM answers** (a `generated_answer` slot is reserved for
    Milestone 3 but never populated).
  - `documents.py` — **simplified**: the technical search-index panel was removed; upload now
    **auto-indexes** via `POST /documents/{id}/index` (called once, only when the upload is not an
    error; indexing failure is non-fatal and surfaces a warning while the document stays uploaded).
  - `state.py` — added `KEY_CONVERSATION` (+ init). `theme.py` — added chat-bubble / suggestion-chip /
    result-card CSS; removed the now-unused `.aurora-index-status` and `.aurora-coming-soon` styles.
  - Tests — `test_navigation_theme_upload.py` rewritten for the conversational Ask page (conversation
    render, no-match state, error state) + `test_view_and_theme.py` updated CSS-class assertions.
- **Quality gates (executed this machine, Windows):** `uv sync --locked` clean (103 packages);
  `uv run ruff check .` **passed**; `uv run ruff format --check .` **passed** (92 files);
  `uv run pytest` **223 passed** (106 backend, 103 frontend, 14 integration) in ~19s;
  `docker compose config` **valid**.
- **Docker (executed this machine, Windows):** the running `eaida-frontend` container predated the
  change (no `_auto_index`/`KEY_CONVERSATION` present), so the frontend image was **rebuilt from the
  current source** and the container recreated. Both `eaida-api` (host 18000) and `eaida-frontend`
  (host 18501) are **healthy**; the new code is confirmed present inside the running container.
  Unrelated containers (`ead-web`, `open-webui`, `hp_*`, `docker-*`) were not touched.
- **End-to-end HTTP smoke test (Dockerized API, port 18000, synthetic PDF only):** `GET /health` →
  `ok`; `POST /documents` (multipart) → `201 processed`, `page_count=1`; `POST /documents/{id}/index`
  → `chunks_indexed=1`, `vectors_added=0`; `GET /index/status` → `vectors_present=false`,
  `retrieval_mode=lexical`; `POST /search` "refund policy" → 1 ranked result, `sources=["bm25"]`,
  correct citation (filename + page 1); no-match query → `results: []`, `citations: []` (no dummy
  results). Frontend reachable on 18501 (HTTP 200).
- **Security/portability:** no secrets/credentials in the diff; `.env` not tracked; `.data/`
  git-ignored; no machine-specific absolute paths in the changed files; single worktree, single
  branch (`main`).
- **Commit:** `4523bbf` on `main` (8 files). **No push performed** — `main` is now 2 commits ahead of
  `origin/main`.

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
- Git repository on `main`, in sync with `origin/main` (remote
  `https://github.com/NunolacombaRebelo/enterprise-ai-document-assistant.git`); Milestone 1+2 work
  consolidated in commit `14940d7`.
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
- **Milestone 3 placeholder-dimension caveat.** `VectorStore._PLACEHOLDER_DIM = 384` is hardcoded to
  match the default local model's output dimension. Chroma collections have a fixed dimension per
  collection, so if the Milestone 3 embedding model has a different output dimension (e.g.
  `text-embedding-3-small` = 1536), the upsert will conflict. When real embeddings land, derive the
  placeholder dimension from the configured embedding model (or create the collection lazily on first
  real-embedding upsert). This is a Milestone 3 concern, not a Milestone 2 blocker.
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
### Milestone 2 — COMPLETE
- **Agent 2 (backend): complete.** Chunking, BM25, embedded-Chroma `VectorStore`, `Retriever` with
  lexical/vector/hybrid modes + RRF, and the `POST /documents/{id}/index`, `GET /index/status`,
  `POST /search` endpoints are implemented and tested (see `docs/handoffs/02-backend.md`).
- **Agent 3 (frontend): complete.** Index/status panel on the Documents page + functional BM25
  search workspace on the Ask page, consuming the three Milestone 2 endpoints per
  `docs/contracts/api.md` (see `docs/handoffs/03-frontend.md`).
- **Agent 1:** Milestone 2 integration review is **complete** (see the 2026-11-16 coordination log
  entry). No dependency or config changes were needed. The only forward-looking note for Agent 2 is
  the Milestone 3 placeholder-dimension caveat (see Known limitations).

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
- **Milestone 3:** read `docs/contracts/retrieval.md` — the `EmbeddingProvider` interface is
  defined but has no concrete implementation. Implement a concrete OpenAI-compatible embedding
  provider against `embedding_base_url` / `embedding_api_key`, wire it into `IndexService` and
  `Retriever`, and upsert real vectors over the zero placeholders. Address the
  `_PLACEHOLDER_DIM = 384` caveat (see Known limitations) before activating vector/hybrid mode.
- Extend `src/enterprise_ai_document_assistant/api/main.py` (keep `app` as the app object).
- Add endpoints under `api/`; business logic in `services/`; RAG in `rag/`; providers in
  `providers/`.
- Backend-specific settings can be added to `core/config.py` through coordination if they affect
  shared behavior. The Milestone 2 Chroma/retrieval settings are already present.
- Keep `GET /health` working; it is part of the contract.

### Agent 3 (Frontend) starting points
- **Milestone 3:** extend the conversational Ask page to display grounded LLM answers alongside the
  retrieved passages (clearly separated sections). The `chat.py` assistant message already reserves a
  `generated_answer` slot for this; the result-card rendering is in place (Milestone 2).
- Talk to the backend over HTTP using `API_BASE_URL` (native `http://localhost:8000`, Docker
  `http://api:8000`). Never import backend internals.
- Frontend tests go in `tests/frontend/`.
