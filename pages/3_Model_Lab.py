"""Model Lab: real training configuration and held-out evaluation results."""
import pandas as pd
import streamlit as st

from src.config import LABELS, LOW_CONFIDENCE_MARGIN, LOW_CONFIDENCE_PROB
from src.ui import charts
from src.ui import components as ui
from src.ui import state

model = state.get_model()
report = state.get_training_report(model.status.trained_at)

primary = report["models"][report["primary_model"]] if report else None
ui.hero("Model Lab", "A classifier you can <em>inspect.</em>",
        "Supervised sentiment classification with spaCy preprocessing, TF-IDF features and Logistic Regression, "
        "compared against baselines. Every number on this page is read from the saved training report.",
        [(f"Trained {report['trained_at']}" if report else "No training report", ""),
         (f"Source: {model.status.source}", ""), ("Held-out test set · never used for tuning", "live")],
        {"label": "Held-out macro-F1 · Logistic Regression", "value": f"{primary['test']['macro_f1']:.3f}" if primary else "n/a",
         "note": (f"Accuracy {primary['test']['accuracy']:.3f} on {report['split']['test_rows']} unseen comments. "
                  f"Majority baseline macro-F1: {report['models']['majority_baseline']['test']['macro_f1']:.3f}.") if primary else
                 "Train the model to see results."} if primary else None)

if not model.available:
    st.error(model.status.message)
elif model.status.source == "trained_at_startup":
    st.info(model.status.message)
if not report:
    ui.empty("No training report found", "Run `python -m src.models.train` (or use the button below) to train and evaluate the model.")

tab_eval, tab_data, tab_errors, tab_try, tab_cfg = st.tabs(
    ["Evaluation", "Training data", "Error analysis", "Try the model", "Configuration & retraining"])

if report:
    models = report["models"]
    with tab_eval:
        ui.section("Model comparison", "Cross-validated macro-F1 on training folds (used for tuning) vs. held-out test scores (reported only).", "01")
        st.plotly_chart(charts.model_comparison(models), width="stretch", config=charts.CONFIG)
        comp = pd.DataFrame([{"Model": m["display_name"], "CV macro-F1": m["cv_macro_f1_mean"], "CV std": m["cv_macro_f1_std"],
                              "Test accuracy": m["test"]["accuracy"], "Test macro-F1": m["test"]["macro_f1"],
                              "Test weighted-F1": m["test"]["weighted_f1"], "Probabilities": "yes" if m["supports_probabilities"] else "no",
                              "Selected hyper-parameters": ", ".join(f"{k.split('__')[-1]}={v}" for k, v in m["best_params"].items())}
                             for m in models.values()])
        st.dataframe(comp, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.3f") for c in
                                    ["CV macro-F1", "CV std", "Test accuracy", "Test macro-F1", "Test weighted-F1"]})
        best_test = max(models.values(), key=lambda m: m["test"]["macro_f1"])
        if best_test["display_name"] != primary["display_name"]:
            st.caption(f"Note: {best_test['display_name']} scores slightly higher on the test set "
                       f"({best_test['test']['macro_f1']:.3f} vs {primary['test']['macro_f1']:.3f}). Logistic Regression remains the "
                       "pre-declared primary model because it provides class probabilities and switching models based on the "
                       "test set would leak test information into model selection.")

        a, b = st.columns(2, gap="large")
        with a:
            ui.section("Confusion matrix", "Logistic Regression on the held-out test set (row-normalised).", "02")
            st.plotly_chart(charts.confusion_heatmap(primary["test"]["confusion_matrix"], primary["test"]["labels"]),
                            width="stretch", config=charts.CONFIG)
        with b:
            ui.section("Per-class metrics", "Precision, recall and F1 per sentiment class.", "03")
            st.plotly_chart(charts.per_class_bars(primary["test"]["per_class"]), width="stretch", config=charts.CONFIG)
            pc = pd.DataFrame(primary["test"]["per_class"]).T.reset_index().rename(columns={"index": "class"})
            st.dataframe(pc, hide_index=True, width="stretch",
                         column_config={c: st.column_config.NumberColumn(format="%.3f") for c in ["precision", "recall", "f1"]})

        c, d = st.columns([1.1, 1], gap="large")
        with c:
            ui.section("Probability calibration", "Does a 70% top probability mean ~70% accuracy? (test set)", "04")
            st.plotly_chart(charts.reliability_chart(report["calibration"]["bins"]), width="stretch", config=charts.CONFIG)
            st.caption(f"Expected calibration error: **{report['calibration']['ece']:.3f}** (0 = perfectly calibrated). No extra "
                       "calibration step is applied, so probabilities are shown as model estimates, not guarantees. Predictions with "
                       f"top probability < {LOW_CONFIDENCE_PROB:.0%} or a margin < {LOW_CONFIDENCE_MARGIN:.0%} over the runner-up "
                       "are flagged **review needed**.")
        with d:
            ui.section("Most informative features", "Largest Logistic Regression weights per class (TF-IDF n-grams of spaCy lemmas).", "05")
            cls = st.radio("Class", LABELS, horizontal=True, key="ml_feat_cls", index=2)
            st.dataframe(pd.DataFrame(report["top_features"][cls]), hide_index=True, width="stretch", height=300)

        neutral = primary["test"]["per_class"]["neutral"]
        st.warning(f"**Honest reading of the results.** The neutral class is small ({report['dataset']['cleaning']['clean_label_counts']['neutral']} "
                   f"examples in total, {neutral['support']} in the test set) and loosely defined in the source data (many 'neutral' "
                   f"comments are suggestions or wishes), so neutral F1 is low ({neutral['f1']:.2f}). Positive vs negative "
                   "separation is substantially better. Treat neutral predictions with particular caution.")

    with tab_data:
        clean = report["dataset"]["cleaning"]
        ds_info = report["dataset"]
        st.markdown(f"**{ds_info['name']}**, [{ds_info['url']}]({ds_info['url']})  \nLicence: {ds_info['license']}  \n"
                    f"Label mapping: {ds_info['label_mapping']}  \nFile SHA-256: `{ds_info['sha256']}`")
        k = st.columns(4)
        with k[0]:
            ui.kpi("Raw rows", clean["raw_rows"], f"encoding detected: {clean['encoding_detected']}", "violet")
        with k[1]:
            ui.kpi("Exact/normalised duplicates", clean["dropped_duplicate_rows"], "removed (first kept)")
        with k[2]:
            ui.kpi("Conflicting-label rows", clean["dropped_conflicting_rows"], "same text with different labels, removed", "neg")
        with k[3]:
            ui.kpi("Clean labelled rows", clean["clean_rows"], "used for train/test split", "pos")
        if clean["conflicting_label_texts"]:
            st.caption("Texts with conflicting labels: " + "; ".join(f"“{t}”" for t in clean["conflicting_label_texts"]))
        e, f = st.columns(2, gap="large")
        with e:
            st.plotly_chart(charts.class_distribution(clean["clean_label_counts"], "Class distribution after cleaning"),
                            width="stretch", config=charts.CONFIG)
        with f:
            sp = report["split"]
            st.plotly_chart(charts.class_distribution(sp["test_label_counts"], f"Held-out test set ({sp['test_rows']} comments)"),
                            width="stretch", config=charts.CONFIG)
            st.caption(f"Stratified split: {sp['train_rows']} train / {sp['test_rows']} test, test size {sp['test_size']:.0%}, "
                       f"random_state={sp['random_state']}.")
        st.caption("The bundled demonstration dataset is synthetic and is never used for training or evaluation.")

    with tab_errors:
        st.markdown(f"**{report['misclassified_total']}** of {report['split']['test_rows']} test comments were misclassified by "
                    "Logistic Regression. The most confident mistakes are shown first. They often reveal label noise or "
                    "sarcasm/suggestions the model cannot capture.")
        errs = pd.DataFrame([{"text": e["text"], "true label": e["true"], "predicted": e["predicted"],
                              **{f"P({c})": e["probabilities"].get(c) for c in LABELS}} for e in report["misclassified_examples"]])
        fl = st.multiselect("True label", LABELS, key="ml_err_true", placeholder="All")
        if fl:
            errs = errs[errs["true label"].isin(fl)]
        st.dataframe(errs, hide_index=True, width="stretch", height=420,
                     column_config={f"P({c})": st.column_config.ProgressColumn(f"P({c})", min_value=0, max_value=1, format="%.2f")
                                    for c in LABELS})

    with tab_cfg:
        v = report["versions"]
        st.markdown(f"""
| Setting | Value |
|---|---|
| Preprocessing | spaCy `{v['spacy_model']}` tokenisation + lemmatisation, stopwords removed except negators/intensifiers, negation-scope `neg_` marking (3 tokens) |
| Features | TF-IDF (sublinear tf), n-gram range tuned per model |
| Primary model | Logistic Regression, `class_weight="balanced"`, C tuned |
| Baselines | Majority class, Multinomial Naive Bayes, Linear SVM |
| Model selection | {report['primary_selection_rule']} |
| Leakage control | scikit-learn `Pipeline` (preprocessing → TF-IDF → classifier) fitted inside each CV fold; the test set is scored once |
| Reload check | identical predictions after reload: **{report.get('reload_check', {}).get('identical_predictions')}**, artifact {report.get('reload_check', {}).get('artifact_bytes', 0) / 1024:.0f} KB |
| Training time | {report['training_seconds']} s |
| Versions | Python {v['python']}, scikit-learn {v['scikit_learn']}, spaCy {v['spacy']}, pandas {v['pandas']}, NumPy {v['numpy']} |
""")

