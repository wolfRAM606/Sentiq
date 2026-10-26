"""Supervised sentiment training on the verified public student-feedback dataset.

Run from the project root:  python -m src.models.train
"""
from __future__ import annotations

import hashlib
import json
import logging
import platform
import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.config import LABELS, METRICS_PATH, MODEL_PATH, RANDOM_STATE, TRAINING_DATASET, TRAINING_LABEL_MAP
from src.data.loader import read_csv_path
from src.data.validation import normalise_text
from src.models.evaluate import classification_metrics, reliability
from src.nlp.preprocessing import SpacyTextNormalizer, get_nlp

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "logistic_regression"
TEST_SIZE = 0.2
CV_FOLDS = 5

DATASET_INFO = {
    "name": "Student Feedback Data (mbalvi/student_feedback_data)",
    "url": "https://github.com/mbalvi/student_feedback_data",
    "file": "Student_Feedback.csv",
    "license": "GPL-3.0 (as declared in the source repository's LICENSE file)",
    "label_mapping": "0 = negative, 1 = positive, 2 = neutral (inferred from README class counts and verified against the file)",
}


class TrainingError(ValueError):
    pass


@dataclass
class TrainingResult:
    pipeline: Pipeline
    report: dict


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_training_data(path: Path = TRAINING_DATASET, text_col: str = "comments", label_col: str = "sentiments"):
    """Load and clean the labelled dataset, returning (frame, cleaning_log)."""
    loaded = read_csv_path(path, max_rows=1_000_000)
    df = loaded.frame
    if text_col not in df.columns or label_col not in df.columns:
        raise TrainingError(f"Training data must contain '{text_col}' and '{label_col}' columns; found {list(df.columns)}.")
    log = {"encoding_detected": loaded.encoding, "raw_rows": int(len(df))}
    raw_counts = df[label_col].astype(str).str.strip().value_counts().to_dict()
    log["raw_label_counts"] = {str(k): int(v) for k, v in raw_counts.items()}

    df = df[[text_col, label_col]].rename(columns={text_col: "text", label_col: "raw_label"})
    df["text"] = df["text"].astype(str).str.strip()
    df["raw_label"] = df["raw_label"].astype(str).str.strip()
    label_map = {str(k): v for k, v in TRAINING_LABEL_MAP.items()}
    df["label"] = df["raw_label"].map(label_map)

    unknown = df["label"].isna()
    empty = df["text"] == ""
    log["dropped_unknown_label"] = int(unknown.sum())
    log["dropped_empty_text"] = int((empty & ~unknown).sum())
    df = df[~unknown & ~empty].copy()

    df["norm"] = df["text"].map(normalise_text)
    conflicting = df.groupby("norm")["label"].nunique()
    conflicting = set(conflicting[conflicting > 1].index)
    log["conflicting_label_texts"] = sorted(conflicting)
    log["dropped_conflicting_rows"] = int(df["norm"].isin(conflicting).sum())
    df = df[~df["norm"].isin(conflicting)]
    dup = df.duplicated("norm", keep="first")
    log["dropped_duplicate_rows"] = int(dup.sum())
    df = df[~dup].reset_index(drop=True)
    log["clean_rows"] = int(len(df))
    log["clean_label_counts"] = {k: int(v) for k, v in df["label"].value_counts().items()}
    if df["label"].nunique() < 2:
        raise TrainingError("Training data needs at least two sentiment classes.")
    if df["label"].value_counts().min() < CV_FOLDS:
        raise TrainingError("Every class needs at least as many examples as cross-validation folds.")
    return df[["text", "label"]], log


def candidate_models() -> dict[str, tuple[Pipeline, dict]]:
    def tfidf():
        return TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, token_pattern=r"(?u)\b[\w']+\b")

    return {
        "majority_baseline": (
            Pipeline([("prep", SpacyTextNormalizer()), ("tfidf", tfidf()), ("clf", DummyClassifier(strategy="most_frequent"))]),
            {},
        ),
        "multinomial_nb": (
            Pipeline([("prep", SpacyTextNormalizer()), ("tfidf", tfidf()), ("clf", MultinomialNB())]),
            {"clf__alpha": [0.1, 0.3, 1.0], "tfidf__ngram_range": [(1, 1), (1, 2)]},
        ),
        "logistic_regression": (
            Pipeline([
                ("prep", SpacyTextNormalizer()),
                ("tfidf", tfidf()),
                ("clf", LogisticRegression(max_iter=5000, class_weight="balanced", random_state=RANDOM_STATE)),
            ]),
            {"clf__C": [0.5, 1.0, 3.0, 10.0], "tfidf__ngram_range": [(1, 1), (1, 2)]},
        ),
        "linear_svm": (
            Pipeline([
                ("prep", SpacyTextNormalizer()),
                ("tfidf", tfidf()),
                ("clf", LinearSVC(class_weight="balanced", random_state=RANDOM_STATE)),
            ]),
            {"clf__C": [0.1, 0.5, 1.0, 3.0], "tfidf__ngram_range": [(1, 1), (1, 2)]},
        ),
    }


MODEL_DISPLAY = {
    "majority_baseline": "Majority-class baseline",
    "multinomial_nb": "Multinomial Naive Bayes",
    "logistic_regression": "Logistic Regression (primary)",
    "linear_svm": "Linear SVM",
}


