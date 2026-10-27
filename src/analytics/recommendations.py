"""Deterministic, evidence-linked recommendations.

A recommendation is produced only when enough independent reviews support it:
* Issue: at least ``MIN_ASPECT_MENTIONS`` negative aspect mentions AND a negative share >= 35%.
* Strength: at least ``MIN_ASPECT_MENTIONS`` positive aspect mentions AND a positive share >= 60%.
Every recommendation carries its counts, example evidence and caveats.
"""
from __future__ import annotations

import pandas as pd

from src.config import MIN_ASPECT_MENTIONS

ISSUE_NEG_SHARE = 0.35
STRENGTH_POS_SHARE = 0.60
SMALL_SAMPLE = 10


def build_recommendations(summary: pd.DataFrame, mentions: pd.DataFrame, reviews: pd.DataFrame, taxonomy,
                          max_examples: int = 3) -> list[dict]:
    if summary.empty:
        return []
    tax = taxonomy.by_id
    active = mentions[mentions["record_id"].isin(reviews["record_id"])]
    text_by_id = reviews.set_index("record_id")["review_text"]
    recs = []
    for _, row in summary.iterrows():
        aid, n = row["aspect_id"], int(row["reviews"])
        for kind, count, share, threshold, sentiment in (
            ("issue", int(row["negative"]), row["negative_share"], ISSUE_NEG_SHARE, "negative"),
            ("strength", int(row["positive"]), row["positive_share"], STRENGTH_POS_SHARE, "positive"),
        ):
            if count < MIN_ASPECT_MENTIONS or share < threshold:
                continue
            ev = active[(active["aspect_id"] == aid) & (active["aspect_sentiment"] == sentiment)]
            ev = ev.sort_values(f"aspect_prob_{sentiment}", ascending=False).drop_duplicates("record_id")
            examples = [{"record_id": int(r.record_id), "evidence": r.evidence, "review": text_by_id.get(r.record_id, ""),
                         "probability": float(getattr(r, f"aspect_prob_{sentiment}"))}
                        for r in ev.head(max_examples).itertuples()]
            caveats = []
            if n < SMALL_SAMPLE:
                caveats.append(f"Small sample: only {n} reviews mention this aspect.")
            uncertain = int(ev["aspect_review_needed"].fillna(True).astype(bool).sum())
            if count and uncertain / count > 0.3:
                caveats.append(f"{uncertain} of the {count} supporting predictions are low-confidence.")
            if (ev["match_type"] == "general (no specific aspect)").any():
                caveats.append("Some matches are general statements without a specific teaching aspect.")
            caveats.append("Based on lexicon matches and predicted sentiment; verify by reading the example reviews.")
            asp = tax.get(aid)
            recs.append({
                "kind": kind, "aspect_id": aid, "aspect": row["aspect"],
                "priority": ("high" if share >= 0.5 and n >= SMALL_SAMPLE else "medium") if kind == "issue" else "keep",
                "headline": (f"{count} of {n} reviews raise concerns about {row['aspect'].lower()}" if kind == "issue"
                             else f"{count} of {n} reviews praise {row['aspect'].lower()}"),
                "supporting_reviews": count, "aspect_reviews": n, "share": float(share),
                "action": (asp.action_negative if kind == "issue" else asp.action_positive) if asp else "",
                "examples": examples, "caveats": caveats,
            })
    order = {"high": 0, "medium": 1, "keep": 2}
    recs.sort(key=lambda r: (order[r["priority"]], -r["supporting_reviews"]))
    return recs
