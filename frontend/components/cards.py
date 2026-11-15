"""Reusable presentational building blocks for the Aurora theme.

These helpers render the bespoke HTML/CSS cards and badges used across the app. They are
presentation-only: they take plain data and emit styled markup. No business logic lives here.

Owned by Agent 3 (Frontend Engineering).
"""

from __future__ import annotations

import html

import streamlit as st
from frontend.api.models import DocumentStatus

from frontend import theme


def _esc(value: object) -> str:
    """HTML-escape a value for safe interpolation into markup."""
    return html.escape(str(value), quote=True)


def stat_card(
    label: str,
    value: str | int,
    icon: str,
    accent: str = theme.GRADIENT,
) -> str:
    """Return the HTML for a single overview/stat card."""
    return f"""
<div class="aurora-stat" style="--aurora-accent: {accent};">
  <div class="aurora-stat-icon">{icon}</div>
  <div class="aurora-stat-value">{_esc(value)}</div>
  <div class="aurora-stat-label">{_esc(label)}</div>
</div>
"""


def render_stats(cards: list[tuple[str, str | int, str, str]]) -> None:
    """Render a row of stat cards.

    Each entry is ``(label, value, icon, accent)``. The accent is a CSS colour or gradient used for
    the card's top accent bar.
    """
    inner = "".join(stat_card(label, value, icon, accent) for label, value, icon, accent in cards)
    st.markdown(f'<div class="aurora-stats">{inner}</div>', unsafe_allow_html=True)


def status_badge(status: str) -> str:
    """Return the HTML for a status badge.

    Maps the backend status to a coloured pill. Unknown statuses render as a neutral badge so a
    future backend status never breaks the UI.
    """
    if status == DocumentStatus.PROCESSED:
        cls, label = "processed", "Processed"
    elif status == DocumentStatus.ERROR:
        cls, label = "error", "Error"
    else:
        cls, label = "neutral", status
    badge = (
        f'<span class="aurora-badge {cls}">'
        f'<span class="aurora-badge-dot"></span>{_esc(label)}</span>'
    )
    return badge


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section header with a title and optional subtitle."""
    sub = f'<div class="aurora-card-sub">{_esc(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div><div class="aurora-card-title">{_esc(title)}</div>{sub}</div>',
        unsafe_allow_html=True,
    )
