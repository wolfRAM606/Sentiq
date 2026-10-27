"""Web API tests: every endpoint, error paths, and agreement with the core pipeline."""
import io

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")

from api.main import app  # noqa: E402

client = fastapi_testclient.TestClient(app)


def test_health_and_meta():
    assert client.get("/api/health").json() == {"status": "ok"}
    meta = client.get("/api/meta").json()
    assert meta["product"] == "Sentiq"
    assert "using spaCy and Streamlit" in meta["academic_title"]
    assert meta["model"]["available"] is True
    assert len(meta["aspects"]) == 12
    assert meta["limits"]["max_rows"] == 10_000


def test_demo_summary_and_overview_numbers():
    s = client.get("/api/datasets/demo").json()
    assert s["kind"] == "demo" and s["valid_reviews"] == 84
    assert s["report"]["total_records"] == s["report"]["valid_records"] + s["report"]["excluded_records"]
    o = client.get("/api/datasets/demo/overview").json()
    assert o["kpis"]["valid_reviews"] == 84
    assert sum(o["kpis"]["counts"].values()) == 84
    assert round(o["kpis"]["effectiveness"], 1) == 66.1
    assert o["selection"] == "all 84 valid reviews"
    assert o["topics"]["ok"] and sum(t["n_reviews"] for t in o["topics"]["items"]) <= 84
    assert len(o["points"]) == 84 and {p["sentiment"] for p in o["points"]} <= {"positive", "neutral", "negative"}
    assert sum(sum(t[s] for s in ("positive", "neutral", "negative")) for t in o["trend"]) == 84


def test_filters_match_core_filter_function():
    from api.main import demo
    from src.analytics.filters import Filters, apply_filters

    ds = demo()
    params = {"course": "CS305 Machine Learning", "confidence": "confident"}
    o = client.get("/api/datasets/demo/overview", params=params).json()
    expected, _ = apply_filters(ds.result.reviews, ds.result.mentions, Filters(course=["CS305 Machine Learning"], confidence="confident"))
    assert o["kpis"]["valid_reviews"] == len(expected)
    assert o["selection"] == f"{len(expected)} of 84 valid reviews"
    multi = client.get("/api/datasets/demo/overview", params=[("course", "CS305 Machine Learning"), ("course", "MA102 Linear Algebra")]).json()
    assert multi["kpis"]["valid_reviews"] == 42
    dated = client.get("/api/datasets/demo/overview", params={"date_from": "2025-09-01", "date_to": "2025-12-31"}).json()
    assert dated["kpis"]["valid_reviews"] == 42
    none = client.get("/api/datasets/demo/overview", params={"aspect": "(no aspect detected)"}).json()
    assert none["kpis"]["valid_reviews"] == 1
    empty = client.get("/api/datasets/demo/overview", params={"course": "CS305 Machine Learning", "semester": "Fall 2025", "sentiment": "neutral"}).json()
    assert empty["kpis"]["valid_reviews"] == 0 and empty["insights"] == []
    assert client.get("/api/datasets/demo/overview", params={"confidence": "bogus"}).status_code == 422


def test_reviews_search_sort_paging_and_detail():
    r = client.get("/api/datasets/demo/reviews", params={"q": "assignment"}).json()
    assert r["total"] == 8 and all("assignment" in it["review_text"].lower() for it in r["items"])
    neg = client.get("/api/datasets/demo/reviews", params={"sort": "negative", "limit": 5}).json()["items"]
    probs = [it["prob_negative"] for it in neg]
    assert probs == sorted(probs, reverse=True)
    unc = client.get("/api/datasets/demo/reviews", params={"sort": "uncertain", "limit": 5}).json()["items"]
    assert [it["confidence"] for it in unc] == sorted(it["confidence"] for it in unc)
    p1 = client.get("/api/datasets/demo/reviews", params={"limit": 10, "offset": 0}).json()["items"]
    p2 = client.get("/api/datasets/demo/reviews", params={"limit": 10, "offset": 10}).json()["items"]
    assert not {i["record_id"] for i in p1} & {i["record_id"] for i in p2}
    assert client.get("/api/datasets/demo/reviews", params={"sort": "x"}).status_code == 422
    d = client.get("/api/datasets/demo/reviews/12").json()
    assert d["review"]["record_id"] == 12 and {m["aspect_id"] for m in d["mentions"]} >= {"assignments"}
    assert client.get("/api/datasets/demo/reviews/99999").status_code == 404


