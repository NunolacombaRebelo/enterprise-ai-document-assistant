"""Application layout: page config, branded sidebar chrome, and the offline banner.

Navigation is handled by a single native ``st.navigation`` (see ``app.py``). This module renders
the non-navigation parts of the application shell: the page config + theme injection, the branded
logo/tagline, the backend-connection status pill, and the offline banner. It contains no business
logic.

Owned by Agent 3 (Frontend Engineering).
"""

from __future__ import annotations

import streamlit as st
from frontend.api.client import (
    APIError,
    BackendUnavailableError,
    DocumentAPIClient,
    RequestTimeoutError,
)

from frontend import config, state, theme


def setup_page() -> None:
    """Configure the Streamlit page (title, icon, layout) and inject the theme.

    The theme is injected on every rerun (not gated by a session flag) so the Aurora styling is
    guaranteed to be present on every page and after every navigation transition. Re-emitting the
    same ``<style>`` block is cheap and idempotent.
    """
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    theme.inject_theme()


def render_sidebar_chrome() -> None:
    """Render the branded sidebar chrome (logo, tagline, backend status).

    This is called from each page body so the branded header and status pill appear above the
    native navigation on every page. The navigation itself is rendered by ``st.navigation``.
    """
    with st.sidebar:
        theme.brand_header()
        st.markdown(
            f'<div class="aurora-brand-sub" style="padding:0 8px 12px;">{config.APP_TAGLINE}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<hr>", unsafe_allow_html=True)
        _render_backend_status()


def _render_backend_status() -> None:
    """Show the backend connection status pill in the sidebar.

    Three honest states: Connected (verified), Disconnected (verified), and Checking (not yet
    verified). A status that has not been verified is never shown as connected.
    """
    available = state.get(state.KEY_BACKEND_AVAILABLE)
    if available is True:
        theme.status_pill(True, sub=config.get_api_base_url())
    elif available is False:
        theme.status_pill(False, sub="unreachable")
    else:
        theme.status_pill_checking()


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
