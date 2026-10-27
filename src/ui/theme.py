"""Sentiq design tokens (Ivory, Burgundy and Sage; see docs/DESIGN_SYSTEM.md) and global CSS."""
from __future__ import annotations

import streamlit as st

LIGHT = {
    "bg": "#F5F0E8", "surface": "#EDE6DA", "surface_2": "#E5DCCC", "rule": "#D3C8B6",
    "text": "#25242A", "muted": "#625C57",
    "brand": "#702F45", "brand_ink": "#F5F0E8", "brand_tint": "rgba(112,47,69,.08)",
    "sage": "#8AAB91", "sage_text": "#45694E",
    "positive": "#45694E", "neutral": "#7A5D16", "negative": "#A8442F",
}
DARK = {
    "bg": "#1D1B1F", "surface": "#26232A", "surface_2": "#302C34", "rule": "#3D3842",
    "text": "#EFE8DC", "muted": "#ABA399",
    "brand": "#D08AA0", "brand_ink": "#1D1B1F", "brand_tint": "rgba(208,138,160,.12)",
    "sage": "#8AAB91", "sage_text": "#9DBDA3",
    "positive": "#9DBDA3", "neutral": "#D9B66A", "negative": "#E58C73",
}
SENTIMENT_ORDER = ["positive", "neutral", "negative"]

FONT_BODY = "'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif"
FONT_DISPLAY = "Fraunces, 'Iowan Old Style', Georgia, serif"
FONT_MONO = "'IBM Plex Mono', Consolas, 'SFMono-Regular', monospace"


def mode() -> str:
    """'light' or 'dark', following the viewer's Streamlit theme setting."""
    try:
        return "dark" if (st.context.theme.type or "light") == "dark" else "light"
    except Exception:  # outside a script run (tests, reports)
        return "light"


def palette(which: str | None = None) -> dict:
    return DARK if (which or mode()) == "dark" else LIGHT


def sentiment_colors(which: str | None = None) -> dict:
    p = palette(which)
    return {"positive": p["positive"], "neutral": p["neutral"], "negative": p["negative"], "unavailable": p["muted"]}


