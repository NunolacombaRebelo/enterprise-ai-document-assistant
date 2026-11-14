# Frontend — Enterprise AI Document Assistant

The Streamlit frontend is a professional document-intelligence application for small businesses.
Milestone 1 delivers the **document management experience**: upload PDFs, manage the collection,
and inspect metadata and processing status. The conversational ("Ask") experience is a clearly
identified future area and does not provide working AI functionality.

Owned by Agent 3 (Frontend Engineering). See `docs/contracts/api.md` for the integration contract
and `docs/handoffs/03-frontend.md` for the handoff.

## Stack

- Python 3.12 (managed by `uv`)
- Streamlit (entrypoint `frontend/app.py`, port `8501`)
- HTTP communication with the FastAPI backend via `httpx`
- pytest + Ruff (configured in `pyproject.toml`)

The frontend is **independent of backend business logic**: it never imports backend internals and
never performs PDF processing, embeddings, retrieval, or model invocation. All document operations
go through the HTTP API at `API_BASE_URL`.

## Configuration

The backend base URL is read from the `API_BASE_URL` environment variable (see
`frontend/config.py`):

| Environment | Value |
| --- | --- |
| Native default | `http://localhost:8000` |
| Docker Compose | `http://api:8000` (set in `compose.yaml`) |

Other frontend constants (app title, upload limit, timeouts) live in `frontend/config.py`. The
upload limit (`MAX_UPLOAD_BYTES = 25 MB`) matches the backend's `max_upload_bytes` so the user gets
fast client-side feedback before a request is sent; the backend remains the source of truth.

## Architecture

```
frontend/
├─ app.py               # entrypoint: page config, client, backend check, nav, page dispatch
├─ config.py            # API_BASE_URL + app constants (no backend imports)
├─ state.py             # session-state keys + helpers (predictable, no duplicate submits)
├─ api/
│  ├─ __init__.py
│  ├─ client.py         # DocumentAPIClient (httpx): health/upload/list/get + typed errors
│  └─ models.py         # Document dataclass + defensive JSON parsing
└─ components/
   ├─ __init__.py
   ├─ layout.py         # sidebar nav, backend-connection indicator, offline banner
   ├─ documents.py      # upload panel + collection table + status badges + error expander
   └─ chat.py           # "Ask" page — clearly-identified future area (no fake AI)
```

**Separation of concerns:**
- `api/client.py` is the **only** module that performs HTTP calls. It is built on `httpx` and is
  fully injectable (a fake transport is used in tests).
- `api/models.py` holds the data model and **defensive parsing** — unexpected or missing fields
  raise a clean `ValueError` that the client maps to a typed error, so the UI never crashes on a
  malformed response.
- `components/` are **presentation-only**: they read/write session state, call the client, and map
  typed errors to concise, user-facing messages.
- `state.py` centralises session-state keys so behaviour stays predictable across Streamlit reruns.

### API client error model

The client never raises raw `httpx` exceptions to the UI. It raises a small set of typed errors:

| Exception | Meaning |
| --- | --- |
| `BackendUnavailableError` | Backend offline / connection refused / DNS failure |
| `RequestTimeoutError` | Request exceeded the configured timeout |
| `HTTPStatusError` | Non-2xx response (carries `status_code` + a short, safe `detail`) |
| `UnexpectedResponseError` | 2xx response whose body did not match the expected shape |
| `APIError` | Base class for the above |

The presentation layer maps these to concise messages and never exposes raw internal exceptions.

## UI

- **Sidebar:** app title, navigation (Documents / Ask), and a live backend-connection indicator
  (green "Backend connected" / red "Backend offline").
- **Documents page:**
  - **Upload panel** — PDF file picker with client-side pre-validation (PDF type, 25 MB limit),
    an Upload button, a loading spinner, and success/error feedback.
  - **Collection** — a table with `Filename`, `Status` (badge), `Pages`, `Added`, `ID`; a Refresh
    control; an empty state; and an expander listing the reason for any document that failed to
    process.
- **Ask page:** a clearly-labelled "coming in a future milestone" placeholder. It establishes the
  navigation structure but does not pretend to provide working AI functionality.

### Statuses

The frontend mirrors the backend `DocumentStatus` enum: `processed` and `error`. Status badges are
`✅ Processed` and `⚠️ Error`. Unknown status strings are rendered verbatim (never dropped), so a
future backend status does not break the UI.

### States handled

- **Backend offline** — sidebar indicator + top banner; the app stays navigable.
- **Loading** — spinners for upload and collection load.
- **Empty collection** — "No documents yet" info.
- **Success** — upload success message with the document ID.
- **Error** — upload failures (invalid PDF, oversized, server error), list failures, and per-document
  processing errors (shown in an expander).

## Testing

Frontend tests live in `tests/frontend/` and **do not require a running production backend, real
credentials, or network access**:

- `test_api_client.py` — request construction (method, path, multipart field), upload 201 handling,
  list parsing, and error states (400/404/413/500, timeout, offline, unexpected body). A
  `TestAgainstRealBackend` class additionally validates the client against the **actual FastAPI
  app** in-process (via `TestClient`'s transport) to confirm the request/response shapes match the
  backend contract.
- `test_models.py` — document/list parsing, required-field validation, the `error` field, and
  status semantics.
- `test_config.py` — `API_BASE_URL` resolution (default, env override, trailing-slash, blank) and
  PDF filename detection.

A `conftest.py` provides a fake `httpx` transport and makes the `frontend` package importable.

## Running

Native (with the backend running):

```bash
uv sync --locked
uv run streamlit run frontend/app.py
```

Docker Compose (see `docs/development.md`):

```bash
docker compose up
```

## Validation (Milestone 1)

Executed on this machine (Windows):

- `uv run ruff check .` — passed.
- `uv run ruff format --check frontend/ tests/frontend/` — passed (my files formatted).
- `uv run pytest` — **87 passed** (52 frontend + backend + integration).
- **End-to-end (real backend):** started the FastAPI app on `127.0.0.1:8000`; the frontend client
  uploaded a PDF (→ `processed`, `page_count=1`) and listed the collection (→ 2 documents) through
  the live HTTP API. The Streamlit `AppTest` rendered the app with "Backend connected", the
  collection table (2 rows), and the error expander for a failed document. Test artifacts were
  cleaned up (`.data/` is git-ignored).

## Known limitations

- The `Ask` page is a placeholder only; no AI functionality is implemented (out of scope for
  Milestone 1).
- Document **deletion** is not exposed in the UI (no `DELETE /documents/{id}` endpoint in the
  current contract). This is a future addition.
- The frontend's 25 MB upload limit is a client-side pre-check; the backend enforces the real
  limit. If the backend limit changes, `frontend/config.py` should be updated to match.
