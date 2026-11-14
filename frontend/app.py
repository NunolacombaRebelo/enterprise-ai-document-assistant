"""Streamlit frontend entrypoint.

This is the application shell: it configures the page, builds the API client from the configured
``API_BASE_URL``, checks backend availability, renders the sidebar navigation, and dispatches to
the active page. All document operations go through the HTTP API client; no backend internals are
imported and no PDF processing happens here.

Owned by Agent 3 (Frontend Engineering). See ``docs/frontend.md`` for the architecture and
``docs/contracts/api.md`` for the integration contract.
"""

from __future__ import annotations

import logging

from frontend.api.client import DocumentAPIClient
from frontend.components import chat, documents, layout

from frontend import state

logger = logging.getLogger(__name__)


def main() -> None:
    """Application entrypoint, run on every Streamlit rerun."""
    layout.setup_page()
    state.init_state()

    client = DocumentAPIClient()
    layout.check_backend(client)

    page = layout.render_sidebar(client)
    layout.render_banner()

    if page == layout.NAV_DOCUMENTS:
        documents.render_documents_page(client)
    else:
        chat.render_ask_page()


main()
