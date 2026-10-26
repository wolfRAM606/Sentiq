"""Exploratory topic discovery with TF-IDF + NMF (scikit-learn)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import MIN_TOPIC_REVIEWS, RANDOM_STATE
from src.nlp.keywords import DOMAIN_STOPWORDS


@dataclass
class TopicResult:
    ok: bool
    message: str
    k: int = 0
    topics: list = field(default_factory=list)            # [{"topic_id","label","terms","weights","n_reviews"}]
    assignments: pd.Series | None = None                   # topic_id per review (-1 = unassigned)
    strengths: pd.Series | None = None


def discover_topics(reviews: pd.DataFrame, k: int = 4, n_terms: int = 8, random_state: int = RANDOM_STATE) -> TopicResult:
    if len(reviews) < MIN_TOPIC_REVIEWS:
        return TopicResult(False, f"Topic discovery needs at least {MIN_TOPIC_REVIEWS} reviews; "
                                  f"the active selection has {len(reviews)}.")
    docs = [" ".join(t for t in lem if t not in DOMAIN_STOPWORDS) for lem in reviews["content_lemmas"]]
    nonempty = sum(1 for d in docs if d.strip())
    if nonempty < MIN_TOPIC_REVIEWS:
        return TopicResult(False, "Too few reviews contain informative words for topic discovery.")
    vec = TfidfVectorizer(min_df=2, max_df=0.8, ngram_range=(1, 2), sublinear_tf=True)
    try:
        X = vec.fit_transform(docs)
    except ValueError:
        return TopicResult(False, "The vocabulary is too small for topic discovery (no term appears in two or more reviews).")
    vocab = vec.get_feature_names_out()
    if len(vocab) < max(3 * k, 10):
        return TopicResult(False, f"The vocabulary ({len(vocab)} recurring terms) is too small for {k} topics. Try fewer topics or more data.")
    k = min(k, max(2, nonempty // 5))
    model = NMF(n_components=k, init="nndsvda", random_state=random_state, max_iter=600)
    W = model.fit_transform(X)
    H = model.components_
    assign = np.where(W.max(axis=1) > 0, W.argmax(axis=1), -1)
    topics = []
    for t in range(k):
        n_rev = int((assign == t).sum())
        if n_rev == 0:
            continue
        order = np.argsort(H[t])[::-1][:n_terms]
        terms = [str(vocab[i]) for i in order if H[t][i] > 0]
        topics.append({"topic_id": t, "label": f"Topic {len(topics) + 1}: " + " · ".join(terms[:3]),
                       "terms": terms, "weights": [float(H[t][i]) for i in order[:len(terms)]], "n_reviews": n_rev})
    remap = {tp["topic_id"]: i for i, tp in enumerate(topics)}
    for i, tp in enumerate(topics):
        tp["topic_id"] = i
    assignments = pd.Series([remap.get(a, -1) for a in assign], index=reviews.index)
    strengths = pd.Series(W.max(axis=1), index=reviews.index)
    if len(topics) < 2:
        return TopicResult(False, "Topic modelling produced fewer than two non-empty topics; the data is not diverse enough.")
    return TopicResult(True, f"{len(topics)} topics discovered from {nonempty} reviews and {len(vocab)} recurring terms.",
                       len(topics), topics, assignments, strengths)
