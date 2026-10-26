"""spaCy preprocessing, aspect matching, keyword and topic tests."""
import pandas as pd

from src.nlp.aspects import MATCH_GENERAL, taxonomy_from_dict, AspectAnalyzer
from src.nlp.keywords import keyword_table, ngrams
from src.nlp.preprocessing import preprocess_for_model, process_texts


def test_tokenisation_and_lemmatisation():
    p = process_texts(["The assignments were explained clearly"])[0]
    assert "assignment" in p.model_text.split()
    assert "explain" in p.model_text.split()
    assert "assignments" in p.tokens


def test_negation_preserved_and_scoped():
    (text,) = preprocess_for_model(["The teacher is not helpful."])
    toks = text.split()
    assert "not" in toks and "neg_helpful" in toks
    assert "helpful" not in toks  # "not helpful" must not look like the positive feature "helpful"


def test_contractions_and_hardly():
    a, b, c = preprocess_for_model(["He doesn't explain anything", "She doesnt explain", "I hardly understood it"])
    assert "neg_explain" in a.split()
    assert "neg_explain" in b.split()
    assert c.split()[0] == "hardly" and "neg_understand" in c.split()


def test_negation_scope_stops_at_contrast():
    (text,) = preprocess_for_model(["not boring but the exams are hard"])
    toks = text.split()
    assert "but" in toks
    assert "hard" in toks and "neg_hard" not in toks


def test_empty_input():
    p = process_texts([""])[0]
    assert p.model_text == "" and p.content_lemmas == ()
    assert preprocess_for_model([]) == []


def _aspects(analyzer, nlp, text):
    return analyzer.analyze_doc(nlp(text))


def test_multiple_aspects_with_clause_evidence(analyzer, nlp):
    r = _aspects(analyzer, nlp, "The lectures were well organised, but the assignment deadlines were impossible.")
    ids = {m.aspect_id for m in r.matches}
    assert {"content", "assignments"} <= ids
    by = {m.aspect_id: m for m in r.matches}
    assert "assignment" in by["assignments"].evidence.lower()
    assert "organised" not in by["assignments"].evidence.lower()   # clause-level, not whole review


def test_unmatched_review_has_no_fabricated_aspects(analyzer, nlp):
    r = _aspects(analyzer, nlp, "The weather was nice and the canteen sells tea.")
    assert r.matches == []


def test_general_statement_maps_to_overall(analyzer, nlp):
    r = _aspects(analyzer, nlp, "She is a wonderful teacher.")
    assert [m.aspect_id for m in r.matches] == ["overall"]
    assert r.matches[0].match_type == MATCH_GENERAL


def test_ambiguous_term_needs_context(analyzer, nlp):
    no_ctx = _aspects(analyzer, nlp, "The answer was clear.")
    assert "clarity" not in {m.aspect_id for m in no_ctx.matches}
    assert any(a["term"].lower() == "clear" for a in no_ctx.ambiguous)
    ctx = _aspects(analyzer, nlp, "The lectures were clear.")
    assert "clarity" in {m.aspect_id for m in ctx.matches}


def test_fast_without_teaching_context_is_ambiguous(analyzer, nlp):
    r = _aspects(analyzer, nlp, "The wifi is fast.")
    assert "pace" not in {m.aspect_id for m in r.matches}
    r2 = _aspects(analyzer, nlp, "He teaches too fast.")
    assert "pace" in {m.aspect_id for m in r2.matches}


def test_negation_flag_is_local(analyzer, nlp):
    r = _aspects(analyzer, nlp, "He explains everything well and grading is not fair to students.")
    by = {m.aspect_id: m for m in r.matches}
    assert by["assessment"].negated is True
    assert by["clarity"].negated is False
    assert _aspects(analyzer, nlp, "Teacher has no knowledge about the subject").matches[0].negated


def test_exclude_phrase_suppresses_match(analyzer, nlp):
    r = _aspects(analyzer, nlp, "Teachers should give us practical knowledge.")
    ids = {m.aspect_id for m in r.matches}
    assert "practical" in ids and "knowledge" not in ids


def test_taxonomy_is_configurable(nlp):
    tax = taxonomy_from_dict({"general_targets": [], "aspects": [
        {"id": "food", "label": "Food", "terms": ["pizza"], "phrases": ["free lunch"]}]})
    a = AspectAnalyzer(nlp, tax)
    r = a.analyze_doc(nlp("They gave us pizza and a free lunch."))
    assert [m.aspect_id for m in r.matches] == ["food"]
    assert set(r.matches[0].terms) >= {"pizza", "free", "lunch"}


def test_keyword_table_counts_reviews_not_tokens():
    reviews = pd.DataFrame({"content_lemmas": [("exam", "exam", "hard"), ("exam", "fair"), ("notes",)],
                            "sentiment": ["negative", "positive", "neutral"]})
    kw = keyword_table(reviews, 1, min_reviews=1).set_index("term")
    assert kw.loc["exam", "reviews"] == 2
    assert kw.loc["exam", "negative"] == 1 and kw.loc["exam", "positive"] == 1
    assert ngrams(["a", "b", "c"], 2) == ["a b", "b c"]


def test_topics_skip_small_data_and_run_on_demo(demo_analysis):
    from src.analytics.topics import discover_topics

    *_, result = demo_analysis
    small = discover_topics(result.reviews.head(5), 3)
    assert not small.ok and "at least" in small.message
    big = discover_topics(result.reviews, 3)
    assert big.ok
    assert all(t["n_reviews"] > 0 and t["terms"] for t in big.topics)
    assert sum(t["n_reviews"] for t in big.topics) + int((big.assignments == -1).sum()) == len(result.reviews)
