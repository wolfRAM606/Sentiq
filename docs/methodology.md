# Sentiq: methodology

**Academic project title:** An Automated Text Mining Dashboard for Evaluating Course Feedback and Teaching Effectiveness Reviews using spaCy and Streamlit

**Product:** Sentiq · NLP-Powered Course Feedback Intelligence · *Every response tells a story.*

## 1. Objective

Help instructors and departments find patterns in free-text course feedback, and show the evidence behind each
pattern. The system has three parts: a supervised sentiment classifier, a transparent aspect analysis, and
exploratory keyword/topic mining.

## 2. Data ingestion and validation

* Bytes are decoded as UTF-8-BOM, UTF-8, Windows-1252 or Latin-1, in that order. The delimiter is sniffed from `,`, `;`, tab or `|`.
* Every column is read as a string, so the original review text is preserved byte for byte in exports.
* Limits: 10 MB per file, 10,000 rows, and 5,000 characters analysed per review (the original is kept in full).
* Exclusions, each with a reason: empty or whitespace-only reviews, reviews with no alphabetic characters, and
  duplicates of an earlier review with the same normalised text and course/instructor/semester. The rule
  `valid + excluded = total` is checked in code and in tests.
* Dates and ratings that cannot be parsed are left blank and counted in the validation report.

## 3. spaCy preprocessing

The pipeline uses `en_core_web_sm` 3.8 with tokenizer, tagger, parser, attribute ruler and lemmatizer. NER is disabled.

