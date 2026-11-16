# Handoff — Agent 3 (Frontend Engineering)

## Current status
**Milestone 2 (Document Search & Retrieval Experience) is implemented and validated.** The "Ask"
page is now a **functional BM25 lexical-retrieval workspace** (no fake AI), the Documents page gained
a **search-index panel** (status + idempotent per-document index action), and the UI received a
focused **UX refinement** (wider responsive layout, larger typography, and a clear sidebar
hierarchy: brand → navigation → status). All Milestone 1 functionality is preserved. The
conversational / grounded-answer experience remains a clearly-labelled future area (Milestone 3+).

This handoff supersedes the Milestone 1 UI/UX-refinement notes below; both are retained for history.

## Milestone 2 — Document Search & Retrieval Experience

All changes are within Agent 3 ownership (`frontend/`, `tests/frontend/`). No backend, dependency,
or infrastructure changes. The frontend now consumes the three retrieval endpoints already shipped
by the backend (Milestone 2, lexical-only).

### What was built
1. **API client + models (`frontend/api/`).** Added `SearchResult`, `Citation`, `SearchResponse`,
   `IndexStatus`, `IndexResult` dataclasses with defensive parsers, and three client methods:
   `search(query, top_k=None)` → `POST /search`, `index_document(document_id)` →
   `POST /documents/{id}/index`, `index_status()` → `GET /index/status`. `top_k=None` is omitted
   from the body so the backend default applies. All reuse the existing typed-error model
   (`BackendUnavailableError`, `RequestTimeoutError`, `HTTPStatusError`, `UnexpectedResponseError`).
2. **Ask page — functional search workspace (`frontend/components/chat.py`).** Replaced the
   "In development" placeholder with a real BM25 retrieval UI: a retrieval-mode indicator
   ("BM25 · keyword retrieval" + honest note that semantic/AI answers arrive later), a `st.form`
   search panel (query + submit) with example-query buttons, and **ranked result cards** (rank,
   filename, page, score, expandable passage, source citation). Distinct states: initial guidance
   (with a "nothing indexed yet" variant), "no matching passages" (valid empty, not an error), and
   concise error messages (offline / timeout / 422 / 5xx / unexpected body). No AI answers are
   fabricated.
3. **Documents page — search-index panel (`frontend/components/documents.py`).** A card showing the
   **real** global index status (documents indexed, chunks, retrieval mode, vectors present) plus an
   idempotent **Index document** action (selectbox of processed documents + button →
   `POST /documents/{id}/index`). Result (chunk count) shown immediately; 404/409/5xx mapped to
   concise messages. Index status is cached in session state and best-effort (offline →
   "Index status unavailable.", no crash).
4. **UX refinement (`frontend/theme.py`, `frontend/components/layout.py`, `frontend/app.py`).**
   - Wider responsive layout: `.block-container` `max-width` 1440px (1100px at ≤1200px), larger
     base font (16px) and bumped heading/caption/label sizes.
   - **Sidebar hierarchy** brand → navigation → status. `st.navigation` is now rendered **hidden**
     (`position="hidden"`); the visible nav is drawn with one `st.page_link` per page (same native
     widget, so it keeps the active-page highlight + URL routing). `theme.py` themes `stPageLink`
     (replacing the old `stSidebarNav` rules).
   - `layout.py` split into `render_sidebar_brand()` / `render_sidebar_nav(pages, active_page)` /
     `render_sidebar_status()` so `app.py` controls the ordering.

### Files modified (Agent 3 ownership only)
- `frontend/api/client.py` — `search()`, `index_document()`, `index_status()`.
- `frontend/api/models.py` — `SearchResult`, `Citation`, `SearchResponse`, `IndexStatus`,
  `IndexResult` + parsers.
- `frontend/components/chat.py` — rewritten as the functional search workspace.
- `frontend/components/documents.py` — added the search-index panel.
- `frontend/components/layout.py` — split sidebar into brand / nav / status; `st.page_link` nav.
- `frontend/app.py` — `st.navigation(..., position="hidden")`; sidebar brand → nav → status;
  `nav.run()`; passes a `DocumentAPIClient` to the Ask page.
