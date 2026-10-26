"""Plotly charts with Sentiq's consistent colour semantics."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from src.ui.theme import COLORS, FONT_BODY, SENTIMENT_COLORS, SENTIMENT_ORDER

pio.templates["sentiq"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_BODY, color=COLORS["text"], size=12),
        colorway=[COLORS["violet"], COLORS["ice"], COLORS["lime"], COLORS["positive"], COLORS["neutral"], COLORS["negative"]],
        xaxis=dict(gridcolor="rgba(48,50,71,0.6)", zerolinecolor=COLORS["border"], linecolor=COLORS["border"],
                   tickfont=dict(color=COLORS["muted"]), title_font=dict(color=COLORS["muted"])),
        yaxis=dict(gridcolor="rgba(48,50,71,0.6)", zerolinecolor=COLORS["border"], linecolor=COLORS["border"],
                   tickfont=dict(color=COLORS["muted"]), title_font=dict(color=COLORS["muted"])),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(color=COLORS["muted"]), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=COLORS["panel"], bordercolor=COLORS["border"], font=dict(color=COLORS["text"], family=FONT_BODY)),
        margin=dict(l=10, r=10, t=48, b=10),
    )
)
TEMPLATE = "sentiq"
CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _layout(fig, height=320, title=None):
    fig.update_layout(template=TEMPLATE, height=height)
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=13, color=COLORS["muted"]), x=0, y=0.98),
                          margin=dict(t=60))
    return fig


def sentiment_donut(counts: dict, center_label: str = "reviews") -> go.Figure:
    labels = [s for s in SENTIMENT_ORDER if counts.get(s, 0) > 0] or SENTIMENT_ORDER
    values = [counts.get(s, 0) for s in labels]
    fig = go.Figure(go.Pie(labels=[s.capitalize() for s in labels], values=values, hole=0.68, sort=False,
                           marker=dict(colors=[SENTIMENT_COLORS[s] for s in labels], line=dict(color=COLORS["bg"], width=3)),
                           textinfo="percent", textfont=dict(color=COLORS["bg"], size=12),
                           hovertemplate="%{label}: %{value} reviews (%{percent})<extra></extra>"))
    total = sum(values)
    fig.add_annotation(text=f"<b>{total}</b><br><span style='font-size:11px;color:{COLORS['muted']}'>{center_label}</span>",
                       showarrow=False, font=dict(size=24, color=COLORS["text"]))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"))
    return _layout(fig, 300)


def aspect_sentiment_bars(summary: pd.DataFrame, height: int | None = None) -> go.Figure:
    df = summary.sort_values("reviews", ascending=True)
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        share = df[s] / df["reviews"]
        fig.add_bar(y=df["aspect"], x=share, name=s.capitalize(), orientation="h", marker_color=SENTIMENT_COLORS[s],
                    customdata=np.stack([df[s], df["reviews"]], axis=1),
                    hovertemplate="%{y}<br>" + s.capitalize() + ": %{customdata[0]} of %{customdata[1]} reviews (%{x:.0%})<extra></extra>")
    fig.update_layout(barmode="stack", xaxis=dict(tickformat=".0%", range=[0, 1], title="Share of mentioning reviews"),
                      yaxis=dict(ticksuffix="  ", ticktext=[f"{a}  (n={n})" for a, n in zip(df["aspect"], df["reviews"])],
                                 tickvals=list(df["aspect"])), bargap=0.35)
    return _layout(fig, height or max(260, 34 * len(df) + 80))


def aspect_volume_bars(summary: pd.DataFrame) -> go.Figure:
    df = summary.sort_values("reviews", ascending=True)
    fig = go.Figure(go.Bar(y=df["aspect"], x=df["reviews"], orientation="h", marker_color=COLORS["ice"],
                           text=df["reviews"], textposition="outside", textfont=dict(color=COLORS["muted"]),
                           hovertemplate="%{y}: %{x} reviews<extra></extra>"))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(xaxis=dict(title="Reviews mentioning aspect", range=[0, max(df["reviews"].max(), 1) * 1.18]), bargap=0.4)
    return _layout(fig, max(260, 30 * len(df) + 70))


def keyword_bars(table: pd.DataFrame, top: int = 15, term_col: str = "term") -> go.Figure:
    df = table.head(top).iloc[::-1]
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        fig.add_bar(y=df[term_col], x=df[s], name=s.capitalize(), orientation="h", marker_color=SENTIMENT_COLORS[s],
                    hovertemplate="%{y}<br>" + s.capitalize() + ": %{x} reviews<extra></extra>")
    fig.update_layout(barmode="stack", xaxis_title="Reviews containing term", bargap=0.3)
    return _layout(fig, max(280, 26 * len(df) + 90))


def topic_bars(topics: list[dict], sentiment_by_topic: pd.DataFrame) -> go.Figure:
    labels = [t["label"] for t in topics][::-1]
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        vals = [int(sentiment_by_topic.loc[t["topic_id"], s]) if t["topic_id"] in sentiment_by_topic.index and s in sentiment_by_topic else 0
                for t in topics][::-1]
        fig.add_bar(y=labels, x=vals, name=s.capitalize(), orientation="h", marker_color=SENTIMENT_COLORS[s],
                    hovertemplate="%{y}<br>" + s.capitalize() + ": %{x} reviews<extra></extra>")
    fig.update_layout(barmode="stack", xaxis_title="Reviews assigned (dominant topic)", bargap=0.35)
    return _layout(fig, max(240, 48 * len(topics) + 80))


def topic_terms_chart(topic: dict) -> go.Figure:
    terms, w = topic["terms"][::-1], topic["weights"][::-1]
    fig = go.Figure(go.Bar(y=terms, x=w, orientation="h", marker_color=COLORS["violet"],
                           hovertemplate="%{y}: weight %{x:.3f}<extra></extra>"))
    fig.update_layout(xaxis_title="NMF term weight", bargap=0.3)
    return _layout(fig, 260)


def trend_chart(reviews: pd.DataFrame) -> go.Figure | None:
    dated = reviews.dropna(subset=["date"])
    if len(dated) < 5:
        return None
    span_days = (dated["date"].max() - dated["date"].min()).days
    freq = "W" if span_days <= 120 else "MS"
    g = (dated.groupby([pd.Grouper(key="date", freq=freq), "sentiment"]).size().unstack(fill_value=0))
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        if s in g:
            fig.add_bar(x=g.index, y=g[s], name=s.capitalize(), marker_color=SENTIMENT_COLORS[s],
                        hovertemplate="%{x|%b %Y}<br>" + s.capitalize() + ": %{y}<extra></extra>")
    fig.update_layout(barmode="stack", yaxis_title="Reviews", bargap=0.25)
    return _layout(fig, 280)


def probability_bars(probs: dict) -> go.Figure:
    labs = [s for s in SENTIMENT_ORDER]
    vals = [probs.get(s, 0.0) for s in labs]
    fig = go.Figure(go.Bar(x=vals, y=[s.capitalize() for s in labs], orientation="h",
                           marker_color=[SENTIMENT_COLORS[s] for s in labs], text=[f"{v:.0%}" for v in vals],
                           textposition="outside", textfont=dict(color=COLORS["muted"]),
                           hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(xaxis=dict(range=[0, 1.15], tickformat=".0%"), bargap=0.35)
    return _layout(fig, 180)


def model_comparison(models: dict) -> go.Figure:
    names = [m["display_name"] for m in models.values()]
    fig = go.Figure()
    fig.add_bar(x=names, y=[m["cv_macro_f1_mean"] for m in models.values()], name="CV macro-F1 (train folds)",
                marker_color=COLORS["ice"],
                error_y=dict(type="data", array=[m["cv_macro_f1_std"] for m in models.values()], color=COLORS["muted"]),
                hovertemplate="%{x}<br>CV macro-F1: %{y:.3f}<extra></extra>")
    fig.add_bar(x=names, y=[m["test"]["macro_f1"] for m in models.values()], name="Held-out test macro-F1",
                marker_color=COLORS["violet"], hovertemplate="%{x}<br>Test macro-F1: %{y:.3f}<extra></extra>")
    fig.add_bar(x=names, y=[m["test"]["accuracy"] for m in models.values()], name="Held-out test accuracy",
                marker_color="rgba(167,139,250,0.35)", hovertemplate="%{x}<br>Test accuracy: %{y:.3f}<extra></extra>")
    fig.update_layout(barmode="group", yaxis=dict(range=[0, 1], title="Score"), bargap=0.25)
    return _layout(fig, 340)


def confusion_heatmap(cm: list, labels: list[str]) -> go.Figure:
    cm = np.asarray(cm)
    row_tot = cm.sum(axis=1, keepdims=True)
    pct = np.divide(cm, row_tot, out=np.zeros_like(cm, dtype=float), where=row_tot > 0)
    text = [[f"<b>{cm[i, j]}</b><br>{pct[i, j]:.0%}" for j in range(len(labels))] for i in range(len(labels))]
    fig = go.Figure(go.Heatmap(z=pct, x=[l.capitalize() for l in labels], y=[l.capitalize() for l in labels],
                               text=text, texttemplate="%{text}", textfont=dict(size=14, color=COLORS["text"]),
                               colorscale=[[0, COLORS["panel"]], [0.5, "#5B4BB0"], [1, COLORS["violet"]]],
                               showscale=False, zmin=0, zmax=1, xgap=3, ygap=3,
                               hovertemplate="True %{y} → predicted %{x}<br>%{z:.0%} of true %{y}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Predicted", side="bottom", showgrid=False), yaxis=dict(title="True", autorange="reversed", showgrid=False))
    return _layout(fig, 340)


def per_class_bars(per_class: dict) -> go.Figure:
    labs = [l for l in SENTIMENT_ORDER if l in per_class]
    fig = go.Figure()
    for metric, color in (("precision", COLORS["ice"]), ("recall", COLORS["violet"]), ("f1", COLORS["lime"])):
        fig.add_bar(x=[l.capitalize() for l in labs], y=[per_class[l][metric] for l in labs], name=metric.capitalize() if metric != "f1" else "F1",
                    marker_color=color, hovertemplate="%{x} " + metric + ": %{y:.3f}<extra></extra>")
    fig.update_layout(barmode="group", yaxis=dict(range=[0, 1]), bargap=0.3)
    return _layout(fig, 320)


def class_distribution(counts: dict, title: str | None = None) -> go.Figure:
    labs = [l for l in SENTIMENT_ORDER if l in counts]
    fig = go.Figure(go.Bar(x=[l.capitalize() for l in labs], y=[counts[l] for l in labs],
                           marker_color=[SENTIMENT_COLORS[l] for l in labs], text=[counts[l] for l in labs],
                           textposition="outside", textfont=dict(color=COLORS["muted"]),
                           hovertemplate="%{x}: %{y}<extra></extra>"))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(yaxis=dict(title="Examples", range=[0, max(counts.values() or [1]) * 1.15]), bargap=0.45)
    return _layout(fig, 280, title)


def reliability_chart(bins: list[dict]) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=COLORS["border"], dash="dot"), name="Perfect calibration",
                    hoverinfo="skip")
    fig.add_scatter(x=[b["confidence"] for b in bins], y=[b["accuracy"] for b in bins], mode="lines+markers",
                    marker=dict(size=[6 + min(b["count"], 60) / 3 for b in bins], color=COLORS["lime"]),
                    line=dict(color=COLORS["lime"]), name="Logistic Regression",
                    customdata=[b["count"] for b in bins],
                    hovertemplate="Mean confidence %{x:.2f}<br>Accuracy %{y:.2f}<br>%{customdata} test reviews<extra></extra>")
    fig.update_layout(xaxis=dict(range=[0, 1], title="Predicted top-class probability"), yaxis=dict(range=[0, 1], title="Observed accuracy"))
    return _layout(fig, 320)


def rating_sentiment_heatmap(reviews: pd.DataFrame) -> go.Figure | None:
    df = reviews.dropna(subset=["rating"])
    if len(df) < 5:
        return None
    ct = pd.crosstab(df["rating"], df["sentiment"]).reindex(columns=SENTIMENT_ORDER, fill_value=0)
    fig = go.Figure(go.Heatmap(z=ct.values, x=[c.capitalize() for c in ct.columns], y=[f"{r:g}" for r in ct.index],
                               colorscale=[[0, COLORS["panel"]], [1, COLORS["ice"]]], showscale=False, xgap=3, ygap=3,
                               text=ct.values, texttemplate="%{text}",
                               hovertemplate="Rating %{y}, predicted %{x}: %{z} reviews<extra></extra>"))
    fig.update_layout(xaxis_title="Predicted sentiment", yaxis_title="Submitted rating")
    return _layout(fig, 280)


def score_gauge(score: float | None, title: str = "") -> go.Figure:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=score if score is not None else 0,
                                 number=dict(suffix=" / 100", font=dict(color=COLORS["lime"], size=34), valueformat=".1f"),
                                 gauge=dict(axis=dict(range=[0, 100], tickcolor=COLORS["muted"]),
                                            bar=dict(color=COLORS["lime"], thickness=0.28),
                                            bgcolor=COLORS["panel"], borderwidth=0,
                                            steps=[dict(range=[0, 40], color="rgba(251,113,133,0.18)"),
                                                   dict(range=[40, 60], color="rgba(251,191,36,0.14)"),
                                                   dict(range=[60, 100], color="rgba(110,231,183,0.14)")])))
    return _layout(fig, 240, title)
