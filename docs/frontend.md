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
├─ config.py            # API_BASE_URL + app constants + brand identity (no backend imports)
├─ state.py             # session-state keys + helpers (predictable, no duplicate submits)
├─ theme.py             # "Aurora" design system: colour tokens, logo SVG, injected CSS
├─ api/
│  ├─ __init__.py
│  ├─ client.py         # DocumentAPIClient (httpx): health/upload/list/get + typed errors
│  └─ models.py         # Document dataclass + defensive JSON parsing
└─ components/
   ├─ __init__.py
   ├─ cards.py          # reusable stat card, status badge, section header (presentation-only)
   ├─ layout.py         # page setup, branded sidebar chrome, backend check, banner
   ├─ documents.py      # overview cards + upload panel + card library (search/sort/filter)
   └─ chat.py           # "Ask" page — clearly-identified future area (no fake AI)
```

**Navigation:** the app uses Streamlit's native multipage navigation (`st.navigation` + `st.Page`)
declared in `app.py`. This is the single source of truth for navigation state — there is no
duplicate radio or decorative pill navigation. The native sidebar nav is themed via the
`stSidebarNav` data-testid selector in `theme.py`. Each `st.Page` carries an explicit `url_path`
(`documents` / `ask`) so the active page is stable across reruns and shareable via URL.

**Separation of concerns:**
- `api/client.py` is the **only** module that performs HTTP calls. It is built on `httpx` and is
  fully injectable (a fake transport is used in tests).
- `api/models.py` holds the data model and **defensive parsing** — unexpected or missing fields
  raise a clean `ValueError` that the client maps to a typed error, so the UI never crashes on a
  malformed response.
- `theme.py` is the **single source of truth** for the visual identity (the "Aurora" design
  system): colour tokens, the original logo mark, and the CSS injected on **every rerun**. It
  contains no business logic.
- `components/` are **presentation-only**: they read/write session state, call the client, and map
  typed errors to concise, user-facing messages. `cards.py` holds the reusable card/badge
  building blocks shared across pages.
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

## Visual identity — "Aurora"

The frontend has an original visual identity ("Aurora"): a deep-space AI theme with a deep navy
background, electric blue → violet → cyan gradient accents, and a custom SVG logo mark (no copied
branding). The design system lives in `frontend/theme.py`:

- **Surfaces:** deep navy `#0B1120` page background with subtle radial gradient glows; slate
  `#0F172A` cards/panels; hairline borders.
- **Accents:** electric blue `#3B82F6`, violet `#8B5CF6`, cyan `#22D3EE` (gradient).
- **Semantic:** success `#34D399`, error `#F87171`, warning `#FBBF24`.
- **Components:** rounded cards (14px), soft shadows, pill status badges, gradient-accented stat
  cards, hover/active states on navigation and document cards.

The CSS is injected on **every rerun** via `st.markdown(..., unsafe_allow_html=True)`. It is
deliberately *not* gated by a session-state flag: gating caused the theme to be lost when
navigating between pages (the flag was set on the first page but the CSS element was not re-emitted
on the second page). Re-injecting is cheap (a single `<style>` block) and guarantees the theme is
present on every page and after every rerun. It targets Streamlit's stable element selectors
(including `stHeader`, `stToolbar`, and `stSidebarNav`) plus a small set of bespoke `.aurora-*`
classes — no fragile, deeply-nested selectors.

## UI

- **Branded sidebar:** original logo mark + "Aurora" wordmark + tagline, a live
  backend-connection status pill (green "Backend connected" / red "Backend offline" / amber
  "Checking…"), and the **native** `st.navigation` sidebar nav (Documents / Ask) themed to match the
  Aurora palette. The nav is the single source of truth for navigation state — there is no
  duplicate radio or decorative pill navigation.
- **Documents page:**
  - **Overview cards** — four stat cards derived from **real** backend data (never fabricated):
    Total documents, Processed, Errors, and Backend status. When the collection cannot be loaded
    the document-derived cards show a neutral "—".
   - **Upload panel** — a gradient-accented card with a single, fully-styled `st.file_uploader`
     (PDF only, 25 MB limit stated in the help text to match the backend), a loading spinner, and
     success/error feedback. The decorative drag-and-drop zone was removed so the upload control is
     one coherent, functional element rather than a decorative dropzone plus a separate native
     uploader. On success the collection is refreshed so the new document appears immediately.
  - **Document library** — a responsive grid of document cards (filename, status badge, page
    count, upload timestamp, document ID, and an inline error reason for failed documents) with a
    **client-side toolbar**: search by name, sort (newest / oldest / name A–Z), and filter
    (all / processed / errors). Includes a "no matches" state and a Refresh control.
