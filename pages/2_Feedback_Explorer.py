"""Feedback Explorer: upload, validate, map, analyse and inspect reviews."""
import logging

import pandas as pd
import streamlit as st

from src.analytics.pipeline import analyze_reviews
from src.config import MAX_ROWS, MAX_UPLOAD_MB
from src.data.loader import DataLoadError, read_csv_bytes
from src.data.schema_mapping import OPTIONAL_ROLES, ROLE_LABELS, guess_text_column, suggest_mapping
from src.data.validation import ValidationError, prepare_dataset
from src.nlp.preprocessing import clean_raw, get_nlp, process_texts
from src.ui import charts
from src.ui import components as ui
from src.ui import state

logger = logging.getLogger(__name__)
ds = state.active()
model = state.get_model()
analyzer = state.get_analyzer()
reviews, mentions = state.filtered(ds)

ui.hero("Feedback Explorer", "Read the <em>evidence</em>, review by review.",
        "Upload a CSV, map its columns and analyse it with the same spaCy + Logistic Regression pipeline used everywhere in "
        "Sentiq. Every record is accounted for — nothing is silently dropped.",
        [("Synthetic demonstration data" if ds.kind == "demo" else ds.name, "demo" if ds.kind == "demo" else "live"),
         (state.filter_summary(ds, reviews), ""), (f"Uploads ≤ {MAX_UPLOAD_MB} MB · ≤ {MAX_ROWS:,} rows", "")])

tab_explore, tab_upload, tab_single, tab_quality = st.tabs(
    ["Explore reviews", "Upload & analyse CSV", "Analyse a single review", "Validation report"])

# ---------------------------------------------------------------------------
with tab_explore:
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Search review text", placeholder="e.g. assignment, pace, not clear", key="fx_query")
    sort = c2.selectbox("Sort by", ["Record order", "Most negative first", "Most positive first", "Lowest confidence first"], key="fx_sort")
    n_cards = c3.number_input("Cards to show", 5, 100, 10, step=5, key="fx_cards")
    view = reviews
    if query.strip():
        view = view[view["review_text"].str.contains(query.strip(), case=False, regex=False, na=False)]
    if sort == "Most negative first":
        view = view.sort_values("prob_negative", ascending=False)
    elif sort == "Most positive first":
        view = view.sort_values("prob_positive", ascending=False)
    elif sort == "Lowest confidence first":
        view = view.sort_values("confidence", ascending=True)
    st.caption(f"{len(view)} reviews match the search and sidebar filters.")

    if view.empty:
        ui.empty("No matching reviews", "Try a different search term or clear the sidebar filters.")
    else:
        table = state.export_frame(view)
        st.dataframe(
            table, width="stretch", hide_index=True, height=360,
            column_config={
                "record_id": st.column_config.NumberColumn("#", width="small"),
                "review_text": st.column_config.TextColumn("Original review", width="large"),
                "prob_positive": st.column_config.ProgressColumn("P(pos)", min_value=0, max_value=1, format="%.2f"),
                "prob_neutral": st.column_config.ProgressColumn("P(neu)", min_value=0, max_value=1, format="%.2f"),
                "prob_negative": st.column_config.ProgressColumn("P(neg)", min_value=0, max_value=1, format="%.2f"),
                "confidence": st.column_config.NumberColumn("Top prob.", format="%.2f"),
                "review_needed": st.column_config.CheckboxColumn("Review needed"),
                "sentiment_score": st.column_config.NumberColumn("Score", format="%+.2f"),
                "processed_text": st.column_config.TextColumn("spaCy processed text", width="medium"),
            })
        d1, d2 = st.columns([1, 3])
        d1.download_button("Download analysed CSV", state.export_frame(view).to_csv(index=False).encode("utf-8"),
                           file_name="sentiq_analysed_reviews.csv", mime="text/csv", width="stretch",
                           help="Matching reviews with original text, predictions, probabilities, aspects and processed text.")
        d2.caption("The export contains the reviews currently shown (search + sidebar filters), original text unchanged.")

        ui.section("Review intelligence cards", "Matched aspect evidence is highlighted. ⚑ marks low-confidence predictions.")
        terms_by_id = mentions.groupby("record_id")["terms"].apply(lambda s: [t.strip() for x in s for t in x.split(",")]).to_dict()
        for _, row in view.head(int(n_cards)).iterrows():
            ui.review_card(row, terms_by_id.get(row["record_id"], []))

        ui.section("Inspect one review", "Full transparency: probabilities, aspect evidence and the exact model input.")
        rid = st.selectbox("Record", view["record_id"].tolist(), key="fx_inspect",
                           format_func=lambda r: f"#{r} — {view.loc[view['record_id'] == r, 'review_text'].iloc[0][:90]}")
        row = view[view["record_id"] == rid].iloc[0]
        i1, i2 = st.columns([1, 1.2], gap="large")
        with i1:
            ui.review_card(row, terms_by_id.get(rid, []))
            if model.available:
                st.plotly_chart(charts.probability_bars({"positive": row["prob_positive"], "neutral": row["prob_neutral"],
                                                         "negative": row["prob_negative"]}), width="stretch", config=charts.CONFIG)
                st.caption("Class probabilities from Logistic Regression. The top probability is not a calibrated certainty; "
                           "see calibration in the Model Lab.")
        with i2:
            st.markdown("**Detected aspects (clause-level sentiment)**")
            m = mentions[mentions["record_id"] == rid]
            if m.empty:
                st.caption("No teaching aspect matched this review (this is different from neutral sentiment).")
            else:
                st.dataframe(m[["aspect", "evidence", "terms", "match_type", "negated", "aspect_sentiment", "aspect_confidence"]],
                             hide_index=True, width="stretch",
                             column_config={"aspect_confidence": st.column_config.NumberColumn("confidence", format="%.2f")})
            st.markdown("**Processed text (classifier input)**")
            st.code(row["processed_text"] or "(empty after preprocessing)", language=None)
            st.caption("spaCy lemmas; generic stopwords removed, negators kept; words in a negation's scope get the `neg_` prefix.")

