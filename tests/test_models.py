"""Training, evaluation, persistence and inference tests."""
import json

import numpy as np
import pandas as pd
import pytest

from src.config import LABELS, METRICS_PATH, TRAINING_DATASET
from src.models.evaluate import classification_metrics, reliability
from src.models.predict import PRED_COLUMNS, load_model
from src.models.train import TrainingError, load_training_data, save_artifacts, train_and_evaluate


@pytest.fixture(scope="module")
def training_data():
    return load_training_data()


def test_training_dataset_verified_counts(training_data):
    df, log = training_data
    assert log["raw_rows"] == 1086
    assert log["raw_label_counts"] == {"1": 551, "0": 436, "2": 99}
    assert log["encoding_detected"] == "cp1252"
    assert log["clean_rows"] == len(df)
    assert not df["text"].str.strip().str.lower().duplicated().any()
    assert set(df["label"]) == set(LABELS)


def test_label_mapping(training_data):
    df, _ = training_data
    raw = pd.read_csv(TRAINING_DATASET, encoding="cp1252")
    sample = raw[raw["comments"].str.strip() == "teacher was kind"]
    assert sample["sentiments"].iloc[0] == 1
    assert df.loc[df["text"] == "teacher was kind", "label"].iloc[0] == "positive"
    assert df.loc[df["text"] == "not good at all", "label"].iloc[0] == "negative"


def _small(training_data, n=240):
    df, log = training_data
    return df.groupby("label").sample(n=n // 3, random_state=0), log


def test_training_with_valid_labels_and_baseline(training_data):
    df, log = _small(training_data)
    res = train_and_evaluate(df, log, cv_folds=3)
    models = res.report["models"]
    assert set(models) == {"majority_baseline", "multinomial_nb", "logistic_regression", "linear_svm"}
    assert models["logistic_regression"]["test"]["macro_f1"] > models["majority_baseline"]["test"]["macro_f1"]
    assert set(res.pipeline.classes_) == set(LABELS)


def test_reproducible_split_and_training(training_data):
    df, log = _small(training_data)
    a = train_and_evaluate(df, log, cv_folds=3)
    b = train_and_evaluate(df, log, cv_folds=3)
    assert a.report["split"] == b.report["split"]
    assert a.report["models"]["logistic_regression"]["test"] == b.report["models"]["logistic_regression"]["test"]


def test_missing_labels_fail():
    with pytest.raises(TrainingError):
        train_and_evaluate(pd.DataFrame({"text": ["a", "b"], "label": ["positive", None]}))
    with pytest.raises(TrainingError):
        train_and_evaluate(pd.DataFrame({"text": ["a", "b"]}))


def test_load_training_data_requires_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("review\nhello\n", encoding="utf-8")
    with pytest.raises(TrainingError):
        load_training_data(p)


def test_metric_calculations():
    y_true = ["positive", "positive", "negative", "neutral", "negative", "positive"]
    y_pred = ["positive", "negative", "negative", "positive", "negative", "positive"]
    m = classification_metrics(y_true, y_pred, LABELS)
    assert m["accuracy"] == pytest.approx(4 / 6)
    # per-class F1: negative 0.8, neutral 0.0, positive 2/3  -> macro (0.8 + 0 + 0.6667) / 3
    assert m["per_class"]["negative"]["f1"] == pytest.approx(0.8)
    assert m["per_class"]["positive"]["f1"] == pytest.approx(2 / 3)
    assert m["macro_f1"] == pytest.approx((0.8 + 0 + 2 / 3) / 3)
    # rows = true [negative, neutral, positive], cols = predicted
    assert m["confusion_matrix"] == [[2, 0, 0], [0, 0, 1], [1, 0, 2]]


def test_reliability_perfect_and_bins():
    proba = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    r = reliability(["positive", "negative"], proba, LABELS)
    assert r["ece"] == pytest.approx(0.0)
    assert sum(b["count"] for b in r["bins"]) == 2


def test_saved_report_is_real_and_consistent(model):
    report = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    assert report["reload_check"]["identical_predictions"] is True
    lr = report["models"]["logistic_regression"]["test"]
    cm = np.array(lr["confusion_matrix"])
    assert cm.sum() == report["split"]["test_rows"]
    assert lr["accuracy"] == pytest.approx(np.trace(cm) / cm.sum())


def test_save_reload_consistency(tmp_path, training_data):
    df, log = _small(training_data, 150)
    res = train_and_evaluate(df, log, cv_folds=3)
    check = save_artifacts(res, tmp_path / "m.joblib", tmp_path / "r.json")
    assert check["identical_predictions"] and check["max_probability_difference"] == 0.0
    reloaded = load_model(tmp_path / "m.joblib", allow_training=False)
    texts = ["Brilliant explanations every week", "The exams were unfair and confusing"]
    assert (reloaded.predict(texts)["sentiment"].values == res.pipeline.predict(texts)).all()


def test_inference_on_unseen_text(model):
    out = model.predict(["The professor explains every concept clearly and is very helpful",
                         "The teacher is rude and never explains anything, worst class",
                         "hmm"])
    assert list(out.columns) == PRED_COLUMNS
    assert out.loc[0, "sentiment"] == "positive"
    assert out.loc[1, "sentiment"] == "negative"
    probs = out[["prob_negative", "prob_neutral", "prob_positive"]].sum(axis=1)
    assert np.allclose(probs, 1.0)
    assert out["sentiment_score"].between(-1, 1).all()


def test_negation_changes_prediction(model):
    out = model.predict(["The teacher is helpful", "The teacher is not helpful"])
    assert out.loc[0, "prob_positive"] > out.loc[1, "prob_positive"]
    assert out.loc[1, "prob_negative"] > out.loc[0, "prob_negative"]


def test_missing_artifact_without_training_is_explicit(tmp_path):
    m = load_model(tmp_path / "missing.joblib", allow_training=False)
    assert not m.available and m.status.source == "unavailable"
    out = m.predict(["anything"])
    assert out.loc[0, "sentiment"] == "unavailable" and bool(out.loc[0, "review_needed"])


def test_corrupt_artifact_handled(tmp_path):
    p = tmp_path / "bad.joblib"
    p.write_bytes(b"not a pickle")
    m = load_model(p, allow_training=False)
    assert not m.available and m.status.details["load_error"]