- **Ask page:** a polished "In development" panel with feature cards (document search,
  natural-language questions, grounded answers, source citations). It is clearly identified as a
  future feature and does not pretend to provide working AI functionality.

### Statuses

The frontend mirrors the backend `DocumentStatus` enum: `processed` and `error`. Status badges are
`Processed` (green) and `Error` (red). Unknown status strings render as a neutral badge (never
dropped), so a future backend status does not break the UI.

### States handled

- **Backend offline** — sidebar status pill (red) + top banner; the app stays navigable and the
  overview cards show a neutral "—".
- **Loading** — spinners for upload and collection load.
- **Empty collection** — a styled empty state ("No documents yet").
- **No matches** — when search/filter excludes all documents.
- **Success** — upload success message; the collection refreshes automatically.
- **Error** — upload failures (invalid PDF, oversized, server error), list failures, and per-document
  processing errors (shown inline on the document card).

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
- `test_view_and_theme.py` — the client-side library view logic (search / sort / filter, including
  combined and no-match cases) and the theme module (logo SVG well-formedness, CSS contains the
  core classes, status-badge variants, and HTML-escaping of card values).
- `test_navigation_theme_upload.py` — `AppTest`-based rendering of the real app: a single native
  `st.navigation` (no duplicate radio / decorative pills), the Aurora theme present and idempotent
  (one `<style>` block) on every rerun, a single PDF-only file uploader with accurate 25 MB
  messaging, the backend status pill states, and the Ask page "coming soon" panel (no fake chat).

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

## Validation (Milestone 1 + visual redesign)

Executed on this machine (Windows):

- `uv run ruff check frontend/ tests/frontend/` — passed.
- `uv run ruff format --check frontend/ tests/frontend/` — passed (my files formatted).
- `uv run pytest tests/frontend/` — **80 passed** (52 original + 14 view/theme + 14
  navigation/theme/upload `AppTest` tests).
- **End-to-end (real backend):** started the FastAPI app on `127.0.0.1:8000`; the frontend client
  uploaded a PDF (→ `processed`, `page_count=1`) and listed the collection through the live HTTP
  API. The Streamlit `AppTest` rendered the redesigned dashboard with **0 exceptions**: overview
  stat cards, the document-card grid (document ID demoted to a details line), the single styled
  file uploader (25 MB help text), processed + error badges, the branded logo, the native
  `st.navigation` sidebar nav (no duplicate radio), the online status pill, and the
  search/sort/filter toolbar. The theme CSS (all `.aurora-*` + `stSidebarNav` + `stHeader` +
  `stFileUploader` classes) was confirmed present in the rendered output as a single `<style>`
  block. The offline state was verified (red status pill, offline banner, neutral stat cards,
  empty state). Test artifacts were cleaned up (`.data/` is git-ignored).

> Note: the full repository `pytest` run also includes the RAG integration tests
> (`tests/integration/test_retrieval_infrastructure.py`). The full suite (backend + frontend +
> integration) is green; the frontend suite (`tests/frontend/`) is fully green.

## Known limitations

- The `Ask` page is a placeholder only; no AI functionality is implemented (out of scope).
- Document **deletion** is not exposed in the UI (no `DELETE /documents/{id}` endpoint in the
  current contract). This is a future addition.
- The frontend's 25 MB upload limit is a client-side pre-check; the backend enforces the real
  limit. If the backend limit changes, `frontend/config.py` should be updated to match.
- The `st.file_uploader` help text states the 25 MB limit, but Streamlit's native uploader also
  shows its own default size cap (200 MB) in the widget. Capping that display value requires a
  `server.maxUploadSize` entry in `streamlit/config.toml`, which is an Agent 1 (Platform) file.
  This is documented as a coordination request in `docs/handoffs/03-frontend.md`; the functional
  25 MB pre-check and backend enforcement are unaffected.
- The theme is a single primary (dark) design. A light-mode toggle is not implemented; the dark
  "Aurora" theme is the consistent primary experience.
- Cross-platform (Linux) frontend rendering was not executed here; the code is portable and follows
  the repo's portability rules.