def _css(p: dict) -> str:
    return f"""
<style>
:root {{
  --bg:{p['bg']}; --surface:{p['surface']}; --surface-2:{p['surface_2']}; --rule:{p['rule']};
  --text:{p['text']}; --muted:{p['muted']}; --brand:{p['brand']}; --brand-ink:{p['brand_ink']};
  --brand-tint:{p['brand_tint']}; --sage:{p['sage']}; --sage-text:{p['sage_text']};
  --pos:{p['positive']}; --neu:{p['neutral']}; --neg:{p['negative']};
}}
html, body, .stApp {{ font-family:{FONT_BODY}; }}
.stApp {{ background: var(--bg); }}
.block-container {{ padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1280px; }}
h1, h2, h3, h4 {{ font-family:{FONT_DISPLAY}; letter-spacing:-0.01em; }}
[data-testid="stHeader"] {{ background: transparent; }}
*, *::before, *::after {{ box-shadow: none !important; }}

/* Sidebar navigation: selected page gets a burgundy tint and text colour, no stripe */
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{ border-radius:0; }}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ background: var(--brand-tint); }}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{ background: var(--brand-tint); }}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: var(--brand); font-weight:600; }}
.sq-side-status {{ border-top:1px solid var(--rule); border-bottom:1px solid var(--rule); padding:.7rem 0; font-size:.8rem;
  color:var(--muted); margin:.4rem 0 .8rem; line-height:1.5; }}
.sq-side-status b {{ color:var(--text); font-weight:600; }}
.sq-label {{ font-family:{FONT_MONO}; font-size:.7rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}

/* Editorial header */
.sq-hero {{ display:grid; grid-template-columns:minmax(0,1.7fr) minmax(240px,1fr); gap:2.2rem; align-items:end;
  border-bottom:1px solid var(--rule); padding-bottom:1.6rem; margin-bottom:1.6rem; }}
.sq-eyebrow {{ font-family:{FONT_MONO}; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--brand); }}
.sq-title {{ font-family:{FONT_DISPLAY}; font-size:clamp(2.1rem,3.6vw,3.3rem); line-height:1.04; font-weight:500;
  color:var(--text); margin:.5rem 0 .6rem; font-variation-settings:"opsz" 96; }}
.sq-title em {{ font-style:italic; color:var(--brand); }}
.sq-sub {{ color:var(--muted); font-size:1.02rem; max-width:60ch; line-height:1.6; }}
.sq-meta {{ display:flex; flex-wrap:wrap; gap:.4rem .9rem; margin-top:1rem; }}
.sq-chip {{ font-family:{FONT_MONO}; font-size:.72rem; color:var(--muted); white-space:nowrap; }}
.sq-chip + .sq-chip::before {{ content:"/"; margin-right:.9rem; color:var(--rule); }}
.sq-chip.demo {{ color:var(--neu); }}
.sq-chip.live {{ color:var(--sage-text); }}
.sq-feature {{ border-top:2px solid var(--brand); padding-top:.9rem; }}
.sq-feature .lbl {{ font-family:{FONT_MONO}; font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
.sq-feature .val {{ font-family:{FONT_DISPLAY}; font-size:3.4rem; line-height:1; color:var(--brand); margin:.4rem 0 .3rem; font-weight:500; }}
.sq-feature .val small {{ font-size:1.05rem; color:var(--muted); margin-left:.3rem; font-family:{FONT_BODY}; }}
.sq-feature .note {{ font-size:.82rem; color:var(--muted); line-height:1.5; }}

/* Figures: numbers set in type, separated by hairlines */
.sq-kpi {{ border-top:1px solid var(--rule); padding:.8rem 0 .2rem; height:100%; }}
.sq-kpi .lbl {{ font-family:{FONT_MONO}; font-size:.68rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
.sq-kpi .val {{ font-family:{FONT_DISPLAY}; font-size:2rem; font-weight:500; color:var(--text); margin-top:.2rem; font-variant-numeric:tabular-nums; }}
.sq-kpi .note {{ font-size:.78rem; color:var(--muted); margin-top:.1rem; }}
.sq-kpi.compact .val {{ font-family:{FONT_BODY}; font-size:1.08rem; line-height:1.35; font-weight:600; }}
.sq-kpi.accent-pos .val {{ color:var(--pos); }}
.sq-kpi.accent-neg .val {{ color:var(--neg); }}
.sq-kpi.accent-neu .val {{ color:var(--neu); }}
.sq-kpi.accent-violet .val, .sq-kpi.accent-brand .val {{ color:var(--brand); }}
.sq-kpi.accent-ice .val {{ color:var(--sage-text); }}

/* Section headings */
.sq-section {{ margin:2.2rem 0 .7rem; }}
.sq-section h3 {{ font-family:{FONT_DISPLAY}; font-weight:500; font-size:1.5rem; margin:0; color:var(--text); }}
.sq-section p {{ color:var(--muted); font-size:.88rem; margin:.25rem 0 0; max-width:75ch; }}
.sq-num {{ font-family:{FONT_MONO}; color:var(--brand); font-size:.75rem; margin-right:.6rem; vertical-align:.25em; }}

/* Insights: a numbered list with hairlines */
.sq-insights {{ border-top:1px solid var(--rule); }}
.sq-insight {{ display:grid; grid-template-columns:2.2rem 1fr; gap:.4rem; padding:.7rem 0; border-bottom:1px solid var(--rule);
  font-size:.94rem; line-height:1.55; color:var(--text); }}
.sq-insight .n {{ font-family:{FONT_MONO}; font-size:.75rem; color:var(--muted); padding-top:.15rem; }}

/* Review cards */
.sq-review {{ border:1px solid var(--rule); background:var(--surface); padding:.85rem 1rem; margin-bottom:.6rem; }}
.sq-review .txt {{ color:var(--text); font-size:.96rem; line-height:1.6; }}
.sq-review .meta {{ display:flex; flex-wrap:wrap; gap:.35rem .8rem; margin-top:.55rem; align-items:center; font-size:.74rem; color:var(--muted); }}
.sq-review mark {{ background:var(--brand-tint); color:var(--text); padding:0 .12rem; text-decoration:underline; text-decoration-color:var(--brand);
  text-underline-offset:3px; }}
.sq-pill {{ display:inline-flex; align-items:center; gap:.35rem; font-family:{FONT_MONO}; font-size:.7rem; font-weight:500;
  text-transform:uppercase; letter-spacing:.06em; }}
.sq-pill i {{ display:inline-block; width:.55rem; height:.55rem; }}
.sq-tag {{ font-size:.72rem; color:var(--text); border-bottom:1px solid var(--sage); }}
.sq-warn {{ color:var(--neu); font-weight:600; }}

/* Recommendations */
.sq-rec {{ border-top:1px solid var(--rule); padding:1rem 0 1.1rem; }}
.sq-rec .head {{ display:flex; justify-content:space-between; gap:1rem; align-items:baseline; flex-wrap:wrap; }}
.sq-rec .title {{ font-family:{FONT_DISPLAY}; font-size:1.2rem; color:var(--text); }}
.sq-rec .action {{ margin:.5rem 0; color:var(--text); font-size:.93rem; max-width:80ch; }}
.sq-rec .ev {{ font-size:.88rem; color:var(--muted); padding-left:1rem; margin:.3rem 0; font-family:{FONT_DISPLAY}; font-style:italic; }}
.sq-rec .cav {{ font-size:.76rem; color:var(--muted); margin-top:.5rem; }}

/* Empty / notice states */
.sq-empty {{ border:1px dashed var(--rule); padding:1.4rem; color:var(--muted); background:var(--surface); }}
.sq-empty b {{ display:block; color:var(--text); font-size:1rem; margin-bottom:.3rem; font-family:{FONT_DISPLAY}; font-weight:500; }}

/* Native components */
[data-testid="stMetric"] {{ border-top:1px solid var(--rule); padding:.6rem 0; }}
[data-testid="stExpander"] details {{ border-radius:0 !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap:1.2rem; border-bottom:1px solid var(--rule); }}
.stTabs [data-baseweb="tab"] {{ padding:.5rem 0; }}
.stTabs [data-baseweb="tab"]:hover {{ color:var(--brand); }}
a {{ text-underline-offset:3px; }}
a:hover {{ text-decoration-thickness:2px; }}
.stButton button:hover, .stDownloadButton button:hover {{ background:var(--brand-tint); }}
.sq-foot {{ margin-top:3.5rem; padding-top:1rem; border-top:1px solid var(--rule); color:var(--muted); font-size:.76rem; line-height:1.6; }}

@media (max-width: 900px) {{
  .sq-hero {{ grid-template-columns: 1fr; }}
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
"""


def inject_css() -> None:
    st.markdown(_css(palette()), unsafe_allow_html=True)
