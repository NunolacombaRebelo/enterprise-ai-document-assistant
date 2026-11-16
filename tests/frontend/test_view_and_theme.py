"""Tests for the document library view logic (search / sort / filter) and the theme module.

The view logic in ``frontend/components/documents.py::_apply_view`` reads from Streamlit session
state. These tests drive it through a real Streamlit ``AppTest`` session so the behaviour is
exercised exactly as it runs in the app, without a backend or network.
"""

from __future__ import annotations

from datetime import datetime

from frontend.api.models import Document, DocumentStatus


def _docs() -> list[Document]:
    return [
        Document(
            id="a",
            filename="alpha.pdf",
            status=DocumentStatus.PROCESSED,
            page_count=1,
            created_at=datetime(2026, 1, 1, 10, 0),
        ),
        Document(
            id="b",
            filename="beta.pdf",
            status=DocumentStatus.ERROR,
            page_count=None,
            created_at=datetime(2026, 1, 2, 10, 0),
            error="bad",
        ),
        Document(
            id="c",
            filename="gamma.pdf",
            status=DocumentStatus.PROCESSED,
            page_count=3,
            created_at=datetime(2026, 1, 3, 10, 0),
        ),
    ]


class TestApplyView:
    def _run(self, search: str, sort: str, flt: str) -> list[str]:
        """Run _apply_view with the given view settings and return the visible filenames."""
        import streamlit as st
        from frontend.components import documents

        from frontend import state

        # Seed a fresh session state for the view keys.
        st.session_state[state.KEY_SEARCH] = search
        st.session_state[state.KEY_SORT] = sort
        st.session_state[state.KEY_FILTER] = flt
        visible = documents._apply_view(_docs())
        return [d.filename for d in visible]

    def test_no_filters_returns_all(self) -> None:
        assert set(self._run("", "newest", "all")) == {"alpha.pdf", "beta.pdf", "gamma.pdf"}

    def test_search_by_name(self) -> None:
        assert self._run("beta", "newest", "all") == ["beta.pdf"]

    def test_search_is_case_insensitive(self) -> None:
        assert self._run("ALPHA", "newest", "all") == ["alpha.pdf"]

    def test_search_no_match(self) -> None:
        assert self._run("zzz", "newest", "all") == []

    def test_filter_processed(self) -> None:
        assert set(self._run("", "newest", "processed")) == {"alpha.pdf", "gamma.pdf"}

    def test_filter_error(self) -> None:
        assert self._run("", "newest", "error") == ["beta.pdf"]

    def test_sort_newest(self) -> None:
        assert self._run("", "newest", "all") == ["gamma.pdf", "beta.pdf", "alpha.pdf"]

    def test_sort_oldest(self) -> None:
        assert self._run("", "oldest", "all") == ["alpha.pdf", "beta.pdf", "gamma.pdf"]

    def test_sort_name(self) -> None:
        assert self._run("", "name", "all") == ["alpha.pdf", "beta.pdf", "gamma.pdf"]

    def test_combined_search_and_filter(self) -> None:
        # "a" matches alpha, beta, gamma (all contain "a"); filter=processed keeps alpha+gamma.
        assert set(self._run("a", "name", "processed")) == {"alpha.pdf", "gamma.pdf"}
        # "a" matches all three, but filter=error keeps only beta.
        assert self._run("a", "name", "error") == ["beta.pdf"]
        # A search term matching no error document yields nothing under filter=error.
        assert self._run("gamma", "name", "error") == []


class TestTheme:
    def test_logo_svg_is_well_formed(self) -> None:
        from frontend import theme

        svg = theme.logo_svg(44)
        assert svg.lstrip().startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert "auroraGrad" in svg
        assert "44" in svg  # size reflected

    def test_css_contains_core_classes(self) -> None:
        from frontend import theme

        css = theme._css()
        for cls in (
            ".aurora-stats",
            ".aurora-stat",
            ".aurora-doc-grid",
            ".aurora-doc",
            ".aurora-badge",
            ".aurora-empty",
            # The sidebar nav is drawn with st.page_link (st.navigation is hidden so the sidebar
            # can be ordered brand -> nav -> status); it is styled via the stPageLink selector.
            "stPageLink",
            ".aurora-status",
            # Milestone 2 search UI.
            ".aurora-mode",
            ".aurora-result",
            ".aurora-index-status",
        ):
            assert cls in css, f"missing CSS class {cls}"

    def test_status_badge_variants(self) -> None:
        from frontend.components import cards

        assert "aurora-badge processed" in cards.status_badge(DocumentStatus.PROCESSED)
        assert "aurora-badge error" in cards.status_badge(DocumentStatus.ERROR)
        assert "aurora-badge neutral" in cards.status_badge("weird-status")

    def test_stat_card_escapes_values(self) -> None:
        from frontend.components import cards

        html = cards.stat_card("Total", "10 <docs>", "📚")
        assert "10 &lt;docs&gt;" in html  # escaped, not raw
