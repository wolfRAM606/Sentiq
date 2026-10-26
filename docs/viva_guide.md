# Viva guide — Sentiq

**Title:** An Automated Text Mining Dashboard for Evaluating Course Feedback and Teaching Effectiveness Reviews using spaCy and Streamlit
**Product:** Sentiq — NLP-Powered Course Feedback Intelligence (*Every response tells a story.*)

## 60-second pitch

Sentiq turns free-text student feedback into evidence. It reads each review with spaCy, predicts its sentiment
with a Logistic Regression model trained on a public labelled dataset of 1,086 student comments, finds which
teaching aspects each review talks about using a transparent lexicon, and assigns sentiment to the clause that
mentions each aspect. The dashboard shows distributions, aspect comparisons, keywords, topics and an explainable
feedback indicator. Every recommendation links back to the reviews that triggered it. It is built in Python with
Streamlit, needs no paid APIs, and reports its real (modest) accuracy honestly.

## Demo script (5 minutes)

1. **Overview:** point out the synthetic-data badge, the feedback indicator and its formula note, and the KPI
   counts (84 valid, 5 excluded). Walk through the donut chart, the aspect sentiment bars with their n values,
   and the generated insights.
2. **Sidebar filters:** choose *CS305 Machine Learning*. Every KPI and chart updates. Clear the filters.
3. **Feedback Explorer:** upload a small CSV and show the auto-mapped columns. Click Analyse and open the
   validation report, which lists excluded rows and their reasons. Inspect one review: probabilities, aspect
   evidence, processed text with `neg_`. Then use **Analyse a single review** with *"The lectures were clear but
   the assignments were confusing."*, which gives two aspects with different clause sentiment.
4. **Model Lab:** baseline comparison, confusion matrix, the low neutral F1 and why, calibration chart,
   misclassifications.
5. **Aspect Analysis:** drill into *Assignments & workload*, then show the unmatched and ambiguous terms tab.
6. **Effectiveness Insights:** the formula, the caveats, and the recommendations with evidence.
7. **Reports:** download the CSV and the HTML report.

## Likely questions and answers

**Why spaCy?** It provides industrial-strength tokenisation, lemmatisation, POS tags, dependency parses and
sentence segmentation in one fast pipeline. We use lemmas for features, POS tags to select content words and
noun chunks, dependencies for negation (`dep_ == "neg"`), and sentences and clauses for aspect evidence.

**How do you handle negation?** We do not remove negators as stopwords. Up to three content tokens after a negator
get a `neg_` prefix, stopping at punctuation or *but*. So *"not helpful"* becomes `not neg_helpful`, a different
feature from `helpful`. Bigrams also capture "not neg_helpful". A test asserts this, and another test checks that
"not helpful" gets a lower positive probability than "helpful".

**Why TF-IDF + Logistic Regression rather than BERT?** The data is small (about 1k comments). A linear model is
fast, reproducible, CPU-only and deployable on Streamlit Cloud. It gives class probabilities and interpretable
feature weights (shown in the Model Lab). The brief also excluded heavyweight deep-learning dependencies.

**How did you avoid data leakage?** Preprocessing, TF-IDF and the classifier sit inside one scikit-learn
`Pipeline`. GridSearchCV refits the whole pipeline on each training fold. Hyper-parameters are chosen only by
5-fold CV on the training split, and the stratified test split is scored once at the end. Duplicate texts were
removed before splitting, so the same comment cannot appear in both train and test.

**Your accuracy is only 65%. Is that a failure?** It is an honest result on a hard dataset: short fragments, a
noisy and small neutral class, and informal spelling. The relevant comparison is the majority baseline, which has
macro-F1 0.23; we reach 0.53. Positive and negative F1 are 0.73 and 0.66, while neutral is only 0.20. We flag
low-confidence predictions for human review, and every page reminds users that these are predictions.

**Why is Linear SVM slightly better on test but not the primary model?** Logistic Regression was chosen in advance
because it gives probabilities. Its CV score was also the highest. Switching models because of the test score
would use test-set information for model selection.

**What are macro-F1 and the confusion matrix?** F1 is the harmonic mean of precision and recall. Macro-F1 averages
F1 over the classes equally, so a weak minority class (neutral) is not hidden by a strong majority class. The
confusion matrix counts true versus predicted labels. Ours shows most errors are positive↔negative and
neutral→positive.

**Are the probabilities calibrated?** We measure calibration on the test set (ECE = 0.062) and show a reliability
chart. We do not apply post-hoc calibration, so we call the top probability a "model estimate" and add a
review-needed flag below 55% or for small margins.

**How does aspect analysis work, and is it a trained model?** No, it is a hybrid rule-assisted component. A JSON
taxonomy of 12 teaching aspects is matched on spaCy lemmas and phrases within clauses. Ambiguous words need
context, and exclusion phrases prevent known false matches. Sentiment comes from the trained classifier applied to
the clause. We report no aspect accuracy because we had no aspect-annotated evaluation data.

**What is the feedback indicator?** 100 × (positive share + ½ neutral share), on a 0–100 scale. That equals
50% positive share + 50% negative complement (1 − negative share), because p + u + n = 1 gives
0.5p + 0.5(1 − n) = p + 0.5u. 50 means positive and negative balance, and all-neutral feedback also scores 50. The
brief's "70/30" wording would give 100 × (p + 0.3u) instead: all-neutral would score 30. We chose 50/50 because it
is symmetric. It describes expressed opinion, not teaching quality. It is withheld for groups with fewer
than 15 reviews, and groups are not ranked.

**How are recommendations generated?** By deterministic rules. An issue needs at least 3 negative mentions and at
least a 35% negative share for an aspect. Each recommendation shows counts, example clauses with record ids, an
action from the taxonomy and caveats. With no evidence, there is no recommendation.

**How is topic modelling done?** TF-IDF on content lemmas, then NMF (scikit-learn) with a selectable k. Reviews are
assigned to their dominant topic, and labels are the top terms. It is skipped below 25 reviews because the topics
would be meaningless.

**What about privacy?** Uploads are processed in memory, nothing is written to disk, and logs never contain
review text. No external API calls are made.

**What would you improve next?** Evaluate the aspect component against EduRABSA, collect more neutral and
suggestion examples, try a small transformer (DistilBERT) if compute allows, add post-hoc calibration, and add
multilingual support.

## Numbers to remember

* Training data: 1,086 rows → 1,061 after cleaning (23 duplicates and 2 conflicting-label rows removed). Labels:
  548 positive, 414 negative, 99 neutral. Licence GPL-3.0. The file is cp1252-encoded.
* Split: 848 train / 213 test, stratified, seed 42, 5-fold CV.
* Logistic Regression: CV macro-F1 0.644, test accuracy 0.653, test macro-F1 0.529, ECE 0.062.
* Baseline macro-F1: 0.227.
* Demo data: 89 synthetic rows → 84 valid, 5 excluded. 12 aspects, 62 automated tests.
