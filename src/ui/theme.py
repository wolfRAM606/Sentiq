"""Midnight Intelligence design tokens and global CSS for Sentiq."""
from __future__ import annotations

import streamlit as st

COLORS = {
    "bg": "#10111B",          # Obsidian
    "panel": "#191B2B",       # Raised Navy
    "panel_2": "#20233A",
    "violet": "#A78BFA",      # Electric Violet (primary accent)
    "lime": "#D9F66F",        # Acid Lime (featured KPI only)
    "ice": "#7DD3FC",         # Ice Blue (secondary data accent)
    "positive": "#6EE7B7",    # Mint
    "negative": "#FB7185",    # Coral
    "neutral": "#FBBF24",     # Amber
    "text": "#F4F4FA",
    "muted": "#AAA8C3",
    "border": "#303247",
}
SENTIMENT_COLORS = {"positive": COLORS["positive"], "neutral": COLORS["neutral"], "negative": COLORS["negative"],
                    "unavailable": COLORS["muted"]}
SENTIMENT_ORDER = ["positive", "neutral", "negative"]

FONT_BODY = "'Inter', 'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif"
FONT_DISPLAY = "'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, 'Times New Roman', serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Mono', Consolas, 'SFMono-Regular', Menlo, monospace"

_CSS = f"""
<style>
:root {{
  --sq-bg: {COLORS['bg']}; --sq-panel: {COLORS['panel']}; --sq-panel-2: {COLORS['panel_2']};
  --sq-violet: {COLORS['violet']}; --sq-lime: {COLORS['lime']}; --sq-ice: {COLORS['ice']};
  --sq-pos: {COLORS['positive']}; --sq-neg: {COLORS['negative']}; --sq-neu: {COLORS['neutral']};
  --sq-text: {COLORS['text']}; --sq-muted: {COLORS['muted']}; --sq-border: {COLORS['border']};
}}
html, body, [class*="css"], .stApp {{ font-family: {FONT_BODY}; }}
.stApp {{ background: radial-gradient(1200px 500px at 85% -10%, rgba(167,139,250,0.10), transparent 60%), var(--sq-bg); }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1320px; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
[data-testid="stHeader"] {{ background: transparent; }}

/* Sidebar */
section[data-testid="stSidebar"] {{ background: #0C0D16; border-right: 1px solid var(--sq-border); }}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: rgba(167,139,250,0.14); box-shadow: inset 3px 0 0 var(--sq-violet);
}}
.sq-brand {{ display:flex; align-items:center; gap:.6rem; margin:.2rem 0 .2rem; }}
.sq-mark {{ width:30px; height:30px; border-radius:8px; display:grid; place-items:center;
  background: linear-gradient(135deg, var(--sq-violet), #6D5AE6); color:#10111B; font-weight:800; font-family:{FONT_DISPLAY}; font-size:1.05rem; }}
.sq-brand-name {{ font-family:{FONT_DISPLAY}; font-size:1.35rem; font-weight:700; color:var(--sq-text); line-height:1; }}
.sq-brand-sub {{ font-size:.68rem; color:var(--sq-muted); letter-spacing:.08em; text-transform:uppercase; margin-top:.2rem; }}
.sq-side-status {{ border:1px solid var(--sq-border); border-radius:10px; padding:.6rem .7rem; background:var(--sq-panel);
  font-size:.78rem; color:var(--sq-muted); margin:.4rem 0 .6rem; }}
.sq-side-status b {{ color:var(--sq-text); font-weight:600; }}
.sq-dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:.4rem; vertical-align:middle; }}

/* Hero */
.sq-hero {{ display:grid; grid-template-columns: minmax(0, 1.65fr) minmax(240px, 1fr); gap:1.4rem; align-items:end;
  border-bottom:1px solid var(--sq-border); padding-bottom:1.4rem; margin-bottom:1.4rem; }}
.sq-eyebrow {{ font-family:{FONT_MONO}; font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:var(--sq-violet); }}
.sq-title {{ font-family:{FONT_DISPLAY}; font-size:clamp(2rem, 3.4vw, 3.05rem); line-height:1.05; font-weight:600; color:var(--sq-text); margin:.45rem 0 .55rem; }}
.sq-title em {{ font-style:italic; color:var(--sq-violet); }}
.sq-sub {{ color:var(--sq-muted); font-size:1rem; max-width:62ch; line-height:1.55; }}
.sq-meta {{ display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.9rem; }}
.sq-chip {{ font-family:{FONT_MONO}; font-size:.7rem; color:var(--sq-muted); border:1px solid var(--sq-border);
  border-radius:999px; padding:.18rem .6rem; background:rgba(25,27,43,.6); white-space:nowrap; }}
.sq-chip.demo {{ color:var(--sq-neu); border-color:rgba(251,191,36,.45); }}
.sq-chip.live {{ color:var(--sq-ice); border-color:rgba(125,211,252,.45); }}
.sq-feature {{ background:var(--sq-panel); border:1px solid var(--sq-border); border-radius:14px; padding:1.1rem 1.2rem;
  border-top:3px solid var(--sq-lime); }}
.sq-feature .lbl {{ font-size:.74rem; text-transform:uppercase; letter-spacing:.1em; color:var(--sq-muted); }}
.sq-feature .val {{ font-family:{FONT_DISPLAY}; font-size:3rem; line-height:1; color:var(--sq-lime); margin:.35rem 0 .25rem; font-weight:600; }}
.sq-feature .val small {{ font-size:1.1rem; color:var(--sq-muted); margin-left:.25rem; }}
.sq-feature .note {{ font-size:.8rem; color:var(--sq-muted); line-height:1.45; }}

/* KPI cards */
.sq-kpi {{ background:var(--sq-panel); border:1px solid var(--sq-border); border-radius:12px; padding:.85rem 1rem; height:100%; }}
.sq-kpi .lbl {{ font-size:.72rem; text-transform:uppercase; letter-spacing:.09em; color:var(--sq-muted); }}
.sq-kpi .val {{ font-size:1.75rem; font-weight:650; color:var(--sq-text); margin-top:.2rem; font-variant-numeric: tabular-nums; }}
.sq-kpi .note {{ font-size:.76rem; color:var(--sq-muted); margin-top:.15rem; }}
.sq-kpi.compact .val {{ font-size:1.12rem; line-height:1.3; font-weight:600; }}
.sq-kpi.accent-pos {{ box-shadow: inset 0 3px 0 var(--sq-pos); }}
.sq-kpi.accent-neg {{ box-shadow: inset 0 3px 0 var(--sq-neg); }}
.sq-kpi.accent-neu {{ box-shadow: inset 0 3px 0 var(--sq-neu); }}
.sq-kpi.accent-violet {{ box-shadow: inset 0 3px 0 var(--sq-violet); }}
.sq-kpi.accent-ice {{ box-shadow: inset 0 3px 0 var(--sq-ice); }}

/* Sections */
.sq-section {{ margin: 1.6rem 0 .6rem; }}
.sq-section h3 {{ font-family:{FONT_DISPLAY}; font-weight:600; font-size:1.35rem; margin:0; color:var(--sq-text); }}
.sq-section p {{ color:var(--sq-muted); font-size:.86rem; margin:.2rem 0 0; }}
.sq-num {{ font-family:{FONT_MONO}; color:var(--sq-violet); font-size:.75rem; margin-right:.5rem; }}

/* Insights */
.sq-insight {{ display:flex; gap:.7rem; padding:.65rem .2rem; border-bottom:1px dashed var(--sq-border); font-size:.92rem; line-height:1.5; }}
.sq-insight:last-child {{ border-bottom:none; }}
.sq-insight .bar {{ flex:0 0 4px; border-radius:4px; }}

/* Review cards */
.sq-review {{ background:var(--sq-panel); border:1px solid var(--sq-border); border-left:3px solid var(--sq-border);
  border-radius:10px; padding:.8rem .95rem; margin-bottom:.6rem; }}
.sq-review .txt {{ color:var(--sq-text); font-size:.95rem; line-height:1.55; }}
.sq-review .meta {{ display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.55rem; align-items:center; font-size:.72rem; color:var(--sq-muted); }}
.sq-review mark {{ background: rgba(167,139,250,.22); color: var(--sq-text); padding:0 .15rem; border-radius:3px; }}
.sq-pill {{ display:inline-block; font-size:.7rem; font-weight:600; padding:.1rem .5rem; border-radius:999px; text-transform:capitalize; }}
.sq-tag {{ display:inline-block; font-size:.7rem; padding:.1rem .45rem; border-radius:6px; border:1px solid var(--sq-border); color:var(--sq-ice); }}
.sq-warn {{ color:var(--sq-neu); font-weight:600; }}

/* Recommendations */
.sq-rec {{ background:var(--sq-panel); border:1px solid var(--sq-border); border-radius:12px; padding:1rem 1.1rem; margin-bottom:.8rem; }}
.sq-rec .head {{ display:flex; justify-content:space-between; gap:1rem; align-items:baseline; flex-wrap:wrap; }}
.sq-rec .title {{ font-family:{FONT_DISPLAY}; font-size:1.12rem; color:var(--sq-text); }}
.sq-rec .action {{ margin:.5rem 0; color:var(--sq-text); font-size:.92rem; }}
.sq-rec .ev {{ font-size:.85rem; color:var(--sq-muted); border-left:2px solid var(--sq-border); padding-left:.7rem; margin:.3rem 0; font-style:italic; }}
.sq-rec .cav {{ font-size:.76rem; color:var(--sq-muted); margin-top:.4rem; }}

/* Empty / notice states */
.sq-empty {{ border:1px dashed var(--sq-border); border-radius:12px; padding:1.4rem; text-align:center; color:var(--sq-muted); background:rgba(25,27,43,.5); }}
.sq-empty b {{ display:block; color:var(--sq-text); font-size:1rem; margin-bottom:.3rem; }}

/* Native components */
[data-testid="stMetric"] {{ background:var(--sq-panel); border:1px solid var(--sq-border); border-radius:12px; padding:.7rem .9rem; }}
[data-testid="stExpander"] details {{ border-color: var(--sq-border) !important; border-radius:10px; background: var(--sq-panel); }}
.stTabs [data-baseweb="tab-list"] {{ gap: .4rem; border-bottom:1px solid var(--sq-border); }}
.stTabs [data-baseweb="tab"] {{ padding: .4rem .8rem; }}
[data-testid="stDataFrame"] {{ border:1px solid var(--sq-border); border-radius:10px; }}
.stDownloadButton button, .stButton button {{ border-radius:8px; }}
.sq-foot {{ margin-top:3rem; padding-top:1rem; border-top:1px solid var(--sq-border); color:var(--sq-muted); font-size:.75rem; }}

@media (max-width: 900px) {{
  .sq-hero {{ grid-template-columns: 1fr; }}
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
