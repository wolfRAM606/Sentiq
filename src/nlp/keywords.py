"""Keyword and phrase statistics computed from spaCy lemmas of the active dataset."""
from __future__ import annotations

from collections import Counter

import pandas as pd

# Words that are frequent in any teaching feedback and rarely informative on their own.
DOMAIN_STOPWORDS = {
    "teacher", "sir", "madam", "mam", "maam", "student", "students", "class", "course", "subject",
    "professor", "lecture", "lecturer", "instructor", "teach", "teaching", "faculty", "university",
    "college", "semester", "really", "also", "thing", "lot", "way", "time", "get", "make", "go",
}


def ngrams(lemmas: tuple | list, n: int) -> list[str]:
    if n == 1:
        return list(lemmas)
    return [" ".join(lemmas[i:i + n]) for i in range(len(lemmas) - n + 1)]


def keyword_table(reviews: pd.DataFrame, n: int = 1, hide_domain_words: bool = True, min_reviews: int = 2) -> pd.DataFrame:
    """Document-frequency table of lemma n-grams, split by predicted sentiment.

    Counts are numbers of reviews containing the term (not raw token counts),
    so one long review cannot dominate the ranking.
    """
    cols = ["term", "reviews", "positive", "neutral", "negative", "share_of_reviews", "net_sentiment"]
    if reviews.empty:
        return pd.DataFrame(columns=cols)
    total, by_sent = Counter(), {"positive": Counter(), "neutral": Counter(), "negative": Counter()}
    for lemmas, sent in zip(reviews["content_lemmas"], reviews["sentiment"]):
        toks = [t for t in lemmas if not (hide_domain_words and t in DOMAIN_STOPWORDS)]
        terms = set(ngrams(toks, n))
        total.update(terms)
        if sent in by_sent:
            by_sent[sent].update(terms)
    rows = []
    for term, cnt in total.items():
        if cnt < min_reviews:
            continue
        pos, neu, neg = by_sent["positive"][term], by_sent["neutral"][term], by_sent["negative"][term]
        rows.append({"term": term, "reviews": cnt, "positive": pos, "neutral": neu, "negative": neg,
                     "share_of_reviews": cnt / len(reviews), "net_sentiment": (pos - neg) / cnt})
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values(["reviews", "term"], ascending=[False, True]).reset_index(drop=True)


def noun_phrase_table(reviews: pd.DataFrame, min_reviews: int = 2) -> pd.DataFrame:
    cols = ["phrase", "reviews", "positive", "neutral", "negative"]
    if reviews.empty or "noun_phrases" not in reviews:
        return pd.DataFrame(columns=cols)
    total, by = Counter(), {k: Counter() for k in ["positive", "neutral", "negative"]}
    for phrases, sent in zip(reviews["noun_phrases"], reviews["sentiment"]):
        uniq = set(phrases)
        total.update(uniq)
        if sent in by:
            by[sent].update(uniq)
    rows = [{"phrase": p, "reviews": c, **{k: by[k][p] for k in by}} for p, c in total.items() if c >= min_reviews]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values(["reviews", "phrase"], ascending=[False, True]).reset_index(drop=True)


def reviews_with_term(reviews: pd.DataFrame, term: str, n: int) -> pd.DataFrame:
    mask = reviews["content_lemmas"].map(lambda lem: term in ngrams(list(lem), n))
    return reviews[mask]
