"""End-to-end analysis of a validated feedback dataset.

The same function is used for the demo dataset, uploaded CSVs and tests, so
every page sees results from one preprocessing + model pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.models.predict import SentimentModel
from src.nlp.aspects import AspectAnalyzer
from src.nlp.preprocessing import _CACHE, clean_raw, get_nlp, process_doc

MENTION_COLUMNS = ["record_id", "aspect_id", "aspect", "evidence", "sentence", "terms", "match_type", "negated",
                   "aspect_sentiment", "aspect_prob_positive", "aspect_prob_neutral", "aspect_prob_negative",
                   "aspect_confidence", "aspect_review_needed"]


@dataclass
class AnalysisResult:
    reviews: pd.DataFrame
    mentions: pd.DataFrame
    ambiguous: pd.DataFrame


def _noun_phrases(doc) -> list[str]:
    out = []
    for chunk in doc.noun_chunks:
        toks = [t for t in chunk if not (t.is_stop or t.is_punct or t.pos_ in {"DET", "PRON"})]
        if not toks:
            continue
        phrase = " ".join(t.lemma_.lower() for t in toks)
        if len(phrase) > 2 and (len(toks) > 1 or toks[0].pos_ in {"NOUN", "PROPN"}):
            out.append(phrase)
    return out


def analyze_reviews(valid: pd.DataFrame, model: SentimentModel, analyzer: AspectAnalyzer, progress=None) -> AnalysisResult:
    nlp = get_nlp()
    reviews = valid.copy().reset_index(drop=True)
    texts = [clean_raw(t) for t in reviews["review_text"]]
    processed, aspects, phrases = [], [], []
    n = max(len(texts), 1)
    for i, (text, doc) in enumerate(zip(texts, nlp.pipe(texts, batch_size=256))):
        p = process_doc(doc)
        _CACHE.setdefault(text, p)          # model's preprocessing step reuses this parse
        processed.append(p)
        aspects.append(analyzer.analyze_doc(doc))
        phrases.append(_noun_phrases(doc))
        if progress and i % 50 == 0:
            progress(0.1 + 0.6 * i / n, f"Processing reviews with spaCy ({i}/{len(texts)})")

    reviews["processed_text"] = [p.model_text for p in processed]
    reviews["content_lemmas"] = [p.content_lemmas for p in processed]
    reviews["noun_phrases"] = phrases
    reviews["word_count"] = [len(p.tokens) for p in processed]

    if progress:
        progress(0.75, "Predicting sentiment")
    preds = model.predict(texts)
    for col in preds.columns:
        reviews[col] = preds[col].values

    rows, amb_rows = [], []
    for rid, doc_aspects in zip(reviews["record_id"], aspects):
        for m in doc_aspects.matches:
            rows.append({"record_id": rid, "aspect_id": m.aspect_id, "aspect": m.aspect_label, "evidence": m.evidence,
                         "sentence": m.sentence, "terms": ", ".join(m.terms), "match_type": m.match_type,
                         "negated": m.negated})
        seen = set()
        for a in doc_aspects.ambiguous:
            key = (a["term"].lower(), a["aspect_id"], a["sentence"])
            if key not in seen:
                seen.add(key)
                amb_rows.append({"record_id": rid, **a})
    mentions = pd.DataFrame(rows, columns=MENTION_COLUMNS[:8])

    if progress:
        progress(0.9, "Scoring aspect evidence at clause level")
    if not mentions.empty:
        evid = mentions["evidence"].tolist()
        uniq = list(dict.fromkeys(evid))
        ep = model.predict(uniq)
        ep.index = uniq
        mentions["aspect_sentiment"] = ep.loc[evid, "sentiment"].values
        mentions["aspect_prob_positive"] = ep.loc[evid, "prob_positive"].values
        mentions["aspect_prob_neutral"] = ep.loc[evid, "prob_neutral"].values
        mentions["aspect_prob_negative"] = ep.loc[evid, "prob_negative"].values
        mentions["aspect_confidence"] = ep.loc[evid, "confidence"].values
        mentions["aspect_review_needed"] = ep.loc[evid, "review_needed"].values
        # one row per (review, aspect): keep the most confident clause
        mentions = (mentions.sort_values("aspect_confidence", ascending=False, na_position="last")
                    .drop_duplicates(["record_id", "aspect_id"]).sort_values(["record_id", "aspect_id"])
                    .reset_index(drop=True))
    else:
        mentions = pd.DataFrame(columns=MENTION_COLUMNS)

    per_review = mentions.groupby("record_id")["aspect"].apply(lambda s: "; ".join(sorted(s))) if not mentions.empty else pd.Series(dtype=str)
    terms = mentions.groupby("record_id")["terms"].apply(lambda s: ", ".join(s)) if not mentions.empty else pd.Series(dtype=str)
    reviews["aspects"] = reviews["record_id"].map(per_review).fillna("")
    reviews["aspect_count"] = reviews["aspects"].map(lambda s: len(s.split("; ")) if s else 0)
    reviews["evidence_terms"] = reviews["record_id"].map(terms).fillna("")
    ambiguous = pd.DataFrame(amb_rows, columns=["record_id", "term", "aspect_id", "aspect_label", "sentence"])
    if progress:
        progress(1.0, "Analysis complete")
    return AnalysisResult(reviews, mentions, ambiguous)
