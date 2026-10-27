"""Overview dashboard."""
import streamlit as st

from src.analytics.metrics import aspect_summary, generate_insights, most_positive_negative, overview_kpis
from src.config import MIN_ASPECT_MENTIONS, TAGLINE
from src.nlp.keywords import keyword_table
from src.ui import charts
from src.ui import components as ui
from src.ui import state

ds = state.active()
model = state.get_model()
reviews, mentions = state.filtered(ds)
analyzer = state.get_analyzer()
kpis = overview_kpis(reviews, ds.report.excluded_records)
summary = aspect_summary(mentions, reviews, analyzer.taxonomy)

score = kpis["effectiveness"]
chips = [("Synthetic demonstration data" if ds.kind == "demo" else "Uploaded dataset", "demo" if ds.kind == "demo" else "live"),
         (state.filter_summary(ds, reviews), ""),
         ("Logistic Regression · spaCy" if model.available else "Model unavailable", "")]
ui.hero(
    "Overview · Course feedback intelligence",
    "Every response <em>tells a story.</em>",
    "Sentiq reads each review with spaCy, predicts its sentiment with a trained classifier and links what students "
    "say to specific teaching aspects, so every pattern is backed by the comments behind it.",
    chips,
    {"label": "Sentiment-derived feedback indicator", "value": f"{score:.1f}" if score is not None else "n/a", "suffix": "/ 100",
     "note": f"100 × (positive + ½ neutral share) over {kpis['valid_reviews']} reviews. It summarises expressed opinion and should be read alongside other evidence."},
)

if ds.kind == "demo":
    st.info("You are viewing the bundled **synthetic demonstration dataset** (written for demonstration, not real student feedback). "
            "Upload your own CSV on the **Feedback Explorer** page.")
if not model.available:
    st.warning(model.status.message)
if reviews.empty:
    ui.empty("No reviews match the current filters", "Clear or widen the filters in the sidebar to see results.")
    st.stop()

c = kpis["counts"]
n = kpis["valid_reviews"]
cols = st.columns([1.1, 1, 1, 1, 1.1])
with cols[0]:
    ui.kpi("Reviews analysed", n, f"{ds.report.total_records} records in file · {ds.report.excluded_records} excluded", "violet")
with cols[1]:
    ui.kpi("Positive", c["positive"], f"{kpis['shares']['positive']:.0%} of reviews", "pos")
with cols[2]:
    ui.kpi("Neutral", c["neutral"], f"{kpis['shares']['neutral']:.0%} of reviews", "neu")
with cols[3]:
    ui.kpi("Negative", c["negative"], f"{kpis['shares']['negative']:.0%} of reviews", "neg")
with cols[4]:
    avg = kpis["avg_sentiment_score"]
    ui.kpi("Avg sentiment score", f"{avg:+.2f}" if avg is not None else "n/a", "P(pos) − P(neg), scale −1 to +1", "ice")

left, right = st.columns([1, 1.45], gap="large")
with left:
    ui.section("Sentiment distribution", "Predicted by the trained Logistic Regression model.", "01")
    st.plotly_chart(charts.sentiment_donut(c), width="stretch", config=charts.CONFIG)
    best, worst = most_positive_negative(summary)
    b1, b2 = st.columns(2)
    with b1:
        ui.kpi("Most positive aspect", best["aspect"] if best else "Not enough evidence",
               f"{int(best['positive'])}/{int(best['reviews'])} mentions positive" if best else f"needs ≥{MIN_ASPECT_MENTIONS} mentions", "pos", compact=True)
    with b2:
        ui.kpi("Most negative aspect", worst["aspect"] if worst else "Not enough evidence",
               f"{int(worst['negative'])}/{int(worst['reviews'])} mentions negative" if worst else f"needs ≥{MIN_ASPECT_MENTIONS} mentions", "neg", compact=True)
with right:
    ui.section("Aspect-level sentiment", "Share of positive / neutral / negative mentions per teaching aspect (n = mentioning reviews).", "02")
    if summary.empty:
        ui.empty("No aspects detected", "None of the selected reviews matched the teaching-aspect lexicon.")
    else:
        st.plotly_chart(charts.aspect_sentiment_bars(summary), width="stretch", config=charts.CONFIG)

ui.section("What the feedback says", "Automatically generated from the numbers above; every statement can be traced on the detail pages.", "03")
ins_col, kw_col = st.columns([1.3, 1], gap="large")
with ins_col:
    ui.insights(generate_insights(reviews, summary))
with kw_col:
    kw = keyword_table(reviews, 1)
    if kw.empty:
        ui.empty("No recurring keywords", "Keywords need to appear in at least two reviews.")
    else:
        st.plotly_chart(charts.keyword_bars(kw, top=10), width="stretch", config=charts.CONFIG)

t1, t2 = st.columns([1, 1], gap="large")
with t1:
    ui.section("Topic distribution", "Exploratory NMF topics on spaCy lemmas (4 topics). Labels are automatic.", "04")
    topics = state.topics_for(ds, reviews, 4)
    if topics.ok:
        sent_by_topic = reviews.assign(topic=topics.assignments).groupby("topic")["sentiment"].value_counts().unstack(fill_value=0)
        st.plotly_chart(charts.topic_bars(topics.topics, sent_by_topic), width="stretch", config=charts.CONFIG)
    else:
        ui.empty("Topic discovery skipped", topics.message)
with t2:
    ui.section("Dataset coverage & quality", "How much of the data each analysis could use.", "05")
    q1, q2 = st.columns(2)
    with q1:
        ui.kpi("Reviews with ≥1 aspect", f"{kpis['with_aspect'] / n:.0%}", f"{kpis['with_aspect']} of {n} reviews", "ice")
        ui.kpi("Avg review length", f"{kpis['avg_words']:.0f} words", "tokens per review (spaCy)")
    with q2:
        ui.kpi("Low-confidence predictions", kpis["review_needed"], f"{kpis['review_needed'] / n:.0%} flagged 'review needed'", "neu")
        reasons = ds.report.exclusion_reasons
        ui.kpi("Excluded records", ds.report.excluded_records,
               "; ".join(f"{v} {k.split(' (')[0].lower()}" for k, v in reasons.items()) or "none")
    trend = charts.trend_chart(reviews)
    if trend is not None:
        st.plotly_chart(trend, width="stretch", config=charts.CONFIG)

ui.footer()
