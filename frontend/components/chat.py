"""The "Ask" page: a clearly-identified future area for the AI document chat.

This page must NOT pretend to provide working AI functionality. It exists only to establish the
navigation structure and set expectations for the conversational experience that lands in a later
milestone.
"""

from __future__ import annotations

import streamlit as st


def render_ask_page() -> None:
    """Render the placeholder for the future conversational experience."""
    st.header("Ask")
    st.caption("Ask natural-language questions about your documents.")

    st.info(
        "The AI document assistant is coming in a future milestone. "
        "Once available, you will be able to ask questions about your uploaded documents and "
        "receive grounded answers with source citations.",
        icon="✨",
    )

    st.divider()
    st.markdown(
        """
**Planned capabilities (not yet available):**

- Natural-language questions over your document collection
- AI-generated, grounded answers
- Source citations and document references
- Retrieval feedback
"""
    )
