"""Design system for the Enterprise AI Document Assistant frontend.

This module is the single source of truth for the visual identity ("Aurora"): colour tokens, the
original logo mark, and the CSS that is injected once per session. It contains no business logic —
only styling. The CSS targets Streamlit's stable element selectors and uses a small number of
custom classes (``.aurora-*``) for the bespoke cards, badges, and layout, so the theme stays
maintainable and does not rely on fragile, deeply-nested selectors.

Owned by Agent 3 (Frontend Engineering).
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Colour tokens (the "Aurora" palette)
# ---------------------------------------------------------------------------
# Deep-space surfaces
BG_PRIMARY = "#0B1120"  # page background
BG_SURFACE = "#0F172A"  # card / panel background
BG_SURFACE_2 = "#111C33"  # elevated surface (hover)
BORDER = "rgba(148, 163, 184, 0.16)"  # subtle hairline border
BORDER_STRONG = "rgba(148, 163, 184, 0.30)"

# Accents
ACCENT_BLUE = "#3B82F6"
ACCENT_VIOLET = "#8B5CF6"
ACCENT_CYAN = "#22D3EE"
GRADIENT = "linear-gradient(135deg, #3B82F6 0%, #8B5CF6 55%, #22D3EE 120%)"

# Semantic
SUCCESS = "#34D399"
ERROR = "#F87171"
WARNING = "#FBBF24"
INFO = "#38BDF8"

# Text
TEXT_PRIMARY = "#E2E8F0"
TEXT_MUTED = "#94A3B8"
TEXT_DIM = "#64748B"

# Radius + shadow
RADIUS = "14px"
RADIUS_SM = "10px"
SHADOW = "0 8px 24px rgba(2, 6, 23, 0.45)"
SHADOW_SM = "0 2px 8px rgba(2, 6, 23, 0.35)"


# ---------------------------------------------------------------------------
# Original logo mark (abstract "document + spark" glyph — no copied branding)
# ---------------------------------------------------------------------------
def logo_svg(size: int = 44) -> str:
    """Return an inline SVG logo: a rounded document tile with a gradient spark."""
    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none"
     xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Aurora logo">
  <defs>
    <linearGradient id="auroraGrad" x1="4" y1="4" x2="44" y2="44"
                    gradientUnits="userSpaceOnUse">
      <stop stop-color="#3B82F6"/>
      <stop offset="0.55" stop-color="#8B5CF6"/>
      <stop offset="1" stop-color="#22D3EE"/>
    </linearGradient>
  </defs>
  <rect x="4" y="4" width="40" height="40" rx="12"
        fill="url(#auroraGrad)" fill-opacity="0.16"/>
  <rect x="4" y="4" width="40" height="40" rx="12"
        stroke="url(#auroraGrad)" stroke-width="2"/>
  <path d="M17 15h10l6 6v12a2 2 0 0 1-2 2H17a2 2 0 0 1-2-2V17a2 2 0 0 1 2-2Z"
        fill="url(#auroraGrad)"/>
  <path d="M27 15v6h6" stroke="#0B1120" stroke-width="2" stroke-linejoin="round"/>
  <path d="M19 26h10M19 30h7" stroke="#0B1120" stroke-width="2" stroke-linecap="round"/>
  <circle cx="34" cy="34" r="4.5" fill="#22D3EE"/>
  <path d="M34 31.5v5M31.5 34h5" stroke="#0B1120" stroke-width="1.4" stroke-linecap="round"/>
</svg>
"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def _css() -> str:
    """Build the full stylesheet for the Aurora theme."""
    return f"""
<style>
/* ---- Base surface ------------------------------------------------------- */
html, body, [class*="css"] {{
  color: {TEXT_PRIMARY};
  font-size: 16px;
}}
.stApp {{
  background: radial-gradient(1200px 600px at 80% -10%, rgba(139, 92, 246, 0.18), transparent 60%),
              radial-gradient(900px 500px at 0% 0%, rgba(59, 130, 246, 0.16), transparent 55%),
              {BG_PRIMARY};
  color: {TEXT_PRIMARY};
  font-size: 16px;
}}
/* Body copy is slightly larger and more legible than Streamlit's default. */
.stApp p, .stApp li {{
  font-size: 1rem;
  line-height: 1.55;
}}

