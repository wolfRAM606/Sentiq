"""spaCy-based text preprocessing shared by training, inference and analytics.

Design choices
--------------
* Lemmatisation and tokenisation come from spaCy (``en_core_web_sm``).
* Generic stopwords are removed, **but** negators ("not", "never", "hardly", "no",
  "n't" ...) and intensity/contrast words are kept, because they carry sentiment.
* Negation scope marking: the content tokens following a negator (up to
  ``NEGATION_WINDOW`` tokens, stopping at punctuation or a contrastive
  conjunction) receive a ``neg_`` prefix. "not helpful" therefore becomes
  ``not neg_helpful`` and can never look like the positive feature ``helpful``.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from sklearn.base import BaseEstimator, TransformerMixin

from src.config import MAX_REVIEW_CHARS, SPACY_MODEL

logger = logging.getLogger(__name__)

NEGATORS = {
    "not", "no", "never", "n't", "nt", "hardly", "barely", "scarcely", "neither", "nor",
    "nothing", "nobody", "none", "nowhere", "cannot", "without", "lack", "lacking", "dont",
    "didnt", "doesnt", "isnt", "wasnt", "arent", "werent", "cant", "couldnt", "wont", "wouldnt",
    "shouldnt", "havent", "hasnt",
}
NEGATOR_NORMAL = {"n't": "not", "nt": "not", "cannot": "not", "dont": "not", "didnt": "not", "doesnt": "not",
                  "isnt": "not", "wasnt": "not", "arent": "not", "werent": "not", "cant": "not",
                  "couldnt": "not", "wont": "not", "wouldnt": "not", "shouldnt": "not", "havent": "not",
                  "hasnt": "not"}
CONTRAST = {"but", "however", "although", "though", "whereas", "yet", "except", "while"}
KEEP_WORDS = NEGATORS | CONTRAST | {
    "very", "too", "more", "most", "less", "least", "much", "few", "only", "enough", "well",
    "really", "quite", "so", "always", "sometimes", "often", "should", "must", "please",
}
NEGATION_WINDOW = 3
SCOPE_BREAK_POS = {"PUNCT", "CCONJ", "SCONJ"}

# common informal spellings in student feedback
_TEXT_FIXES = [
    (re.compile(r"\b(do|does|did|is|was|are|were|could|would|should|have|has|ca|wo)nt\b", re.I), r"\1n't"),
    (re.compile(r"\bcant\b", re.I), "can't"),
    (re.compile(r"\bwont\b", re.I), "won't"),
    (re.compile(r"\s+"), " "),
]


@lru_cache(maxsize=1)
def get_nlp():
    """Load the spaCy pipeline once per process (NER is disabled for speed)."""
    import spacy

    try:
        nlp = spacy.load(SPACY_MODEL, disable=["ner"])
    except OSError as exc:  # model not installed
        raise RuntimeError(
            f"The spaCy model '{SPACY_MODEL}' is not installed. Run: python -m spacy download {SPACY_MODEL}"
        ) from exc
    logger.info("Loaded spaCy model %s %s", SPACY_MODEL, nlp.meta.get("version"))
    return nlp


def clean_raw(text: str) -> str:
    text = "" if text is None else str(text)
    text = text[:MAX_REVIEW_CHARS]
    for pattern, repl in _TEXT_FIXES:
        text = pattern.sub(repl, text)
    return text.strip()


@dataclass(frozen=True)
class ProcessedText:
    model_text: str          # lemmas with negation marking -> classifier input
    content_lemmas: tuple    # informative lemmas (no negation prefix) -> keywords/topics
    tokens: tuple            # raw token texts (for transparency)


def _is_negator(tok) -> bool:
    low = tok.lower_
    return low in NEGATORS or tok.dep_ == "neg"


def process_doc(doc) -> ProcessedText:
    out: list[str] = []
    content: list[str] = []
    scope = 0
    for tok in doc:
        if tok.is_space:
            continue
        if _is_negator(tok):
            low = tok.lower_
            out.append(NEGATOR_NORMAL.get(low, low if low in NEGATORS else "not"))
            scope = NEGATION_WINDOW
            continue
        if tok.pos_ in SCOPE_BREAK_POS or tok.lower_ in CONTRAST or tok.is_punct:
            if tok.lower_ in CONTRAST:
                out.append(tok.lower_)
            scope = 0
            continue
        if tok.like_num or tok.like_url or tok.like_email:
            continue
        lemma = tok.lemma_.lower().strip()
        if not lemma or not re.search(r"[a-z]", lemma):
            continue
        if tok.is_stop and tok.lower_ not in KEEP_WORDS:
            continue
        if scope > 0:
            out.append("neg_" + lemma)
            scope -= 1
        else:
            out.append(lemma)
        if tok.pos_ in {"NOUN", "PROPN", "ADJ", "VERB", "ADV"} and not tok.is_stop and len(lemma) > 2:
            content.append(lemma)
    return ProcessedText(" ".join(out), tuple(content), tuple(t.text for t in doc if not t.is_space))


_CACHE: dict[str, ProcessedText] = {}
_CACHE_LIMIT = 100_000


def process_texts(texts: Iterable[str], batch_size: int = 256) -> list[ProcessedText]:
    """Process texts with spaCy's batched ``nlp.pipe`` and an in-process cache."""
    texts = [clean_raw(t) for t in texts]
    missing = list(dict.fromkeys(t for t in texts if t not in _CACHE))
    if missing:
        nlp = get_nlp()
        for text, doc in zip(missing, nlp.pipe(missing, batch_size=batch_size)):
            if len(_CACHE) < _CACHE_LIMIT:
                _CACHE[text] = process_doc(doc)
            else:  # pragma: no cover - only for very large sessions
                _CACHE.clear()
                _CACHE[text] = process_doc(doc)
    return [_CACHE[t] if t in _CACHE else process_doc(get_nlp()(t)) for t in texts]


def preprocess_for_model(texts: Iterable[str]) -> list[str]:
    return [p.model_text for p in process_texts(texts)]


class SpacyTextNormalizer(BaseEstimator, TransformerMixin):
    """Stateless scikit-learn transformer wrapping :func:`preprocess_for_model`.

    It learns nothing from data, so placing it inside the Pipeline is leak-safe,
    and saving the Pipeline guarantees identical preprocessing at inference time.
    """

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return preprocess_for_model(list(X))