- `frontend/state.py` — added search/index session-state keys.
- `frontend/theme.py` — wider layout, larger typography, `stPageLink` theming, `.aurora-mode`,
  `.aurora-result`, `.aurora-index-status`, search-form styling.
- `tests/frontend/test_api_client.py` — added `TestSearch`, `TestIndexDocument`, `TestIndexStatus`,
  `TestRetrievalAgainstRealBackend`.
- `tests/frontend/test_navigation_theme_upload.py` — Ask search-workspace + result-card tests;
  sidebar-hierarchy + `st.page_link` tests.
- `tests/frontend/test_view_and_theme.py` — updated CSS-class assertions.
- `docs/frontend.md` — updated for Milestone 2.

No new dependencies (still the existing `httpx`). No shared, backend, or infrastructure files were
modified.

### API assumptions (Milestone 2)
The frontend now also consumes the retrieval endpoints in `docs/contracts/api.md`:
- `POST /search` body `{query, top_k?}` → `200 {query, mode, results[], citations[]}`;
  `422` empty/invalid query; empty match → `200 results: []`.
- `POST /documents/{id}/index` → `200 {document_id, chunks_indexed, vectors_added}`; `404` unknown
  document; `409` no extractable text.
- `GET /index/status` → `200 {documents_indexed, chunks_indexed, vectors_present, retrieval_mode,
  collection}`.

> **BM25 note (not a bug):** on very small corpora a term present in *every* chunk has IDF ≤ 0,
> which rank-bm25 clamps to 0, so the query can return no matches. Documented in the backend
> handoff; the frontend renders the (possibly empty) result set honestly.

### Validation results (actually executed on this machine)
- `uv run ruff check .` — passed (whole repo clean).
- `uv run ruff format --check .` — passed (92 files already formatted).
- `uv run pytest tests/frontend/` — **101 passed** (Milestone 1 suite + 18 new tests).
- `uv run pytest` (full repo: backend + frontend + integration) — **221 passed**.
- **End-to-end (real backend, live HTTP on `127.0.0.1:8000`):** upload a 3-page PDF → `processed`;
  `POST /documents/{id}/index` → `chunks_indexed=3`, `vectors_added=0`; `GET /index/status` →
  lexical mode, `vectors_present=False`; `POST /search` "Page 2" → ranked results, top on page 2,
  citations present; no-match query → `results: []`; empty query → `HTTPStatusError(422)`.
- **Streamlit `AppTest`:** Ask page renders with **0 exceptions** (mode indicator, search input,
  example buttons, guidance/empty states, result cards); sidebar renders brand → `st.page_link` nav
  → status; theme CSS present as a single `<style>` block.

### Known limitations (Milestone 2)
- The Ask page is **lexical (BM25) only**; natural-language Q&A and grounded LLM answers are
  Milestone 3+. The UI is clearly labelled "BM25 · keyword retrieval" and does not fabricate AI
  answers.
- Document **deletion** is not exposed in the UI (no `DELETE /documents/{id}` endpoint).
- The 25 MB upload limit is a client-side pre-check; the backend enforces the real limit.
- The theme is a single primary (dark) design; a light-mode toggle is not implemented.
- Cross-platform (Linux) frontend rendering was not executed here; the code is portable.

### Remaining tasks (for later milestones)
- **Milestone 3+:** grounded LLM answers over the retrieved passages (the Ask page and the
  search/results rendering are already scaffolded; a clearly-separated "generated answer" section
  is the intended addition, distinct from the retrieved passages).
- Add document deletion to the UI once the backend exposes it.
- Optional: a light-mode toggle, and a richer per-document detail view.

### Notes for Agent 1 / Agent 2 (Milestone 2)
- The work is **frontend-only**; no contract, dependency, or infrastructure changes are required.
- The frontend reads `API_BASE_URL` from the environment only; it does not import backend internals.
- No new dependencies were introduced.
- **Working-tree note:** I did **not** touch any file outside `frontend/` and `tests/frontend/`
  (plus my own `docs/frontend.md` and this handoff). I did not create a commit (other agents may
  have uncommitted work).

---

