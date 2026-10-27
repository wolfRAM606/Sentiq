"""Markdown and HTML report generation (self-contained, printable)."""
from __future__ import annotations

import html
import time

import pandas as pd

from src.config import ACADEMIC_TITLE, PRODUCT_DESCRIPTOR, PRODUCT_NAME, TAGLINE

esc = html.escape


def _pct(x) -> str:
    return "n/a" if x is None or x != x else f"{100 * x:.0f}%"


def build_context(dataset_name: str, dataset_kind: str, validation: dict, kpis: dict, summary: pd.DataFrame,
                  insights: list[dict], recommendations: list[dict], training_report: dict | None,
                  filter_text: str, topics: list[dict] | None = None, model_status: str = "") -> dict:
    return {
        "generated": time.strftime("%Y-%m-%d %H:%M"), "dataset_name": dataset_name, "dataset_kind": dataset_kind,
        "validation": validation, "kpis": kpis, "summary": summary, "insights": insights,
        "recommendations": recommendations, "training": training_report, "filter_text": filter_text,
        "topics": topics or [], "model_status": model_status,
    }


def _model_lines(tr: dict | None) -> list[tuple[str, str, str, str]]:
    if not tr:
        return []
    return [(m["display_name"], f"{m['cv_macro_f1_mean']:.3f} ± {m['cv_macro_f1_std']:.3f}",
             f"{m['test']['accuracy']:.3f}", f"{m['test']['macro_f1']:.3f}") for m in tr["models"].values()]


LIMITATIONS = [
    "Sentiment labels are model predictions, not ground truth. The model was trained on a small public dataset "
    "(short comments from one higher-education institution); performance on other populations may differ.",
    "Aspect detection is rule-assisted (lexicon + spaCy lemmas). It can miss paraphrases and mis-assign ambiguous words; "
    "no aspect-level accuracy is claimed because no annotated aspect data was used for evaluation.",
    "The feedback indicator summarises predicted sentiment only. Student feedback can be biased, incomplete or "
    "unrepresentative, and the indicator is not an objective measure of teaching quality.",
    "Associations between aspects and sentiment are descriptive and do not establish causes.",
]


def build_markdown(ctx: dict) -> str:
    k, v = ctx["kpis"], ctx["validation"]
    lines = [f"# {PRODUCT_NAME} feedback report", "", f"*{PRODUCT_DESCRIPTOR}. {TAGLINE}*", "",
             f"Academic project: **{ACADEMIC_TITLE}**", "",
             f"- Generated: {ctx['generated']}", f"- Dataset: {ctx['dataset_name']}"
             + (" (synthetic demonstration data written for this project, not real student feedback)" if ctx["dataset_kind"] == "demo" else ""),
             f"- Selection: {ctx['filter_text']}", f"- Sentiment model: {ctx['model_status']}", "",
             "## Data quality", "",
             f"- Records in file: {v['total_records']}", f"- Valid reviews: {v['valid_records']}",
             f"- Excluded records: {v['excluded_records']}"]
    for reason, n in v.get("exclusion_reasons", {}).items():
        lines.append(f"  - {reason}: {n}")
    lines += ["", "## Sentiment overview", "", "| Sentiment | Reviews | Share |", "|---|---:|---:|"]
    for s in ("positive", "neutral", "negative"):
        lines.append(f"| {s.capitalize()} | {k['counts'][s]} | {_pct(k['shares'][s])} |")
    score = k.get("effectiveness")
    lines += ["", f"- Average sentiment score (P(positive) − P(negative), range −1 to +1): "
                  f"{k['avg_sentiment_score']:.2f}" if k.get("avg_sentiment_score") is not None else "",
              f"- Sentiment-derived feedback indicator: {score:.1f} / 100 "
              "(100 × [positive share + 0.5 × neutral share] = 50% positive share + 50% negative complement)"
              if score is not None else "",
              f"- Low-confidence predictions flagged for review: {k['review_needed']}", "",
              "## Key findings", ""]
    lines += [f"- {i['text']}" for i in ctx["insights"]] or ["- No findings for this selection."]
    lines += ["", "## Aspect summary", "", "| Aspect | Reviews | Positive | Neutral | Negative | Aspect indicator |",
              "|---|---:|---:|---:|---:|---:|"]
    for r in ctx["summary"].itertuples():
        ind = f"{r.aspect_score:.0f}" if r.enough_evidence and r.aspect_score is not None else "insufficient evidence"
        lines.append(f"| {r.aspect} | {r.reviews} | {r.positive} | {r.neutral} | {r.negative} | {ind} |")
    lines += ["", "## Evidence-linked recommendations", ""]
    if not ctx["recommendations"]:
        lines.append("No recommendation met the evidence thresholds for this selection.")
    for rec in ctx["recommendations"]:
        lines += [f"### {rec['headline']}", "", f"**Suggested action:** {rec['action']}", ""]
        lines += [f"> “{e['evidence']}” (review #{e['record_id']})" for e in rec["examples"]]
        lines += ["", f"*Caveats:* {' '.join(rec['caveats'])}", ""]
    if ctx["topics"]:
        lines += ["## Discovered topics (unsupervised, automatically labelled)", ""]
        lines += [f"- {t['label']}: {t['n_reviews']} reviews; top terms: {', '.join(t['terms'][:6])}" for t in ctx["topics"]]
        lines.append("")
    tr = ctx["training"]
    if tr:
        ds = tr["dataset"]
        lines += ["## Sentiment model evaluation (held-out test set)", "",
                  f"Training data: {ds['name']}, {ds['url']}, licence {ds['license']}. "
                  f"{ds['cleaning'].get('clean_rows')} labelled comments after cleaning; "
                  f"{tr['split']['train_rows']} train / {tr['split']['test_rows']} test (stratified, seed {tr['split']['random_state']}).", "",
                  "| Model | CV macro-F1 (train) | Test accuracy | Test macro-F1 |", "|---|---:|---:|---:|"]
        lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in _model_lines(tr)]
        lines += ["", f"Calibration (expected calibration error of top-class probability, test set): {tr['calibration']['ece']:.3f}", ""]
    lines += ["## Limitations", ""] + [f"- {l}" for l in LIMITATIONS]
    return "\n".join(l for l in lines if l is not None) + "\n"


