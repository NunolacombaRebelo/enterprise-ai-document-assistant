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
│  ├─ client.py         # DocumentAPIClient (httpx): health/upload/list/get + index/search + typed errors
│  └─ models.py         # Document + SearchResult/Citation/IndexStatus/IndexResult + defensive parsing
└─ components/
   ├─ __init__.py
   ├─ cards.py          # reusable stat card, status badge, section header (presentation-only)
   ├─ layout.py         # page setup, sidebar brand/nav/status, backend check, banner
   ├─ documents.py      # overview cards + upload panel + search-index panel + card library
   └─ chat.py           # "Ask" page — functional BM25 document-search workspace (no fake AI)
```

**Navigation:** the app uses Streamlit's native multipage navigation (`st.navigation` + `st.Page`)
declared in `app.py`. This is the single source of truth for navigation state — there is no
duplicate radio or decorative pill navigation. `st.navigation` is rendered **hidden**
(`position="hidden"`) so the sidebar can be ordered **brand → navigation → status**; the visible
nav is drawn with one `st.page_link` per page (the same native widget the sidebar nav uses, so it
keeps the active-page highlight and URL routing). The page links are themed via the `stPageLink`
data-testid selector in `theme.py`. Each `st.Page` carries an explicit `url_path`
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

### Milestone 2 — retrieval API integration

The client exposes three additional methods that map 1:1 to the backend retrieval contract
(`docs/contracts/api.md`):

| Method | Endpoint | Returns |
| --- | --- | --- |
| `search(query, top_k=None)` | `POST /search` | `SearchResponse` (`query`, `mode`, `results[]`, `citations[]`) |
| `index_document(document_id)` | `POST /documents/{id}/index` | `IndexResult` (`document_id`, `chunks_indexed`, `vectors_added`) |
| `index_status()` | `GET /index/status` | `IndexStatus` (`documents_indexed`, `chunks_indexed`, `vectors_present`, `retrieval_mode`, `collection`) |

The models (`SearchResult`, `Citation`, `SearchResponse`, `IndexStatus`, `IndexResult`) and their
defensive parsers live in `api/models.py`. A `top_k` of `None` is omitted from the request body so
the backend default applies. Empty / invalid queries surface as `HTTPStatusError(422)`; an unknown
document as `HTTPStatusError(404)`; a document with no extractable text as `HTTPStatusError(409)`.

> **BM25 note (not a bug):** on very small corpora, a term that appears in *every* chunk has
> inverse-document-frequency ≤ 0, which rank-bm25 clamps to 0, so that term contributes no score and
> the query can return no matches. This is documented in the backend handoff; the frontend simply
> renders the (possibly empty) result set honestly.

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
(including `stHeader`, `stToolbar`, and `stPageLink`) plus a small set of bespoke `.aurora-*`
classes — no fragile, deeply-nested selectors.

## UI

- **Branded sidebar:** original logo mark + "Aurora" wordmark + tagline, the **native** page
  navigation (Documents / Ask) drawn with `st.page_link` and themed to match the Aurora palette,
  and a live backend-connection status pill (green "Backend connected" / red "Backend offline" /
  amber "Checking…"). The sidebar is ordered **brand → navigation → status** for a clear visual
  hierarchy. The nav is the single source of truth for navigation state — there is no duplicate
  radio or decorative pill navigation.
- **Documents page:**
  - **Overview cards** — four stat cards derived from **real** backend data (never fabricated):
    Total documents, Processed, Errors, and Backend status. When the collection cannot be loaded
    the document-derived cards show a neutral "—".
    - **Upload panel** — a gradient-accented card with a single, fully-styled `st.file_uploader`
      (PDF only, 25 MB limit stated in the help text to match the backend), a loading spinner, and
      success/error feedback. The decorative drag-and-drop zone was removed so the upload control is
      one coherent, functional element rather than a decorative dropzone plus a separate native
      uploader. On success the collection is refreshed so the new document appears immediately.
  - **Search-index panel** — a card that shows the **real** global index status (documents indexed,
    chunks, retrieval mode, vectors present) and offers an idempotent **Index document** action: a
    selectbox of processed documents + a button that calls `POST /documents/{id}/index`. The result
    (chunks indexed) is shown immediately; 404/409/5xx are mapped to concise messages. Index status
    is cached in session state and best-effort (an offline backend shows "Index status unavailable."
    rather than crashing).
  - **Document library** — a responsive grid of document cards (filename, status badge, page
    count, upload timestamp, document ID, and an inline error reason for failed documents) with a
    **client-side toolbar**: search by name, sort (newest / oldest / name A–Z), and filter
    (all / processed / errors). Includes a "no matches" state and a Refresh control.
- **Ask page (Milestone 2 — functional document search):** a real **BM25 lexical retrieval
  workspace**, not a generative-AI chat. It shows:
  - A clear **retrieval-mode indicator** ("BM25 · keyword retrieval") with an honest note that
    semantic / AI answers arrive in a later milestone.
  - A `st.form` search panel (query input + "Search documents" submit) plus example-query buttons
    (shown only before the first search).
  - **Ranked result cards**: rank badge, filename, page, score, an expandable passage, and a source
    citation line — all from the real `POST /search` response.
  - Distinct states: initial guidance (with a "no documents indexed yet" variant that points to the
    Documents page), a "no matching passages" state (a valid empty result, not an error), and
    concise error messages for offline / timeout / HTTP / unexpected responses.
  - No AI-generated answers are fabricated; results are real retrieved passages with citations.

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
- **Success** — upload success message; the collection refreshes automatically; index success
  message with the chunk count.
- **Error** — upload failures (invalid PDF, oversized, server error), list failures, per-document
  processing errors (shown inline on the document card), index failures (404 unknown document,
  409 no extractable text, 5xx), and search failures (offline / timeout / 422 / 5xx / unexpected
  body) — all mapped to concise, user-facing messages.
- **Search: no results** — a styled "No matching passages found" state (a valid empty result, not
  an error) with guidance to try different keywords or index more documents.
- **Search: nothing indexed** — an initial-guidance variant that explains no documents are indexed
  yet and points to the Documents page.

## Testing

Frontend tests live in `tests/frontend/` and **do not require a running production backend, real
credentials, or network access**:

- `test_api_client.py` — request construction (method, path, multipart field), upload 201 handling,
  list parsing, and error states (400/404/413/500, timeout, offline, unexpected body). Milestone 2
  adds `TestSearch` (request construction, `top_k` omission, response parsing, empty results, 422,
  offline, timeout, unexpected body), `TestIndexDocument` (construction, 404, 409, offline), and
  `TestIndexStatus` (construction, offline). A `TestAgainstRealBackend` class and a
  `TestRetrievalAgainstRealBackend` class additionally validate the client against the **actual
  FastAPI app** in-process (via `TestClient`'s transport) to confirm the request/response shapes
  match the backend contract (index status shape, empty-index search, 404, 422).
- `test_models.py` — document/list parsing, required-field validation, the `error` field, and
  status semantics; plus search-result / citation / index-status / index-result parsing.
- `test_config.py` — `API_BASE_URL` resolution (default, env override, trailing-slash, blank) and
  PDF filename detection.
- `test_view_and_theme.py` — the client-side library view logic (search / sort / filter, including
  combined and no-match cases) and the theme module (logo SVG well-formedness, CSS contains the
  core classes — now including `stPageLink`, `.aurora-mode`, `.aurora-result`,
  `.aurora-index-status` — status-badge variants, and HTML-escaping of card values).
- `test_navigation_theme_upload.py` — `AppTest`-based rendering of the real app: a single native
  `st.navigation` (no duplicate radio / decorative pills), the Aurora theme present and idempotent
  (one `<style>` block) on every rerun, a single PDF-only file uploader with accurate 25 MB
  messaging, the backend status pill states, the sidebar hierarchy (brand → nav → status) with
  `st.page_link` elements, and the Ask page search workspace (mode indicator, search input, example
  buttons, no fake chat) plus rendered result cards.

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

## Validation (Milestone 2 — document search & retrieval)

Executed on this machine (Windows):

- `uv run ruff check .` — passed (whole repo clean).
- `uv run ruff format --check .` — passed (92 files already formatted).
- `uv run pytest tests/frontend/` — **101 passed** (Milestone 1 suite + 18 new tests for the
  search / index / status API client and the Ask search workspace).
- `uv run pytest` (full repo: backend + frontend + integration) — **221 passed**.
- **End-to-end (real backend, live HTTP):** started the FastAPI app on `127.0.0.1:8000` and drove
  the full cycle through the frontend client:
  1. Upload a 3-page PDF → `processed`, `page_count=3`.
  2. `POST /documents/{id}/index` → `chunks_indexed=3`, `vectors_added=0` (lexical-only).
  3. `GET /index/status` → `documents_indexed`, `chunks_indexed`, `retrieval_mode=lexical`,
     `vectors_present=False`.
  4. `POST /search` "Page 2" → ranked results, top result on page 2, citations present.
  5. No-match query → `results: []` (valid empty, not an error).
  6. Empty query → `HTTPStatusError(422)`.
- **Streamlit `AppTest`:** the Ask page renders with **0 exceptions** — BM25 mode indicator, search
  input, example-query buttons, and the empty/guidance states; result cards render with rank,
  filename, page, score, expandable passage, and citation. The sidebar renders in the order
  brand → `st.page_link` nav → status pill. The theme CSS (all `.aurora-*` + `stPageLink` +
  `stHeader` + `stFileUploader` classes) is present as a single `<style>` block.

> Note: the full repository `pytest` run also includes the RAG integration tests
> (`tests/integration/test_retrieval_infrastructure.py`). The full suite (backend + frontend +
> integration) is green; the frontend suite (`tests/frontend/`) is fully green.

## Known limitations

- The `Ask` page performs **lexical (BM25) retrieval only**. Natural-language question answering
  and grounded LLM answers are out of scope for Milestone 2 (planned Milestone 3+); the UI is
  clearly labelled as "BM25 · keyword retrieval" and does not fabricate AI answers.
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