with tab_try:
    txt = st.text_area("Write a comment to classify", "The teacher explains well but the exams are not fair.", key="ml_try")
    if model.available and txt.strip():
        p = model.predict([txt]).iloc[0]
        st.markdown(f"Prediction: {ui.pill(p['sentiment'])} &nbsp; top probability {p['confidence']:.0%}"
                    + (" &nbsp; <span class='sq-warn'>⚑ review needed</span>" if p["review_needed"] else ""), unsafe_allow_html=True)
        st.plotly_chart(charts.probability_bars({"positive": p["prob_positive"], "neutral": p["prob_neutral"],
                                                 "negative": p["prob_negative"]}), width="stretch", config=charts.CONFIG)
        st.caption("This is a prediction on new, unlabelled text and is separate from the held-out evaluation above.")

with tab_cfg:
    st.markdown("**Retrain**")
    st.caption("Retraining is deterministic (fixed seed) and uses only the bundled labelled dataset. It takes roughly 10–30 seconds. "
               "Afterwards the active dataset is reset to the demonstration data and re-analysed with the new model.")
    if st.button("Re-run training & evaluation", key="ml_retrain"):
        from src.models.train import load_training_data, save_artifacts, train_and_evaluate

        bar = st.progress(0.0, text="Loading labelled data")
        try:
            df, log = load_training_data()
            result = train_and_evaluate(df, log, progress=lambda f, m: bar.progress(f, text=m))
            check = save_artifacts(result)
            st.cache_resource.clear()
            st.cache_data.clear()
            st.session_state.pop("dataset", None)
            st.success(f"Retrained. Test macro-F1 {result.report['models']['logistic_regression']['test']['macro_f1']:.3f}; "
                       f"reload check identical: {check['identical_predictions']}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Training failed: {type(exc).__name__}: {exc}")

ui.footer()
