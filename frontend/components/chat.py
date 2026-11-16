"""The "Ask" page: a conversational document-search interface.

Presents a chat-style UI where the user types a question and sees retrieved
passages from their indexed documents as assistant-side messages.  No LLM is
involved — results are purely lexical (BM25) retrieval, clearly labelled as
such.  The architecture is prepared for a future LLM-generated answer layer
(Milestone 3) without requiring a UI rebuild.

Owned by Agent 3 (Frontend Engineering).
"""

from __future__ import annotations

import html as _html

import streamlit as st
from frontend.api.client import (
    APIError,
    BackendUnavailableError,
    DocumentAPIClient,
    HTTPStatusError,
    RequestTimeoutError,
    UnexpectedResponseError,
)
from frontend.api.models import SearchResponse, SearchResult

from frontend import state, theme

# Suggestion chips shown when the conversation is empty.
EXAMPLE_QUERIES = [
    "What is the refund policy?",
    "How do I reset my password?",
    "What are the support hours?",
]

MODE_LABEL = "BM25 · keyword retrieval"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_ask_page(client: DocumentAPIClient) -> None:
    """Render the full Ask page: header, conversation, and composer."""
    theme.page_header(
        eyebrow="Ask",
        title="Ask your documents",
        description="Type a question or keyword to search across your indexed documents.",
    )

    _render_mode_indicator()
    _render_conversation()
    _render_composer(client)


# ---------------------------------------------------------------------------
# Mode indicator
# ---------------------------------------------------------------------------


