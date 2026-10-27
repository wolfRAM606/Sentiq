"""The showcase CSV must keep exercising every feature used in the demo script (docs/DEMO_SCRIPT.md)."""
from pathlib import Path

from src.analytics.metrics import aspect_summary
from src.analytics.pipeline import analyze_reviews
from src.analytics.recommendations import build_recommendations
from src.analytics.topics import discover_topics
from src.data.loader import read_csv_path
from src.data.schema_mapping import suggest_mapping
from src.data.validation import prepare_dataset

SHOWCASE = Path(__file__).resolve().parent.parent / "data" / "sample" / "sentiq_showcase_feedback.csv"


def test_showcase_covers_every_feature(model, analyzer):
    loaded = read_csv_path(SHOWCASE)
    mapping = suggest_mapping(list(loaded.frame.columns))
    assert all(mapping[r] for r in ("text", "course", "instructor", "date", "semester", "rating", "label"))
    valid, excluded, report = prepare_dataset(loaded.frame, mapping)
    assert len(report.exclusion_reasons) == 3 and report.excluded_records == 6
    assert report.truncated_reviews == 1 and report.unparseable_dates == 1 and report.unparseable_ratings == 1
    res = analyze_reviews(valid, model, analyzer)
    summary = aspect_summary(res.mentions, res.reviews, analyzer.taxonomy)
    assert len(summary) == 12 and summary["enough_evidence"].all()
    kinds = {r["kind"] for r in build_recommendations(summary, res.mentions, res.reviews, analyzer.taxonomy)}
    assert kinds == {"issue", "strength"}
    sizes = res.reviews.groupby("course").size()
    assert (sizes < 15).sum() == 1 and (sizes >= 15).sum() == 4
    assert discover_topics(res.reviews, 5).ok
    assert (res.reviews["aspect_count"] == 0).any() and len(res.ambiguous) > 0
    assert res.reviews["date"].notna().sum() > 100 and res.reviews["semester"].nunique() == 2
