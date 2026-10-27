"""Plotly charts in the Sentiq design system. Colours are read from the active theme at draw time."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.ui.theme import FONT_BODY, FONT_MONO, SENTIMENT_ORDER, palette, sentiment_colors

CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _layout(fig, height=320, title=None):
    p = palette()
    axis = dict(gridcolor=p["rule"], zerolinecolor=p["rule"], linecolor=p["rule"], tickfont=dict(color=p["muted"], family=FONT_MONO, size=11),
                title_font=dict(color=p["muted"], family=FONT_BODY, size=12))
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_BODY, color=p["text"], size=12),
        xaxis=axis, yaxis=axis, margin=dict(l=10, r=14, t=48, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(color=p["muted"], size=11), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=p["surface"], bordercolor=p["rule"], font=dict(color=p["text"], family=FONT_BODY)),
    )
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=13, color=p["muted"]), x=0, y=0.98), margin=dict(t=60))
    return fig


def sentiment_strip(counts: dict) -> go.Figure:
    """A single 100% bar: the share of each sentiment, labelled in place."""
    sc = sentiment_colors()
    total = sum(counts.get(s, 0) for s in SENTIMENT_ORDER) or 1
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        v = counts.get(s, 0)
        fig.add_bar(y=[""], x=[v / total], orientation="h", name=s.capitalize(), marker_color=sc[s], marker_line_width=0,
                    text=[f"{v / total:.0%}" if v / total >= 0.06 else ""], textposition="inside", insidetextanchor="start",
                    textfont=dict(color=palette()["bg"], family=FONT_MONO, size=12), customdata=[[v]],
                    hovertemplate=s.capitalize() + ": %{customdata[0]} reviews (%{x:.0%})<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0, xaxis=dict(range=[0, 1], tickformat=".0%", showgrid=False), yaxis=dict(showticklabels=False))
    return _layout(fig, 150)


sentiment_donut = sentiment_strip  # kept for callers written against the earlier chart name


def aspect_sentiment_bars(summary: pd.DataFrame, height: int | None = None) -> go.Figure:
    sc = sentiment_colors()
    df = summary.sort_values("reviews", ascending=True)
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        share = df[s] / df["reviews"]
        fig.add_bar(y=df["aspect"], x=share, name=s.capitalize(), orientation="h", marker_color=sc[s], marker_line_width=0,
                    customdata=np.stack([df[s], df["reviews"]], axis=1),
                    hovertemplate="%{y}<br>" + s.capitalize() + ": %{customdata[0]} of %{customdata[1]} reviews (%{x:.0%})<extra></extra>")
    fig.update_layout(barmode="stack", xaxis=dict(tickformat=".0%", range=[0, 1], title="Share of mentioning reviews"),
                      yaxis=dict(ticktext=[f"{a}  (n={n})" for a, n in zip(df["aspect"], df["reviews"])], tickvals=list(df["aspect"])),
                      bargap=0.45)
    return _layout(fig, height or max(260, 34 * len(df) + 80))


def aspect_volume_bars(summary: pd.DataFrame) -> go.Figure:
    p = palette()
    df = summary.sort_values("reviews", ascending=True)
    fig = go.Figure(go.Bar(y=df["aspect"], x=df["reviews"], orientation="h", marker_color=p["sage"], marker_line_width=0,
                           text=df["reviews"], textposition="outside", textfont=dict(color=p["muted"], family=FONT_MONO),
                           hovertemplate="%{y}: %{x} reviews<extra></extra>"))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(xaxis=dict(title="Reviews mentioning aspect", range=[0, max(df["reviews"].max(), 1) * 1.18]), bargap=0.5)
    return _layout(fig, max(260, 30 * len(df) + 70))


def keyword_bars(table: pd.DataFrame, top: int = 15, term_col: str = "term") -> go.Figure:
    sc = sentiment_colors()
    df = table.head(top).iloc[::-1]
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        fig.add_bar(y=df[term_col], x=df[s], name=s.capitalize(), orientation="h", marker_color=sc[s], marker_line_width=0,
                    hovertemplate="%{y}<br>" + s.capitalize() + ": %{x} reviews<extra></extra>")
    fig.update_layout(barmode="stack", xaxis_title="Reviews containing term", bargap=0.4)
    return _layout(fig, max(280, 26 * len(df) + 90))


def topic_bars(topics: list[dict], sentiment_by_topic: pd.DataFrame) -> go.Figure:
    sc = sentiment_colors()
    labels = [t["label"] for t in topics][::-1]
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        vals = [int(sentiment_by_topic.loc[t["topic_id"], s]) if t["topic_id"] in sentiment_by_topic.index and s in sentiment_by_topic else 0
                for t in topics][::-1]
        fig.add_bar(y=labels, x=vals, name=s.capitalize(), orientation="h", marker_color=sc[s], marker_line_width=0,
                    hovertemplate="%{y}<br>" + s.capitalize() + ": %{x} reviews<extra></extra>")
    fig.update_layout(barmode="stack", xaxis_title="Reviews assigned (dominant topic)", bargap=0.45)
    return _layout(fig, max(240, 48 * len(topics) + 80))


def topic_terms_chart(topic: dict) -> go.Figure:
    p = palette()
    terms, w = topic["terms"][::-1], topic["weights"][::-1]
    fig = go.Figure(go.Bar(y=terms, x=w, orientation="h", marker_color=p["brand"], marker_line_width=0,
                           hovertemplate="%{y}: weight %{x:.3f}<extra></extra>"))
    fig.update_layout(xaxis_title="NMF term weight", bargap=0.4)
    return _layout(fig, 260)


def trend_chart(reviews: pd.DataFrame) -> go.Figure | None:
    sc = sentiment_colors()
    dated = reviews.dropna(subset=["date"])
    if len(dated) < 5:
        return None
    span_days = (dated["date"].max() - dated["date"].min()).days
    freq = "W" if span_days <= 120 else "MS"
    g = dated.groupby([pd.Grouper(key="date", freq=freq), "sentiment"]).size().unstack(fill_value=0)
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        if s in g:
            fig.add_bar(x=g.index, y=g[s], name=s.capitalize(), marker_color=sc[s], marker_line_width=0,
                        hovertemplate="%{x|%b %Y}<br>" + s.capitalize() + ": %{y}<extra></extra>")
    fig.update_layout(barmode="stack", yaxis_title="Reviews", bargap=0.3)
    return _layout(fig, 280)


def probability_bars(probs: dict) -> go.Figure:
    p, sc = palette(), sentiment_colors()
    vals = [probs.get(s, 0.0) for s in SENTIMENT_ORDER]
    fig = go.Figure(go.Bar(x=vals, y=[s.capitalize() for s in SENTIMENT_ORDER], orientation="h", marker_line_width=0,
                           marker_color=[sc[s] for s in SENTIMENT_ORDER], text=[f"{v:.0%}" for v in vals],
                           textposition="outside", textfont=dict(color=p["muted"], family=FONT_MONO),
                           hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(xaxis=dict(range=[0, 1.15], tickformat=".0%"), bargap=0.45)
    return _layout(fig, 180)


def model_comparison(models: dict) -> go.Figure:
    p = palette()
    names = [m["display_name"] for m in models.values()]
    fig = go.Figure()
    fig.add_bar(x=names, y=[m["cv_macro_f1_mean"] for m in models.values()], name="CV macro-F1 (train folds)", marker_color=p["sage"],
                marker_line_width=0, error_y=dict(type="data", array=[m["cv_macro_f1_std"] for m in models.values()], color=p["muted"]),
                hovertemplate="%{x}<br>CV macro-F1: %{y:.3f}<extra></extra>")
    fig.add_bar(x=names, y=[m["test"]["macro_f1"] for m in models.values()], name="Held-out test macro-F1", marker_color=p["brand"],
                marker_line_width=0, hovertemplate="%{x}<br>Test macro-F1: %{y:.3f}<extra></extra>")
    fig.add_bar(x=names, y=[m["test"]["accuracy"] for m in models.values()], name="Held-out test accuracy", marker_color=p["surface_2"],
                marker_line=dict(color=p["muted"], width=1), hovertemplate="%{x}<br>Test accuracy: %{y:.3f}<extra></extra>")
    fig.update_layout(barmode="group", yaxis=dict(range=[0, 1], title="Score"), bargap=0.3)
    return _layout(fig, 340)


def confusion_heatmap(cm: list, labels: list[str]) -> go.Figure:
    p = palette()
    cm = np.asarray(cm)
    row_tot = cm.sum(axis=1, keepdims=True)
    pct = np.divide(cm, row_tot, out=np.zeros_like(cm, dtype=float), where=row_tot > 0)
    text = [[f"<b>{cm[i, j]}</b><br>{pct[i, j]:.0%}" for j in range(len(labels))] for i in range(len(labels))]
    fig = go.Figure(go.Heatmap(z=pct, x=[l.capitalize() for l in labels], y=[l.capitalize() for l in labels],
                               text=text, texttemplate="%{text}", textfont=dict(size=14, family=FONT_MONO),
                               colorscale=[[0, p["surface"]], [1, p["brand"]]], showscale=False, zmin=0, zmax=1, xgap=2, ygap=2,
                               hovertemplate="True %{y}, predicted %{x}<br>%{z:.0%} of true %{y}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Predicted", showgrid=False), yaxis=dict(title="True", autorange="reversed", showgrid=False))
    return _layout(fig, 340)


def per_class_bars(per_class: dict) -> go.Figure:
    p = palette()
    labs = [l for l in SENTIMENT_ORDER if l in per_class]
    fig = go.Figure()
    for metric, color in (("precision", p["sage"]), ("recall", p["brand"]), ("f1", p["neutral"])):
        fig.add_bar(x=[l.capitalize() for l in labs], y=[per_class[l][metric] for l in labs], marker_line_width=0,
                    name=metric.capitalize() if metric != "f1" else "F1", marker_color=color,
                    hovertemplate="%{x} " + metric + ": %{y:.3f}<extra></extra>")
    fig.update_layout(barmode="group", yaxis=dict(range=[0, 1]), bargap=0.35)
    return _layout(fig, 320)


def class_distribution(counts: dict, title: str | None = None) -> go.Figure:
    p, sc = palette(), sentiment_colors()
    labs = [l for l in SENTIMENT_ORDER if l in counts]
    fig = go.Figure(go.Bar(x=[l.capitalize() for l in labs], y=[counts[l] for l in labs], marker_line_width=0,
                           marker_color=[sc[l] for l in labs], text=[counts[l] for l in labs],
                           textposition="outside", textfont=dict(color=p["muted"], family=FONT_MONO),
                           hovertemplate="%{x}: %{y}<extra></extra>"))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(yaxis=dict(title="Examples", range=[0, max(counts.values() or [1]) * 1.15]), bargap=0.5)
    return _layout(fig, 280, title)


def reliability_chart(bins: list[dict]) -> go.Figure:
    p = palette()
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=p["rule"], dash="dot"), name="Perfect calibration", hoverinfo="skip")
    fig.add_scatter(x=[b["confidence"] for b in bins], y=[b["accuracy"] for b in bins], mode="lines+markers",
                    marker=dict(size=[6 + min(b["count"], 60) / 3 for b in bins], color=p["brand"], symbol="square"),
                    line=dict(color=p["brand"]), name="Logistic Regression", customdata=[b["count"] for b in bins],
                    hovertemplate="Mean confidence %{x:.2f}<br>Accuracy %{y:.2f}<br>%{customdata} test reviews<extra></extra>")
    fig.update_layout(xaxis=dict(range=[0, 1], title="Predicted top-class probability"), yaxis=dict(range=[0, 1], title="Observed accuracy"))
    return _layout(fig, 320)


def rating_sentiment_heatmap(reviews: pd.DataFrame) -> go.Figure | None:
    p = palette()
    df = reviews.dropna(subset=["rating"])
    if len(df) < 5:
        return None
    ct = pd.crosstab(df["rating"], df["sentiment"]).reindex(columns=SENTIMENT_ORDER, fill_value=0)
    fig = go.Figure(go.Heatmap(z=ct.values, x=[c.capitalize() for c in ct.columns], y=[f"{r:g}" for r in ct.index],
                               colorscale=[[0, p["surface"]], [1, p["sage"]]], showscale=False, xgap=2, ygap=2,
                               text=ct.values, texttemplate="%{text}",
                               hovertemplate="Rating %{y}, predicted %{x}: %{z} reviews<extra></extra>"))
    fig.update_layout(xaxis_title="Predicted sentiment", yaxis_title="Submitted rating")
    return _layout(fig, 280)


def score_gauge(score: float | None, title: str = "") -> go.Figure:
    """Linear 0-100 scale with the indicator marked; bands at 40 and 60 for orientation."""
    p = palette()
    v = score if score is not None else 0
    fig = go.Figure()
    for lo, hi, col in ((0, 40, p["negative"]), (40, 60, p["neutral"]), (60, 100, p["positive"])):
        fig.add_bar(y=[""], x=[hi - lo], base=lo, orientation="h", marker_color=col, opacity=0.25, marker_line_width=0,
                    hoverinfo="skip", showlegend=False)
    fig.add_bar(y=[""], x=[v], orientation="h", marker_color=p["brand"], width=0.28, marker_line_width=0, showlegend=False,
                hovertemplate="Indicator %{x:.1f} / 100<extra></extra>")
    fig.add_annotation(x=v, y=0.55, yref="paper", text=f"<b>{v:.1f}</b>", showarrow=False, yanchor="bottom",
                       font=dict(family="Fraunces, Georgia, serif", size=30, color=p["brand"]))
    fig.update_layout(barmode="overlay", xaxis=dict(range=[0, 100], dtick=20, showgrid=False), yaxis=dict(showticklabels=False))
    return _layout(fig, 190, title)
