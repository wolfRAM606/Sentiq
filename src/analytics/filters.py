"""One filter implementation shared by the Streamlit app and the web API."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

NO_ASPECT = "(no aspect detected)"
CONFIDENCE_OPTIONS = ("all", "confident", "review")


@dataclass
class Filters:
    course: list[str] = field(default_factory=list)
    instructor: list[str] = field(default_factory=list)
    semester: list[str] = field(default_factory=list)
    sentiment: list[str] = field(default_factory=list)
    aspect: list[str] = field(default_factory=list)      # aspect labels, may include NO_ASPECT
    confidence: str = "all"                              # "all" | "confident" | "review"
    date_from: date | None = None
    date_to: date | None = None

    def is_active(self) -> bool:
        return bool(self.course or self.instructor or self.semester or self.sentiment or self.aspect
                    or self.confidence != "all" or self.date_from or self.date_to)


def apply_filters(reviews: pd.DataFrame, mentions: pd.DataFrame, f: Filters) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the review and aspect-mention subsets selected by ``f``.

    Reviews without a date are kept when a date range is set, because excluding them would silently drop
    feedback that simply has no timestamp.
    """
    r = reviews
    mask = pd.Series(True, index=r.index)
    for values, col in ((f.course, "course"), (f.instructor, "instructor"), (f.semester, "semester")):
        if values:
            mask &= r[col].astype(str).isin(values)
    if f.sentiment:
        mask &= r["sentiment"].isin(f.sentiment)
    if f.aspect:
        labels = [a for a in f.aspect if a != NO_ASPECT]
        ids_with = set(mentions.loc[mentions["aspect"].isin(labels), "record_id"]) if labels else set()
        aspect_mask = r["record_id"].isin(ids_with)
        if NO_ASPECT in f.aspect:
            aspect_mask |= r["aspect_count"] == 0
        mask &= aspect_mask
    if f.confidence == "confident":
        mask &= ~r["review_needed"].astype(bool)
    elif f.confidence == "review":
        mask &= r["review_needed"].astype(bool)
    if f.date_from or f.date_to:
        lo = pd.Timestamp(f.date_from) if f.date_from else pd.Timestamp.min
        hi = pd.Timestamp(f.date_to) + pd.Timedelta(days=1) if f.date_to else pd.Timestamp.max
        mask &= r["date"].isna() | ((r["date"] >= lo) & (r["date"] < hi))
    out = r[mask]
    return out, mentions[mentions["record_id"].isin(out["record_id"])]
