"""Reusable HTML components for the Sentiq interface."""
from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

from src.config import ACADEMIC_TITLE, PRODUCT_DESCRIPTOR, PRODUCT_NAME
from src.ui.theme import COLORS, SENTIMENT_COLORS

esc = html.escape


def _md(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, subtitle: str, chips: list[tuple[str, str]] | None = None,
         feature: dict | None = None) -> None:
    """Editorial page header. ``title`` may contain <em>…</em> (trusted, static strings only)."""
    chip_html = "".join(f'<span class="sq-chip {cls}">{esc(text)}</span>' for text, cls in (chips or []))
    feat = ""
    if feature:
        suffix = f"<small>{esc(feature.get('suffix', ''))}</small>" if feature.get("suffix") else ""
        feat = (f'<div class="sq-feature"><div class="lbl">{esc(feature["label"])}</div>'
                f'<div class="val">{esc(str(feature["value"]))}{suffix}</div>'
                f'<div class="note">{esc(feature.get("note", ""))}</div></div>')
    _md(f'<div class="sq-hero"><div><div class="sq-eyebrow">{esc(eyebrow)}</div>'
        f'<div class="sq-title">{title}</div><div class="sq-sub">{esc(subtitle)}</div>'
        f'<div class="sq-meta">{chip_html}</div></div><div>{feat}</div></div>')


def section(title: str, caption: str = "", number: str | None = None) -> None:
    num = f'<span class="sq-num">{esc(number)}</span>' if number else ""
    cap = f"<p>{esc(caption)}</p>" if caption else ""
    _md(f'<div class="sq-section"><h3>{num}{esc(title)}</h3>{cap}</div>')


def kpi(label: str, value, note: str = "", accent: str = "", compact: bool = False) -> None:
    cls = (f"accent-{accent}" if accent else "") + (" compact" if compact else "")
    _md(f'<div class="sq-kpi {cls}"><div class="lbl">{esc(label)}</div><div class="val">{esc(str(value))}</div>'
        f'<div class="note">{esc(note)}</div></div>')


def pill(sentiment: str) -> str:
    color = SENTIMENT_COLORS.get(sentiment, COLORS["muted"])
    return (f'<span class="sq-pill" style="background:{color}22;color:{color};border:1px solid {color}66">'
            f'{esc(str(sentiment))}</span>')


def insights(items: list[dict]) -> None:
    tone_color = {"positive": COLORS["positive"], "negative": COLORS["negative"], "neutral": COLORS["neutral"],
                  "info": COLORS["ice"]}
    if not items:
        empty("No insights yet", "Insights appear once there are reviews in the current selection.")
        return
    rows = "".join(f'<div class="sq-insight"><div class="bar" style="background:{tone_color.get(i["tone"], COLORS["violet"])}"></div>'
                   f'<div>{esc(i["text"])}</div></div>' for i in items)
    _md(f'<div class="sq-kpi" style="padding:.4rem 1rem">{rows}</div>')


def empty(title: str, message: str) -> None:
    _md(f'<div class="sq-empty"><b>{esc(title)}</b>{esc(message)}</div>')


def highlight(text: str, terms: list[str]) -> str:
    """Escape text and wrap matched evidence terms in <mark>."""
    safe = esc(text)
    terms = sorted({t for t in terms if t and len(t) > 1}, key=len, reverse=True)
    if not terms:
        return safe
    pattern = re.compile(r"\b(" + "|".join(re.escape(esc(t)) for t in terms) + r")\b", re.IGNORECASE)
    return pattern.sub(r"<mark>\1</mark>", safe)


def review_card(row: pd.Series | dict, terms: list[str] | None = None, show_meta: bool = True, max_chars: int = 600) -> None:
    text = str(row["review_text"])
    shown = text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + " …"
    sentiment = row.get("sentiment", "unavailable")
    color = SENTIMENT_COLORS.get(sentiment, COLORS["border"])
    meta = [pill(sentiment)]
    conf = row.get("confidence")
    if conf is not None and conf == conf:
        meta.append(f"<span>confidence {conf:.0%}</span>")
    if bool(row.get("review_needed", False)) and sentiment != "unavailable":
        meta.append('<span class="sq-warn">⚑ review needed</span>')
    if row.get("aspects"):
        meta.extend(f'<span class="sq-tag">{esc(a)}</span>' for a in str(row["aspects"]).split("; "))
    if show_meta:
        for key in ("course", "instructor", "semester"):
            val = row.get(key)
            if val is not None and val == val and str(val):
                meta.append(f"<span>· {esc(str(val))}</span>")
        meta.append(f"<span>· #{int(row['record_id'])}</span>")
    _md(f'<div class="sq-review" style="border-left-color:{color}"><div class="txt">{highlight(shown, terms or [])}</div>'
        f'<div class="meta">{"".join(meta)}</div></div>')


def recommendation_card(rec: dict) -> None:
    color = COLORS["negative"] if rec["kind"] == "issue" else COLORS["positive"]
    badge = {"high": "High priority", "medium": "Worth attention", "keep": "Strength"}[rec["priority"]]
    examples = "".join(f'<div class="ev">“{esc(e["evidence"])}” <span style="font-style:normal">— review #{e["record_id"]}</span></div>'
                       for e in rec["examples"])
    caveats = " ".join(esc(c) for c in rec["caveats"])
    _md(f'<div class="sq-rec" style="border-left:3px solid {color}"><div class="head"><div class="title">{esc(rec["headline"])}</div>'
        f'<span class="sq-pill" style="background:{color}22;color:{color};border:1px solid {color}66">{badge}</span></div>'
        f'<div class="action"><b>Suggested action:</b> {esc(rec["action"])}</div>{examples}'
        f'<div class="cav">Evidence: {rec["supporting_reviews"]} of {rec["aspect_reviews"]} reviews mentioning '
        f'{esc(rec["aspect"])} ({rec["share"]:.0%}). {caveats}</div></div>')


def sidebar_brand() -> None:
    from src.config import ROOT

    st.logo(str(ROOT / "static" / "sentiq_wordmark.svg"), size="large", icon_image=str(ROOT / "static" / "sentiq_mark.svg"))


def footer() -> None:
    _md(f'<div class="sq-foot">{PRODUCT_NAME} — {esc(PRODUCT_DESCRIPTOR)} · Academic project: <i>{esc(ACADEMIC_TITLE)}</i>. '
        "Sentiment predictions come from a trained Logistic Regression model; aspect analysis is rule-assisted. "
        "Indicators summarise student opinion and are not objective measures of teaching quality.</div>")
