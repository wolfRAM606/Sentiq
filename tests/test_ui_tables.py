"""Checks the contents of Streamlit tables (rendered on canvas in the browser) by running the real app
script through Streamlit's AppTest and driving the same widgets a user would."""
import os
from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def app():
    os.chdir(ROOT)
    at = st_testing.AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception
    return at


def _frames(at):
    return [d.value for d in at.dataframe]


def test_validation_tab_lists_excluded_records(app):
    app.switch_page("pages/2_Feedback_Explorer.py").run()
    ds = app.session_state["dataset"]
    excluded = [f for f in _frames(app) if "exclusion_reason" in f.columns]
    assert excluded, "excluded-records table missing"
    tab = excluded[0]
    assert len(tab) == ds.report.excluded_records == 5
    assert set(tab["exclusion_reason"]) == set(ds.report.exclusion_reasons)


def test_aspect_tables_unmatched_ambiguous_taxonomy(app):
    app.switch_page("pages/4_Aspect_Analysis.py").run()
    ds = app.session_state["dataset"]
    frames = _frames(app)
    summary = next(f for f in frames if {"aspect", "positive", "neutral", "negative", "reviews"} <= set(f.columns))
    assert (summary["positive"] + summary["neutral"] + summary["negative"] == summary["reviews"]).all()
    unmatched = next(f for f in frames if list(f.columns) == ["record_id", "review_text", "sentiment"])
    assert len(unmatched) == int((ds.result.reviews["aspect_count"] == 0).sum())
    ambiguous = next(f for f in frames if "term" in f.columns and "aspect_label" in f.columns)
    assert len(ambiguous) == len(ds.result.ambiguous)
    taxonomy = next(f for f in frames if "context-dependent terms" in f.columns)
    assert len(taxonomy) == 12


def test_effectiveness_tables_and_group_withholding(app):
    app.switch_page("pages/6_Effectiveness_Insights.py").run()
    ds = app.session_state["dataset"]
    frames = _frames(app)
    contrib = next(f for f in frames if {"record_id", "aspect_sentiment", "evidence", "review_text"} <= set(f.columns))
    chosen = app.selectbox(key="ei_aspect").value
    expected = ds.result.mentions[ds.result.mentions["aspect"] == chosen]
    assert set(contrib["record_id"]) == set(expected["record_id"])
    groups = next(f for f in frames if "indicator" in f.columns and "evidence" in f.columns)
    assert groups["reviews"].sum() == len(ds.result.reviews)
    assert groups["indicator"].notna().all()  # every course has >= 15 reviews in the demo data

def test_small_groups_are_withheld(app):
    # AppTest only exposes sidebar widgets on the entry page, so set the filter there, then switch.
    # Fall 2025 alone leaves every course group with fewer than 15 reviews -> indicators withheld
    app.multiselect(key="f_semester__v0").set_value(["Fall 2025"]).run()
    app.switch_page("pages/6_Effectiveness_Insights.py").run()
    assert not app.exception
    groups = next(f for f in _frames(app) if "indicator" in f.columns and "evidence" in f.columns)
    assert groups["reviews"].sum() == 42
    assert (groups["reviews"] < 15).all()
    assert groups["indicator"].isna().all()
    assert set(groups["evidence"]) == {"insufficient sample"}


def test_recommendation_evidence_ids_are_valid_reviews(app):
    from src.analytics.metrics import aspect_summary
    from src.analytics.recommendations import build_recommendations

    ds = app.session_state["dataset"]
    from src.ui.state import get_analyzer

    tax = get_analyzer().taxonomy
    recs = build_recommendations(aspect_summary(ds.result.mentions, ds.result.reviews, tax), ds.result.mentions, ds.result.reviews, tax)
    valid_ids = set(ds.result.reviews["record_id"])
    excluded_ids = set(ds.excluded["record_id"])
    for rec in recs:
        for ex in rec["examples"]:
            assert ex["record_id"] in valid_ids and ex["record_id"] not in excluded_ids


def test_model_lab_tables(app):
    app.switch_page("pages/3_Model_Lab.py").run()
    from src.models.predict import load_report

    report = load_report()
    feats = next(f for f in _frames(app) if list(f.columns) == ["feature", "weight"])
    assert feats["feature"].tolist() == [x["feature"] for x in report["top_features"]["positive"]]
    app.radio(key="ml_feat_cls").set_value("negative").run()
    feats = next(f for f in _frames(app) if list(f.columns) == ["feature", "weight"])
    assert feats["feature"].tolist() == [x["feature"] for x in report["top_features"]["negative"]]
    app.multiselect(key="ml_err_true").set_value(["neutral"]).run()
    errs = next(f for f in _frames(app) if "true label" in f.columns)
    assert len(errs) > 0 and set(errs["true label"]) == {"neutral"}
    comp = next(f for f in _frames(app) if "Test macro-F1" in f.columns)
    lr = comp[comp["Model"].str.startswith("Logistic")].iloc[0]
    assert lr["Test macro-F1"] == pytest.approx(report["models"]["logistic_regression"]["test"]["macro_f1"])
