"""Hybrid, lexicon-assisted aspect analysis.

This is a transparent rule-assisted component. It is not a trained aspect-based model.
Each review is split into sentences (spaCy) and then into clauses at contrastive
conjunctions ("but", "however", ...). Aspect terms/phrases from the configurable
taxonomy are matched on lemmas and lowercase tokens; each match keeps the clause
that triggered it so that aspect sentiment can be predicted at clause level
instead of copying the whole-review sentiment onto every aspect.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from spacy.matcher import PhraseMatcher

from src.config import TAXONOMY_PATH
from src.nlp.preprocessing import CONTRAST, NEGATORS

MIN_CLAUSE_TOKENS = 3
MATCH_PHRASE = "phrase"
MATCH_TERM = "term"
MATCH_CONTEXT = "context-confirmed term"
MATCH_GENERAL = "general (no specific aspect)"


def _is_neg_token(tok) -> bool:
    return tok.lower_ in NEGATORS or tok.dep_ == "neg"


def is_negated(tokens, span, window: int = 3) -> bool:
    """True when a negator governs, or closely precedes, one of the matched tokens.

    Conservative: a negator is linked to a match if it attaches to the matched
    token or to the matched token's head (e.g. "is *not* punctual", "*no* knowledge"),
    or appears at most ``window`` tokens before it within the same clause.
    """
    negs = [t for t in span if _is_neg_token(t)]
    if not negs:
        return False
    for tok in tokens:
        for n in negs:
            if n.head == tok or n.head == tok.head or tok.head == n:
                return True
            if 0 < tok.i - n.i <= window:
                return True
    return False


@dataclass
class Aspect:
    id: str
    label: str
    description: str
    terms: set
    phrases: list
    ambiguous_terms: dict
    exclude_phrases: list
    action_negative: str
    action_positive: str


@dataclass
class Taxonomy:
    aspects: list
    general_targets: set
    version: int = 1

    @property
    def by_id(self) -> dict:
        return {a.id: a for a in self.aspects}


def load_taxonomy(path: Path | str = TAXONOMY_PATH) -> Taxonomy:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return taxonomy_from_dict(raw)


def taxonomy_from_dict(raw: dict) -> Taxonomy:
    aspects = []
    seen = set()
    for a in raw.get("aspects", []):
        if not a.get("id") or a["id"] in seen:
            raise ValueError(f"Aspect ids must be unique and non-empty (problem with {a.get('id')!r}).")
        seen.add(a["id"])
        aspects.append(Aspect(
            id=a["id"], label=a.get("label", a["id"]), description=a.get("description", ""),
            terms={t.lower() for t in a.get("terms", [])},
            phrases=[p.lower() for p in a.get("phrases", [])],
            ambiguous_terms={k.lower(): {c.lower() for c in v} for k, v in a.get("ambiguous_terms", {}).items()},
            exclude_phrases=[p.lower() for p in a.get("exclude_phrases", [])],
            action_negative=a.get("action_negative", ""), action_positive=a.get("action_positive", ""),
        ))
    return Taxonomy(aspects, {t.lower() for t in raw.get("general_targets", [])}, raw.get("version", 1))


@dataclass
class AspectMatch:
    aspect_id: str
    aspect_label: str
    evidence: str            # clause (or sentence) that triggered the match
    sentence: str
    terms: list              # surface forms of the matched words
    match_type: str
    negated: bool
    start_char: int
    end_char: int


@dataclass
class DocAspects:
    matches: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)   # [{"term", "aspect_id", "sentence"}]


class AspectAnalyzer:
    def __init__(self, nlp, taxonomy: Taxonomy | None = None):
        self.nlp = nlp
        self.taxonomy = taxonomy or load_taxonomy()
        self._lemma = PhraseMatcher(nlp.vocab, attr="LEMMA")
        self._lower = PhraseMatcher(nlp.vocab, attr="LOWER")
        self._excl_lemma = PhraseMatcher(nlp.vocab, attr="LEMMA")
        self._excl_lower = PhraseMatcher(nlp.vocab, attr="LOWER")
        self.term_index: dict[str, list[str]] = {}
        self.ambiguous_index: dict[str, list[tuple[str, set]]] = {}
        for asp in self.taxonomy.aspects:
            if asp.phrases:
                pdocs = list(nlp.pipe(asp.phrases))
                self._lemma.add(asp.id, pdocs)
                self._lower.add(asp.id, [nlp.make_doc(p) for p in asp.phrases])
            if asp.exclude_phrases:
                edocs = list(nlp.pipe(asp.exclude_phrases))
                self._excl_lemma.add(asp.id, edocs)
                self._excl_lower.add(asp.id, [nlp.make_doc(p) for p in asp.exclude_phrases])
            for t in asp.terms:
                self.term_index.setdefault(t, []).append(asp.id)
            for t, ctx in asp.ambiguous_terms.items():
                self.ambiguous_index.setdefault(t, []).append((asp.id, ctx))

    # ------------------------------------------------------------------
    @staticmethod
    def clauses(sent):
        """Split a sentence span into clauses at contrastive conjunctions / semicolons."""
        bounds, start = [], sent.start
        for tok in sent:
            if tok.i > sent.start and (tok.lower_ in CONTRAST or tok.text == ";"):
                if tok.i > start:
                    bounds.append((start, tok.i))
                start = tok.i
        bounds.append((start, sent.end))
        return [sent.doc[s:e] for s, e in bounds if e > s]

    def analyze_doc(self, doc) -> DocAspects:
        result = DocAspects()
        tax = self.taxonomy.by_id
        excluded: dict[str, set[int]] = {}
        for matcher in (self._excl_lemma, self._excl_lower):
            for mid, s, e in matcher(doc):
                excluded.setdefault(self.nlp.vocab.strings[mid], set()).update(range(s, e))
        phrase_hits: list[tuple[str, int, int]] = []
        for matcher in (self._lemma, self._lower):
            for mid, s, e in matcher(doc):
                phrase_hits.append((self.nlp.vocab.strings[mid], s, e))

        for sent in doc.sents:
            sent_lemmas = {t.lemma_.lower() for t in sent} | {t.lower_ for t in sent}
            for clause in self.clauses(sent):
                content_tokens = [t for t in clause if not t.is_punct and not t.is_space]
                use_span = clause if len(content_tokens) >= MIN_CLAUSE_TOKENS else sent
                found: dict[str, dict] = {}

                def add(aid, tokens, mtype):
                    if any(t.i in excluded.get(aid, set()) for t in tokens):
                        return
                    entry = found.setdefault(aid, {"terms": [], "type": mtype, "tokens": []})
                    entry["terms"].extend(t.text for t in tokens)
                    entry["tokens"].extend(tokens)
                    if mtype == MATCH_PHRASE:
                        entry["type"] = MATCH_PHRASE

                for aid, s, e in phrase_hits:
                    if clause.start <= s < clause.end:
                        add(aid, list(doc[s:e]), MATCH_PHRASE)
                for tok in clause:
                    keys = {tok.lemma_.lower(), tok.lower_}
                    for key in keys:
                        for aid in self.term_index.get(key, []):
                            add(aid, [tok], MATCH_TERM)
                        for aid, ctx in self.ambiguous_index.get(key, []):
                            if aid in found:
                                continue
                            if ctx & (sent_lemmas - keys):
                                add(aid, [tok], MATCH_CONTEXT)
                            else:
                                result.ambiguous.append({"term": tok.text, "aspect_id": aid,
                                                         "aspect_label": tax[aid].label, "sentence": sent.text.strip()})
                for aid, info in found.items():
                    negated = is_negated(info["tokens"], clause)
                    result.matches.append(AspectMatch(
                        aid, tax[aid].label, use_span.text.strip(), sent.text.strip(),
                        list(dict.fromkeys(info["terms"])), info["type"], negated,
                        use_span.start_char, use_span.end_char,
                    ))

        if not result.matches and "overall" in tax:
            for sent in doc.sents:
                hits = [t for t in sent if t.lower_ in self.taxonomy.general_targets or t.lemma_.lower() in self.taxonomy.general_targets]
                evaluative = [t for t in sent if t.pos_ in {"ADJ", "ADV", "VERB"} and not t.is_stop]
                if hits and evaluative:
                    negated = is_negated(evaluative + hits, sent)
                    result.matches.append(AspectMatch("overall", tax["overall"].label, sent.text.strip(), sent.text.strip(),
                                                      [hits[0].text], MATCH_GENERAL, negated, sent.start_char, sent.end_char))
                    break
        # remove ambiguous candidates that ended up confirmed for the same aspect
        matched_ids = {m.aspect_id for m in result.matches}
        result.ambiguous = [a for a in result.ambiguous if a["aspect_id"] not in matched_ids]
        return result

    def analyze_texts(self, texts: list[str]) -> list[DocAspects]:
        return [self.analyze_doc(d) for d in self.nlp.pipe(texts, batch_size=256)]
