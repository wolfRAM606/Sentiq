"""Aspect-based feedback analysis (hybrid, lexicon-assisted)."""
import pandas as pd
import streamlit as st

from src.analytics.metrics import aspect_summary
from src.config import MIN_ASPECT_MENTIONS, TAXONOMY_PATH
from src.ui import charts
from src.ui import components as ui
from src.ui import state

ds = state.active()
analyzer = state.get_analyzer()
reviews, mentions = state.filtered(ds)
summary = aspect_summary(mentions, reviews, analyzer.taxonomy)
ambiguous = ds.result.ambiguous[ds.result.ambiguous["record_id"].isin(reviews["record_id"])]
unmatched = reviews[reviews["aspect_count"] == 0]

coverage = (reviews["aspect_count"] > 0).mean() if len(reviews) else 0
ui.hero("Aspect Analysis", "What exactly are students <em>talking about?</em>",
        "A transparent, lexicon-assisted aspect component: spaCy sentences, clauses and lemmas are matched against a "
        "configurable teaching-aspect taxonomy, and sentiment is predicted for the clause that triggered each match.",
        [("Rule-assisted · not a trained aspect model", ""), (state.filter_summary(ds, reviews), ""),
         (f"{len(analyzer.taxonomy.aspects)} aspects in taxonomy", "")],
        {"label": "Reviews with at least one aspect", "value": f"{coverage:.0%}",
         "note": f"{int((reviews['aspect_count'] > 0).sum())} of {len(reviews)} reviews · {len(unmatched)} unmatched · "
                 f"{ambiguous['record_id'].nunique()} with ambiguous terms"})

if reviews.empty:
    ui.empty("No reviews match the current filters", "Clear or widen the filters in the sidebar.")
    st.stop()

tab_sum, tab_drill, tab_unmatched, tab_tax = st.tabs(["Aspect summary", "Evidence drill-down", "Unmatched & ambiguous", "Taxonomy"])

with tab_sum:
    if summary.empty:
        ui.empty("No aspects detected", "None of the selected reviews matched the lexicon.")
    else:
        a, b = st.columns([1.5, 1], gap="large")
        with a:
            ui.section("Sentiment by aspect", "Clause-level sentiment share; the label shows the number of mentioning reviews.", "01")
            st.plotly_chart(charts.aspect_sentiment_bars(summary), width="stretch", config=charts.CONFIG)
        with b:
            ui.section("Discussion volume", "Reviews mentioning each aspect (one review can mention several).", "02")
            st.plotly_chart(charts.aspect_volume_bars(summary), width="stretch", config=charts.CONFIG)
        table = summary.copy()
        table["aspect_score"] = table.apply(lambda r: r["aspect_score"] if r["enough_evidence"] else None, axis=1)
        st.dataframe(table.drop(columns=["aspect_id", "enough_evidence"]), hide_index=True, width="stretch",
                     column_config={"coverage": st.column_config.NumberColumn("coverage", format="percent"),
                                    "positive_share": st.column_config.NumberColumn("positive %", format="percent"),
                                    "negative_share": st.column_config.NumberColumn("negative %", format="percent"),
                                    "aspect_score": st.column_config.NumberColumn("aspect indicator", format="%.0f",
                                                                                  help=f"100 × (pos + ½ neu share); blank when fewer than {MIN_ASPECT_MENTIONS} mentions"),
                                    "uncertain": st.column_config.NumberColumn("low-confidence", help="Mentions whose clause prediction was flagged review needed")})
        st.caption("No aspect-level accuracy is reported: the labelled training data has no aspect annotations, so this "
                   "component is exploratory. Percentages are always shown with their review counts.")