1. Informal contractions are normalised ("doesnt" → "doesn't").
2. Tokens are lemmatised and lowercased. Punctuation, numbers, URLs and generic stopwords are removed.
3. Negators (*not, no, never, n't, hardly, barely, nothing, without…*), contrastive conjunctions (*but, however…*)
   and intensifiers/modals (*very, too, should, must…*) are **kept**.
4. **Negation scope:** up to three content tokens after a negator get a `neg_` prefix. The scope stops at
   punctuation, conjunctions or contrast words. *"The teacher is not helpful"* becomes `teacher not neg_helpful`.
5. Content lemmas (nouns, verbs, adjectives, adverbs) are kept separately, without negation marks, for keywords and topics.

## 4. Sentiment classification

* **Data:** 1,061 cleaned labelled comments (see `dataset_provenance.md`).
* **Split:** stratified 80/20 train/test split, `random_state=42`. Train has 848 comments, test has 213.
* **Pipeline:** `SpacyTextNormalizer` → `TfidfVectorizer(sublinear_tf, word n-grams)` → classifier.
* **Candidates:** majority-class baseline, Multinomial Naive Bayes (alpha), Logistic Regression
  (`class_weight="balanced"`, C) and Linear SVM (C). The n-gram range (1,1) or (1,2) is tuned for each.
* **Model selection:** `GridSearchCV` with 5-fold stratified CV on the training split, scored by macro-F1. The test
  set is scored once after tuning. Logistic Regression was declared the primary model in advance.
* **Feature-engineering experiment:** also CV on training data only. Keeping all stopwords or adding character
  n-grams did not improve CV macro-F1 (0.61–0.64 vs 0.644), so the simpler pipeline was kept.

### Results (held-out test set, n = 213)

| Model | CV macro-F1 | Test accuracy | Test macro-F1 | Test weighted-F1 |
|---|---:|---:|---:|---:|
| Majority baseline | 0.227 | 0.516 | 0.227 | 0.352 |
| Multinomial NB | 0.579 | 0.714 | 0.526 | 0.689 |
| **Logistic Regression** | **0.644** | **0.653** | **0.529** | **0.652** |
| Linear SVM | 0.640 | 0.681 | 0.537 | 0.673 |

Logistic Regression per class:

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Negative | 0.688 | 0.639 | 0.662 | 83 |
| Neutral | 0.200 | 0.200 | 0.200 | 20 |
| Positive | 0.707 | 0.745 | 0.726 | 110 |

Confusion matrix (rows are true labels, columns are predictions, ordered negative/neutral/positive):
`[[53, 10, 20], [2, 4, 14], [22, 6, 82]]`.

**Interpretation.** All trained models beat the majority baseline by a wide margin (macro-F1 0.53 vs 0.23).
Absolute performance is modest. The gap between CV (0.64) and test (0.53) macro-F1 comes mainly from the neutral
class: only 20 test examples, so a few errors move its F1 a lot. The balanced class weights raise neutral recall
but cost some accuracy, which is why Naive Bayes has higher accuracy and slightly lower macro-F1.

### Uncertainty and calibration

Every prediction shows its three class probabilities. A prediction is flagged **review needed** when the top
probability is below 0.55, or when its margin over the runner-up is below 0.15. Expected calibration error of the
top-class probability on the test set is 0.062. No post-hoc calibration is applied, so probabilities are presented
as model estimates, not guarantees.

### Persistence

The fitted Pipeline is saved with joblib (`models/sentiment_model.joblib`, ~75 KB). After saving, it is reloaded
and its predictions compared with the in-memory model; the training report records identical predictions and a
maximum probability difference of 0.0.

## 5. Aspect-based analysis (hybrid, rule-assisted)

This is **not** a trained aspect-based model. It is a transparent lexicon-assisted component.

* **Taxonomy** (`config/aspect_taxonomy.json`), 12 aspects: clarity, subject knowledge, content & organisation,
  methodology, engagement & interaction, materials & resources, assignments & workload, assessment & grading
  fairness, pace, availability & responsiveness, practical relevance & examples, and overall experience. Each has
  terms, multi-word phrases, context-dependent terms, exclusion phrases and suggested actions.
* **Matching:** spaCy sentences are split into clauses at *but / however / although / though / whereas / yet / ;*.
  Terms are matched on lemma or lowercase form, and phrases with `PhraseMatcher` (lemma and lowercase).
* **Ambiguity:** context-dependent terms (e.g. *clear, fast, fair, mark, late*) count only when a context word appears
  in the same sentence. Otherwise they are listed as ambiguous candidates. Exclusion phrases (e.g. *practical
  knowledge*) suppress wrong matches for "subject knowledge".
* **General fallback:** a sentence that evaluates the teacher or course without any specific aspect is assigned to
  *Overall course experience* with match type "general".
* **Sentiment:** the trained classifier is applied to the triggering clause. If the clause has fewer than three
  tokens, it is applied to the whole sentence. When one review matches an aspect several times, the most
  confident clause is kept.
* **Negation flag:** set when a negator attaches to, or closely precedes, the matched word.
* "No aspect detected" is reported separately from neutral sentiment.
* **Evaluation:** no human aspect annotations were available, so **no aspect-level accuracy is claimed**. Unit
  tests check behaviour on multiple aspects, negation, ambiguous terms, exclusions and unmatched text.

## 6. Keywords and topics

* Keywords are document frequencies (number of reviews) of content-lemma unigrams and bigrams, split by predicted
  sentiment. Generic domain words (teacher, class, course…) can be hidden. Net sentiment is
  (positive − negative) / reviews.
* Noun phrases are spaCy noun chunks with determiners and pronouns removed, lemmatised.
* Topics come from TF-IDF (min_df = 2, max_df = 0.8, 1–2-grams) followed by NMF (`nndsvda`, seed 42). Each review
  is assigned to its dominant topic. Topics are labelled automatically by their top three terms, which are not
  human-verified. Topic discovery is skipped below 25 reviews, or when there are fewer than max(3k, 10) recurring
  terms. Empty topics are removed.

## 7. Feedback indicator

```
Indicator = 100 × (positive share + 0.5 × neutral share)
          = 50 × positive share + 50 × (1 − negative share)
```

This is a **50% positive share + 50% negative complement (1 − negative share)** weighting. Write p, u and n for the
positive, neutral and negative shares, so that p + u + n = 1. Then 1 − n = p + u, and

```
0.5·p + 0.5·(1 − n) = 0.5·p + 0.5·(p + u) = p + 0.5·u
```

The project brief also described the score as "70% positive share + 30% negative complement". That gives
0.7·p + 0.3·(p + u) = 100 × (p + 0.3·u), which differs from the stated formula whenever there are neutral reviews.
For example, all-neutral feedback scores 30 under 70/30 but 50 under 50/50, and a 40% / 40% / 20% (pos / neu / neg)
split scores 52 vs 60. Sentiq keeps the 50/50 version. It is symmetric, and it puts all-neutral feedback at the
midpoint of 50.

The indicator is computed from *predicted* sentiment. Aspect-level indicators require at least 3 mentioning
reviews, and group indicators require at least 15 reviews. Groups are listed alphabetically and never ranked. A
minimum-sample warning appears below 30 reviews.

## 8. Evidence-linked recommendations

These are deterministic rules applied to the per-aspect summary:

* **Issue:** at least 3 negative mentions and a negative share of at least 35%. Priority is high when the share is
  at least 50% and at least 10 reviews mention the aspect.
* **Strength:** at least 3 positive mentions and a positive share of at least 60%.

Each recommendation includes the counts, up to three example clauses with record ids, the aspect's suggested
action, and caveats about small samples, low-confidence predictions or general matches.

## 9. Limitations and appropriate use

* Predictions are imperfect (about 65% accuracy) and are especially weak for neutral comments.
* The training data comes from one institution, so the model may transfer poorly to other populations.
* The aspect lexicon can miss paraphrases, sarcasm and domain-specific vocabulary.
* Student feedback can be biased (for example, non-response bias or grade expectations), so indicators describe
  expressed opinion, not teaching quality.
* All analyses are descriptive. They do not support causal claims.
* Intended use is reflective, exploratory support. Sentiq is not meant for automated evaluation, ranking or
  personnel decisions.