/* ---- Streamlit header + toolbar (dark, no white strip, no clipping) ----- */
[data-testid="stHeader"] {{
  background: transparent;
  border-bottom: 1px solid {BORDER};
}}
[data-testid="stToolbar"] {{
  background: transparent;
}}
[data-testid="stToolbar"] [data-testid="stToolbarItems"] {{
  background: transparent;
}}
/* Main content starts clear of the fixed header so nothing is clipped.
   Wider on large screens to use the available space, but capped so long passages
   keep a readable line length. */
.block-container {{
  max-width: 1440px;
  padding-top: 4.5rem;
  padding-bottom: 3rem;
  padding-left: 2.5rem;
  padding-right: 2.5rem;
}}
@media (max-width: 1200px) {{
  .block-container {{ max-width: 1100px; }}
}}

/* ---- Typography --------------------------------------------------------- */
h1, h2, h3, h4 {{
  color: {TEXT_PRIMARY};
  font-weight: 650;
  letter-spacing: -0.01em;
}}
h1 {{ font-size: 2rem; }}
h2 {{ font-size: 1.5rem; }}
h3 {{ font-size: 1.2rem; }}
.stApp [data-testid="stCaptionContainer"] p,
.stApp p {{
  color: {TEXT_MUTED};
}}
.stApp [data-testid="stMarkdownContainer"] {{
  color: {TEXT_PRIMARY};
}}
/* Secondary / caption text is readable, not tiny. */
.stApp [data-testid="stCaptionContainer"] p {{
  font-size: 0.9rem;
  color: {TEXT_MUTED};
}}
/* Control labels (selectbox / text_input / radio labels) are clear and legible. */
.stApp label,
.stApp [data-testid="stLabel"] p,
.stApp .stRadio label {{
  font-size: 0.92rem;
  color: {TEXT_PRIMARY};
  font-weight: 550;
}}
/* Sidebar text is legible at a comfortable size. */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label {{
  font-size: 0.9rem;
}}

/* ---- Sidebar ------------------------------------------------------------ */
section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(11, 17, 32, 0.96));
  border-right: 1px solid {BORDER};
  backdrop-filter: blur(6px);
}}
section[data-testid="stSidebar"] > div:first-child {{
  padding-top: 1.4rem;
}}
section[data-testid="stSidebar"] hr {{
  border-color: {BORDER};
  opacity: 1;
}}

/* ---- Sidebar navigation (native st.page_link, the single navigation system) ----
   The native st.navigation widget is hidden so the sidebar can be ordered brand → nav →
   status; the visible nav is drawn with st.page_link, which uses the same active-page
   highlighting and URL routing. */
section[data-testid="stSidebar"] [data-testid="stPageLink"] {{
  display: block;
  margin: 4px 0;
}}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border-radius: {RADIUS_SM};
  border: 1px solid transparent;
  color: {TEXT_MUTED};
  font-size: 0.95rem;
  font-weight: 550;
  text-decoration: none;
  transition: all 0.15s ease;
}}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{
  background: {BG_SURFACE_2};
  color: {TEXT_PRIMARY};
}}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {{
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(139, 92, 246, 0.18));
  border-color: rgba(139, 92, 246, 0.45);
  color: {TEXT_PRIMARY};
  box-shadow: {SHADOW_SM};
}}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a svg {{
  flex: none;
}}

/* ---- Brand header in sidebar ------------------------------------------- */
.aurora-brand {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 8px 10px;
}}
.aurora-brand-name {{
  font-size: 1.02rem;
  font-weight: 700;
  line-height: 1.15;
  color: {TEXT_PRIMARY};
}}
.aurora-brand-sub {{
  font-size: 0.72rem;
  color: {TEXT_DIM};
  letter-spacing: 0.02em;
}}