with tab_drill:
    if summary.empty:
        ui.empty("Nothing to drill into", "No aspect mentions in the current selection.")
    else:
        c1, c2 = st.columns([2, 1])
        asp = c1.selectbox("Aspect", summary["aspect"].tolist(), key="aa_aspect")
        sent = c2.multiselect("Clause sentiment", ["positive", "neutral", "negative"], key="aa_sent", placeholder="All")
        m = mentions[mentions["aspect"] == asp]
        if sent:
            m = m[m["aspect_sentiment"].isin(sent)]
        row = summary[summary["aspect"] == asp].iloc[0]
        k = st.columns(4)
        with k[0]:
            ui.kpi("Mentioning reviews", int(row["reviews"]), f"{row['coverage']:.0%} of selection", "ice")
        with k[1]:
            ui.kpi("Positive", int(row["positive"]), f"{row['positive_share']:.0%}", "pos")
        with k[2]:
            ui.kpi("Neutral", int(row["neutral"]), "", "neu")
        with k[3]:
            ui.kpi("Negative", int(row["negative"]), f"{row['negative_share']:.0%}", "neg")
        if not row["enough_evidence"]:
            st.warning(f"Fewer than {MIN_ASPECT_MENTIONS} reviews mention this aspect — too little evidence for conclusions.")
        st.markdown(f"**{len(m)} evidence clauses**")
        by_id = reviews.set_index("record_id")
        for r in m.sort_values("aspect_confidence", ascending=False).itertuples():
            base = by_id.loc[r.record_id]
            card = {"review_text": r.evidence if r.evidence else base["review_text"], "sentiment": r.aspect_sentiment,
                    "confidence": r.aspect_confidence, "review_needed": r.aspect_review_needed,
                    "aspects": "", "record_id": r.record_id, "course": base["course"], "instructor": base["instructor"],
                    "semester": base["semester"]}
            ui.review_card(card, [t.strip() for t in r.terms.split(",")])
            with st.expander(f"Full review #{r.record_id} · match: {r.match_type}{' · negated' if r.negated else ''}"):
                st.write(base["review_text"])
                st.caption(f"Whole-review prediction: {base['sentiment']} ({base['confidence']:.0%}). Aspect sentiment above is "
                           "predicted for the highlighted clause only.")

with tab_unmatched:
    u1, u2 = st.columns(2, gap="large")
    with u1:
        ui.section("Unmatched reviews", "No aspect term or general target was found. These are 'no aspect detected', not neutral.")
        if unmatched.empty:
            st.caption("Every review in the selection matched at least one aspect.")
        else:
            st.dataframe(unmatched[["record_id", "review_text", "sentiment"]], hide_index=True, width="stretch")
    with u2:
        ui.section("Ambiguous terms", "Words such as 'clear', 'fast' or 'fair' that only count with supporting context.")
        if ambiguous.empty:
            st.caption("No ambiguous candidate terms in the selection.")
        else:
            st.dataframe(ambiguous[["record_id", "term", "aspect_label", "sentence"]], hide_index=True, width="stretch")

with tab_tax:
    st.markdown(f"The taxonomy is loaded from `{TAXONOMY_PATH.relative_to(TAXONOMY_PATH.parent.parent)}`. Edit that JSON file "
                "to add synonyms, phrases or aspects; Sentiq reloads it automatically when the file changes.")
    st.dataframe(pd.DataFrame([{"aspect": a.label, "description": a.description, "terms": ", ".join(sorted(a.terms)),
                                "phrases": ", ".join(a.phrases), "context-dependent terms": ", ".join(a.ambiguous_terms)}
                               for a in analyzer.taxonomy.aspects]), hide_index=True, width="stretch")
    st.markdown("""
**How matching works**
1. spaCy splits each review into sentences, and each sentence into clauses at *but / however / although / though / whereas / yet / ;*.
2. Terms are matched on lemma or lowercase form; phrases with spaCy `PhraseMatcher` (lemma and lowercase).
3. Context-dependent terms (e.g. *clear*, *fast*, *fair*) count only when a context word appears in the same sentence; otherwise they are listed as ambiguous.
4. If nothing specific matches but the sentence evaluates the teacher/course in general, it is assigned to *Overall course experience* (match type "general").
5. The sentiment model is applied to the triggering clause, so *"clear lectures but confusing assignments"* yields different sentiment per aspect.
6. A negation flag is set when a negator governs or closely precedes the matched word (e.g. *not punctual*, *no knowledge*).
""")

ui.footer()
