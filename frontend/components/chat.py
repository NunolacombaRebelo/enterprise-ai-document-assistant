"""The "Ask" page: a functional document-search workspace (Milestone 2).

This page lets the user enter a natural-language question or keyword query and retrieve the most
relevant passages across their indexed documents using the backend's BM25 lexical retrieval. It is
a **document retrieval experience, not a generative AI chat**: results are real retrieved passages
with source citations, and no AI-generated answers are fabricated. The current retrieval mode is
BM25 (lexical) — clearly labelled as such.

The page is architecturally prepared for future grounded-answer generation: search results and any
future generated answer would be presented as separate, clearly-distinguished sections.

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
from frontend.api.models import IndexStatus, SearchResponse, SearchResult

from frontend import state, theme

# Example queries shown to help the user get started. These are plain keyword/phrase examples that
# the BM25 retriever can match against indexed passages.
EXAMPLE_QUERIES = [
    "What is the refund policy?",
    "How do I reset my password?",
    "What are the support hours?",
]

# The retrieval mode label shown to the user. In Milestone 2 the backend always runs lexical (BM25).
MODE_LABEL = "BM25 · keyword retrieval"


def render_ask_page(client: DocumentAPIClient) -> None:
    """Render the Ask page: search workspace with results and clear states."""
    theme.page_header(
        eyebrow="Search",
        title="Ask",
        description="Search your indexed documents and find the most relevant passages.",
    )

    _render_mode_indicator()
    _render_search_panel(client)
    _render_results(client)


def _render_mode_indicator() -> None:
    """Show a clear, honest indicator of the current retrieval mode."""
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


def _render_search_panel(client: DocumentAPIClient) -> None:
    """Render the search input, submit button, and example queries.

    A ``st.form`` is used so the query is submitted once per button press (no accidental duplicate
    submissions on rerun) and the query text is preserved across reruns.
    """
    with st.form("ask_search_form", clear_on_submit=False):
        query = st.text_input(
            "Search your documents",
            value=state.get(state.KEY_QUERY, ""),
            placeholder="e.g. What is the refund policy?",
            key="ask_query_input",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Search documents", type="primary")

    if submitted:
        _perform_search(client, query)

    # Example queries (only shown before a search has been run, to reduce clutter).
    if not state.get(state.KEY_SEARCHED):
        st.markdown(
            '<div class="aurora-examples-label">Try one of these:</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(EXAMPLE_QUERIES))
        for col, example in zip(cols, EXAMPLE_QUERIES, strict=True):
            with col:
                if st.button(example, key=f"example_{example}", use_container_width=True):
                    _perform_search(client, example)


def _perform_search(client: DocumentAPIClient, query: str) -> None:
    """Run a search and store the outcome in session state.

    The query is preserved so the user can refine it. Errors are stored (not raised) so the UI
    state stays predictable across reruns.
    """
    query = (query or "").strip()
    state.set_value(state.KEY_QUERY, query)

    if not query:
        state.set_value(state.KEY_SEARCH_ERROR, "Please enter a search query.")
        state.set_value(state.KEY_SEARCH_RESULTS, None)
        state.set_value(state.KEY_SEARCHED, False)
        return

    state.set_value(state.KEY_LAST_QUERY, query)
    state.set_value(state.KEY_SEARCH_ERROR, None)
    state.set_value(state.KEY_SEARCHED, True)

    with st.spinner("Searching your documents…"):
        try:
            response = client.search(query)
        except BackendUnavailableError:
            state.set_value(
                state.KEY_SEARCH_ERROR, "The backend is not reachable. Please try again."
            )
            state.set_value(state.KEY_SEARCH_RESULTS, None)
            return
        except RequestTimeoutError:
            state.set_value(
                state.KEY_SEARCH_ERROR, "The search did not complete in time. Please try again."
            )
            state.set_value(state.KEY_SEARCH_RESULTS, None)
            return
        except HTTPStatusError as exc:
            state.set_value(state.KEY_SEARCH_ERROR, _map_http_error(exc))
            state.set_value(state.KEY_SEARCH_RESULTS, None)
            return
        except UnexpectedResponseError:
            state.set_value(
                state.KEY_SEARCH_ERROR,
                "The backend returned an unexpected response. Please try again.",
            )
            state.set_value(state.KEY_SEARCH_RESULTS, None)
            return
        except APIError:
            state.set_value(state.KEY_SEARCH_ERROR, "The search failed. Please try again.")
            state.set_value(state.KEY_SEARCH_RESULTS, None)
            return

    state.set_value(state.KEY_SEARCH_RESULTS, response)


def _map_http_error(exc: HTTPStatusError) -> str:
    """Map a search HTTP error to a concise, user-facing message."""
    if exc.status_code == 422:
        return "That query could not be processed. Please enter a valid search term."
    if exc.status_code in (500, 502, 503):
        return "The search service is temporarily unavailable. Please try again."
    return f"Search failed ({exc.status_code}). Please try again."


def _render_results(client: DocumentAPIClient) -> None:
    """Render the search results (or the appropriate empty / error / guidance state)."""
    error = state.get(state.KEY_SEARCH_ERROR)
    if error:
        st.error(error)
        return

    if not state.get(state.KEY_SEARCHED):
        _render_initial_guidance(client)
        return

    response = state.get(state.KEY_SEARCH_RESULTS)
    if response is None:
        # A search was attempted but produced no usable result (e.g. an error path already handled).
        return

    _render_results_header(response)
    if not response.results:
        _render_no_results(response.query)
        return

    _render_result_cards(response)


def _render_initial_guidance(client: DocumentAPIClient) -> None:
    """Show guidance before any search: index status + how to get started."""
    status = state.get(state.KEY_INDEX_STATUS)
    if status is None:
        status = _load_index_status(client)

    if status is not None and status.documents_indexed == 0:
        st.markdown(
            """
