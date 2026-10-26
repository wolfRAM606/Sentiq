"""Teaching effectiveness insights: an explainable, sentiment-derived indicator and recommendations."""
import pandas as pd
import streamlit as st

from src.analytics.metrics import aspect_summary, effectiveness_indicator, overview_kpis, sentiment_counts
from src.analytics.recommendations import build_recommendations
from src.config import MIN_ASPECT_MENTIONS, MIN_SAMPLE_WARNING
from src.ui import charts
from src.ui import components as ui
from src.ui import state

GROUP_MIN = 15  # groups with fewer reviews get no indicator

ds = state.active()
analyzer = state.get_analyzer()
reviews, mentions = state.filtered(ds)
kpis = overview_kpis(reviews, ds.report.excluded_records)
summary = aspect_summary(mentions, reviews, analyzer.taxonomy)
score = kpis["effectiveness"]

ui.hero("Effectiveness Insights", "From opinions to <em>actionable</em> evidence.",
        "A transparent, sentiment-derived feedback indicator with aspect-level breakdowns and deterministic "
        "recommendations — each linked to the reviews that triggered it.",
        [(state.filter_summary(ds, reviews), ""), ("Indicator ≠ objective teaching quality", "demo")],
        {"label": "Feedback indicator", "value": f"{score:.1f}" if score is not None else "—", "suffix": "/ 100",
         "note": f"Based on {kpis['valid_reviews']} reviews' predicted sentiment."})

if reviews.empty:
    ui.empty("No reviews match the current filters", "Clear or widen the filters in the sidebar.")
    st.stop()

a, b = st.columns([1, 1.3], gap="large")
with a:
    st.plotly_chart(charts.score_gauge(score), width="stretch", config=charts.CONFIG)
with b:
    ui.section("How the indicator is calculated", "")
    st.latex(r"\text{Indicator} = 100 \times \left(p_{\text{positive}} + 0.5 \times p_{\text{neutral}}\right)"
             r"= 50\,p_{\text{positive}} + 50\,(1 - p_{\text{negative}})")
    c = kpis["counts"]
    n = kpis["valid_reviews"]
    st.markdown(f"With **{c['positive']}** positive, **{c['neutral']}** neutral and **{c['negative']}** negative predictions out of "
                f"**{n}** reviews: 100 × ({c['positive']}/{n} + 0.5 × {c['neutral']}/{n}) = **{score:.1f}**.")
    st.caption("Proportions use predicted (not human-labelled) sentiment. A neutral review counts half. 50 means positive and "
               "negative feedback balance out.")
if n < MIN_SAMPLE_WARNING:
    st.warning(f"Minimum-sample warning: only {n} reviews are in the selection (recommended ≥ {MIN_SAMPLE_WARNING}). "
               "The indicator can change substantially with a few additional reviews.")
st.info("**Interpret with care.** Student feedback may be biased, incomplete or unrepresentative (e.g. only motivated students "
        "respond), and the sentiment model makes errors (see Model Lab). This indicator summarises expressed opinion; it is "
        "not an objective measurement of instructor quality and must not be used on its own for evaluation decisions.",
        icon=":material/balance:")

ui.section("Aspect-level indicators", f"Shown only for aspects with at least {MIN_ASPECT_MENTIONS} mentioning reviews.", "01")
eligible = summary[summary["enough_evidence"]] if len(summary) else summary
if eligible.empty:
    ui.empty("Not enough aspect evidence", f"No aspect has {MIN_ASPECT_MENTIONS}+ mentions in this selection.")
else:
    tbl = eligible[["aspect", "reviews", "positive", "neutral", "negative", "aspect_score", "uncertain"]].copy()
    st.dataframe(tbl, hide_index=True, width="stretch",
                 column_config={"aspect_score": st.column_config.ProgressColumn("aspect indicator", min_value=0, max_value=100, format="%.0f"),
                                "uncertain": st.column_config.NumberColumn("low-confidence mentions")})
    pick = st.selectbox("Inspect the reviews contributing to an aspect", eligible["aspect"].tolist(), key="ei_aspect")
    contrib = mentions[mentions["aspect"] == pick].merge(reviews[["record_id", "review_text"]], on="record_id")
    st.dataframe(contrib[["record_id", "aspect_sentiment", "aspect_confidence", "evidence", "review_text"]], hide_index=True,
                 width="stretch", column_config={"aspect_confidence": st.column_config.NumberColumn("confidence", format="%.2f")})

ui.section("Breakdown by group", f"Indicators are withheld for groups with fewer than {GROUP_MIN} reviews. Groups are listed "
           "alphabetically, not ranked.", "02")
group_cols = [c for c in ("course", "instructor", "semester") if reviews[c].notna().any()]
if not group_cols:
    st.caption("The dataset has no course, instructor or semester column.")
else:
    gcol = st.radio("Group by", group_cols, horizontal=True, key="ei_group")
    rows = []
    for g, sub in reviews.groupby(gcol):
        sc = sentiment_counts(sub)
        rows.append({gcol: g, "reviews": len(sub), **sc,
                     "indicator": effectiveness_indicator(sc["positive"], sc["neutral"], sc["negative"]) if len(sub) >= GROUP_MIN else None,
                     "evidence": "sufficient" if len(sub) >= GROUP_MIN else "insufficient sample"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={"indicator": st.column_config.NumberColumn("indicator", format="%.1f")})
    st.caption("Differences between groups are descriptive. They do not show that one course or instructor causes higher "
               "satisfaction, and groups may differ in who responded.")

ui.section("Evidence-linked recommendations", "Generated by transparent rules: an issue needs ≥3 negative mentions and ≥35% "
           "negative share; a strength needs ≥3 positive mentions and ≥60% positive share.", "03")
recs = build_recommendations(summary, mentions, reviews, analyzer.taxonomy)
kind = st.radio("Show", ["All", "Issues", "Strengths"], horizontal=True, key="ei_kind")
shown = [r for r in recs if kind == "All" or (kind == "Issues") == (r["kind"] == "issue")]
if not shown:
    ui.empty("No recommendation meets the evidence thresholds", "Sentiq does not generate recommendations the data does not support.")
for rec in shown:
    ui.recommendation_card(rec)

ui.footer()
