"""Sentiq web API: the same NLP/ML core as the Streamlit app, exposed over HTTP for the web interface.

Run from the project root:  uvicorn api.main:app --port 8000
The built web interface (web/dist) is served from the same process when present.
"""
from __future__ import annotations

import logging
import platform
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.serialize import clean, records
from api.store import Dataset, Store, Upload
from src.analytics.exports import export_frame
from src.analytics.filters import NO_ASPECT, Filters, apply_filters
from src.analytics.metrics import aspect_summary, effectiveness_indicator, generate_insights, most_positive_negative, overview_kpis, sentiment_counts
from src.analytics.pipeline import analyze_reviews
from src.analytics.recommendations import build_recommendations
from src.analytics.reports import build_context, build_html, build_markdown
from src.analytics.topics import discover_topics
from src.config import (ACADEMIC_TITLE, DEMO_DATASET, LOW_CONFIDENCE_MARGIN, LOW_CONFIDENCE_PROB, MAX_ROWS, MAX_UPLOAD_MB,
                        MIN_ASPECT_MENTIONS, MIN_SAMPLE_WARNING, MIN_TOPIC_REVIEWS, PRODUCT_DESCRIPTOR, PRODUCT_NAME, ROOT, TAGLINE)
from src.data.loader import DataLoadError, read_csv_bytes, read_csv_path
from src.data.schema_mapping import OPTIONAL_ROLES, ROLE_LABELS, guess_text_column, suggest_mapping
from src.data.validation import ValidationError, prepare_dataset
from src.models.predict import load_model, load_report
from src.nlp.aspects import AspectAnalyzer, load_taxonomy
from src.nlp.keywords import keyword_table, noun_phrase_table, reviews_with_term
from src.nlp.preprocessing import clean_raw, get_nlp, process_texts

logger = logging.getLogger("sentiq.api")
GROUP_MIN = 15
WEB_DIST = ROOT / "web" / "dist"

