"""The "Ask" page: a clearly-identified future area for the AI document chat.

This page must NOT pretend to provide working AI functionality. It exists to establish the
navigation structure and set expectations for the conversational experience that lands in a later
milestone. It is styled to match the Aurora theme but contains no AI logic.

Owned by Agent 3 (Frontend Engineering).
"""

from __future__ import annotations

import streamlit as st

from frontend import theme

_FEATURES = [
    ("🔎", "Document search", "Find the most relevant passages across your uploaded documents."),
    ("💬", "Natural-language questions", "Ask questions in plain language about your collection."),
    ("📌", "Grounded answers", "Responses grounded in your documents, not generic text."),
    ("📚", "Source citations", "See exactly which documents and passages support each answer."),
]


def render_ask_page() -> None:
    """Render the placeholder for the future conversational experience."""
    theme.page_header(
        eyebrow="Coming soon",
        title="Ask",
        description="Ask natural-language questions about your documents.",
    )

    features = "".join(
        f"""
<div class="aurora-feature">
  <div class="aurora-feature-icon">{icon}</div>
  <div class="aurora-feature-title">{title}</div>
  <div class="aurora-feature-desc">{desc}</div>
</div>
"""
        for icon, title, desc in _FEATURES
    )

    st.markdown(
        f"""
<div class="aurora-coming-soon">
  <div class="aurora-cs-badge">✨ In development</div>
  <h2>The AI document assistant is on its way</h2>
  <p>
    This workspace is being prepared for a conversational experience. Once available, you will be
    able to ask questions about your uploaded documents and receive grounded answers with source
    citations. This feature is not available yet.
  </p>
  <div class="aurora-feature-grid">
    {features}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
