# Handoff — Agent 3 (Frontend Engineering)

## Current status
Milestone 1 (Document Management Interface) is **implemented and validated**. The frontend is a
coherent, professional document-intelligence application: PDF upload, document collection view,
metadata/status presentation, and graceful handling of loading, empty, success, and error states.
The conversational ("Ask") area is a clearly-identified placeholder and does not provide working AI
functionality (out of scope for this milestone).

## What changed
Replaced the Phase 0 placeholder `frontend/app.py` with a modular frontend:

- `frontend/app.py` — application shell (page config, API client, backend check, nav, dispatch).
- `frontend/config.py` — `API_BASE_URL` resolution + app constants (upload limit, timeouts).
- `frontend/state.py` — session-state keys/helpers (predictable behaviour, no duplicate submits).
- `frontend/api/client.py` — `DocumentAPIClient` (httpx): `health`, `upload_document`,
  `list_documents`, `get_document`; typed error hierarchy.
- `frontend/api/models.py` — `Document` dataclass + defensive JSON parsing.
- `frontend/components/layout.py` — sidebar nav, backend-connection indicator, offline banner.
- `frontend/components/documents.py` — upload panel + collection table + status badges + error
  expander.
- `frontend/components/chat.py` — "Ask" placeholder (no fake AI).
- `tests/frontend/` — `conftest.py` (fake httpx transport + path bootstrap), `test_api_client.py`,
  `test_models.py`, `test_config.py`.

No new dependencies were added (uses the existing `httpx` dev dependency). No shared files were
modified.

## API assumptions
The frontend implements the Milestone 1 document endpoints as described in `docs/contracts/api.md`
(now updated by Agent 1/2):

- `POST /documents` — multipart field `file` → `201` with document metadata.
- `GET /documents` — `{"documents": [...]}`.
- `GET /documents/{document_id}` — document metadata; `404` if missing.

Document metadata fields: `id`, `filename`, `status` (`processed` | `error`), `page_count`,
`created_at`, and `error` (reason when status is `error`). The frontend's status handling and
`error` field were aligned to the **actual backend implementation** (`DocumentStatus` enum in
`src/.../services/documents/models.py`), not the initially-assumed values.

## Validation results (actually executed on this machine)
- `uv run ruff check .` — passed.
- `uv run ruff format --check frontend/ tests/frontend/` — passed (my files formatted).
- `uv run pytest` — **87 passed** (52 frontend + Agent 2 backend + integration).
- **End-to-end (real backend):** started the FastAPI app on `127.0.0.1:8000`; the frontend client
  uploaded a PDF (→ `processed`, `page_count=1`) and listed the collection (→ 2 documents) via the
  live HTTP API. The Streamlit `AppTest` rendered the app with "Backend connected", the collection
  table (2 rows), and the error expander for a failed document. Test artifacts were cleaned up
  (`.data/` is git-ignored).
- The frontend suite also includes `TestAgainstRealBackend`, which validates the client against the
  actual FastAPI app in-process (no running server needed).

## Known limitations
- The `Ask` page is a placeholder only; no AI functionality is implemented (out of scope).
- Document **deletion** is not exposed in the UI (no `DELETE /documents/{id}` endpoint in the
  current contract).
- The frontend's 25 MB upload limit is a client-side pre-check; the backend enforces the real limit.
  If the backend limit changes, update `frontend/config.py` to match.
- Cross-platform (Linux) frontend rendering was not executed here; the code is portable and follows
  the repo's portability rules.

## Remaining tasks (for later milestones)
- Milestone 2+: the conversational experience (question input, grounded answers, source citations).
  The `Ask` page and navigation are already scaffolded.
- Add document deletion to the UI once the backend exposes it.
- Consider a richer document detail view (per-document metadata/status) once the backend supports
  more operations.

## Notes for Agent 1 / Agent 2
- The frontend is validated against the **real** backend contract (in-process + live e2e). No
  contract changes are required from the frontend side.
- The frontend reads `API_BASE_URL` from the environment only (native `http://localhost:8000`,
  Docker `http://api:8000`); it does not import backend internals.
- No new dependencies were introduced; the frontend uses the existing `httpx` dev dependency.
- **Unrelated working-tree note:** `src/.../core/config.py` (Agent 2's file) had uncommitted
  modifications when I started; I did not touch it.
