"""Session-state helpers for the Streamlit frontend.

Streamlit reruns the whole script on every interaction, so all mutable UI state must live in
``st.session_state`` under stable keys. This module centralises those keys and the small helpers
that read/write them, keeping application behaviour predictable and avoiding duplicate submissions.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# Stable session-state keys. Keep these in one place so components never invent ad-hoc keys.
KEY_DOCUMENTS = "documents"
KEY_LAST_REFRESH = "last_refresh"
KEY_UPLOAD_RESULT = "upload_result"
KEY_BACKEND_AVAILABLE = "backend_available"
KEY_BACKEND_CHECKED = "backend_checked"
KEY_ACTIVE_PAGE = "active_page"
KEY_SEARCH = "doc_search"
KEY_SORT = "doc_sort"
KEY_FILTER = "doc_filter"


def init_state() -> None:
    """Initialise session-state defaults once per session."""
    if KEY_DOCUMENTS not in st.session_state:
        st.session_state[KEY_DOCUMENTS] = None
    if KEY_LAST_REFRESH not in st.session_state:
        st.session_state[KEY_LAST_REFRESH] = None
    if KEY_UPLOAD_RESULT not in st.session_state:
        st.session_state[KEY_UPLOAD_RESULT] = None
    if KEY_BACKEND_AVAILABLE not in st.session_state:
        st.session_state[KEY_BACKEND_AVAILABLE] = None
    if KEY_BACKEND_CHECKED not in st.session_state:
        st.session_state[KEY_BACKEND_CHECKED] = False
    if KEY_ACTIVE_PAGE not in st.session_state:
        st.session_state[KEY_ACTIVE_PAGE] = "documents"
    if KEY_SEARCH not in st.session_state:
        st.session_state[KEY_SEARCH] = ""
    if KEY_SORT not in st.session_state:
        st.session_state[KEY_SORT] = "newest"
    if KEY_FILTER not in st.session_state:
        st.session_state[KEY_FILTER] = "all"


def get(key: str, default: Any = None) -> Any:
    """Return a session-state value, falling back to ``default``."""
    return st.session_state.get(key, default)


def set_value(key: str, value: Any) -> None:
    """Set a session-state value under ``key``."""
    st.session_state[key] = value