/* ---- Status pill -------------------------------------------------------- */
.aurora-status {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: {RADIUS_SM};
  border: 1px solid {BORDER};
  background: {BG_SURFACE};
  font-size: 0.85rem;
  font-weight: 550;
}}
.aurora-status .aurora-dot {{
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: none;
}}
.aurora-status.online .aurora-dot {{
  background: {SUCCESS};
  box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.18);
}}
.aurora-status.offline .aurora-dot {{
  background: {ERROR};
  box-shadow: 0 0 0 4px rgba(248, 113, 113, 0.18);
}}
.aurora-status.checking .aurora-dot {{
  background: {WARNING};
  box-shadow: 0 0 0 4px rgba(251, 191, 36, 0.18);
}}
.aurora-status .aurora-status-label {{ color: {TEXT_PRIMARY}; }}
.aurora-status .aurora-status-sub {{ color: {TEXT_DIM}; font-size: 0.72rem; }}

/* ---- Page header -------------------------------------------------------- */
.aurora-page-header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}}
.aurora-page-title {{
  font-size: 1.7rem;
  font-weight: 700;
  color: {TEXT_PRIMARY};
  letter-spacing: -0.02em;
}}
.aurora-page-desc {{
  color: {TEXT_MUTED};
  font-size: 0.95rem;
  margin-top: 4px;
}}
.aurora-eyebrow {{
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  background: {GRADIENT};
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 6px;
}}

/* ---- Stat / overview cards --------------------------------------------- */
.aurora-stats {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 18px 0 8px;
}}
@media (max-width: 900px) {{
  .aurora-stats {{ grid-template-columns: repeat(2, 1fr); }}
}}
.aurora-stat {{
  position: relative;
  background: {BG_SURFACE};
  border: 1px solid {BORDER};
  border-radius: {RADIUS};
  padding: 18px 18px 16px;
  overflow: hidden;
  box-shadow: {SHADOW_SM};
}}
.aurora-stat::before {{
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: var(--aurora-accent, {GRADIENT});
}}
.aurora-stat .aurora-stat-icon {{
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  background: rgba(148, 163, 184, 0.10);
  border: 1px solid {BORDER};
  margin-bottom: 12px;
}}
.aurora-stat .aurora-stat-value {{
  font-size: 1.9rem;
  font-weight: 750;
  line-height: 1;
  color: {TEXT_PRIMARY};
}}
.aurora-stat .aurora-stat-label {{
  font-size: 0.86rem;
  color: {TEXT_MUTED};
  margin-top: 6px;
  font-weight: 500;
}}

/* ---- Generic card ------------------------------------------------------- */
.aurora-card {{
  background: {BG_SURFACE};
  border: 1px solid {BORDER};
  border-radius: {RADIUS};
  padding: 20px;
  box-shadow: {SHADOW_SM};
}}
.aurora-card-title {{
  font-size: 1.02rem;
  font-weight: 650;
  color: {TEXT_PRIMARY};
  margin-bottom: 4px;
}}
.aurora-card-sub {{
  font-size: 0.9rem;
  color: {TEXT_MUTED};
  margin-bottom: 14px;
}}

/* ---- Upload (native st.file_uploader, styled to match Aurora) ----------- */
[data-testid="stFileUploader"] {{
  background: {BG_SURFACE};
  border: 1px solid {BORDER};
  border-radius: {RADIUS};
  padding: 16px;
  box-shadow: {SHADOW_SM};
}}
[data-testid="stFileUploader"] section {{
  background: {BG_SURFACE_2};
  border: 1px dashed {BORDER_STRONG};
  border-radius: {RADIUS_SM};
}}
[data-testid="stFileUploader"] section:hover {{
  border-color: {ACCENT_VIOLET};
}}
[data-testid="stFileUploader"] section p {{
  color: {TEXT_MUTED};
}}
[data-testid="stFileUploader"] section button {{
  background: {GRADIENT};
  border: none;
  color: white;
  font-weight: 600;
  border-radius: {RADIUS_SM};
}}
[data-testid="stFileUploader"] section button:hover {{
  filter: brightness(1.08);
}}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {{
  border-color: {BORDER_STRONG};
}}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {{
  background: {BG_SURFACE_2};
  border: 1px solid {BORDER};
  border-radius: {RADIUS_SM};
  color: {TEXT_PRIMARY};
}}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] p {{
  color: {TEXT_PRIMARY};
}}