def build_html(ctx: dict) -> str:
    k, v = ctx["kpis"], ctx["validation"]
    demo = ctx["dataset_kind"] == "demo"

    def tr_row(cells, tag="td"):
        return "<tr>" + "".join(f"<{tag}>{esc(str(c))}</{tag}>" for c in cells) + "</tr>"

    sent_rows = "".join(tr_row([s.capitalize(), k["counts"][s], _pct(k["shares"][s])]) for s in ("positive", "neutral", "negative"))
    asp_rows = "".join(tr_row([r.aspect, r.reviews, r.positive, r.neutral, r.negative,
                               f"{r.aspect_score:.0f}" if r.enough_evidence and r.aspect_score is not None else "insufficient evidence"])
                       for r in ctx["summary"].itertuples())
    recs = ""
    for rec in ctx["recommendations"]:
        ex = "".join(f"<blockquote>“{esc(e['evidence'])}” <span>(review #{e['record_id']})</span></blockquote>" for e in rec["examples"])
        recs += (f"<div class='rec {rec['kind']}'><h3>{esc(rec['headline'])}</h3><p><b>Suggested action:</b> {esc(rec['action'])}</p>"
                 f"{ex}<p class='cav'>{esc(' '.join(rec['caveats']))}</p></div>")
    recs = recs or "<p>No recommendation met the evidence thresholds for this selection.</p>"
    excl = "".join(f"<li>{esc(r)}: {n}</li>" for r, n in v.get("exclusion_reasons", {}).items())
    ins = "".join(f"<li>{esc(i['text'])}</li>" for i in ctx["insights"]) or "<li>No findings for this selection.</li>"
    topics = ""
    if ctx["topics"]:
        topics = "<h2>Discovered topics</h2><p class='muted'>Unsupervised NMF topics with automatic labels (not human-verified categories).</p><ul>" + \
                 "".join(f"<li><b>{esc(t['label'])}</b>: {t['n_reviews']} reviews; {esc(', '.join(t['terms'][:6]))}</li>" for t in ctx["topics"]) + "</ul>"
    model = ""
    tr = ctx["training"]
    if tr:
        ds = tr["dataset"]
        rows = "".join(tr_row(r) for r in _model_lines(tr))
        model = (f"<h2>Sentiment model evaluation</h2><p class='muted'>Held-out test set from {esc(ds['name'])} "
                 f"(<a href='{esc(ds['url'])}'>{esc(ds['url'])}</a>, licence {esc(ds['license'])}). "
                 f"{tr['split']['train_rows']} train / {tr['split']['test_rows']} test, stratified, seed {tr['split']['random_state']}. "
                 "Hyper-parameters were selected by cross-validation on the training split only.</p>"
                 f"<table><thead>{tr_row(['Model', 'CV macro-F1 (train)', 'Test accuracy', 'Test macro-F1'], 'th')}</thead><tbody>{rows}</tbody></table>"
                 f"<p class='muted'>Expected calibration error (test): {tr['calibration']['ece']:.3f}</p>")
    lim = "".join(f"<li>{esc(l)}</li>" for l in LIMITATIONS)
    score = k.get("effectiveness")
    avg = k.get("avg_sentiment_score")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{PRODUCT_NAME} feedback report</title>
