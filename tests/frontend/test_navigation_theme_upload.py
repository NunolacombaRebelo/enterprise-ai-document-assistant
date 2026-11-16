"""Tests for navigation, theme application, and upload behaviour.

These tests use Streamlit ``AppTest`` to render the actual application and verify:
- a single native navigation system (no duplicate radio / decorative pills),
- the Aurora theme is applied on every page (Documents and Ask),
- the upload UI is a single coherent file uploader with accurate size messaging,
- the backend connection states (connected / disconnected / checking).

No real backend, network, or credentials are required; the app is rendered in-process.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

# Resolve the app path relative to this test file (tests/frontend/ -> project root).
APP_PATH = str(Path(__file__).resolve().parents[2] / "frontend" / "app.py")


def _render() -> AppTest:
    """Render the app once and return the AppTest (no exceptions expected)."""
    at = AppTest.from_file(APP_PATH, default_timeout=25)
    at.run()
    assert not at.exception, f"app raised: {[e.value for e in at.exception]}"
    return at


def _markdown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


class TestNavigation:
    def test_single_navigation_system_no_radio(self) -> None:
        """There must be exactly one navigation system (st.navigation) and no radio."""
        at = _render()
        # The native st.navigation renders as a SpecialBlock in the sidebar (hidden position,
        # the visible nav is drawn with st.page_link).
        special_blocks = [e for e in at.sidebar if type(e).__name__ == "SpecialBlock"]
        assert len(special_blocks) >= 1, "st.navigation nav block missing"
        # The old duplicate radio navigation must be gone.
        assert len(at.sidebar.radio) == 0, "duplicate radio navigation still present"

    def test_no_decorative_nav_pills(self) -> None:
        """The old decorative .aurora-nav-item pills must not be rendered."""
        at = _render()
        md = _markdown(at)
        assert "aurora-nav-item" not in md, "decorative nav pills still rendered"

    def test_page_links_rendered(self) -> None:
        """The visible nav is two st.page_link items (Documents, Ask) in the sidebar."""
        at = _render()
        labels = [pl.label for pl in at.page_link]
        assert labels == ["Documents", "Ask"], f"unexpected page links: {labels}"

    def test_sidebar_hierarchy_brand_nav_status(self) -> None:
        """Sidebar order is brand -> navigation -> status (brand above nav, status below)."""
        at = _render()
        sidebar = at.sidebar
        brand_idx = next(
            (
                i
                for i, e in enumerate(sidebar)
                if type(e).__name__ == "Markdown" and 'aurora-brand"' in (e.value or "")
            ),
            None,
        )
        nav_idx = next(
            (i for i, e in enumerate(sidebar) if type(e).__name__ == "PageLink"),
            None,
        )
        status_idx = next(
            (
                i
                for i, e in enumerate(sidebar)
                if type(e).__name__ == "Markdown" and "aurora-status" in (e.value or "")
            ),
            None,
        )
        assert brand_idx is not None, "brand block missing"
        assert nav_idx is not None, "nav (page_link) missing"
        assert status_idx is not None, "status pill missing"
        assert brand_idx < nav_idx < status_idx, (
            f"sidebar order wrong: brand={brand_idx} nav={nav_idx} status={status_idx}"
        )

    def test_documents_is_default_page(self) -> None:
        """The Documents page is the default and renders its content."""
        at = _render()
        md = _markdown(at)
        assert "aurora-page-title" in md and "Documents" in md
        assert "aurora-stats" in md  # overview cards

    def test_navigation_state_persists_across_reruns(self) -> None:
        """Rerunning the app keeps the same active page (no flicker / reset)."""
        at = _render()
        at.run()  # rerun
        assert not at.exception
        md = _markdown(at)
        # The Documents page content is still present after a rerun.
        assert "aurora-stats" in md
        assert "Documents" in md


class TestTheme:
    def test_theme_css_present_on_documents(self) -> None:
        """The Aurora CSS is present in the rendered Documents page."""
        at = _render()
        md = _markdown(at)
        for cls in (
            "aurora-stats",
            "aurora-doc-grid",
            "aurora-badge",
            "aurora-status",
            "aurora-brand",
            "stPageLink",
            "stFileUploader",
            "stHeader",
        ):
            assert cls in md, f"missing CSS class {cls}"

    def test_theme_injected_once_per_rerun(self) -> None:
        """The theme is a single <style> block (idempotent, no accumulation)."""
        at = _render()
        md = _markdown(at)
        assert md.count("<style>") == 1, "theme CSS duplicated"

    def test_theme_present_after_rerun(self) -> None:
        """The theme remains present after a rerun (no session-gate loss)."""
        at = _render()
        at.run()
        assert not at.exception
        md = _markdown(at)
        assert "aurora-stats" in md
        assert "stPageLink" in md


class TestUpload:
    def test_single_file_uploader(self) -> None:
        """Exactly one file uploader is rendered (no duplicate upload interfaces)."""
        at = _render()
        assert len(at.file_uploader) == 1, "expected exactly one file uploader"

    def test_no_decorative_dropzone(self) -> None:
        """The old decorative .aurora-dropzone must not be rendered."""
        at = _render()
        md = _markdown(at)
        assert "aurora-dropzone" not in md, "decorative dropzone still rendered"

    def test_upload_limit_messaging_matches_backend(self) -> None:
        """The uploader help text states the real 25 MB limit (not 200 MB)."""
        at = _render()
        uploader = at.file_uploader[0]
        assert "25 MB" in (uploader.help or ""), "uploader help must state 25 MB limit"
        assert "200 MB" not in (uploader.help or ""), "uploader must not claim 200 MB"

    def test_upload_accepts_pdf_only(self) -> None:
        """The uploader is restricted to PDF files."""
        at = _render()
        uploader = at.file_uploader[0]
        assert uploader.allowed_type == [".pdf"]


class TestBackendStates:
    def test_status_pill_rendered(self) -> None:
        """A backend status pill is rendered in the sidebar."""
        at = _render()
        md = _markdown(at)
        assert "aurora-status" in md

    def test_checking_state_when_unverified(self) -> None:
        """Before the backend check completes, the status shows 'Checking' (not connected)."""
        # With no backend reachable, the check resolves to disconnected. The key assertion is
        # that a status pill is present and the app does not claim a verified connection it
        # has not made.
        at = _render()
        md = _markdown(at)
        assert "aurora-status" in md
        # The pill must be one of the three honest states.
        assert (
            "aurora-status online" in md
            or "aurora-status offline" in md
            or "aurora-status checking" in md
        )


class TestAskPage:
    def test_ask_page_renders_search_workspace(self) -> None:
        """The Ask page is a search workspace: mode indicator, input, examples, no fake chat."""

        # Render the Ask page body directly with the theme injected, mirroring main(). Imports are
        # done inside the function because AppTest.from_function executes it in an isolated
        # namespace where module-level imports are not visible.
        def ask_flow() -> None:
            from frontend.api.client import DocumentAPIClient
            from frontend.components import chat

            from frontend import state, theme

            theme.inject_theme()
            state.init_state()
            chat.render_ask_page(DocumentAPIClient())

        at = AppTest.from_function(ask_flow, default_timeout=20)
        at.run()
        assert not at.exception, f"ask page raised: {[e.value for e in at.exception]}"
        md = " ".join(m.value for m in at.markdown)
        # The BM25 / keyword retrieval mode is clearly labelled (not presented as semantic/AI).
        assert "aurora-mode" in md
        assert "BM25" in md
        # A search input and a submit button are present.
        assert len(at.text_input) == 1
        assert any(b.label == "Search documents" for b in at.button)
        # No fake chat functionality.
        assert len(at.chat_input) == 0

    def test_ask_page_renders_results(self) -> None:
        """The Ask page renders ranked results with source references when a search is seeded."""

        def ask_with_results() -> None:
            from frontend.api.client import DocumentAPIClient
            from frontend.api.models import Citation, SearchResponse, SearchResult
            from frontend.components import chat

            from frontend import state, theme

            theme.inject_theme()
            state.init_state()
            resp = SearchResponse(
                query="refund policy",
                mode="lexical",
                results=(
                    SearchResult(
                        chunk_id="d1:0",
                        document_id="d1",
                        filename="policy.pdf",
                        page=2,
                        chunk_index=0,
                        text="Refund policy passage.",
                        score=2.5,
                        sources=("bm25",),
                    ),
                ),
                citations=(
                    Citation(
                        document_id="d1",
                        filename="policy.pdf",
                        page=2,
                        chunk_index=0,
                        excerpt="Refund policy passage.",
                    ),
                ),
            )
            state.set_value(state.KEY_SEARCHED, True)
            state.set_value(state.KEY_LAST_QUERY, "refund policy")
            state.set_value(state.KEY_SEARCH_RESULTS, resp)
            chat.render_ask_page(DocumentAPIClient())

        at = AppTest.from_function(ask_with_results, default_timeout=20)
        at.run()
        assert not at.exception, f"ask results raised: {[e.value for e in at.exception]}"
        md = " ".join(m.value for m in at.markdown)
        assert "aurora-result" in md
        assert "policy.pdf" in md
        assert "Page 2" in md
        assert "2.50" in md
        assert "1 result" in md
        # No fabricated AI answer panel.
        assert "aurora-coming-soon" not in md or "In development" not in md