# ---------------------------------------------------------------------------
with tab_upload:
    st.markdown("Upload a CSV with one review per row. Column names are detected automatically and can be changed below. "
                "Files are processed in memory and are not stored on disk.")
    up = st.file_uploader("CSV file", type=["csv", "txt"], key="fx_upload", help=f"Maximum {MAX_UPLOAD_MB} MB.")
    b1, b2 = st.columns([1, 3])
    if ds.kind != "demo" and b1.button("Reset to demonstration data", width="stretch"):
        state.set_active(state.load_demo())
        st.success("Demonstration dataset restored.")
        st.rerun()
    if up is not None:
        try:
            loaded = read_csv_bytes(up.getvalue())
        except DataLoadError as exc:
            st.error(f"**Could not read this file.** {exc}")
            loaded = None
        if loaded is not None:
            frame = loaded.frame
            st.success(f"Read **{len(frame):,} rows** and **{frame.shape[1]} columns** "
                       f"(encoding {loaded.encoding}, delimiter {loaded.delimiter!r}).")
            if loaded.truncated:
                st.warning(f"The file has {loaded.original_rows:,} rows; only the first {MAX_ROWS:,} will be analysed.")
            st.markdown("**Preview (first 10 rows)**")
            st.dataframe(frame.head(10), width="stretch", hide_index=True)

            suggested = suggest_mapping(list(frame.columns))
            if not suggested["text"]:
                suggested["text"] = guess_text_column(frame)
            st.markdown("**Column mapping**")
            cols = list(frame.columns)
            none = "— not available —"
            mc = st.columns(4)
            mapping = {"text": mc[0].selectbox(ROLE_LABELS["text"], cols,
                                               index=cols.index(suggested["text"]) if suggested["text"] in cols else 0,
                                               key=f"map_text_{up.file_id}")}
            for i, role in enumerate(OPTIONAL_ROLES):
                opts = [none] + cols
                default = suggested.get(role)
                choice = mc[(i + 1) % 4].selectbox(ROLE_LABELS[role], opts, index=opts.index(default) if default in opts else 0,
                                                   key=f"map_{role}_{up.file_id}")
                mapping[role] = None if choice == none else choice
            used = [c for c in mapping.values() if c]
            if len(used) != len(set(used)):
                st.error("Each column can be mapped to only one role.")
            else:
                name = st.text_input("Dataset name", value=up.name, key=f"name_{up.file_id}")
                if st.button("Analyse dataset", type="primary", key=f"analyse_{up.file_id}"):
                    bar = st.progress(0.0, text="Validating records")
                    try:
                        valid, excluded, report = prepare_dataset(frame, mapping)
                        bar.progress(0.1, text=f"{report.valid_records} valid reviews — starting NLP pipeline")
                        result = analyze_reviews(valid, model, analyzer,
                                                 progress=lambda f, msg: bar.progress(min(max(f, 0.0), 1.0), text=msg))
                        state.set_active(state.ActiveDataset(name or up.name, "upload", valid, excluded, report, result,
                                                             state.frame_key(valid)))
                        st.session_state["fx_flash"] = (f"Analysed **{report.valid_records}** valid reviews from **{name}**; "
                                                        f"{report.excluded_records} record(s) excluded (see Validation report).")
                        st.rerun()
                    except ValidationError as exc:
                        bar.empty()
                        st.error(f"**Validation failed.** {exc}")
                    except Exception as exc:  # pragma: no cover - surfaced to the user, logged without review text
                        bar.empty()
                        logger.exception("Analysis failed")
                        st.error(f"Analysis failed unexpectedly ({type(exc).__name__}). Please check the file and mapping.")
    flash = st.session_state.pop("fx_flash", None)
    if flash:
        st.success(flash)
    with st.expander("Expected format and accepted column names"):
        st.markdown("""
* **Required:** one text column (e.g. `review`, `feedback`, `comment`, `comments`, `text`, `response`).
* **Optional:** `course`/`subject`, `instructor`/`teacher`/`faculty`, `date`/`timestamp`, `semester`/`term`,
  `rating`/`score`, and an existing `sentiment`/`label` column (kept for reference only; it is **not** used for training).
* Encodings UTF-8, UTF-8 with BOM, Windows-1252 and Latin-1 are detected automatically; `,` `;` tab and `|` delimiters are supported.
* Empty, non-alphabetic and duplicate reviews are excluded **with a reason** and listed in the validation report.
""")

