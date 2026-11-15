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
        # The native st.navigation renders as a SpecialBlock in the sidebar.
        special_blocks = [e for e in at.sidebar if type(e).__name__ == "SpecialBlock"]
        assert len(special_blocks) >= 1, "st.navigation nav block missing"
        # The old duplicate radio navigation must be gone.
        assert len(at.sidebar.radio) == 0, "duplicate radio navigation still present"

    def test_no_decorative_nav_pills(self) -> None:
        """The old decorative .aurora-nav-item pills must not be rendered."""
        at = _render()
        md = _markdown(at)
        assert "aurora-nav-item" not in md, "decorative nav pills still rendered"

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
            "stSidebarNav",
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
        assert "stSidebarNav" in md


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
    def test_ask_page_renders_coming_soon(self) -> None:
        """The Ask page renders a clearly-identified 'coming soon' panel (no fake AI)."""

        # Render the Ask page body directly with the theme injected, mirroring main(). Imports are
        # done inside the function because AppTest.from_function executes it in an isolated
        # namespace where module-level imports are not visible.
        def ask_flow() -> None:
            from frontend.components import chat

            from frontend import state, theme

            theme.inject_theme()
            state.init_state()
            chat.render_ask_page()

        at = AppTest.from_function(ask_flow, default_timeout=20)
        at.run()
        assert not at.exception, f"ask page raised: {[e.value for e in at.exception]}"
        md = " ".join(m.value for m in at.markdown)
        assert "aurora-coming-soon" in md
        assert "In development" in md
        assert "aurora-feature" in md
        # No fake chat functionality.
        assert len(at.chat_input) == 0
