"""Reports (CSV / Markdown / HTML) and the methodology & about page."""
import platform

import pandas as pd
import plotly
import sklearn
import spacy
import streamlit as st
import streamlit.components.v1 as components

from src.analytics.metrics import aspect_summary, generate_insights, overview_kpis
from src.analytics.recommendations import build_recommendations
from src.analytics.reports import LIMITATIONS, build_context, build_html, build_markdown
from src.config import ACADEMIC_TITLE, PRODUCT_DESCRIPTOR, PRODUCT_NAME, TAGLINE
from src.ui import components as ui
from src.ui import state

ds = state.active()
model = state.get_model()
analyzer = state.get_analyzer()
report = state.get_training_report(model.status.trained_at)
reviews, mentions = state.filtered(ds)

ui.hero("Reports & Methodology", "Show your <em>working.</em>",
        f"Download the analysed data and a printable report, and read exactly how {PRODUCT_NAME} turns raw comments into "
        "evidence — including what it cannot do.",
        [(PRODUCT_NAME + " · " + PRODUCT_DESCRIPTOR, ""), (state.filter_summary(ds, reviews), "")])

tab_rep, tab_method, tab_about = st.tabs(["Reports & exports", "Methodology", "About & sources"])

with tab_rep:
    if reviews.empty:
        ui.empty("No reviews match the current filters", "Reports are generated for the current selection. Widen the filters.")
    else:
        kpis = overview_kpis(reviews, ds.report.excluded_records)
        summary = aspect_summary(mentions, reviews, analyzer.taxonomy)
        topics = state.topics_for(ds, reviews, 4)
        ctx = build_context(ds.name, ds.kind, ds.report.as_dict(), kpis, summary, generate_insights(reviews, summary),
                            build_recommendations(summary, mentions, reviews, analyzer.taxonomy), report,
                            state.filter_summary(ds, reviews), topics.topics if topics.ok else None,
                            "Logistic Regression (trained)" if model.available else "unavailable")
        html_report = build_html(ctx)
        md_report = build_markdown(ctx)
        st.markdown("All exports reflect the **current sidebar filters**. The CSV keeps the original review text unchanged.")
        d = st.columns(3)
        d[0].download_button("Analysed reviews (CSV)", state.export_frame(reviews).to_csv(index=False).encode("utf-8"),
                             "sentiq_analysed_reviews.csv", "text/csv", width="stretch", type="primary")
        d[1].download_button("Report (HTML, printable)", html_report.encode("utf-8"), "sentiq_report.html", "text/html", width="stretch")
        d[2].download_button("Report (Markdown)", md_report.encode("utf-8"), "sentiq_report.md", "text/markdown", width="stretch")
        a = st.columns(3)
        a[0].download_button("Aspect mentions (CSV)", mentions.to_csv(index=False).encode("utf-8"), "sentiq_aspect_mentions.csv",
                             "text/csv", width="stretch")
        a[1].download_button("Excluded records (CSV)", ds.excluded.to_csv(index=False).encode("utf-8"), "sentiq_excluded_records.csv",
                             "text/csv", width="stretch")
        st.caption("PDF: open the HTML report in a browser and use Print → Save as PDF (a print stylesheet is included).")
        ui.section("Report preview", "The same HTML that the download contains.")
        components.html(html_report, height=900, scrolling=True)