def test_aspects_keywords_topics_effectiveness():
    a = client.get("/api/datasets/demo/aspects").json()
    assert len(a["summary"]) == 12
    assert all(x["positive"] + x["neutral"] + x["negative"] == x["reviews"] for x in a["summary"])
    assert len(a["unmatched"]) == a["reviews"] - a["with_aspect"] == 1
    ev = client.get("/api/datasets/demo/aspects/pace/evidence", params={"clause_sentiment": "negative"}).json()
    assert ev["items"] and {i["aspect_sentiment"] for i in ev["items"]} == {"negative"}
    k = client.get("/api/datasets/demo/keywords").json()
    top = {t["term"]: t["reviews"] for t in k["terms"]}
    assert top["assignment"] == 8 and top["exam"] == 5
    assert client.get("/api/datasets/demo/keywords", params={"n": 2}).json()["terms"][0]["term"] == "answer question"
    kr = client.get("/api/datasets/demo/keywords/reviews", params={"term": "exam"}).json()
    assert kr["total"] == 5
    for kk in (2, 5, 8):
        t = client.get("/api/datasets/demo/topics", params={"k": kk}).json()
        assert t["ok"] and len(t["items"]) == kk
        assert sum(i["n_reviews"] for i in t["items"]) + t["unassigned"] == 84
    small = client.get("/api/datasets/demo/topics", params={"course": "CS305 Machine Learning"}).json()
    assert small["ok"] is False and "at least" in small["message"]
    e = client.get("/api/datasets/demo/effectiveness").json()
    assert round(e["indicator"], 1) == 66.1 and len(e["recommendations"]) == 11
    assert all(g["indicator"] is not None for g in e["groups"])
    e2 = client.get("/api/datasets/demo/effectiveness", params={"semester": "Fall 2025"}).json()
    assert all(g["indicator"] is None and g["evidence"] == "insufficient sample" for g in e2["groups"])
    assert client.get("/api/datasets/demo/effectiveness", params={"group_by": "x"}).status_code == 422


def test_exports_follow_filters():
    import csv

    r = client.get("/api/datasets/demo/export/reviews.csv", params={"course": "CS305 Machine Learning"})
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 22 and {x["course"] for x in rows} == {"CS305 Machine Learning"}
    assert len(list(csv.DictReader(io.StringIO(client.get("/api/datasets/demo/export/mentions.csv").text)))) == 120
    assert len(list(csv.DictReader(io.StringIO(client.get("/api/datasets/demo/export/excluded.csv").text)))) == 5
    html = client.get("/api/datasets/demo/export/report.html").text
    assert "An Automated Text Mining Dashboard" in html and "<script" not in html.lower()
    md = client.get("/api/datasets/demo/export/report.md", params={"course": "CS305 Machine Learning"}).text
    assert "Selection: 22 of 84 valid reviews" in md
    assert client.get("/api/datasets/demo/export/nope").status_code == 404


def test_upload_flow_and_errors():
    csv_bytes = ("Student Comment;Module;Tutor\n"
                 "The professor explains concepts clearly;PHY;Dr X\n"
                 ";PHY;Dr X\n"
                 "The professor explains concepts clearly;PHY;Dr X\n"
                 "Assignments are far too long;CHE;Dr Y\n").encode()
    up = client.post("/api/uploads", files={"file": ("f.csv", csv_bytes, "text/csv")}).json()
    assert up["delimiter"] == ";" and up["suggested_mapping"]["text"] == "Student Comment"
    assert up["suggested_mapping"]["course"] == "Module" and up["suggested_mapping"]["instructor"] == "Tutor"
    bad = client.post(f"/api/uploads/{up['upload_id']}/analyze", json={"mapping": {"text": "Student Comment", "course": "Student Comment"}})
    assert bad.status_code == 422 and "only one role" in bad.json()["detail"]
    ok = client.post(f"/api/uploads/{up['upload_id']}/analyze", json={"mapping": up["suggested_mapping"], "name": "Physics"}).json()
    assert ok["kind"] == "upload" and ok["name"] == "Physics" and ok["valid_reviews"] == 2
    assert ok["report"]["excluded_records"] == 2
    assert client.get(f"/api/datasets/{ok['id']}/overview").json()["kpis"]["valid_reviews"] == 2
    assert client.get(f"/api/datasets/{ok['id']}/validation").json()["excluded"][0]["exclusion_reason"]
    for raw, frag in ((b"", "empty"), (b"review,review\na,b\n", "duplicate column"), (b"\x00\x01PK", "binary"), (b"review\n", "no records")):
        r = client.post("/api/uploads", files={"file": ("x.csv", raw, "text/csv")})
        assert r.status_code == 422 and frag in r.json()["detail"].lower()
    numeric = client.post("/api/uploads", files={"file": ("n.csv", b"id,score\n1,2\n3,4\n", "text/csv")}).json()
    r = client.post(f"/api/uploads/{numeric['upload_id']}/analyze", json={"mapping": numeric["suggested_mapping"]})
    assert r.status_code == 422 and "No valid reviews" in r.json()["detail"]
    assert client.post("/api/uploads/missing/analyze", json={"mapping": {"text": "x"}}).status_code == 404
    assert client.get("/api/datasets/not-a-dataset").status_code == 404


def test_analyze_text():
    r = client.post("/api/analyze-text", json={"text": "The lectures were clear but the assignment instructions were confusing."}).json()
    assert r["prediction"]["sentiment"] in {"positive", "neutral", "negative"}
    ids = [a["aspect_id"] for a in r["aspects"]]
    assert len(ids) == len(set(ids)) and {"clarity", "assignments"} <= set(ids)
    assert "but" in r["processed_text"]
    amb = client.post("/api/analyze-text", json={"text": "The answer was clear."}).json()
    assert amb["aspects"] == [] and any(a["term"].lower() == "clear" for a in amb["ambiguous"])
    assert client.post("/api/analyze-text", json={"text": "   "}).status_code == 422


def test_model_report_and_unknown_api_path():
    m = client.get("/api/model").json()
    assert round(m["models"]["logistic_regression"]["test"]["macro_f1"], 3) == 0.529
    assert client.get("/api/definitely-not-a-route").status_code == 404
