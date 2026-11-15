"""Document management UI: overview, PDF upload, and the document library.

This component is presentation-only. It reads/writes session state, calls the API client, and maps
typed API errors to concise, user-facing messages. It never imports backend internals.

Owned by Agent 3 (Frontend Engineering).
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st
from frontend.api.client import (
    APIError,
    BackendUnavailableError,
    DocumentAPIClient,
    HTTPStatusError,
    RequestTimeoutError,
    UnexpectedResponseError,
)
from frontend.api.models import Document, DocumentStatus
from frontend.components import cards

from frontend import config, state, theme

# Sort options (client-side; the backend returns most-recent-first by default).
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"
SORT_NAME = "name"
_SORT_LABELS = {SORT_NEWEST: "Newest", SORT_OLDEST: "Oldest", SORT_NAME: "Name A-Z"}

# Filter options.
FILTER_ALL = "all"
FILTER_PROCESSED = "processed"
FILTER_ERROR = "error"
_FILTER_LABELS = {FILTER_ALL: "All", FILTER_PROCESSED: "Processed", FILTER_ERROR: "Errors"}


def render_documents_page(client: DocumentAPIClient) -> None:
    """Render the full Documents page: header, overview, upload, and the library."""
    theme.page_header(
        eyebrow="Workspace",
        title="Documents",
        description="Upload PDF documents, monitor processing, and browse your collection.",
    )

    documents = _ensure_documents_loaded(client)
    _render_overview(documents)
    _render_upload_panel(client)
    _render_library(client, documents)


def _ensure_documents_loaded(client: DocumentAPIClient) -> list[Document] | None:
    """Load the collection once per session (or after a refresh) and return it."""
    documents = state.get(state.KEY_DOCUMENTS)
    if documents is None:
        _load_documents(client)
        documents = state.get(state.KEY_DOCUMENTS)
    return documents


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
def _render_overview(documents: list[Document] | None) -> None:
    """Render summary stat cards derived from real backend data (never fabricated)."""
    if documents is None:
        # Could not load — show a neutral "—" for the document-derived cards.
        total = processed = errors = "—"
    else:
        total = len(documents)
        processed = sum(1 for d in documents if d.status == DocumentStatus.PROCESSED)
        errors = sum(1 for d in documents if d.is_error)

    online = state.get(state.KEY_BACKEND_AVAILABLE) is True
    conn_value = "Online" if online else "Offline"
    conn_accent = theme.SUCCESS if online else theme.ERROR
    conn_icon = "🟢" if online else "🔴"

    cards.render_stats(
        [
            ("Total documents", total, "📚", theme.GRADIENT),
            ("Processed", processed, "✅", theme.SUCCESS),
            ("Errors", errors, "⚠️", theme.ERROR),
            ("Backend", conn_value, conn_icon, conn_accent),
        ]
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
def _render_upload_panel(client: DocumentAPIClient) -> None:
    """Render the PDF upload panel: a single native file uploader, styled to match Aurora.

    The native ``st.file_uploader`` is the one and only interactive upload surface. There is no
    separate decorative dropzone. The displayed limit matches the backend's real limit (25 MB).
    """
    st.markdown(
        '<div class="aurora-card-title">Upload a PDF</div>'
        '<div class="aurora-card-sub">Add a document to your collection. PDF only, up to '
        f"{config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.</div>",
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Choose a PDF file to upload",
        type=["pdf"],
        key="upload_file",
        help=f"PDF only · Maximum size {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
    )

    if uploaded is None:
        return

    # Client-side pre-validation: fast, clear feedback before hitting the backend.
    if not config.is_pdf_filename(uploaded.name):
        st.error("Only PDF files are supported.")
        return
    size_mb = len(uploaded.getvalue()) / (1024 * 1024)
    if len(uploaded.getvalue()) > config.MAX_UPLOAD_BYTES:
        st.error(
            f"This file is {size_mb:.1f} MB, larger than the "
            f"{config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
        )
        return

    if st.button("Upload document", type="primary", key="upload_button"):
        _perform_upload(client, uploaded)


def _perform_upload(client: DocumentAPIClient, uploaded: st.runtime.UploadFile) -> None:
    """Upload the selected file and record the outcome in session state."""
    filename = uploaded.name
    content = uploaded.getvalue()

    with st.spinner(f"Uploading {filename}…"):
        try:
            document = client.upload_document(filename, content)
        except BackendUnavailableError:
            st.error("The backend is not reachable. Please try again.")
            return
        except RequestTimeoutError:
            st.error("The upload did not complete in time. Please try again.")
            return
        except HTTPStatusError as exc:
            _render_http_error(exc)
            return
        except UnexpectedResponseError:
            st.error("The backend returned an unexpected response. Please try again.")
            return
        except APIError:
            st.error("The upload failed. Please try again.")
            return

    state.set_value(state.KEY_UPLOAD_RESULT, document)
    # Refresh the collection so the new document appears immediately.
    _load_documents(client)
    if document.is_error:
        msg = f"“{document.filename}” was uploaded but could not be processed: {document.error}"
        st.warning(msg)
    else:
        st.success(f"Uploaded “{document.filename}” — processed successfully.")


def _render_http_error(exc: HTTPStatusError) -> None:
    """Map a backend HTTP error to a concise, user-facing message."""
    if exc.status_code in (413,):
        st.error("The file is too large to upload.")
    elif exc.status_code in (415,):
        st.error("The file type is not supported. Please upload a PDF.")
    elif exc.status_code in (400, 422):
        st.error(f"Upload rejected: {exc.detail}")
    elif exc.status_code in (500, 502, 503):
        st.error("The server could not process the upload. Please try again.")
    else:
        st.error(f"Upload failed ({exc.status_code}). Please try again.")


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------
def _render_library(client: DocumentAPIClient, documents: list[Document] | None) -> None:
    """Render the document library: toolbar (search/sort/filter) + cards + states."""
    st.markdown(
        '<div class="aurora-card-title" style="margin-top:18px;">Your documents</div>',
        unsafe_allow_html=True,
    )

    if documents is None:
        st.info("Could not load documents. Use Refresh to try again.")
        _render_refresh(client)
        return

    if not documents:
        _render_empty()
        _render_refresh(client)
        return

    _render_toolbar()
    visible = _apply_view(documents)

    if not visible:
        st.markdown(
            """