<style>
:root{{--bg:#F5F0E8;--surface:#EDE6DA;--rule:#D3C8B6;--text:#25242A;--muted:#625C57;--brand:#702F45;--sage:#8AAB91;--pos:#45694E;--neu:#7A5D16;--neg:#A8442F}}
body{{background:var(--bg);color:var(--text);font-family:"IBM Plex Sans","Segoe UI",system-ui,Arial,sans-serif;margin:0;line-height:1.6}}
main{{max-width:920px;margin:0 auto;padding:48px 28px 72px}}
h1,h2,h3{{font-family:Fraunces,"Iowan Old Style",Georgia,serif;font-weight:500}}
h1{{font-size:2.5rem;margin:.3rem 0;line-height:1.1}} h2{{border-top:1px solid var(--rule);padding-top:.9rem;margin-top:2.4rem;font-size:1.45rem}}
.eyebrow{{font-family:"IBM Plex Mono",Consolas,monospace;color:var(--brand);letter-spacing:.12em;text-transform:uppercase;font-size:.74rem}}
.muted,.cav{{color:var(--muted);font-size:.9rem}} a{{color:var(--brand)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0 28px;margin:22px 0}}
.kpi{{border-top:1px solid var(--rule);padding:12px 0}}
.kpi .l{{font-family:"IBM Plex Mono",Consolas,monospace;font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
.kpi .v{{font-family:Fraunces,Georgia,serif;font-size:2rem}}
.kpi.feat{{border-top:2px solid var(--brand)}} .kpi.feat .v{{color:var(--brand)}}
.banner{{border:1px solid var(--neu);color:var(--neu);padding:8px 12px;font-size:.9rem}}
table{{width:100%;border-collapse:collapse;font-size:.92rem;margin:12px 0}} th,td{{border-bottom:1px solid var(--rule);padding:8px 8px;text-align:left}}
th{{color:var(--muted);font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}} td:not(:first-child),th:not(:first-child){{text-align:right}}
.rec{{border-top:1px solid var(--rule);padding:6px 0 12px;margin:10px 0}}
.rec h3{{font-size:1.15rem;margin:.6rem 0}} .rec.issue h3{{color:var(--neg)}} .rec.strength h3{{color:var(--pos)}}
blockquote{{margin:6px 0 6px 1rem;color:var(--muted);font-family:Fraunces,Georgia,serif;font-style:italic}}
footer{{margin-top:44px;color:var(--muted);font-size:.82rem;border-top:1px solid var(--rule);padding-top:12px}}
@media print{{body{{background:#fff}} main{{padding:0}} a{{color:#702F45}}}}
</style></head><body><main>
<div class="eyebrow">{PRODUCT_NAME} · {esc(PRODUCT_DESCRIPTOR)}</div>
<h1>Course feedback report</h1>
<p class="muted">{esc(TAGLINE)} · Generated {esc(ctx['generated'])} · Academic project: <i>{esc(ACADEMIC_TITLE)}</i></p>
{"<p class='banner'>This report uses the bundled <b>synthetic demonstration dataset</b>. It is not real student feedback.</p>" if demo else ""}
<p><b>Dataset:</b> {esc(ctx['dataset_name'])} · <b>Selection:</b> {esc(ctx['filter_text'])} · <b>Model:</b> {esc(ctx['model_status'])}</p>
<div class="kpis">
 <div class="kpi feat"><div class="l">Feedback indicator</div><div class="v">{f"{score:.1f}" if score is not None else "n/a"}</div><div class="muted">100 × (positive + 0.5 × neutral share) = 50% positive + 50% (1 − negative)</div></div>
 <div class="kpi"><div class="l">Valid reviews</div><div class="v">{k['valid_reviews']}</div></div>
 <div class="kpi"><div class="l">Avg sentiment score</div><div class="v">{f"{avg:+.2f}" if avg is not None else "n/a"}</div><div class="muted">P(pos) − P(neg), −1…+1</div></div>
 <div class="kpi"><div class="l">Review needed</div><div class="v">{k['review_needed']}</div><div class="muted">low-confidence predictions</div></div>
</div>
<h2>Data quality</h2><p>{v['total_records']} records in file · {v['valid_records']} valid · {v['excluded_records']} excluded</p><ul>{excl}</ul>
<h2>Sentiment overview</h2><table><thead>{tr_row(['Sentiment', 'Reviews', 'Share'], 'th')}</thead><tbody>{sent_rows}</tbody></table>
<h2>Key findings</h2><ul>{ins}</ul>
<h2>Aspect summary</h2><p class="muted">Clause-level sentiment of rule-assisted aspect matches. Indicators shown only with at least 3 mentioning reviews.</p>
<table><thead>{tr_row(['Aspect', 'Reviews', 'Positive', 'Neutral', 'Negative', 'Indicator'], 'th')}</thead><tbody>{asp_rows}</tbody></table>
<h2>Evidence-linked recommendations</h2>{recs}
{topics}{model}
<h2>Limitations</h2><ul>{lim}</ul>
<footer>{PRODUCT_NAME} · {esc(PRODUCT_DESCRIPTOR)}. Use your browser's Print command to save this report as PDF.</footer>
</main></body></html>"""
