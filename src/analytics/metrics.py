"""Dataset-level metrics, the effectiveness indicator and evidence-backed insights."""
from __future__ import annotations

import pandas as pd

from src.config import LABELS, MIN_ASPECT_MENTIONS, MIN_SAMPLE_WARNING


def sentiment_counts(reviews: pd.DataFrame) -> dict[str, int]:
    vc = reviews["sentiment"].value_counts() if len(reviews) else pd.Series(dtype=int)
    return {lab: int(vc.get(lab, 0)) for lab in LABELS}


def effectiveness_indicator(pos: int, neu: int, neg: int) -> float | None:
    """Sentiment-derived feedback indicator on a 0-100 scale.

    score = 100 × (positive proportion + 0.5 × neutral proportion)
          = 50 × positive proportion + 50 × (1 − negative proportion)
    It is NOT an objective measure of teaching quality.
    """
    n = pos + neu + neg
    if n == 0:
        return None
    return 100.0 * (pos + 0.5 * neu) / n


def overview_kpis(reviews: pd.DataFrame, excluded_count: int = 0) -> dict:
    counts = sentiment_counts(reviews)
    n = len(reviews)
    scored = reviews[reviews["sentiment"].isin(LABELS)] if n else reviews
    return {
        "valid_reviews": n,
        "excluded_records": excluded_count,
        "counts": counts,
        "shares": {k: (v / n if n else 0.0) for k, v in counts.items()},
        "avg_sentiment_score": float(scored["sentiment_score"].mean()) if len(scored) else None,
        "effectiveness": effectiveness_indicator(counts["positive"], counts["neutral"], counts["negative"]),
        "review_needed": int(reviews["review_needed"].sum()) if n else 0,
        "with_aspect": int((reviews["aspect_count"] > 0).sum()) if n else 0,
        "avg_words": float(reviews["word_count"].mean()) if n else 0.0,
    }


def aspect_summary(mentions: pd.DataFrame, reviews: pd.DataFrame, taxonomy=None) -> pd.DataFrame:
    """Per-aspect counts using clause-level aspect sentiment."""
    cols = ["aspect_id", "aspect", "reviews", "coverage", "positive", "neutral", "negative", "uncertain",
            "positive_share", "negative_share", "aspect_score", "enough_evidence"]
    active = mentions[mentions["record_id"].isin(reviews["record_id"])] if len(mentions) else mentions
    if active.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for (aid, label), g in active.groupby(["aspect_id", "aspect"]):
        n = len(g)
        pos = int((g["aspect_sentiment"] == "positive").sum())
        neu = int((g["aspect_sentiment"] == "neutral").sum())
        neg = int((g["aspect_sentiment"] == "negative").sum())
        rows.append({"aspect_id": aid, "aspect": label, "reviews": n, "coverage": n / max(len(reviews), 1),
                     "positive": pos, "neutral": neu, "negative": neg,
                     "uncertain": int(g["aspect_review_needed"].fillna(True).astype(bool).sum()),
                     "positive_share": pos / n, "negative_share": neg / n,
                     "aspect_score": effectiveness_indicator(pos, neu, neg) if (pos + neu + neg) else None,
                     "enough_evidence": n >= MIN_ASPECT_MENTIONS})
    out = pd.DataFrame(rows, columns=cols).sort_values("reviews", ascending=False).reset_index(drop=True)
    if taxonomy is not None:
        order = [a.id for a in taxonomy.aspects]
        out["_o"] = out["aspect_id"].map({a: i for i, a in enumerate(order)})
        out = out.sort_values(["reviews", "_o"], ascending=[False, True]).drop(columns="_o").reset_index(drop=True)
    return out


def most_positive_negative(summary: pd.DataFrame) -> tuple[dict | None, dict | None]:
    eligible = summary[summary["enough_evidence"]] if len(summary) else summary
    if eligible.empty:
        return None, None
    best = eligible.sort_values(["positive_share", "reviews"], ascending=[False, False]).iloc[0].to_dict()
    worst = eligible.sort_values(["negative_share", "reviews"], ascending=[False, False]).iloc[0].to_dict()
    if worst["negative"] == 0:
        worst = None
    if best["positive"] == 0:
        best = None
    return best, worst


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def generate_insights(reviews: pd.DataFrame, summary: pd.DataFrame) -> list[dict]:
    """Deterministic, evidence-backed statements. Each insight carries its numbers."""
    insights: list[dict] = []
    n = len(reviews)
    if n == 0:
        return insights
    counts = sentiment_counts(reviews)
    dominant = max(counts, key=counts.get)
    insights.append({"kind": "sentiment", "tone": dominant,
                     "text": f"{dominant.capitalize()} feedback is the largest group: {counts[dominant]} of {n} reviews "
                             f"({_pct(counts[dominant] / n)}) were predicted {dominant}."})
    if n < MIN_SAMPLE_WARNING:
        insights.append({"kind": "caution", "tone": "neutral",
                         "text": f"Only {n} reviews are in the current selection — treat all patterns as indicative, not conclusive."})
    best, worst = most_positive_negative(summary)
    if worst is not None:
        insights.append({"kind": "aspect", "tone": "negative",
                         "text": f"{worst['aspect']} draws the highest share of negative comments: {int(worst['negative'])} of "
                                 f"{int(worst['reviews'])} reviews mentioning it ({_pct(worst['negative_share'])})."})
    if best is not None and (worst is None or best["aspect_id"] != worst["aspect_id"]):
        insights.append({"kind": "aspect", "tone": "positive",
                         "text": f"{best['aspect']} is the most positively discussed aspect: {int(best['positive'])} of "
                                 f"{int(best['reviews'])} mentioning reviews ({_pct(best['positive_share'])}) are positive."})
    if len(summary):
        top = summary.iloc[0]
        insights.append({"kind": "coverage", "tone": "info",
                         "text": f"The most discussed aspect is {top['aspect']}, mentioned in {int(top['reviews'])} reviews "
                                 f"({_pct(top['coverage'])} of the selection)."})
    no_aspect = int((reviews["aspect_count"] == 0).sum())
    if no_aspect:
        insights.append({"kind": "coverage", "tone": "info",
                         "text": f"{no_aspect} reviews ({_pct(no_aspect / n)}) did not match any teaching aspect in the lexicon; "
                                 "they are listed as unmatched on the Aspect Analysis page."})
    rn = int(reviews["review_needed"].sum())
    if rn:
        insights.append({"kind": "uncertainty", "tone": "neutral",
                         "text": f"{rn} predictions ({_pct(rn / n)}) are low-confidence and flagged for human review."})
    if reviews["date"].notna().sum() >= 10:
        dated = reviews.dropna(subset=["date"]).sort_values("date")
        half = len(dated) // 2
        first, second = dated.iloc[:half], dated.iloc[half:]
        a = (first["sentiment"] == "positive").mean()
        b = (second["sentiment"] == "positive").mean()
        if abs(a - b) >= 0.1 and min(len(first), len(second)) >= 5:
            direction = "higher" if b > a else "lower"
            insights.append({"kind": "trend", "tone": "positive" if b > a else "negative",
                             "text": f"The positive share is {direction} in the later half of dated reviews ({_pct(b)} vs {_pct(a)}). "
                                     "This is descriptive only and does not establish a cause."})
    return insights