<div class="aurora-empty">
  <div class="aurora-empty-icon">🔍</div>
  <div class="aurora-empty-title">No documents match your filters</div>
  <div class="aurora-empty-sub">Try a different search term or clear the filter.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        _render_refresh(client)
        return

    _render_document_cards(visible)
    _render_refresh(client)


def _render_refresh(client: DocumentAPIClient) -> None:
    """Render the refresh control and the last-updated caption."""
    col_refresh, col_meta = st.columns([1, 4])
    with col_refresh:
        if st.button("↻ Refresh", key="refresh_documents"):
            _load_documents(client)
            st.rerun()
    with col_meta:
        last_refresh = state.get(state.KEY_LAST_REFRESH)
        if last_refresh is not None:
            st.caption(f"Last updated {last_refresh.strftime('%H:%M:%S')}")


def _render_toolbar() -> None:
    """Render the client-side search, sort, and filter controls."""
    with st.container():
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            search = st.text_input(
                "Search",
                value=state.get(state.KEY_SEARCH, ""),
                placeholder="Filter by document name…",
                key="doc_search_input",
            )
            state.set_value(state.KEY_SEARCH, search)
        with c2:
            sort = st.selectbox(
                "Sort",
                options=[SORT_NEWEST, SORT_OLDEST, SORT_NAME],
                format_func=lambda v: _SORT_LABELS[v],
                index=[SORT_NEWEST, SORT_OLDEST, SORT_NAME].index(
                    state.get(state.KEY_SORT, SORT_NEWEST)
                ),
                key="doc_sort_input",
            )
            state.set_value(state.KEY_SORT, sort)
        with c3:
            flt = st.selectbox(
                "Filter",
                options=[FILTER_ALL, FILTER_PROCESSED, FILTER_ERROR],
                format_func=lambda v: _FILTER_LABELS[v],
                index=[FILTER_ALL, FILTER_PROCESSED, FILTER_ERROR].index(
                    state.get(state.KEY_FILTER, FILTER_ALL)
                ),
                key="doc_filter_input",
            )
            state.set_value(state.KEY_FILTER, flt)


