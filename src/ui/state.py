"""Session state, cached resources and global filters shared by all pages."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.analytics.pipeline import AnalysisResult, analyze_reviews
from src.config import DEMO_DATASET, TAXONOMY_PATH
from src.data.loader import read_csv_path
from src.data.schema_mapping import suggest_mapping
from src.data.validation import ValidationReport, prepare_dataset
from src.models.predict import SentimentModel, load_model, load_report
from src.nlp.aspects import AspectAnalyzer, load_taxonomy
from src.nlp.preprocessing import get_nlp

FILTER_KEYS = ["f_course", "f_instructor", "f_semester", "f_sentiment", "f_aspect", "f_confidence", "f_dates"]


@dataclass
class ActiveDataset:
    name: str
    kind: str                     # "demo" | "upload"
    valid: pd.DataFrame
    excluded: pd.DataFrame
    report: ValidationReport
    result: AnalysisResult
    key: str


@st.cache_resource(show_spinner="Loading the trained sentiment model…")
def get_model() -> SentimentModel:
    return load_model()


@st.cache_resource(show_spinner="Loading spaCy and the aspect taxonomy…")
def _analyzer(taxonomy_mtime: float) -> AspectAnalyzer:
    return AspectAnalyzer(get_nlp(), load_taxonomy())


def get_analyzer() -> AspectAnalyzer:
    return _analyzer(TAXONOMY_PATH.stat().st_mtime)


@st.cache_data(show_spinner=False)
def get_training_report(_model_trained_at: str | None) -> dict | None:
    return load_report()


def frame_key(df: pd.DataFrame) -> str:
    h = hashlib.sha256(pd.util.hash_pandas_object(df.astype(str), index=False).values.tobytes()).hexdigest()
    return h[:16]


@st.cache_data(show_spinner=False, max_entries=8)
def _analyze_cached(_valid: pd.DataFrame, data_key: str, model_key: str, taxonomy_mtime: float) -> AnalysisResult:
    return analyze_reviews(_valid, get_model(), get_analyzer())


def analyze(valid: pd.DataFrame, progress=None) -> AnalysisResult:
    model = get_model()
    key = frame_key(valid)
    model_key = str(model.status.trained_at)
    if progress:
        progress(0.05, "Preparing analysis")
    result = _analyze_cached(valid, key, model_key, TAXONOMY_PATH.stat().st_mtime)
    if progress:
        progress(1.0, "Analysis complete")
    return result


def load_demo() -> ActiveDataset:
    loaded = read_csv_path(DEMO_DATASET)
    mapping = suggest_mapping(list(loaded.frame.columns))
    valid, excluded, report = prepare_dataset(loaded.frame, mapping)
    result = analyze(valid)
    return ActiveDataset("Synthetic demonstration dataset", "demo", valid, excluded, report, result, frame_key(valid))


def set_active(ds: ActiveDataset) -> None:
    st.session_state["dataset"] = ds
    for k in FILTER_KEYS:
        st.session_state.pop(k, None)


def active() -> ActiveDataset:
    if "dataset" not in st.session_state:
        st.session_state["dataset"] = load_demo()
    return st.session_state["dataset"]


# ---------------------------------------------------------------------------
# Global filters (rendered in the sidebar on every page)
# ---------------------------------------------------------------------------
def _options(series: pd.Series) -> list[str]:
    return sorted(series.dropna().astype(str).unique().tolist())


def render_filters(ds: ActiveDataset) -> None:
    reviews = ds.result.reviews
    sb = st.sidebar
    sb.markdown("<div class='sq-eyebrow' style='margin-top:.6rem'>Filters</div>", unsafe_allow_html=True)
    for key, col, label in (("f_course", "course", "Course"), ("f_instructor", "instructor", "Instructor"),
                            ("f_semester", "semester", "Semester")):
        opts = _options(reviews[col])
        if opts:
            sb.multiselect(label, opts, key=key, placeholder="All")
    sb.multiselect("Predicted sentiment", ["positive", "neutral", "negative"], key="f_sentiment", placeholder="All")
    aspects = [a.label for a in get_analyzer().taxonomy.aspects]
    sb.multiselect("Mentions aspect", aspects + ["(no aspect detected)"], key="f_aspect", placeholder="Any")
    sb.radio("Prediction confidence", ["All", "Confident only", "Review needed only"], key="f_confidence", horizontal=False)
    dated = reviews["date"].dropna()
    if len(dated) >= 2 and dated.min().date() != dated.max().date():
        lo, hi = dated.min().date(), dated.max().date()
        sb.date_input("Date range", value=(lo, hi), min_value=lo, max_value=hi, key="f_dates")
    if any(st.session_state.get(k) for k in FILTER_KEYS if k not in ("f_confidence", "f_dates")) or \
            st.session_state.get("f_confidence", "All") != "All":
        if sb.button("Clear filters", width="stretch"):
            for k in FILTER_KEYS:
                st.session_state.pop(k, None)
            st.rerun()


def filtered(ds: ActiveDataset) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (reviews, mentions) for the current filter selection. All pages use this."""
    r = ds.result.reviews
    m = ds.result.mentions
    mask = pd.Series(True, index=r.index)
    for key, col in (("f_course", "course"), ("f_instructor", "instructor"), ("f_semester", "semester")):
        sel = st.session_state.get(key)
        if sel:
            mask &= r[col].astype(str).isin(sel)
    sel = st.session_state.get("f_sentiment")
    if sel:
        mask &= r["sentiment"].isin(sel)
    sel = st.session_state.get("f_aspect")
    if sel:
        want_none = "(no aspect detected)" in sel
        labels = [s for s in sel if s != "(no aspect detected)"]
        ids_with = set(m.loc[m["aspect"].isin(labels), "record_id"]) if labels else set()
        aspect_mask = r["record_id"].isin(ids_with)
        if want_none:
            aspect_mask |= r["aspect_count"] == 0
        mask &= aspect_mask
    conf = st.session_state.get("f_confidence", "All")
    if conf == "Confident only":
        mask &= ~r["review_needed"].astype(bool)
    elif conf == "Review needed only":
        mask &= r["review_needed"].astype(bool)
    dates = st.session_state.get("f_dates")
    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        lo, hi = pd.Timestamp(dates[0]), pd.Timestamp(dates[1]) + pd.Timedelta(days=1)
        mask &= r["date"].isna() | ((r["date"] >= lo) & (r["date"] < hi))
    reviews = r[mask]
    mentions = m[m["record_id"].isin(reviews["record_id"])]
    return reviews, mentions


