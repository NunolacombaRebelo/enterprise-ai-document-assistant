"""Document management UI: PDF upload and the document collection view.

This component is presentation-only. It reads/writes session state, calls the API client, and maps
typed API errors to concise, user-facing messages. It never imports backend internals.
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

from frontend import config, state

# Maps a status string to a (label, emoji) pair for the badge. These mirror the backend
# DocumentStatus enum (processed / error). Unknown statuses fall back to a neutral rendering so a
# new backend status never breaks the UI.
_STATUS_BADGES: dict[str, tuple[str, str]] = {
    DocumentStatus.PROCESSED: ("Processed", "✅"),
    DocumentStatus.ERROR: ("Error", "⚠️"),
}


def _status_badge(status: str) -> str:
    label, icon = _STATUS_BADGES.get(status, (status, "•"))
    return f"{icon} {label}"


def _format_created_at(created_at: datetime | None) -> str:
    if created_at is None:
        return "—"
    return created_at.strftime("%Y-%m-%d %H:%M")


def _format_page_count(page_count: int | None) -> str:
    return str(page_count) if page_count is not None else "—"


def render_documents_page(client: DocumentAPIClient) -> None:
    """Render the full Documents page: upload panel, then the collection."""
    st.header("Documents")
    st.caption("Upload PDF documents and review your collection.")

    _render_upload_panel(client)
    st.divider()
    _render_collection(client)


def _render_upload_panel(client: DocumentAPIClient) -> None:
    """Render the PDF upload panel with progress and success/error feedback."""
    with st.container(border=True):
        st.subheader("Upload a PDF")

        uploaded = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            key="upload_file",
            help=f"Maximum size {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

        if uploaded is None:
            st.caption("No file selected.")
            return

        # Client-side pre-validation: fast, clear feedback before hitting the backend.
        if not config.is_pdf_filename(uploaded.name):
            st.error("Only PDF files are supported.")
            return
        if len(uploaded.getvalue()) > config.MAX_UPLOAD_BYTES:
            st.error(
                f"This file is larger than the {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
            )
            return

        if st.button("Upload", type="primary", key="upload_button"):
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
    st.success(f"Uploaded “{document.filename}” (ID {document.id}).")


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


def _render_collection(client: DocumentAPIClient) -> None:
    """Render the document collection with a refresh control and empty state."""
    st.subheader("Your documents")

    col_refresh, col_count = st.columns([1, 4])
    with col_refresh:
        refresh = st.button("Refresh", key="refresh_documents")
    with col_count:
        pass

    if refresh:
        _load_documents(client)

    documents = state.get(state.KEY_DOCUMENTS)

    if documents is None:
        # First load (or after a cleared state): fetch now.
        _load_documents(client)
        documents = state.get(state.KEY_DOCUMENTS)

    if documents is None:
        st.info("Could not load documents. Use Refresh to try again.")
        return

    if not documents:
        st.info("No documents yet. Upload a PDF to get started.", icon="📁")
        return

    _render_document_table(documents)


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


def _render_document_table(documents: list[Document]) -> None:
    """Render the collection as a table with status badges and metadata."""
    rows = [
        {
            "Filename": doc.filename,
            "Status": _status_badge(doc.status),
            "Pages": _format_page_count(doc.page_count),
            "Added": _format_created_at(doc.created_at),
            "ID": doc.id,
        }
        for doc in documents
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Surface the reason for any document that failed to process, so the user can act on it.
    errors = [doc for doc in documents if doc.is_error and doc.error]
    if errors:
        with st.expander(f"{len(errors)} document(s) could not be processed", expanded=False):
            for doc in errors:
                st.warning(f"“{doc.filename}”: {doc.error}", icon="⚠️")

    last_refresh = state.get(state.KEY_LAST_REFRESH)
    if last_refresh is not None:
        st.caption(f"Last updated {last_refresh.strftime('%H:%M:%S')}.")