/* ---- Buttons ------------------------------------------------------------ */
.stButton > button, .stDownloadButton > button {{
  background: {BG_SURFACE_2};
  border: 1px solid {BORDER_STRONG};
  color: {TEXT_PRIMARY};
  border-radius: {RADIUS_SM};
  font-weight: 600;
  padding: 0.55rem 1.1rem;
  transition: all 0.15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  background: {BG_SURFACE};
  border-color: {ACCENT_VIOLET};
  transform: translateY(-1px);
}}
.stButton > button[kind="primary"], .stButton > button[data-testid="stFormSubmitButton"] {{
  background: {GRADIENT};
  border: none;
  color: white;
  font-weight: 650;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4);
}}
.stButton > button[kind="primary"]:hover {{
  filter: brightness(1.08);
  transform: translateY(-1px);
}}

/* ---- Status badges ------------------------------------------------------ */
.aurora-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 650;
  border: 1px solid transparent;
  white-space: nowrap;
}}
.aurora-badge .aurora-badge-dot {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
}}
.aurora-badge.processed {{
  color: {SUCCESS};
  background: rgba(52, 211, 153, 0.12);
  border-color: rgba(52, 211, 153, 0.35);
}}
.aurora-badge.processed .aurora-badge-dot {{ background: {SUCCESS}; }}
.aurora-badge.error {{
  color: {ERROR};
  background: rgba(248, 113, 113, 0.12);
  border-color: rgba(248, 113, 113, 0.35);
}}
.aurora-badge.error .aurora-badge-dot {{ background: {ERROR}; }}
.aurora-badge.neutral {{
  color: {TEXT_MUTED};
  background: rgba(148, 163, 184, 0.12);
  border-color: {BORDER_STRONG};
}}
.aurora-badge.neutral .aurora-badge-dot {{ background: {TEXT_DIM}; }}

/* ---- Document cards ----------------------------------------------------- */
.aurora-doc-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-top: 16px;
}}
.aurora-doc {{
  position: relative;
  background: {BG_SURFACE};
  border: 1px solid {BORDER};
  border-radius: {RADIUS};
  padding: 18px;
  box-shadow: {SHADOW_SM};
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}}
.aurora-doc:hover {{
  transform: translateY(-3px);
  border-color: rgba(139, 92, 246, 0.5);
  box-shadow: {SHADOW};
}}
.aurora-doc.error {{
  border-color: rgba(248, 113, 113, 0.35);
}}
.aurora-doc-top {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}}
.aurora-doc-icon {{
  width: 44px;
  height: 44px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid {BORDER};
  flex: none;
}}
.aurora-doc.error .aurora-doc-icon {{
  background: rgba(248, 113, 113, 0.12);
}}
.aurora-doc-name {{
  font-size: 1.08rem;
  font-weight: 700;
  color: {TEXT_PRIMARY};
  word-break: break-word;
  line-height: 1.3;
}}
.aurora-doc-meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  font-size: 0.88rem;
  color: {TEXT_MUTED};
}}
.aurora-doc-meta .aurora-doc-meta-item {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
}}
.aurora-doc-error {{
  font-size: 0.82rem;
  color: {ERROR};
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.25);
  border-radius: {RADIUS_SM};
  padding: 8px 10px;
  line-height: 1.4;
}}
.aurora-doc-details {{
  font-size: 0.78rem;
  color: {TEXT_DIM};
  border-top: 1px solid {BORDER};
  padding-top: 10px;
  margin-top: auto;
}}
.aurora-doc-details .aurora-doc-details-label {{
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.66rem;
  font-weight: 650;
  margin-bottom: 4px;
}}
.aurora-doc-details .aurora-doc-id {{
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  word-break: break-all;
  color: {TEXT_DIM};
}}

/* ---- Empty state -------------------------------------------------------- */
.aurora-empty {{
  text-align: center;
  padding: 56px 24px;
  border: 1px dashed {BORDER_STRONG};
  border-radius: {RADIUS};
  background: rgba(148, 163, 184, 0.03);
}}
.aurora-empty .aurora-empty-icon {{ font-size: 2.6rem; margin-bottom: 12px; }}
.aurora-empty .aurora-empty-title {{
  font-size: 1.05rem;
  font-weight: 650;
  color: {TEXT_PRIMARY};
}}
.aurora-empty .aurora-empty-sub {{
  font-size: 0.88rem;
  color: {TEXT_MUTED};
  margin-top: 6px;
}}

