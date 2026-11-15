"""Streamlit frontend entrypoint.

This is the application shell: it configures the page, builds the API client from the
configured ``API_BASE_URL``, checks backend availability, defines the single native navigation
(``st.navigation`` + ``st.Page``), renders the branded sidebar, and dispatches to the active
page. All document operations go through the HTTP API client; no backend internals are imported
and no PDF processing happens here.

Owned by Agent 3 (Frontend Engineering). See ``docs/frontend.md`` for the architecture and
``docs/contracts/api.md`` for the integration contract.
"""

from __future__ import annotations

import logging

import streamlit as st
from frontend.api.client import DocumentAPIClient
from frontend.components import chat, documents, layout

from frontend import state

logger = logging.getLogger(__name__)


def _render_documents_page() -> None:
    """Documents page body (executed by ``st.navigation``)."""
    client = DocumentAPIClient()
    layout.render_banner()
    documents.render_documents_page(client)


def _render_ask_page() -> None:
    """Ask page body (executed by ``st.navigation``)."""
    layout.render_banner()
    chat.render_ask_page()


def main() -> None:
    """Application entrypoint, run on every Streamlit rerun."""
    layout.setup_page()
    state.init_state()

    client = DocumentAPIClient()
    layout.check_backend(client)

    # Branded sidebar chrome (logo, tagline, backend status) renders at the top of the sidebar,
    # above the native navigation.
    layout.render_sidebar_chrome()

    # A single native navigation system. st.navigation returns the active page; calling .run()
    # executes that page's body. This is the one source of truth for navigation state — no
    # duplicate radio or decorative pills.
    nav = st.navigation(
        [
            st.Page(
                _render_documents_page,
                title="Documents",
                icon="📄",
                url_path="documents",
                default=True,
            ),
            st.Page(
                _render_ask_page,
                title="Ask",
                icon="✨",
                url_path="ask",
            ),
        ],
        position="sidebar",
    )
    nav.run()


main()
