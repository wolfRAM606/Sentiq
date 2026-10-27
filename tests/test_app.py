"""Analytics, export and Streamlit application smoke tests."""
import os
import re
from pathlib import Path

import pandas as pd
import pytest

from src.analytics.metrics import aspect_summary, effectiveness_indicator, generate_insights, overview_kpis
from src.analytics.recommendations import build_recommendations
from src.analytics.reports import build_context, build_html, build_markdown

ROOT = Path(__file__).resolve().parent.parent


def test_effectiveness_formula():
    assert effectiveness_indicator(10, 0, 0) == 100
    assert effectiveness_indicator(0, 0, 10) == 0
    assert effectiveness_indicator(5, 0, 5) == 50
    assert effectiveness_indicator(2, 2, 0) == 75
    assert effectiveness_indicator(0, 0, 0) is None


def test_demo_pipeline_accounting(demo_analysis):
    valid, excluded, report, result = demo_analysis
    assert report.total_records == report.valid_records + report.excluded_records
    assert len(result.reviews) == report.valid_records
    assert result.reviews["review_text"].tolist() == valid["review_text"].tolist()
    assert result.reviews["sentiment"].isin(["positive", "neutral", "negative"]).all()
    assert set(result.mentions["record_id"]) <= set(result.reviews["record_id"])
    assert not result.mentions.duplicated(["record_id", "aspect_id"]).any()


def test_kpis_follow_filtered_subset(demo_analysis):
    *_, result = demo_analysis
    r = result.reviews
    subset = r[r["course"] == "CS305 Machine Learning"]
    k_all, k_sub = overview_kpis(r), overview_kpis(subset)
    assert k_sub["valid_reviews"] == len(subset) < k_all["valid_reviews"]
    assert sum(k_sub["counts"].values()) == len(subset)
    s_sub = aspect_summary(result.mentions[result.mentions["record_id"].isin(subset["record_id"])], subset)
    assert s_sub["reviews"].sum() == result.mentions["record_id"].isin(subset["record_id"]).sum()
    # aspect summary restricts mentions to the review subset even if given all mentions
    assert aspect_summary(result.mentions, subset)["reviews"].sum() == s_sub["reviews"].sum()


def test_recommendations_traceable(demo_analysis, analyzer):
    *_, result = demo_analysis
    summary = aspect_summary(result.mentions, result.reviews, analyzer.taxonomy)
    recs = build_recommendations(summary, result.mentions, result.reviews, analyzer.taxonomy)
    assert recs, "demo data should support at least one recommendation"
    ids = set(result.reviews["record_id"])
    for rec in recs:
        assert rec["supporting_reviews"] >= 3 and rec["examples"]
        assert all(e["record_id"] in ids for e in rec["examples"])
        row = summary[summary["aspect_id"] == rec["aspect_id"]].iloc[0]
        expected = row["negative"] if rec["kind"] == "issue" else row["positive"]
        assert rec["supporting_reviews"] == expected


def test_no_recommendations_without_evidence(analyzer):
    empty_mentions = pd.DataFrame(columns=["record_id", "aspect_id", "aspect", "aspect_sentiment", "aspect_review_needed"])
    reviews = pd.DataFrame({"record_id": [1], "review_text": ["ok"]})
    assert build_recommendations(aspect_summary(empty_mentions, reviews), empty_mentions, reviews, analyzer.taxonomy) == []


def test_reports_and_export(demo_analysis, analyzer):
    from src.ui.state import export_frame

    valid, excluded, report, result = demo_analysis
    summary = aspect_summary(result.mentions, result.reviews, analyzer.taxonomy)
    ctx = build_context("Synthetic demonstration dataset", "demo", report.as_dict(), overview_kpis(result.reviews, len(excluded)),
                        summary, generate_insights(result.reviews, summary),
                        build_recommendations(summary, result.mentions, result.reviews, analyzer.taxonomy), None, "all")
    html = build_html(ctx)
    md = build_markdown(ctx)
    assert "Sentiq" in html and "synthetic demonstration dataset" in html.lower()
    assert "An Automated Text Mining Dashboard" in md
    assert "<script" not in html.lower()
    out = export_frame(result.reviews)
    assert len(out) == len(result.reviews)
    assert out["review_text"].tolist() == result.reviews["review_text"].tolist()
    for col in ("sentiment", "prob_positive", "aspects", "processed_text"):
        assert col in out.columns


