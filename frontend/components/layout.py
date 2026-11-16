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


def render_sidebar_brand() -> None:
    """Render the branded header (logo + name + tagline) at the top of the sidebar.

    Called before ``st.navigation`` so the product identity sits above the navigation.
    """
    with st.sidebar:
        theme.brand_header()
        st.markdown(
            f'<div class="aurora-brand-sub" style="padding:0 8px 12px;">{config.APP_TAGLINE}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<hr>", unsafe_allow_html=True)


def render_sidebar_status() -> None:
    """Render the backend-connection status pill at the bottom of the sidebar.

    Called after ``st.navigation`` so the hierarchy is: brand → navigation → status.
    """
    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        _render_backend_status()


def render_sidebar_nav(pages: list, active_page: object) -> None:
    """Render the main navigation in the sidebar, below the brand.

    ``st.navigation`` with ``position="sidebar"`` pins its widget to the very top of the sidebar,
    which would place the nav *above* the product identity. To get the conventional hierarchy
    (brand → navigation → status) we hide the native nav and render one ``st.page_link`` per page
    here instead. ``st.page_link`` is the same native widget the sidebar nav uses, so it keeps the
    active-page highlight and URL routing — this is still a single source of truth for navigation
    (no duplicate radio or decorative pills).
    """
    with st.sidebar:
        for page in pages:
            is_active = page is active_page
            st.page_link(
                page,
                label=page.title,
                icon=page.icon or None,
                use_container_width=True,
            )
            # Track active state for styling (the native page_link already highlights the active
            # page, but we expose the flag for any custom emphasis).
            if is_active:
                st.session_state["aurora_active_page"] = page.url_path


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