<div class="aurora-empty">
  <div class="aurora-empty-icon">🗂️</div>
  <div class="aurora-empty-title">No documents are indexed yet</div>
  <div class="aurora-empty-sub">
    Upload and index a document on the Documents page first, then search here.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        """
<div class="aurora-empty">
  <div class="aurora-empty-icon">🔎</div>
  <div class="aurora-empty-title">Search your document collection</div>
  <div class="aurora-empty-sub">
    Enter a question or keyword above to find the most relevant passages across your indexed
    documents.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _load_index_status(client: DocumentAPIClient) -> IndexStatus | None:
    """Fetch the index status once and cache it in session state (best-effort)."""
    cached = state.get(state.KEY_INDEX_STATUS)
    if cached is not None:
        return cached
    try:
        status = client.index_status()
    except (
        BackendUnavailableError,
        RequestTimeoutError,
        HTTPStatusError,
        UnexpectedResponseError,
        APIError,
    ):
        return None
    state.set_value(state.KEY_INDEX_STATUS, status)
    return status


def _render_results_header(response: SearchResponse) -> None:
    """Render a compact summary line above the results."""
    count = len(response.results)
    mode = response.mode or "lexical"
    st.markdown(
        f"""
<div class="aurora-results-header">
  <span class="aurora-results-count">{count} result{"s" if count != 1 else ""}</span>
  <span class="aurora-results-mode">for “{_html.escape(response.query, quote=True)}” ·
    {_html.escape(mode, quote=True)}</span>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_no_results(query: str) -> None:
    """Render the "no matching passages" state (a valid result, not an error)."""
    st.markdown(
        f"""
<div class="aurora-empty">
  <div class="aurora-empty-icon">🔍</div>
  <div class="aurora-empty-title">No matching passages found</div>
  <div class="aurora-empty-sub">
    Nothing matched “{_html.escape(query, quote=True)}”. Try different keywords, or index more
    documents on the Documents page.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_result_cards(response: SearchResponse) -> None:
    """Render each retrieved passage as a ranked result card with a source citation."""
    cards_html = "".join(_result_card(i, result) for i, result in enumerate(response.results))
    st.markdown(f'<div class="aurora-results">{cards_html}</div>', unsafe_allow_html=True)


def _result_card(position: int, result: SearchResult) -> str:
    """Return the HTML for a single ranked result card.

    The passage text is shown in an expandable section so long passages stay readable. The source
    citation (filename + page) is displayed prominently; the raw chunk id is de-emphasised.
    """
    rank = position + 1
    name = _html.escape(result.filename, quote=True)
    text = _html.escape(result.text, quote=True)
    score = f"{result.score:.2f}"
    sources = ", ".join(_html.escape(s, quote=True) for s in result.sources) or "bm25"

    return f"""
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
"""
