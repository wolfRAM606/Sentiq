"""Column rules for the analysed-review CSV export (shared by the Streamlit app and the web API)."""
from __future__ import annotations

import pandas as pd


def export_frame(reviews: pd.DataFrame) -> pd.DataFrame:
    """Analysed reviews for CSV export (original text preserved, list columns flattened)."""
    cols = ["record_id", "review_text", "sentiment", "confidence", "review_needed", "aspects",
            "prob_positive", "prob_neutral", "prob_negative", "sentiment_score",
            "course", "instructor", "semester", "date", "rating", "source_label", "evidence_terms", "processed_text"]
    optional_meta = {"course", "instructor", "semester", "date", "rating", "source_label"}
    out = reviews[[c for c in cols if c in reviews.columns
                   and not (c in optional_meta and reviews[c].isna().all())]].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d") if "date" in out and pd.api.types.is_datetime64_any_dtype(out["date"]) else out.get("date")
    for c in ("prob_positive", "prob_neutral", "prob_negative", "confidence", "sentiment_score"):
        if c in out:
            out[c] = out[c].round(4)
    return out