def _apply_view(documents: list[Document]) -> list[Document]:
    """Apply the client-side search, filter, and sort to the collection."""
    search = (state.get(state.KEY_SEARCH) or "").strip().lower()
    flt = state.get(state.KEY_FILTER, FILTER_ALL)
    sort = state.get(state.KEY_SORT, SORT_NEWEST)

    result = list(documents)
    if search:
        result = [d for d in result if search in d.filename.lower()]
    if flt == FILTER_PROCESSED:
        result = [d for d in result if d.status == DocumentStatus.PROCESSED]
    elif flt == FILTER_ERROR:
        result = [d for d in result if d.is_error]

    if sort == SORT_NEWEST:
        result.sort(key=lambda d: d.created_at or datetime.min, reverse=True)
    elif sort == SORT_OLDEST:
        result.sort(key=lambda d: d.created_at or datetime.min)
    elif sort == SORT_NAME:
        result.sort(key=lambda d: d.filename.lower())
    return result


def _render_document_cards(documents: list[Document]) -> None:
    """Render the collection as a responsive grid of document cards."""
    cards_html = "".join(_document_card(d) for d in documents)
    st.markdown(f'<div class="aurora-doc-grid">{cards_html}</div>', unsafe_allow_html=True)


def _document_card(doc: Document) -> str:
    """Return the HTML for a single document card.

    The filename is the primary content. The technical UUID is de-emphasised into a details
    footer rather than shown as prominent content.
    """
    import html as _html

    name = _html.escape(doc.filename, quote=True)
    error_html = ""
    if doc.is_error and doc.error:
        error_html = f'<div class="aurora-doc-error">{_html.escape(doc.error, quote=True)}</div>'

    pages = doc.page_count if doc.page_count is not None else "—"
    added = _format_created_at(doc.created_at)
    badge = cards.status_badge(doc.status)
    cls = "aurora-doc error" if doc.is_error else "aurora-doc"
    icon = "⚠️" if doc.is_error else "📄"

    return f"""
<div class="{cls}">
  <div class="aurora-doc-top">
    <div class="aurora-doc-icon">{icon}</div>
    {badge}
  </div>
  <div class="aurora-doc-name">{name}</div>
  <div class="aurora-doc-meta">
    <span class="aurora-doc-meta-item">📄 {pages} pages</span>
    <span class="aurora-doc-meta-item">🕒 {added}</span>
  </div>
  {error_html}
  <div class="aurora-doc-details">
    <div class="aurora-doc-details-label">Document ID</div>
    <div class="aurora-doc-id">{_html.escape(doc.id, quote=True)}</div>
  </div>
</div>
"""


def _render_empty() -> None:
    """Render the empty-collection state."""
    st.markdown(
        """
<div class="aurora-empty">
  <div class="aurora-empty-icon">📂</div>
  <div class="aurora-empty-title">No documents yet</div>
  <div class="aurora-empty-sub">Upload a PDF above to get started.</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _load_documents(client: DocumentAPIClient) -> None:
    """Fetch the collection and store it in session state (or clear on error)."""
    with st.spinner("Loading documents…"):
        try:
            documents = client.list_documents()
        except BackendUnavailableError:
            st.error("The backend is not reachable. Please try again.")
            state.set_value(state.KEY_DOCUMENTS, None)
            return
        except RequestTimeoutError:
            st.error("The request did not complete in time. Please try again.")
            state.set_value(state.KEY_DOCUMENTS, None)
            return
        except HTTPStatusError as exc:
            st.error(f"Could not load documents ({exc.status_code}). Please try again.")
            state.set_value(state.KEY_DOCUMENTS, None)
            return
        except (UnexpectedResponseError, APIError):
            st.error("Could not load documents. Please try again.")
            state.set_value(state.KEY_DOCUMENTS, None)
            return

    state.set_value(state.KEY_DOCUMENTS, documents)
    state.set_value(state.KEY_LAST_REFRESH, datetime.now())


def _format_created_at(created_at: datetime | None) -> str:
    if created_at is None:
        return "—"
    return created_at.strftime("%Y-%m-%d %H:%M")
