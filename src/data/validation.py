"""Validation and preparation of mapped feedback data.

Every input record is accounted for: it is either included for analysis or
listed in the exclusions table with an explicit reason.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field

import pandas as pd

from src.config import MAX_REVIEW_CHARS

STANDARD_COLUMNS = ["record_id", "review_text", "course", "instructor", "date", "semester", "rating", "source_label"]

EXCLUSION_EMPTY = "Empty or whitespace-only review"
EXCLUSION_DUPLICATE = "Duplicate of an earlier review (same normalised text and metadata)"
EXCLUSION_NO_LETTERS = "Review contains no alphabetic characters"


class ValidationError(ValueError):
    """Raised with a user-facing message when mapped data cannot be analysed."""


@dataclass
class ValidationReport:
    total_records: int = 0
    valid_records: int = 0
    excluded_records: int = 0
    exclusion_reasons: dict[str, int] = field(default_factory=dict)
    truncated_reviews: int = 0
    unparseable_dates: int = 0
    unparseable_ratings: int = 0
    missing_metadata: dict[str, int] = field(default_factory=dict)
    mapped_columns: dict[str, str | None] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def _clean_meta(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    return s.mask(s.isin(["", "nan", "NaN", "None", "null", "NULL", "N/A", "n/a"]), None)


def prepare_dataset(frame: pd.DataFrame, mapping: dict[str, str | None]) -> tuple[pd.DataFrame, pd.DataFrame, ValidationReport]:
    """Return (valid_records, excluded_records, report)."""
    text_col = mapping.get("text")
    if not text_col:
        raise ValidationError("Please choose the column that contains the review text.")
    if text_col not in frame.columns:
        raise ValidationError(f"Column '{text_col}' was not found in the file.")
    for role, col in mapping.items():
        if col and col not in frame.columns:
            raise ValidationError(f"Mapped column '{col}' for {role} was not found in the file.")

    report = ValidationReport(total_records=len(frame), mapped_columns=dict(mapping))
    out = pd.DataFrame(index=frame.index)
    out["record_id"] = range(1, len(frame) + 1)
    raw_text = frame[text_col].fillna("").astype(str)
    out["review_text"] = raw_text

    over = raw_text.str.len() > MAX_REVIEW_CHARS
    report.truncated_reviews = int(over.sum())
    if report.truncated_reviews:
        report.warnings.append(
            f"{report.truncated_reviews} review(s) exceed {MAX_REVIEW_CHARS:,} characters; only the first "
            f"{MAX_REVIEW_CHARS:,} characters are analysed (original text is preserved in exports)."
        )

    for role in ["course", "instructor", "semester", "source_label"]:
        src_role = "label" if role == "source_label" else role
        col = mapping.get(src_role)
        out[role] = _clean_meta(frame[col]) if col else None

    date_col = mapping.get("date")
    if date_col:
        raw = _clean_meta(frame[date_col])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(raw, errors="coerce", format="mixed", dayfirst=False)
        report.unparseable_dates = int((raw.notna() & parsed.isna()).sum())
        out["date"] = parsed
        if report.unparseable_dates:
            report.warnings.append(f"{report.unparseable_dates} date value(s) could not be parsed and were left blank.")
    else:
        out["date"] = pd.NaT

    rating_col = mapping.get("rating")
    if rating_col:
        raw = _clean_meta(frame[rating_col])
        parsed = pd.to_numeric(raw.str.replace(",", ".", regex=False), errors="coerce")
        report.unparseable_ratings = int((raw.notna() & parsed.isna()).sum())
        out["rating"] = parsed
        if report.unparseable_ratings:
            report.warnings.append(f"{report.unparseable_ratings} rating value(s) were not numeric and were left blank.")
    else:
        out["rating"] = float("nan")

    for role in ["course", "instructor", "semester", "date", "rating"]:
        if mapping.get(role):
            report.missing_metadata[role] = int(out[role].isna().sum())

    # --- exclusions --------------------------------------------------------
    reason = pd.Series(None, index=out.index, dtype=object)
    stripped = raw_text.str.strip()
    reason[stripped == ""] = EXCLUSION_EMPTY
    no_letters = (stripped != "") & ~stripped.str.contains(r"[A-Za-zÀ-ɏ]", regex=True)
    reason[no_letters & reason.isna()] = EXCLUSION_NO_LETTERS

    key_cols = [c for c in ["course", "instructor", "semester"] if mapping.get(c)]
    dup_key = raw_text.map(normalise_text)
    if key_cols:
        dup_key = dup_key + "||" + out[key_cols].astype(str).agg("|".join, axis=1)
    candidates = reason.isna()
    dup = dup_key[candidates].duplicated(keep="first")
    reason[dup[dup].index] = EXCLUSION_DUPLICATE

    out["exclusion_reason"] = reason
    excluded = out[reason.notna()].copy()
    valid = out[reason.isna()].drop(columns=["exclusion_reason"]).copy()

    report.valid_records = len(valid)
    report.excluded_records = len(excluded)
    report.exclusion_reasons = {k: int(v) for k, v in reason.value_counts().items()}
    if report.valid_records + report.excluded_records != report.total_records:  # defensive accounting check
        raise ValidationError("Internal record accounting mismatch.")
    if report.valid_records == 0:
        raise ValidationError("No valid reviews remain after validation. Check that the correct text column is selected.")
    return valid.reset_index(drop=True), excluded.reset_index(drop=True), report