with tab_method:
    st.markdown(f"""
### Official academic title
**{ACADEMIC_TITLE}**

Product: **{PRODUCT_NAME} — {PRODUCT_DESCRIPTOR}** · *{TAGLINE}*

### Pipeline
1. **Ingestion & validation** — CSV bytes are decoded (UTF-8 / UTF-8-BOM / Windows-1252 / Latin-1), the delimiter is sniffed,
   and every column is read as text so the original review is preserved. Columns are mapped to roles (review text, course,
   instructor, date, semester, rating). Empty, non-alphabetic and duplicate reviews are excluded with an explicit reason; dates
   and ratings that cannot be parsed are reported.
2. **spaCy preprocessing** (`en_core_web_sm`) — tokenisation, lemmatisation, part-of-speech tags and sentence/dependency parses.
   Generic stopwords are removed, but negators (*not, never, no, hardly, n't…*) and intensifiers are kept. Up to three content
   tokens after a negator get a `neg_` prefix, so *“not helpful”* becomes `not neg_helpful` and cannot look positive.
3. **Sentiment classification** — a scikit-learn `Pipeline` (spaCy normaliser → TF-IDF uni/bi-grams → Logistic Regression with
   balanced class weights) trained on a verified public labelled dataset. Baselines: majority class, Multinomial Naive Bayes,
   Linear SVM. Hyper-parameters are tuned with 5-fold stratified cross-validation on the training split only; the stratified
   20% test split is scored once.
4. **Uncertainty** — class probabilities are shown for every prediction; predictions with top probability < 55% or a margin
   < 15% are flagged *review needed*. Calibration on the test set is reported in the Model Lab (no post-hoc calibration).
5. **Aspect analysis (rule-assisted)** — sentences are split into clauses at contrastive conjunctions; a configurable lexicon
   (`config/aspect_taxonomy.json`) is matched on lemmas/lowercase with spaCy `PhraseMatcher`; context-dependent words need a
   supporting context word; the sentiment model is applied to the triggering clause. Unmatched and ambiguous cases are listed.
6. **Keywords & topics** — document frequencies of lemma n-grams and spaCy noun chunks by predicted sentiment; exploratory
   NMF topics on TF-IDF of content lemmas (skipped when data is too small or uniform).
7. **Insights & recommendations** — deterministic rules with minimum-evidence thresholds; each output carries counts,
   example evidence and caveats.

### Scales
* **Average sentiment score** = mean of P(positive) − P(negative), from −1 (all negative) to +1 (all positive).
* **Feedback indicator** = 100 × (positive share + 0.5 × neutral share) = 50 × positive share + 50 × (1 − negative share).

### Limitations and appropriate use
""" + "\n".join(f"* {l}" for l in LIMITATIONS) + """
* Uploaded data is processed in memory and is not written to disk or logs by Sentiq.
* Intended use: exploratory support for instructors and departments reflecting on feedback — not automated evaluation,
  ranking or personnel decisions.
""")

with tab_about:
    st.markdown(f"## {PRODUCT_NAME}\n*{PRODUCT_DESCRIPTOR} — {TAGLINE}*\n\n**Academic project title:** {ACADEMIC_TITLE}")
    st.markdown("### Data sources")
    if report:
        dsi = report["dataset"]
        st.markdown(f"* **Sentiment training data:** {dsi['name']} — <{dsi['url']}> — licence **{dsi['license']}**. "
                    f"{dsi['cleaning']['raw_rows']} raw labelled comments (verified), {dsi['cleaning']['clean_rows']} after cleaning. "
                    f"{dsi['label_mapping']}.")
    st.markdown("* **Demonstration data:** `data/sample/demo_feedback.csv` — **synthetic**, written for this project; not real "
                "student feedback; never used for training or evaluation.\n"
                "* **EduRABSA** (aspect-annotated education reviews, CC BY-NC-SA 4.0) was reviewed but not integrated: the data is "
                "distributed separately via Zenodo in a quadruplet-extraction format that could not be integrated and validated "
                "reliably within the project timeline.")
    st.markdown("### Environment")
    st.dataframe(pd.DataFrame([
        {"component": "Python", "version": platform.python_version()},
        {"component": "Streamlit", "version": st.__version__},
        {"component": "spaCy", "version": spacy.__version__},
        {"component": "spaCy model", "version": report["versions"]["spacy_model"] if report else "—"},
        {"component": "scikit-learn", "version": sklearn.__version__},
        {"component": "pandas", "version": pd.__version__},
        {"component": "Plotly", "version": plotly.__version__},
        {"component": "Sentiment model", "version": f"{model.status.source} · trained {model.status.trained_at}"},
    ]), hide_index=True, width="stretch")

ui.footer()