/* ---- Ask / search: mode indicator -------------------------------------- */
.aurora-mode {{
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 14px;
  border-radius: {RADIUS_SM};
  border: 1px solid {BORDER};
  background: {BG_SURFACE};
  margin-bottom: 14px;
}}
.aurora-mode-dot {{
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: {ACCENT_CYAN};
  box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.16);
  flex: none;
}}
.aurora-mode-label {{
  font-size: 0.82rem;
  font-weight: 650;
  color: {TEXT_PRIMARY};
}}
.aurora-mode-note {{
  font-size: 0.74rem;
  color: {TEXT_DIM};
}}

/* ---- Ask / search: search form ----------------------------------------- */
[data-testid="stForm"] {{
  background: transparent;
  border: none;
  padding: 0;
  gap: 0;
}}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {{
  background: {GRADIENT};
  border: none;
  color: white;
  font-weight: 650;
  border-radius: {RADIUS_SM};
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4);
}}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {{
  filter: brightness(1.08);
}}
.aurora-examples-label {{
  font-size: 0.74rem;
  color: {TEXT_DIM};
  margin: 14px 0 8px;
}}

/* ---- Ask / search: results --------------------------------------------- */
.aurora-results-header {{
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  margin: 18px 0 12px;
}}
.aurora-results-count {{
  font-size: 0.95rem;
  font-weight: 700;
  color: {TEXT_PRIMARY};
}}
.aurora-results-mode {{
  font-size: 0.8rem;
  color: {TEXT_MUTED};
}}
.aurora-results {{
  display: flex;
  flex-direction: column;
  gap: 14px;
}}
.aurora-result {{
  background: {BG_SURFACE};
  border: 1px solid {BORDER};
  border-radius: {RADIUS};
  padding: 16px 18px;
  box-shadow: {SHADOW_SM};
}}
.aurora-result-top {{
  display: flex;
  align-items: flex-start;
  gap: 14px;
}}
.aurora-result-rank {{
  flex: none;
  min-width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 750;
  font-size: 0.95rem;
  color: white;
  background: {GRADIENT};
}}
.aurora-result-source {{ flex: 1; min-width: 0; }}
.aurora-result-filename {{
  font-size: 1rem;
  font-weight: 650;
  color: {TEXT_PRIMARY};
  word-break: break-word;
}}
.aurora-result-meta {{
  font-size: 0.8rem;
  color: {TEXT_MUTED};
  margin-top: 3px;
}}
.aurora-result-passage {{
  margin-top: 12px;
  border-top: 1px solid {BORDER};
  padding-top: 10px;
}}
.aurora-result-passage summary {{
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  color: {ACCENT_CYAN};
  list-style: none;
}}
.aurora-result-passage summary::-webkit-details-marker {{ display: none; }}
.aurora-result-passage summary::before {{ content: "▸ "; }}
.aurora-result-passage[open] summary::before {{ content: "▾ "; }}
.aurora-result-text {{
  margin-top: 10px;
  font-size: 0.9rem;
  line-height: 1.6;
  color: {TEXT_PRIMARY};
  white-space: pre-wrap;
  word-break: break-word;
  background: {BG_SURFACE_2};
  border: 1px solid {BORDER};
  border-radius: {RADIUS_SM};
  padding: 12px 14px;
}}
.aurora-result-cite {{
  margin-top: 12px;
  font-size: 0.78rem;
  color: {TEXT_MUTED};
  display: flex;
  align-items: center;
  gap: 8px;
}}
.aurora-result-cite-label {{
  font-size: 0.64rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {TEXT_DIM};
  border: 1px solid {BORDER};
  border-radius: 999px;
  padding: 2px 8px;
}}

/* ---- Chat bubbles (Ask page) ------------------------------------------- */
.aurora-bubble {{
  border-radius: {RADIUS};
  padding: 12px 16px;
  line-height: 1.55;
  word-break: break-word;
}}
.aurora-bubble-user {{
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.22), rgba(139, 92, 246, 0.22));
  border: 1px solid rgba(139, 92, 246, 0.4);
  color: {TEXT_PRIMARY};
  display: inline-block;
  max-width: 100%;
}}
/* Right-align the user bubble within its (full-width) chat message row. */
[data-testid="stChatMessageUser"] {{
  display: flex;
  justify-content: flex-end;
}}
[data-testid="stChatMessageUser"] .aurora-bubble {{
  max-width: 75%;
}}
/* Assistant messages keep a comfortable reading width. */
[data-testid="stChatMessage"] {{
  gap: 10px;
}}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {{
  max-width: 860px;
}}
/* Suggestion chips (empty-state example queries). */
[data-testid="stChatMessage"] + .stButton,
.aurora-chat-empty + div .stButton {{
  justify-content: center;
}}