def train_and_evaluate(df: pd.DataFrame, cleaning_log: dict | None = None, random_state: int = RANDOM_STATE,
                       test_size: float = TEST_SIZE, cv_folds: int = CV_FOLDS, progress=None) -> TrainingResult:
    if "text" not in df.columns or "label" not in df.columns:
        raise TrainingError("Training frame must have 'text' and 'label' columns.")
    if df["label"].isna().any():
        raise TrainingError("Some training rows have missing labels.")
    started = time.time()
    get_nlp()  # fail fast if spaCy model is missing

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"].tolist(), df["label"].tolist(), test_size=test_size, random_state=random_state, stratify=df["label"]
    )
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    results, fitted = {}, {}
    candidates = candidate_models()
    for i, (name, (pipe, grid)) in enumerate(candidates.items()):
        if progress:
            progress(i / len(candidates), f"Training {MODEL_DISPLAY[name]}")
        search = GridSearchCV(pipe, grid or {"clf__strategy": ["most_frequent"]}, scoring="f1_macro", cv=cv, n_jobs=1, refit=True)
        search.fit(X_train, y_train)
        model = search.best_estimator_
        fitted[name] = model
        y_pred = model.predict(X_test)
        metrics = classification_metrics(y_test, y_pred, LABELS)
        results[name] = {
            "display_name": MODEL_DISPLAY[name],
            "best_params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in search.best_params_.items()},
            "cv_macro_f1_mean": float(search.best_score_),
            "cv_macro_f1_std": float(search.cv_results_["std_test_score"][search.best_index_]),
            "test": metrics,
            "supports_probabilities": hasattr(model, "predict_proba"),
        }

    primary = fitted[PRIMARY_MODEL]
    classes = list(primary.classes_)
    proba = primary.predict_proba(X_test)
    y_pred = primary.predict(X_test)
    calib = reliability(y_test, proba, classes)
    errors = []
    for text, true, pred, p in zip(X_test, y_test, y_pred, proba):
        if true != pred:
            errors.append({"text": text, "true": true, "predicted": pred,
                           "probabilities": {c: round(float(v), 4) for c, v in zip(classes, p)}})
    errors.sort(key=lambda e: -max(e["probabilities"].values()))

    # global feature weights for transparency
    vec, clf = primary.named_steps["tfidf"], primary.named_steps["clf"]
    vocab = np.asarray(vec.get_feature_names_out())
    top_features = {}
    for ci, cls in enumerate(clf.classes_):
        order = np.argsort(clf.coef_[ci])[::-1][:15]
        top_features[cls] = [{"feature": str(vocab[j]), "weight": round(float(clf.coef_[ci][j]), 4)} for j in order]

    import spacy

    report = {
        "primary_model": PRIMARY_MODEL,
        "primary_selection_rule": "Logistic Regression is the pre-declared primary model; all models are tuned with "
                                  f"{cv_folds}-fold stratified cross-validation on the training split only (macro-F1).",
        "dataset": {**DATASET_INFO, "sha256": file_sha256(TRAINING_DATASET) if TRAINING_DATASET.exists() else None,
                    "cleaning": cleaning_log or {}},
        "split": {"strategy": "stratified train/test split", "test_size": test_size, "random_state": random_state,
                  "train_rows": len(X_train), "test_rows": len(X_test),
                  "train_label_counts": pd.Series(y_train).value_counts().to_dict(),
                  "test_label_counts": pd.Series(y_test).value_counts().to_dict()},
        "models": results,
        "calibration": calib,
        "misclassified_examples": errors[:40],
        "misclassified_total": len(errors),
        "top_features": top_features,
        "classes": classes,
        "versions": {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                     "spacy": spacy.__version__, "spacy_model": f"{get_nlp().meta.get('lang', 'en')}_{get_nlp().meta.get('name', '')}-{get_nlp().meta.get('version', '')}",
                     "pandas": pd.__version__, "numpy": np.__version__},
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "training_seconds": round(time.time() - started, 2),
        "test_texts_sample_for_reload_check": X_test[:50],
    }
    if progress:
        progress(1.0, "Training complete")
    return TrainingResult(primary, report)


def save_artifacts(result: TrainingResult, model_path: Path = MODEL_PATH, report_path: Path = METRICS_PATH) -> dict:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": result.pipeline, "classes": list(result.pipeline.classes_),
                 "trained_at": result.report["trained_at"], "sklearn_version": sklearn.__version__}, model_path, compress=3)
    # reload and verify predictions are identical
    reloaded = joblib.load(model_path)["pipeline"]
    sample = result.report["test_texts_sample_for_reload_check"]
    before = result.pipeline.predict_proba(sample)
    after = reloaded.predict_proba(sample)
    check = {"identical_predictions": bool((result.pipeline.predict(sample) == reloaded.predict(sample)).all()),
             "max_probability_difference": float(np.abs(before - after).max()),
             "artifact_bytes": model_path.stat().st_size}
    result.report["reload_check"] = check
    report = {k: v for k, v in result.report.items() if k != "test_texts_sample_for_reload_check"}
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return check


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df, log = load_training_data()
    result = train_and_evaluate(df, log, progress=lambda f, m: logger.info("%3.0f%% %s", f * 100, m))
    check = save_artifacts(result)
    for name, r in result.report["models"].items():
        t = r["test"]
        print(f"{r['display_name']:<32} CV macro-F1 {r['cv_macro_f1_mean']:.3f}±{r['cv_macro_f1_std']:.3f} | "
              f"test acc {t['accuracy']:.3f} macro-F1 {t['macro_f1']:.3f}  params={r['best_params']}")
    print("ECE (primary):", round(result.report["calibration"]["ece"], 4))
    print("Reload check:", check)


if __name__ == "__main__":
    main()