## Milestone 1 (historical) — UI/UX refinement

## What was wrong (root causes) and what changed
All changes are within Agent 3 ownership (`frontend/`, `tests/frontend/`). No backend, dependency,
or infrastructure changes.

1. **Navigation was duplicated and partly broken.** `layout.py` rendered a *hidden* `st.radio`
   (the functional nav) **plus** decorative `.aurora-nav-item` pills (inert). Two nav systems
   competed and the pills did nothing.
   - **Fix:** `frontend/app.py` now uses Streamlit's native multipage navigation
     (`st.navigation` + `st.Page`), the single source of truth for navigation state. Each page has
     an explicit `url_path` (`documents` / `ask`). The decorative pills and the duplicate radio were
     removed. The native sidebar nav is themed via the `stSidebarNav` selector in `theme.py`.

2. **The theme was lost when navigating to the Ask page.** `inject_theme()` was gated by an
   `_aurora_theme_injected` session-state flag, so the CSS was emitted once and not re-emitted on
   the second page.
   - **Fix:** the gate was removed. The CSS is now injected on **every rerun** (a single, idempotent
     `<style>` block), guaranteeing the theme on every page and after every rerun.

3. **The header was clipped / showed a white bar.** Streamlit's `stHeader` and `stToolbar` were not
   themed, and the main container padding-top was too small.
   - **Fix:** `theme.py` now targets `[data-testid="stHeader"]` and `[data-testid="stToolbar"]`, and
     `.block-container` padding-top was increased so the branded header sits cleanly with no clipping.

