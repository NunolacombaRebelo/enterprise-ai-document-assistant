# Handoff — Agent 2 (Backend Engineering)

## Current status
**Milestone 1 (Document Management) is implemented and validated.** PDF upload, validation, text
extraction, local persistence, listing, and status retrieval are functional and tested. The Phase 0
`GET /health` endpoint remains operational.

## What changed (Milestone 1)
- `src/enterprise_ai_document_assistant/api/main.py` — included the documents router; `app` and
  `GET /health` preserved.
- `src/enterprise_ai_document_assistant/api/documents.py` — new thin HTTP router
  (`POST /documents`, `GET /documents`, `GET /documents/{id}`).
- `src/enterprise_ai_document_assistant/services/documents/` — new service package:
  - `models.py` — `DocumentMetadata`, `DocumentListResponse`, `DocumentStatus`.
  - `validation.py` — type/size/magic/filename/path-traversal validation.
  - `extraction.py` — `pypdf` wrapper + `EncryptedPdfError` / `MalformedPdfError`.
  - `storage.py` — local development persistence (`<id>.pdf` + `<id>.json`).
  - `service.py` — `DocumentService` orchestration.
- `src/enterprise_ai_document_assistant/core/config.py` — added backend-specific settings
  `documents_dir` (default `.data/documents`) and `max_upload_bytes` (default 25 MiB).
- `tests/backend/` — `pdf_factory.py` (synthetic PDF fixtures) + `test_validation.py`,
  `test_extraction.py`, `test_storage.py`, `test_documents_api.py`.
- `docs/backend.md` — new backend documentation.

## API behaviour (proposed Milestone 1 contract addition)
- `POST /documents` (multipart field `file`) → `201` + `DocumentMetadata`; `400` for empty /
  non-PDF / oversized uploads.
- `GET /documents` → `200` `{"documents": [...]}` (most recent first).
- `GET /documents/{document_id}` → `200` + `DocumentMetadata`; `404` unknown id.
- `DocumentMetadata`: `id`, `filename`, `status` (`processed`|`error`), `page_count` (nullable),
  `created_at`, `error` (nullable).
- Encrypted / malformed PDFs are **accepted and stored** as `status: "error"` with a reason;
  invalid uploads are **rejected** with `400`.

## ⚠️ Coordination requests for Agent 1

### 1. Dependency: `pypdf` (BLOCKING for CI)
- **Package:** `pypdf` (runtime dependency).
- **Version constraint:** `pypdf>=4` (validated locally with `pypdf==7.1.0`).
- **Why:** Milestone 1 requires PDF text extraction and page count. `pypdf` is pure-Python (no
  native build), portable across Windows/Linux/Docker, and handles encrypted/empty/malformed PDFs
  gracefully. It is the standard lightweight choice and keeps the dependency surface minimal.
- **Phase:** Milestone 1 (Phase 1 of the roadmap — PDF upload and text extraction).
- **Action requested:** add `pypdf` to `pyproject.toml` dependencies and run `uv lock`. I have NOT
  modified `pyproject.toml` or `uv.lock`. I installed `pypdf` into the local venv only for
  validation; please confirm in `docs/handoffs/01-platform.md` and I will re-sync with
  `uv sync --locked`.

### 2. Contract: add Milestone 1 endpoints to `docs/contracts/api.md`
- The endpoints above are a **proposed addition** to the Phase 0 contract (which currently lists
  only `GET /health`). Please add them to `docs/contracts/api.md` so Agent 3 can build the frontend
  against the exact same behaviour. `GET /health` is unchanged.

## Validation results (executed on this machine, Windows)
- `uv run ruff check src tests/backend` — **passed** (all checks).
- `uv run ruff format --check src tests/backend` — **passed** (17 files).
- `uv run pytest tests/backend tests/integration` — **35 passed** (backend + integration health
  contract).
- End-to-end smoke test (TestClient, temp dir): `POST /documents` → `201` with `page_count`;
  `GET /documents` → lists it; `GET /documents/{id}` → returns metadata; `GET /health` → `ok`;
  PDF + JSON persisted to the temp documents dir.
- No runtime data was written into the repository (`.data/` not created; tests use temp dirs).

## Known limitations
- `pypdf` is not yet declared in `pyproject.toml`/`uv.lock` (pending Agent 1). Until it is added,
  a clean `uv sync --locked` will not include it and CI will fail on the import. **This is the one
  blocking item for a clean-machine/CI run.**
- Scanned/image-only PDFs are classified `processed` with empty text (page count known). OCR is out
  of scope for Milestone 1.
- Single-user local development storage (filesystem); no multi-tenancy, background processing, or
  vector store (later milestones).
- Cross-platform (Linux) validation was not executed here; the code is portable (pure-Python deps,
  relative paths, no machine-specific values) but Linux runs are documented, not tested, on this
  machine.

## Remaining tasks (for later milestones — NOT started)
- Milestone 2: chunking, embeddings, ChromaDB indexing (requires LangChain/ChromaDB via Agent 1).
- Milestone 3: retrieval + LLM integration (requires an LLM provider via Agent 1).
- Milestone 4: source citations.
- Frontend upload UI is Agent 3's (against the contract above).

## Instructions / notes for Agents 1 and 3
- **Agent 1:** please add `pypdf` and the Milestone 1 endpoints to the contract (see requests
  above). The backend is otherwise complete for Milestone 1.
- **Agent 3:** the API is ready to build against. `POST /documents` takes a multipart field named
  `file`; responses are the JSON shapes in `docs/backend.md`. `GET /documents` returns
  `{"documents": [...]}`.
