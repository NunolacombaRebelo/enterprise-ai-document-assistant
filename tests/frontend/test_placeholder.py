"""Frontend tests (Agent 3-owned).

Phase 0 contains only a placeholder to establish the directory. Agent 3 will add the full frontend
test suite (Streamlit app behavior, HTTP API client) in later phases.
"""

from __future__ import annotations


def test_frontend_app_module_exists() -> None:
    """Placeholder: the frontend entrypoint file is present and non-empty."""
    from pathlib import Path

    app_path = Path(__file__).resolve().parents[2] / "frontend" / "app.py"
    assert app_path.exists()
    assert app_path.stat().st_size > 0