app = FastAPI(title=f"{PRODUCT_NAME} API", version="2.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
store = Store()


# ---------------------------------------------------------------------------
# shared resources
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def model():
    return load_model()


_analyzer_cache: dict[float, AspectAnalyzer] = {}


def analyzer() -> AspectAnalyzer:
    from src.config import TAXONOMY_PATH

    mtime = TAXONOMY_PATH.stat().st_mtime
    if mtime not in _analyzer_cache:
        _analyzer_cache.clear()
        _analyzer_cache[mtime] = AspectAnalyzer(get_nlp(), load_taxonomy())
    return _analyzer_cache[mtime]


def demo() -> Dataset:
    ds = store.get_dataset("demo")
    if ds is None:
        loaded = read_csv_path(DEMO_DATASET)
        valid, excluded, report = prepare_dataset(loaded.frame, suggest_mapping(list(loaded.frame.columns)))
        ds = Dataset("demo", "Synthetic demonstration dataset", "demo", valid, excluded, report,
                     analyze_reviews(valid, model(), analyzer()))
        store.put_dataset(ds)
    return ds


def dataset(did: str) -> Dataset:
    if did == "demo":
        return demo()
    ds = store.get_dataset(did)
    if ds is None:
        raise HTTPException(404, "This dataset is no longer in memory. Uploaded data is kept only temporarily; please upload it again.")
    return ds


# ---------------------------------------------------------------------------
# filters (query parameters shared by every analysis endpoint)
# ---------------------------------------------------------------------------
def make_filters(course: list[str] | None, instructor: list[str] | None, semester: list[str] | None, sentiment: list[str] | None,
                 aspect: list[str] | None, confidence: str, date_from: date | None, date_to: date | None) -> Filters:
    if confidence not in ("all", "confident", "review"):
        raise HTTPException(422, "confidence must be one of: all, confident, review")
    return Filters(course or [], instructor or [], semester or [], sentiment or [], aspect or [], confidence, date_from, date_to)


def selected(ds: Dataset, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to):
    f = make_filters(course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    reviews, mentions = apply_filters(ds.result.reviews, ds.result.mentions, f)
    return f, reviews, mentions


FilterArgs = dict(
    course=Annotated[list[str] | None, Query()], instructor=Annotated[list[str] | None, Query()],
    semester=Annotated[list[str] | None, Query()], sentiment=Annotated[list[str] | None, Query()],
    aspect=Annotated[list[str] | None, Query()],
)


def _selection_text(ds: Dataset, reviews: pd.DataFrame) -> str:
    total = len(ds.result.reviews)
    return f"all {total} valid reviews" if len(reviews) == total else f"{len(reviews)} of {total} valid reviews"


REVIEW_FIELDS = ["record_id", "review_text", "course", "instructor", "semester", "date", "rating", "sentiment", "prob_positive",
                 "prob_neutral", "prob_negative", "confidence", "margin", "review_needed", "sentiment_score", "aspects",
                 "aspect_count", "evidence_terms", "processed_text"]


# ---------------------------------------------------------------------------
# meta, model, single text
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    m = model()
    report = load_report() or {}
    import sklearn
    import spacy
    import streamlit

    return {
        "product": PRODUCT_NAME, "descriptor": PRODUCT_DESCRIPTOR, "tagline": TAGLINE, "academic_title": ACADEMIC_TITLE,
        "model": {"available": m.available, "source": m.status.source, "message": m.status.message, "trained_at": m.status.trained_at},
        "limits": {"max_upload_mb": MAX_UPLOAD_MB, "max_rows": MAX_ROWS, "min_aspect_mentions": MIN_ASPECT_MENTIONS,
                   "min_sample_warning": MIN_SAMPLE_WARNING, "min_topic_reviews": MIN_TOPIC_REVIEWS, "group_min": GROUP_MIN,
                   "low_confidence_prob": LOW_CONFIDENCE_PROB, "low_confidence_margin": LOW_CONFIDENCE_MARGIN},
        "aspects": [{"id": a.id, "label": a.label, "description": a.description, "terms": sorted(a.terms), "phrases": a.phrases,
                     "context_terms": sorted(a.ambiguous_terms)} for a in analyzer().taxonomy.aspects],
        "roles": [{"role": r, "label": ROLE_LABELS[r], "required": r == "text"} for r in ["text", *OPTIONAL_ROLES]],
        "training_dataset": report.get("dataset"),
        "versions": {"python": platform.python_version(), "spacy": spacy.__version__, "scikit_learn": sklearn.__version__,
                     "pandas": pd.__version__, "streamlit": streamlit.__version__,
                     "spacy_model": (report.get("versions") or {}).get("spacy_model")},
    }


@app.get("/api/model")
def model_report():
    report = load_report()
    if not report:
        raise HTTPException(404, "No training report found. Run: python -m src.models.train")
    return clean(report)


class TextIn(BaseModel):
    text: str = Field(..., max_length=5000)


@app.post("/api/analyze-text")
def analyze_text(body: TextIn):
    text = clean_raw(body.text)
    if not text:
        raise HTTPException(422, "Please enter some text first.")
    m = model()
    pred = m.predict([body.text]).iloc[0]
    found = analyzer().analyze_doc(get_nlp()(text))
    rows = []
    if found.matches:
        ev = list(dict.fromkeys(x.evidence for x in found.matches))
        ep = m.predict(ev)
        ep.index = ev
        best: dict[str, dict] = {}
        for x in found.matches:
            row = {"aspect_id": x.aspect_id, "aspect": x.aspect_label, "evidence": x.evidence, "terms": x.terms,
                   "match_type": x.match_type, "negated": x.negated, "sentiment": ep.loc[x.evidence, "sentiment"],
                   "confidence": float(ep.loc[x.evidence, "confidence"])}
            if x.aspect_id not in best or row["confidence"] > best[x.aspect_id]["confidence"]:
                best[x.aspect_id] = row
        rows = list(best.values())
    return clean({"prediction": pred.to_dict(), "aspects": rows, "ambiguous": found.ambiguous,
                  "processed_text": process_texts([body.text])[0].model_text})


# ---------------------------------------------------------------------------
# uploads
# ---------------------------------------------------------------------------
@app.post("/api/uploads")
async def create_upload(file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    try:
        loaded = read_csv_bytes(raw)
    except DataLoadError as exc:
        raise HTTPException(422, str(exc))
    uid = store.put_upload(Upload(loaded.frame, file.filename or "upload.csv", loaded.encoding, loaded.delimiter,
                                  loaded.truncated, loaded.original_rows))
    mapping = suggest_mapping(list(loaded.frame.columns))
    if not mapping["text"]:
        mapping["text"] = guess_text_column(loaded.frame)
    return clean({"upload_id": uid, "filename": file.filename, "rows": len(loaded.frame), "columns": list(loaded.frame.columns),
                  "encoding": loaded.encoding, "delimiter": loaded.delimiter, "truncated": loaded.truncated,
                  "original_rows": loaded.original_rows, "preview": records(loaded.frame.head(10)), "suggested_mapping": mapping})


class AnalyzeIn(BaseModel):
    mapping: dict[str, str | None]
    name: str | None = None


@app.post("/api/uploads/{upload_id}/analyze")
def analyze_upload(upload_id: str, body: AnalyzeIn):
    up = store.get_upload(upload_id)
    if up is None:
        raise HTTPException(404, "The upload has expired. Please upload the file again.")
    mapping = {r: (body.mapping.get(r) or None) for r in ["text", *OPTIONAL_ROLES]}
    used = [c for c in mapping.values() if c]
    if len(used) != len(set(used)):
        raise HTTPException(422, "Each column can be mapped to only one role.")
    try:
        valid, excluded, report = prepare_dataset(up.frame, mapping)
    except ValidationError as exc:
        raise HTTPException(422, str(exc))
    ds = Dataset(store.new_id(), (body.name or up.filename)[:120], "upload", valid, excluded, report,
                 analyze_reviews(valid, model(), analyzer()))
    store.put_dataset(ds)
    return summary(ds.id)


# ---------------------------------------------------------------------------
# dataset views
# ---------------------------------------------------------------------------
@app.get("/api/datasets/{did}")
def summary(did: str):
    ds = dataset(did)
    r = ds.result.reviews
    dated = r["date"].dropna()
    opts = lambda col: sorted(r[col].dropna().astype(str).unique().tolist())  # noqa: E731
    return clean({"id": ds.id, "name": ds.name, "kind": ds.kind, "report": ds.report.as_dict(),
                  "options": {"course": opts("course"), "instructor": opts("instructor"), "semester": opts("semester"),
                              "aspect": [a.label for a in analyzer().taxonomy.aspects] + [NO_ASPECT],
                              "date_min": dated.min() if len(dated) else None, "date_max": dated.max() if len(dated) else None},
                  "valid_reviews": len(r)})


@app.get("/api/datasets/{did}/overview")
def overview(did: str, course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
             semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
             confidence: str = "all", date_from: date | None = None, date_to: date | None = None, k: int = 4):
    ds = dataset(did)
    _, reviews, mentions = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    tax = analyzer().taxonomy
    kpis = overview_kpis(reviews, ds.report.excluded_records)
    summ = aspect_summary(mentions, reviews, tax)
    best, worst = most_positive_negative(summ)
    topics = discover_topics(reviews, k) if len(reviews) else None
    topic_rows = []
    if topics and topics.ok:
        mix = reviews.assign(topic=topics.assignments).groupby("topic")["sentiment"].value_counts().unstack(fill_value=0)
        for t in topics.topics:
            row = mix.loc[t["topic_id"]] if t["topic_id"] in mix.index else {}
            topic_rows.append({**t, "positive": int(row.get("positive", 0)), "neutral": int(row.get("neutral", 0)),
                               "negative": int(row.get("negative", 0))})
    trend = []
    dated = reviews.dropna(subset=["date"])
    if len(dated) >= 5:
        freq = "W" if (dated["date"].max() - dated["date"].min()).days <= 120 else "MS"
        g = dated.groupby([pd.Grouper(key="date", freq=freq), "sentiment"]).size().unstack(fill_value=0)
        trend = [{"period": idx, **{s: int(g.loc[idx].get(s, 0)) for s in ("positive", "neutral", "negative")}} for idx in g.index]
    first_aspect = mentions.sort_values("aspect_confidence", ascending=False).drop_duplicates("record_id").set_index("record_id")["aspect_id"] \
        if len(mentions) else pd.Series(dtype=str)
    points = [{"id": int(rid), "score": s, "confidence": c, "sentiment": se, "aspect": first_aspect.get(rid)}
              for rid, s, c, se in reviews[["record_id", "sentiment_score", "confidence", "sentiment"]].head(2000).itertuples(index=False)]
    return clean({
        "selection": _selection_text(ds, reviews), "dataset": {"id": ds.id, "name": ds.name, "kind": ds.kind},
        "kpis": kpis, "total_records": ds.report.total_records, "exclusion_reasons": ds.report.exclusion_reasons,
        "most_positive": best, "most_negative": worst, "aspects": records(summ),
        "insights": generate_insights(reviews, summ), "keywords": records(keyword_table(reviews, 1).head(12)),
        "topics": {"ok": bool(topics and topics.ok), "message": topics.message if topics else "No reviews in the selection.", "items": topic_rows},
        "trend": trend, "points": points,
    })


@app.get("/api/datasets/{did}/reviews")
def reviews_list(did: str, course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
                 semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
                 confidence: str = "all", date_from: date | None = None, date_to: date | None = None,
                 q: str = "", sort: str = "record", offset: int = 0, limit: int = Query(25, le=200)):
    ds = dataset(did)
    _, reviews, mentions = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    view = reviews
    if q.strip():
        view = view[view["review_text"].str.contains(q.strip(), case=False, regex=False, na=False)]
    order = {"record": ("record_id", True), "negative": ("prob_negative", False), "positive": ("prob_positive", False),
             "uncertain": ("confidence", True)}
    if sort not in order:
        raise HTTPException(422, "sort must be one of: " + ", ".join(order))
    col, asc = order[sort]
    view = view.sort_values(col, ascending=asc, kind="stable")
    page = view.iloc[offset:offset + limit]
    terms = mentions[mentions["record_id"].isin(page["record_id"])].groupby("record_id")["terms"].apply(
        lambda s: sorted({t.strip() for x in s for t in x.split(",") if t.strip()})).to_dict()
    items = records(page, REVIEW_FIELDS)
    for it in items:
        it["highlight_terms"] = terms.get(it["record_id"], [])
    return {"total": len(view), "selection": _selection_text(ds, reviews), "offset": offset, "limit": limit, "items": items}


@app.get("/api/datasets/{did}/reviews/{rid}")
def review_detail(did: str, rid: int):
    ds = dataset(did)
    r = ds.result.reviews
    row = r[r["record_id"] == rid]
    if row.empty:
        raise HTTPException(404, f"Review #{rid} is not among the valid reviews.")
    m = ds.result.mentions[ds.result.mentions["record_id"] == rid]
    amb = ds.result.ambiguous[ds.result.ambiguous["record_id"] == rid]
    return {"review": records(row, REVIEW_FIELDS)[0], "mentions": records(m), "ambiguous": records(amb)}


@app.get("/api/datasets/{did}/aspects")
def aspects(did: str, course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
            semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
            confidence: str = "all", date_from: date | None = None, date_to: date | None = None):
    ds = dataset(did)
    _, reviews, mentions = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    summ = aspect_summary(mentions, reviews, analyzer().taxonomy)
    unmatched = reviews[reviews["aspect_count"] == 0]
    amb = ds.result.ambiguous[ds.result.ambiguous["record_id"].isin(reviews["record_id"])]
    return clean({"selection": _selection_text(ds, reviews), "reviews": len(reviews),
                  "with_aspect": int((reviews["aspect_count"] > 0).sum()), "summary": records(summ),
                  "unmatched": records(unmatched, ["record_id", "review_text", "sentiment"]),
                  "ambiguous": records(amb)})


@app.get("/api/datasets/{did}/aspects/{aspect_id}/evidence")
def aspect_evidence(did: str, aspect_id: str, clause_sentiment: Annotated[list[str] | None, Query()] = None,
                    course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
                    semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
                    confidence: str = "all", date_from: date | None = None, date_to: date | None = None):
    ds = dataset(did)
    _, reviews, mentions = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    m = mentions[mentions["aspect_id"] == aspect_id]
    if clause_sentiment:
        m = m[m["aspect_sentiment"].isin(clause_sentiment)]
    m = m.merge(reviews[["record_id", "review_text", "sentiment", "confidence", "course", "instructor", "semester"]]
                .rename(columns={"sentiment": "review_sentiment", "confidence": "review_confidence"}), on="record_id")
    return {"aspect_id": aspect_id, "items": records(m.sort_values("aspect_confidence", ascending=False))}


@app.get("/api/datasets/{did}/keywords")
def keywords(did: str, n: int = Query(1, ge=1, le=2), min_reviews: int = Query(2, ge=1), hide_generic: bool = True, top: int = Query(15, le=60),
             course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
             semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
             confidence: str = "all", date_from: date | None = None, date_to: date | None = None):
    ds = dataset(did)
    _, reviews, _ = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    kw = keyword_table(reviews, n, hide_generic, min_reviews)
    return {"selection": _selection_text(ds, reviews), "total_terms": len(kw), "terms": records(kw.head(top)),
            "all_terms": kw["term"].head(80).tolist() if len(kw) else [],
            "noun_phrases": records(noun_phrase_table(reviews).head(top))}


@app.get("/api/datasets/{did}/keywords/reviews")
def keyword_reviews(did: str, term: str, n: int = Query(1, ge=1, le=2), limit: int = 8,
                    course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
                    semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
                    confidence: str = "all", date_from: date | None = None, date_to: date | None = None):
    ds = dataset(did)
    _, reviews, _ = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    hits = reviews_with_term(reviews, term, n)
    return {"term": term, "total": len(hits), "items": records(hits.head(limit), REVIEW_FIELDS)}


@app.get("/api/datasets/{did}/topics")
def topics(did: str, k: int = Query(4, ge=2, le=8), course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
           semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
           confidence: str = "all", date_from: date | None = None, date_to: date | None = None):
    ds = dataset(did)
    _, reviews, _ = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    res = discover_topics(reviews, k)
    if not res.ok:
        return {"ok": False, "message": res.message, "items": [], "unassigned": None}
    assigned = reviews.assign(topic=res.assignments, strength=res.strengths)
    items = []
    for t in res.topics:
        sub = assigned[assigned["topic"] == t["topic_id"]]
        mix = sub["sentiment"].value_counts()
        reps = sub.sort_values("strength", ascending=False).head(4)
        items.append({**t, "positive": int(mix.get("positive", 0)), "neutral": int(mix.get("neutral", 0)), "negative": int(mix.get("negative", 0)),
                      "representatives": records(reps, ["record_id", "review_text", "sentiment", "confidence"])})
    return clean({"ok": True, "message": res.message, "items": items, "unassigned": int((assigned["topic"] == -1).sum())})


@app.get("/api/datasets/{did}/effectiveness")
def effectiveness(did: str, group_by: str = "course", course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
                  semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
                  confidence: str = "all", date_from: date | None = None, date_to: date | None = None):
    if group_by not in ("course", "instructor", "semester"):
        raise HTTPException(422, "group_by must be course, instructor or semester")
    ds = dataset(did)
    _, reviews, mentions = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    tax = analyzer().taxonomy
    summ = aspect_summary(mentions, reviews, tax)
    counts = sentiment_counts(reviews) if len(reviews) else {"positive": 0, "neutral": 0, "negative": 0}
    groups = []
    if len(reviews) and reviews[group_by].notna().any():
        for g, sub in reviews.groupby(group_by):
            sc = sentiment_counts(sub)
            groups.append({"group": g, "reviews": len(sub), **sc,
                           "indicator": effectiveness_indicator(sc["positive"], sc["neutral"], sc["negative"]) if len(sub) >= GROUP_MIN else None,
                           "evidence": "sufficient" if len(sub) >= GROUP_MIN else "insufficient sample"})
    return clean({"selection": _selection_text(ds, reviews), "reviews": len(reviews), "counts": counts,
                  "indicator": effectiveness_indicator(counts["positive"], counts["neutral"], counts["negative"]),
                  "small_sample": len(reviews) < MIN_SAMPLE_WARNING, "aspects": records(summ), "groups": groups,
                  "group_options": [c for c in ("course", "instructor", "semester") if reviews[c].notna().any()] if len(reviews) else [],
                  "recommendations": build_recommendations(summ, mentions, reviews, tax)})


@app.get("/api/datasets/{did}/validation")
def validation(did: str):
    ds = dataset(did)
    return clean({"report": ds.report.as_dict(), "excluded": records(ds.excluded)})


@app.get("/api/datasets/{did}/export/{kind}")
def export(did: str, kind: str, course: FilterArgs["course"] = None, instructor: FilterArgs["instructor"] = None,
           semester: FilterArgs["semester"] = None, sentiment: FilterArgs["sentiment"] = None, aspect: FilterArgs["aspect"] = None,
           confidence: str = "all", date_from: date | None = None, date_to: date | None = None, q: str = ""):
    ds = dataset(did)
    _, reviews, mentions = selected(ds, course, instructor, semester, sentiment, aspect, confidence, date_from, date_to)
    if q.strip():  # the Explore page exports exactly the reviews its search shows
        reviews = reviews[reviews["review_text"].str.contains(q.strip(), case=False, regex=False, na=False)]
        mentions = mentions[mentions["record_id"].isin(reviews["record_id"])]
    if kind == "reviews.csv":
        body, mime = export_frame(reviews).to_csv(index=False), "text/csv"
    elif kind == "mentions.csv":
        body, mime = mentions.to_csv(index=False), "text/csv"
    elif kind == "excluded.csv":
        body, mime = ds.excluded.to_csv(index=False), "text/csv"
    elif kind in ("report.html", "report.md"):
        tax = analyzer().taxonomy
        summ = aspect_summary(mentions, reviews, tax)
        tp = discover_topics(reviews, 4) if len(reviews) else None
        ctx = build_context(ds.name, ds.kind, ds.report.as_dict(), overview_kpis(reviews, ds.report.excluded_records), summ,
                            generate_insights(reviews, summ), build_recommendations(summ, mentions, reviews, tax), load_report(),
                            _selection_text(ds, reviews), tp.topics if tp and tp.ok else None,
                            "Logistic Regression (trained)" if model().available else "unavailable")
        body, mime = (build_html(ctx), "text/html") if kind == "report.html" else (build_markdown(ctx), "text/markdown")
    else:
        raise HTTPException(404, "Unknown export")
    name = f"sentiq_{kind.replace('.', '_').rsplit('_', 1)[0]}.{kind.rsplit('.', 1)[1]}"
    return Response(body.encode("utf-8"), media_type=f"{mime}; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---------------------------------------------------------------------------
# errors and the web interface
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled(request, exc):  # never leak review text or stack traces to the client
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": f"Unexpected server error ({type(exc).__name__})."}, status_code=500)


if (WEB_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (WEB_DIST / path).resolve()
        if path and target.is_file() and WEB_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")
