"""Streamlit frontend entrypoint.

PLACEHOLDER — owned by Agent 3 (Frontend Engineering). This minimal stub exists only so the
frontend service can start and so Agent 3 has a concrete entrypoint to build on. It does not
implement any user-facing functionality.

Agent 3 will replace this with the real UI (document upload, question input, grounded answers
with citations) and an HTTP client that talks to the backend at ``API_BASE_URL``. See
``docs/contracts/api.md`` for the contract and ``docs/handoffs/03-frontend.md`` for the handoff.
"""

from __future__ import annotations

import os

import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Enterprise AI Document Assistant", page_icon=":file_cabinet:")
st.title("Enterprise AI Document Assistant")
st.caption("Phase 0 placeholder. The full frontend is built by the Frontend Engineering agent.")
st.info(f"This is a Phase 0 placeholder. Backend health endpoint: {API_BASE_URL}/health")
