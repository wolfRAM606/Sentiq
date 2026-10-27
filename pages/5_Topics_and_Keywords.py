"""Keywords, noun phrases and exploratory topic discovery."""
import streamlit as st

from src.config import MIN_TOPIC_REVIEWS
from src.nlp.keywords import keyword_table, noun_phrase_table, reviews_with_term
from src.ui import charts
from src.ui import components as ui
from src.ui import state

ds = state.active()
reviews, mentions = state.filtered(ds)

ui.hero("Topics & Keywords", "The <em>vocabulary</em> of student feedback.",
        "Lemmatised keywords and noun phrases from spaCy, split by predicted sentiment, plus exploratory NMF topic "
        "discovery. Everything is computed from the active dataset and filter selection.",
        [("Synthetic demonstration data" if ds.kind == "demo" else ds.name, "demo" if ds.kind == "demo" else "live"),
         (state.filter_summary(ds, reviews), "")])

if reviews.empty:
    ui.empty("No reviews match the current filters", "Clear or widen the filters in the sidebar.")
    st.stop()

tab_kw, tab_np, tab_topics = st.tabs(["Keywords", "Noun phrases", "Topic discovery"])

with tab_kw:
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
    gram = c1.radio("Term type", ["Unigrams", "Bigrams"], horizontal=True, key="tk_gram")
    n = 1 if gram == "Unigrams" else 2
    min_rev = c2.number_input("Min. reviews", 1, 50, 2, key="tk_min")
    top = c3.slider("Show top", 5, 40, 15, key="tk_top")
    hide = c4.toggle("Hide generic words (teacher, class, course…)", value=True, key="tk_hide")
    kw = keyword_table(reviews, n, hide_domain_words=hide, min_reviews=int(min_rev))
    if kw.empty:
        ui.empty("No recurring terms", "Lower the minimum review count or widen the filters.")
    else:
        a, b = st.columns([1.3, 1], gap="large")
        with a:
            ui.section("Most frequent terms", "Number of reviews containing each lemma n-gram, coloured by predicted sentiment.", "01")
            st.plotly_chart(charts.keyword_bars(kw, top), width="stretch", config=charts.CONFIG)
        with b:
            ui.section("Positive vs negative phrases", "Terms ranked by net sentiment (positive − negative reviews) / reviews.", "02")
            eligible = kw[kw["reviews"] >= max(2, int(min_rev))]
            pos = eligible[eligible["positive"] > 0].sort_values(["net_sentiment", "reviews"], ascending=[False, False]).head(8)
            neg = eligible[eligible["negative"] > 0].sort_values(["net_sentiment", "reviews"], ascending=[True, False]).head(8)
            st.markdown("**Leaning positive**")
            st.dataframe(pos[["term", "reviews", "positive", "negative"]], hide_index=True, width="stretch")
            st.markdown("**Leaning negative**")
            st.dataframe(neg[["term", "reviews", "positive", "negative"]], hide_index=True, width="stretch")
        ui.section("Representative reviews for a term", "", "03")
        term = st.selectbox("Term", kw["term"].head(60).tolist(), key="tk_term")
        sample = reviews_with_term(reviews, term, n)
        st.caption(f"{len(sample)} reviews contain “{term}”. Showing up to 8.")
        for _, row in sample.head(8).iterrows():
            ui.review_card(row, term.split())

with tab_np:
    ui.section("Noun phrases", "spaCy noun chunks (lemmatised, determiners and pronouns removed) appearing in ≥2 reviews.")
    npt = noun_phrase_table(reviews)
    if npt.empty:
        ui.empty("No recurring noun phrases", "Noun phrases must appear in at least two reviews.")
    else:
        st.plotly_chart(charts.keyword_bars(npt, 15, term_col="phrase"), width="stretch", config=charts.CONFIG)
        st.dataframe(npt, hide_index=True, width="stretch", height=300)

with tab_topics:
    st.markdown("Topics are discovered with **TF-IDF + Non-negative Matrix Factorisation** (scikit-learn) on spaCy content lemmas. "
                "Labels are generated from the top terms and are **not human-verified categories**.")
    k = st.slider("Number of topics", 2, 8, 4, key="tk_k")
    result = state.topics_for(ds, reviews, k)
    if not result.ok:
        ui.empty("Topic discovery is not available for this selection", result.message +
                 f" (minimum {MIN_TOPIC_REVIEWS} reviews with a diverse vocabulary).")
    else:
        st.success(result.message)
        assigned = reviews.assign(topic=result.assignments, strength=result.strengths)
        sent_by_topic = assigned.groupby("topic")["sentiment"].value_counts().unstack(fill_value=0)
        st.plotly_chart(charts.topic_bars(result.topics, sent_by_topic), width="stretch", config=charts.CONFIG)
        unassigned = int((assigned["topic"] == -1).sum())
        if unassigned:
            st.caption(f"{unassigned} reviews had no informative terms in the topic vocabulary and are unassigned.")
        for t in result.topics:
            with st.expander(f"{t['label']} ({t['n_reviews']} reviews)"):
                a, b = st.columns([1, 1.4], gap="large")
                with a:
                    st.plotly_chart(charts.topic_terms_chart(t), width="stretch", config=charts.CONFIG, key=f"topic_terms_{t['topic_id']}")
                with b:
                    st.markdown("**Most representative reviews**")
                    rep = assigned[assigned["topic"] == t["topic_id"]].sort_values("strength", ascending=False).head(4)
                    for _, row in rep.iterrows():
                        ui.review_card(row, t["terms"][:5], show_meta=False)

ui.footer()
