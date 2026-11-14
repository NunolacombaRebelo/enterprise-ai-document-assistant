"""Application layout: page config, sidebar navigation, and the backend-connection banner.

These helpers compose the consistent visual structure shared by every page. They contain no
business logic; they only render and delegate to the API client / state helpers.
"""

from __future__ import annotations

import streamlit as st
from frontend.api.client import (
    APIError,
    BackendUnavailableError,
    DocumentAPIClient,
    RequestTimeoutError,
)

from frontend import config, state

NAV_DOCUMENTS = "Documents"
NAV_ASK = "Ask"


def setup_page() -> None:
    """Configure the Streamlit page (title, icon, layout)."""
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_sidebar(client: DocumentAPIClient) -> str:
    """Render the sidebar navigation and return the selected page key.

    The "Ask" item is present for future navigation but is clearly marked as not yet available; it
    does not pretend to provide working AI functionality.
    """
    with st.sidebar:
        st.title(f"{config.APP_ICON} {config.APP_TITLE}")
        st.caption(config.APP_DESCRIPTION)
        st.divider()

        page = st.radio(
            "Navigation",
            options=[NAV_DOCUMENTS, NAV_ASK],
            index=0,
            label_visibility="collapsed",
        )
        if page == NAV_ASK:
            st.caption("Coming in a future milestone.")

        st.divider()
        _render_backend_status(client)

    state.set_value(state.KEY_ACTIVE_PAGE, page)
    return page


def _render_backend_status(client: DocumentAPIClient) -> None:
    """Show a concise backend connection indicator in the sidebar."""
    available = state.get(state.KEY_BACKEND_AVAILABLE)
    if available is True:
        st.success("Backend connected", icon="✅")
    elif available is False:
        st.error("Backend offline", icon="⚠️")
    else:
        st.caption("Checking backend…")


def check_backend(client: DocumentAPIClient) -> None:
    """Probe the backend once per session and record availability in session state."""
    if state.get(state.KEY_BACKEND_CHECKED):
        return
    try:
        available = client.health()
    except (BackendUnavailableError, RequestTimeoutError, APIError):
        available = False
    state.set_value(state.KEY_BACKEND_AVAILABLE, available)
    state.set_value(state.KEY_BACKEND_CHECKED, True)


def render_banner() -> None:
    """Render a top-of-page banner when the backend is unavailable.

    The application remains usable for layout/navigation even when offline; document operations
    will report the failure. This banner makes the offline state explicit.
    """
    available = state.get(state.KEY_BACKEND_AVAILABLE)
    if available is False:
        st.warning(
            "The backend is currently unreachable. Document operations are unavailable until it "
            f"comes back online. Configured backend: `{config.get_api_base_url()}`.",
            icon="⚠️",
        )