def _render_mode_indicator() -> None:
    st.markdown(
        f"""
<div class="aurora-mode">
  <span class="aurora-mode-dot"></span>
  <span class="aurora-mode-label">{MODE_LABEL}</span>
  <span class="aurora-mode-note">Semantic / AI answers arrive in a later milestone.</span>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Conversation area
# ---------------------------------------------------------------------------


def _render_conversation() -> None:
    """Render the full message history from session state."""
    messages: list[dict] = state.get(state.KEY_CONVERSATION, [])

    if not messages:
        _render_empty_state()
        return

    for msg in messages:
        _render_message(msg)


def _render_empty_state() -> None:
    """Polished empty state shown before any messages exist."""
    st.markdown(
        """
<div class="aurora-empty aurora-chat-empty">
  <div class="aurora-empty-icon">💬</div>
  <div class="aurora-empty-title">Start a conversation</div>
  <div class="aurora-empty-sub">
    Ask a question about your documents and I'll find the most relevant passages.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    _render_suggestions()


def _render_suggestions() -> None:
    """Show example-query chips when the conversation is empty."""
    cols = st.columns(len(EXAMPLE_QUERIES))
    for col, example in zip(cols, EXAMPLE_QUERIES, strict=True):
        with col:
            if st.button(example, key=f"suggest_{example}", use_container_width=True):
                _handle_query(example)


def _render_message(msg: dict) -> None:
    """Render a single message (user or assistant) as a chat bubble."""
    role = msg.get("role", "user")

    if role == "user":
        _render_user_message(msg["text"])
    elif role == "assistant":
        _render_assistant_message(msg)
    elif role == "error":
        _render_error_message(msg["text"])


def _render_user_message(text: str) -> None:
    with st.chat_message("user"):
        html = f'<div class="aurora-bubble aurora-bubble-user">{_html.escape(text)}</div>'
        st.markdown(html, unsafe_allow_html=True)


def _render_assistant_message(msg: dict) -> None:
    with st.chat_message("assistant", avatar="🤖"):
        # Future: if msg contains a "generated_answer" key, render it here
        # as a distinct block before the retrieved passages.
        if msg.get("generated_answer"):
            st.markdown(msg["generated_answer"])

        response: SearchResponse | None = msg.get("response")
        if response is None:
            st.markdown(msg.get("text", ""))
            return

        if not response.results:
            _render_no_results(response.query)
            return

        _render_results(response)


def _render_error_message(text: str) -> None:
    with st.chat_message("assistant", avatar="⚠️"):
        st.error(text)


def _render_results(response: SearchResponse) -> None:
    """Render retrieved passages inside an assistant chat bubble."""
    count = len(response.results)
    plural = "s" if count != 1 else ""
    mode = _html.escape(response.mode, quote=True)
    query = _html.escape(response.query, quote=True)
    st.markdown(
        f'<div class="aurora-results-header">'
        f'<span class="aurora-results-count">{count} passage{plural} found</span>'
        f'<span class="aurora-results-mode">for "{query}" · {mode}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    for i, result in enumerate(response.results, start=1):
        _render_result_card(i, result)


def _render_result_card(rank: int, result: SearchResult) -> None:
    name = _html.escape(result.filename, quote=True)
    text = _html.escape(result.text, quote=True)
    score = f"{result.score:.2f}"
    sources = ", ".join(_html.escape(s, quote=True) for s in result.sources) or "bm25"

    st.markdown(
        f"""
<div class="aurora-result">
  <div class="aurora-result-top">
    <span class="aurora-result-rank">#{rank}</span>
    <div class="aurora-result-source">
      <div class="aurora-result-filename">📄 {name}</div>
      <div class="aurora-result-meta">Page {result.page} · score {score} · {sources}</div>
    </div>
  </div>
  <details class="aurora-result-passage">
    <summary>View passage</summary>
    <div class="aurora-result-text">{text}</div>
  </details>
  <div class="aurora-result-cite">
    <span class="aurora-result-cite-label">Source</span>
    {name} · page {result.page}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_no_results(query: str) -> None:
    st.markdown(
        f"""
<div class="aurora-empty aurora-chat-empty">
  <div class="aurora-empty-icon">🔍</div>
  <div class="aurora-empty-title">No matching passages</div>
  <div class="aurora-empty-sub">
    Nothing matched "{_html.escape(query, quote=True)}". Try different keywords,
    or add more documents on the Documents page.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Composer (bottom-anchored input)
# ---------------------------------------------------------------------------


def _render_composer(client: DocumentAPIClient) -> None:
    """Render the chat input at the bottom of the page."""
    query = st.chat_input(
        "Ask a question about your documents…",
        key="ask_chat_input",
        disabled=False,
    )
    if query is not None:
        _handle_query(query, client)


# ---------------------------------------------------------------------------
# Query handling
# ---------------------------------------------------------------------------


def _handle_query(query: str, client: DocumentAPIClient | None = None) -> None:
    """Process a user query: append to conversation, call search, append result.

    If ``client`` is not provided (e.g. from suggestion chips before the
    composer renders), a new client is created.
    """
    query = (query or "").strip()
    if not query:
        return

    if client is None:
        client = DocumentAPIClient()

    conversation: list[dict] = state.get(state.KEY_CONVERSATION, [])

    # Append user message
    conversation.append({"role": "user", "text": query})

    # Perform search
    with st.spinner("Searching your documents…"):
        try:
            response = client.search(query)
        except BackendUnavailableError:
            conversation.append(
                {"role": "error", "text": "The backend is not reachable. Please try again."}
            )
        except RequestTimeoutError:
            conversation.append(
                {"role": "error", "text": "The search did not complete in time. Please try again."}
            )
        except HTTPStatusError as exc:
            conversation.append({"role": "error", "text": _map_http_error(exc)})
        except UnexpectedResponseError:
            conversation.append(
                {
                    "role": "error",
                    "text": "The backend returned an unexpected response. Please try again.",
                }
            )
        except APIError:
            conversation.append({"role": "error", "text": "The search failed. Please try again."})
        else:
            conversation.append({"role": "assistant", "response": response})

    state.set_value(state.KEY_CONVERSATION, conversation)
    # Force a rerun so the new messages render
    st.rerun()


def _map_http_error(exc: HTTPStatusError) -> str:
    if exc.status_code == 422:
        return "That query could not be processed. Please enter a valid search term."
    if exc.status_code in (500, 502, 503):
        return "The search service is temporarily unavailable. Please try again."
    return f"Search failed ({exc.status_code}). Please try again."