# ---------------------------------------------------------------------------
with tab_single:
    text = st.text_area("Type or paste one piece of feedback", height=120, key="fx_single",
                        placeholder="e.g. The lectures were clear, but the assignment instructions were confusing.")
    if st.button("Analyse review", type="primary", key="fx_single_btn"):
        if not clean_raw(text):
            st.warning("Please enter some text first.")
        else:
            pred = model.predict([text]).iloc[0]
            doc = get_nlp()(clean_raw(text))
            found = analyzer.analyze_doc(doc)
            processed = process_texts([text])[0]
            s1, s2 = st.columns([1, 1.2], gap="large")
            with s1:
                if model.available:
                    ui.kpi("Predicted sentiment", pred["sentiment"].capitalize(),
                           f"top probability {pred['confidence']:.0%} · margin {pred['margin']:.0%}",
                           {"positive": "pos", "neutral": "neu", "negative": "neg"}[pred["sentiment"]])
                    if pred["review_needed"]:
                        st.warning("Low confidence: the model is unsure about this text — a human should read it.", icon=":material/flag:")
                    st.plotly_chart(charts.probability_bars({"positive": pred["prob_positive"], "neutral": pred["prob_neutral"],
                                                             "negative": pred["prob_negative"]}), width="stretch", config=charts.CONFIG)
                else:
                    st.warning(model.status.message)
            with s2:
                st.markdown("**Detected aspects**")
                if not found.matches:
                    st.caption("No teaching aspect detected.")
                else:
                    ev = list(dict.fromkeys(m.evidence for m in found.matches))
                    ep = model.predict(ev)
                    ep.index = ev
                    st.dataframe(pd.DataFrame([{"aspect": m.aspect_label, "evidence": m.evidence, "terms": ", ".join(m.terms),
                                                "match type": m.match_type, "negated": m.negated,
                                                "clause sentiment": ep.loc[m.evidence, "sentiment"]} for m in found.matches]),
                                 hide_index=True, width="stretch")
                if found.ambiguous:
                    st.caption("Ambiguous words without supporting context: " +
                               ", ".join(f"'{a['term']}' ({a['aspect_label']})" for a in found.ambiguous))
                st.markdown("**Processed text**")
                st.code(processed.model_text or "(empty)", language=None)
            st.caption("Single-review analysis is not added to the active dataset.")

# ---------------------------------------------------------------------------
with tab_quality:
    rep = ds.report
    q = st.columns(4)
    with q[0]:
        ui.kpi("Records in file", rep.total_records, "", "violet")
    with q[1]:
        ui.kpi("Valid reviews", rep.valid_records, "included in all analyses", "pos")
    with q[2]:
        ui.kpi("Excluded", rep.excluded_records, "listed below with reasons", "neg")
    with q[3]:
        ui.kpi("Truncated long reviews", rep.truncated_reviews, "analysed up to 5,000 chars")
    st.markdown("**Column mapping used**")
    st.dataframe(pd.DataFrame([{"role": ROLE_LABELS.get(k, k), "column": v or "—"} for k, v in rep.mapped_columns.items()]),
                 hide_index=True, width="stretch")
    for w in rep.warnings:
        st.warning(w)
    if rep.missing_metadata:
        st.caption("Missing metadata values: " + ", ".join(f"{k}: {v}" for k, v in rep.missing_metadata.items()))
    st.markdown("**Excluded records**")
    if ds.excluded.empty:
        st.caption("No records were excluded.")
    else:
        st.dataframe(ds.excluded[["record_id", "review_text", "exclusion_reason", "course", "instructor"]],
                     hide_index=True, width="stretch")

ui.footer()