/* ---- Toolbar (search / sort / filter) ---------------------------------- */
.aurora-toolbar {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin: 6px 0 4px;
}}
.aurora-toolbar [data-baseweb="select"] > div {{
  background: {BG_SURFACE_2};
  border: 1px solid {BORDER_STRONG};
  border-radius: {RADIUS_SM};
  color: {TEXT_PRIMARY};
}}
.aurora-toolbar input[type="text"] {{
  background: {BG_SURFACE_2};
  border: 1px solid {BORDER_STRONG};
  border-radius: {RADIUS_SM};
  color: {TEXT_PRIMARY};
}}
.aurora-toolbar input[type="text"]::placeholder {{ color: {TEXT_DIM}; }}

/* ---- Streamlit element theming ----------------------------------------- */
[data-testid="stAlert"] {{
  border-radius: {RADIUS_SM};
  border: 1px solid {BORDER};
  background: {BG_SURFACE};
}}
[data-testid="stSpinner"] {{ color: {ACCENT_CYAN}; }}
[data-baseweb="select"] select, [data-baseweb="select"] input {{
  color: {TEXT_PRIMARY};
}}
hr {{ border-color: {BORDER}; }}
[data-testid="stExpander"] {{
  border: 1px solid {BORDER};
  border-radius: {RADIUS_SM};
  background: {BG_SURFACE};
}}
[data-testid="stExpander"] summary {{ color: {TEXT_PRIMARY}; }}
[data-testid="stExpander"] summary p {{ color: {TEXT_PRIMARY}; }}

/* ---- Scrollbar ---------------------------------------------------------- */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {BG_PRIMARY}; }}
::-webkit-scrollbar-thumb {{
  background: rgba(148, 163, 184, 0.25);
  border-radius: 8px;
}}
::-webkit-scrollbar-thumb:hover {{ background: rgba(148, 163, 184, 0.4); }}
</style>
"""


def inject_theme() -> None:
    """Inject the Aurora stylesheet.

    Called on every rerun (from ``layout.setup_page``) so the styling is guaranteed to be present
    on every page and after every navigation transition. Re-emitting the same ``<style>`` block is
    cheap and idempotent — Streamlit renders it as a single markdown block, so there is no
    accumulation of duplicate styles. A session-state gate was deliberately avoided because it
    could leave the CSS absent on a page whose DOM was replaced during a rerun.
    """
    st.markdown(_css(), unsafe_allow_html=True)


def brand_header() -> None:
    """Render the branded logo + name block (used in the sidebar)."""
    st.markdown(
        f"""
<div class="aurora-brand">
  {logo_svg(44)}
  <div>
    <div class="aurora-brand-name">Aurora</div>
    <div class="aurora-brand-sub">Enterprise AI Document Assistant</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, description: str) -> None:
    """Render a consistent page header with an eyebrow, title, and description."""
    st.markdown(
        f"""
<div class="aurora-page-header">
  <div>
    <div class="aurora-eyebrow">{eyebrow}</div>
    <div class="aurora-page-title">{title}</div>
    <div class="aurora-page-desc">{description}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def status_pill(online: bool, sub: str = "") -> None:
    """Render the backend connection status pill (verified connected or disconnected)."""
    cls = "online" if online else "offline"
    label = "Connected" if online else "Disconnected"
    sub_html = f'<div class="aurora-status-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
<div class="aurora-status {cls}">
  <span class="aurora-dot"></span>
  <div>
    <div class="aurora-status-label">{label}</div>
    {sub_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def status_pill_checking() -> None:
    """Render the backend connection status pill while the check is in flight (unverified)."""
    st.markdown(
        """
<div class="aurora-status checking">
  <span class="aurora-dot"></span>
  <div>
    <div class="aurora-status-label">Checking connection…</div>
    <div class="aurora-status-sub">verifying backend</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