4. **The upload UI was disconnected.** A decorative `.aurora-dropzone` sat above a separate native
   `st.file_uploader`, so the dropzone looked interactive but did nothing.
   - **Fix:** the decorative dropzone was removed. There is now a **single**, fully-styled
     `st.file_uploader` (PDF only) whose help text states the real **25 MB** limit (matching the
     backend's `max_upload_bytes`), with success/error feedback.

Additional refinements:
- **`frontend/components/layout.py`** — rewritten: `setup_page()`, `render_sidebar_chrome()`
  (logo, tagline, status pill), `check_backend()`, `render_banner()`. The old `_render_nav`
  (radio + pills) is gone. The status pill now has three honest states: connected / offline /
  checking.
- **`frontend/components/documents.py`** — the document card demotes the raw UUID to a small
  `.aurora-doc-details` line (no longer prominent); the upload panel uses the single uploader.
- **`frontend/theme.py`** — added `status_pill_checking()`, `stSidebarNav` / `stHeader` /
  `stToolbar` / `stFileUploader` styling, and the "checking" pill state.

## Files modified (Agent 3 ownership only)
- `frontend/app.py` — native `st.navigation` + `st.Page` (with `url_path`); page bodies.
- `frontend/components/layout.py` — sidebar chrome, backend check, banner; nav removed.
- `frontend/theme.py` — per-rerun CSS injection; header/toolbar/sidebar-nav/uploader theming.
- `frontend/components/documents.py` — single uploader; UUID demoted to details.
- `frontend/components/chat.py` — "In development" panel (unchanged behaviour).
- `tests/frontend/test_navigation_theme_upload.py` — **NEW**: 14 `AppTest`-based tests.
- `tests/frontend/test_view_and_theme.py` — updated one assertion (nav CSS class).
- `docs/frontend.md` — updated for the new navigation, theming, and upload behaviour.

No new dependencies (still uses the existing `httpx` dev dependency). No shared, backend, or
infrastructure files were modified.

## API assumptions
Unchanged. The frontend implements the document endpoints in `docs/contracts/api.md`:
`POST /documents` (multipart `file` → 201), `GET /documents` (`{"documents": [...]}`),
`GET /documents/{id}` (404 if missing). Metadata fields: `id`, `filename`, `status`
(`processed` | `error`), `page_count`, `created_at`, `error`. No new backend endpoints were added.

## Validation results (actually executed on this machine)
- `uv run ruff check frontend/ tests/frontend/` — passed.
- `uv run ruff format --check frontend/ tests/frontend/` — passed.
- `uv run pytest tests/frontend/` — **80 passed** (52 original + 14 view/theme + 14
  navigation/theme/upload `AppTest` tests).
- **End-to-end (real backend):** FastAPI app on `127.0.0.1:8000`; the frontend client uploaded a
  PDF (→ `processed`, `page_count=1`) and listed the collection via the live HTTP API. The
  Streamlit `AppTest` rendered the dashboard with **0 exceptions**: overview stat cards, the
  document-card grid (UUID demoted to a details line), the single styled file uploader (25 MB help
  text), processed + error badges, the branded logo, the native `st.navigation` sidebar nav
  (no duplicate radio), the online status pill, and the search/sort/filter toolbar. All Aurora CSS
  classes (`aurora-*`, `stSidebarNav`, `stHeader`, `stFileUploader`) were confirmed present in the
  rendered output as a single `<style>` block. The offline state was verified (red status pill,
  offline banner, neutral stat cards, empty state). Test artifacts cleaned up (`.data/` git-ignored).

> The full repo `pytest` also runs the RAG integration tests
> (`tests/integration/test_retrieval_infrastructure.py`). The full suite (backend + frontend +
> integration) is green; the frontend suite is fully green.

## Manual visual verification checklist (browser)
Browser inspection was not available in this environment, so please confirm visually:
1. **Sidebar nav:** only one navigation (the native `st.navigation` list) — no duplicate radio and
   no inert pill row. Clicking "Ask" and "Documents" switches pages; the active item is highlighted.
2. **Theme on both pages:** the Aurora dark theme is present on **both** Documents and Ask (no
   white/unthemed flash when switching).
3. **Header:** the branded header is not clipped and there is no white bar above the content.
4. **Upload:** a single, styled file uploader (no separate decorative dropzone). The help text says
   "PDF only · Maximum size 25 MB". Uploading a valid PDF shows success and the new card appears.
5. **Document cards:** the raw UUID is shown as a small details line, not as a prominent field.
6. **Status pill:** shows "Backend connected" (green) when the API is up, "Backend offline" (red)
   when down, and "Checking…" (amber) before the check resolves.

## Known limitations
- The `Ask` page is a placeholder only; no AI functionality is implemented (out of scope).
- Document **deletion** is not exposed in the UI (no `DELETE /documents/{id}` endpoint).
- The 25 MB upload limit is a client-side pre-check; the backend enforces the real limit.
- The theme is a single primary (dark) design; a light-mode toggle is not implemented.
- Cross-platform (Linux) frontend rendering was not executed here; the code is portable.

## Coordination request for Agent 1 (optional, non-blocking)
- `st.file_uploader` help text states the 25 MB limit, but Streamlit's native uploader also shows
  its own default size cap (200 MB) in the widget. To cap that display value to 25 MB, add
  `server.maxUploadSize = 25` to a `streamlit/config.toml` (an Agent 1 / Platform file). The
  functional 25 MB pre-check and backend enforcement are unaffected, so this is cosmetic only.

## Remaining tasks (for later milestones)
- Milestone 3+: the conversational experience (grounded answers over retrieved passages, source
  citations). The `Ask` page search workspace and result rendering are already scaffolded and
  styled (Milestone 2).
- Add document deletion to the UI once the backend exposes it.
- Optional: a light-mode toggle, and a richer per-document detail view.

## Notes for Agent 1 / Agent 2
- The refinement is **frontend-only**; no contract, dependency, or infrastructure changes are
  required from the frontend side.
- The frontend reads `API_BASE_URL` from the environment only (native `http://localhost:8000`,
  Docker `http://api:8000`); it does not import backend internals.
- No new dependencies were introduced.
- **Working-tree note:** Agent 1's in-progress RAG work (`.env.example`, `compose.yaml`,
  `pyproject.toml`, `uv.lock`, `src/.../core/config.py`, `docs/contracts/retrieval.md`,
  `docs/decisions/0007/0008`, `tests/integration/test_retrieval_infrastructure.py`) is present in
  the working tree. I did **not** touch any of those files, and I did not create a commit (Agent 1
  may have uncommitted work). My changes are scoped to `frontend/` and `tests/frontend/`.