def test_no_api_key_dependency():
    pattern = re.compile(r"(_API_KEY|api_key|st\.secrets|requests\.(get|post)|urllib\.request|http\.client)")
    for path in list((ROOT / "src").rglob("*.py")) + list((ROOT / "pages").glob("*.py")) + [ROOT / "app.py"]:
        assert not pattern.search(path.read_text(encoding="utf-8")), path


# ---------------------------------------------------------------------------
# Streamlit AppTest smoke tests
# ---------------------------------------------------------------------------
st_testing = pytest.importorskip("streamlit.testing.v1")


@pytest.fixture()
def app():
    os.chdir(ROOT)
    at = st_testing.AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception, at.exception
    return at


PAGES = ["pages/1_Overview.py", "pages/2_Feedback_Explorer.py", "pages/3_Model_Lab.py", "pages/4_Aspect_Analysis.py",
         "pages/5_Topics_and_Keywords.py", "pages/6_Effectiveness_Insights.py", "pages/7_Methodology_and_Reports.py"]


def test_startup_loads_demo(app):
    text = " ".join(m.value for m in app.markdown)
    assert "Synthetic demo data" in text or "synthetic demonstration dataset" in text.lower()
    assert app.session_state["dataset"].kind == "demo"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders(app, page):
    app.switch_page(page).run()
    assert not app.exception, f"{page}: {app.exception}"


def test_sentiment_filter_updates_overview(app):
    total = len(app.session_state["dataset"].result.reviews)
    app.multiselect(key="f_sentiment__v0").set_value(["negative"]).run()
    assert not app.exception
    chips = " ".join(m.value for m in app.markdown)
    n_neg = int((app.session_state["dataset"].result.reviews["sentiment"] == "negative").sum())
    assert f"{n_neg} of {total} valid reviews" in chips


def test_clear_filters_resets_widgets(app):
    """Regression: clearing must reset the widgets too, not only the stored values, otherwise
    stale selections are re-applied on the next interaction."""
    total = len(app.session_state["dataset"].result.reviews)
    app.multiselect(key="f_course__v0").set_value(["CS305 Machine Learning"]).run()
    clear = [b for b in app.sidebar.button if b.label == "Clear filters"]
    assert clear, "Clear filters button should appear once a filter is active"
    clear[0].click().run()
    assert not app.exception
    assert app.multiselect(key="f_course__v1").value == []
    app.multiselect(key="f_instructor__v1").set_value(["Instructor C"]).run()
    chips = " ".join(m.value for m in app.markdown)
    n = int((app.session_state["dataset"].result.reviews["instructor"] == "Instructor C").sum())
    assert f"{n} of {total} valid reviews" in chips


def test_filter_to_empty_selection_shows_empty_state(app):
    app.multiselect(key="f_course__v0").set_value(["CS201 Data Structures"]).run()
    app.multiselect(key="f_semester__v0").set_value(["Fall 2025"]).run()
    app.multiselect(key="f_aspect__v0").set_value(["(no aspect detected)"]).run()
    assert not app.exception
    for page in PAGES:
        app.switch_page(page).run()
        assert not app.exception, page


def test_single_review_analysis(app):
    app.switch_page("pages/2_Feedback_Explorer.py").run()
    app.text_area(key="fx_single").input("The lectures were clear but the assignments were confusing.")
    app.button(key="fx_single_btn").click().run()
    assert not app.exception
    assert any("Predicted sentiment" in m.value for m in app.markdown)
    aspects = next(d.value for d in app.dataframe if "clause sentiment" in d.value.columns)
    assert aspects["aspect"].is_unique  # one row per aspect, most confident clause kept
    assert {"Teaching clarity & explanation", "Assignments & workload"} <= set(aspects["aspect"])