def filter_summary(ds: ActiveDataset, reviews: pd.DataFrame) -> str:
    total = len(ds.result.reviews)
    return f"{len(reviews)} of {total} valid reviews" if len(reviews) != total else f"all {total} valid reviews"


def export_frame(reviews: pd.DataFrame) -> pd.DataFrame:
    """Analysed reviews for CSV export (original text preserved, list columns flattened)."""
    cols = ["record_id", "review_text", "course", "instructor", "semester", "date", "rating", "source_label",
            "sentiment", "prob_positive", "prob_neutral", "prob_negative", "confidence", "review_needed",
            "sentiment_score", "aspects", "evidence_terms", "processed_text"]
    out = reviews[[c for c in cols if c in reviews.columns]].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d") if "date" in out and pd.api.types.is_datetime64_any_dtype(out["date"]) else out.get("date")
    for c in ("prob_positive", "prob_neutral", "prob_negative", "confidence", "sentiment_score"):
        if c in out:
            out[c] = out[c].round(4)
    return out


@st.cache_data(show_spinner="Discovering topics…", max_entries=32)
def _topics_cached(_reviews: pd.DataFrame, ids_key: str, data_key: str, k: int):
    from src.analytics.topics import discover_topics

    return discover_topics(_reviews, k)


def topics_for(ds: ActiveDataset, reviews: pd.DataFrame, k: int):
    ids_key = hashlib.sha1(",".join(map(str, reviews["record_id"].tolist())).encode()).hexdigest()
    return _topics_cached(reviews, ids_key, ds.key, k)
