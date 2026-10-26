# Sentiq — NLP-Powered Course Feedback Intelligence

*Every response tells a story.*

**Academic project title:** An Automated Text Mining Dashboard for Evaluating Course Feedback and Teaching Effectiveness Reviews using spaCy and Streamlit

Sentiq is a Streamlit application that analyses student course feedback. It preprocesses each review with spaCy,
predicts sentiment with a trained scikit-learn classifier, links what students say to specific teaching aspects
through a transparent rule-assisted lexicon, discovers recurring keywords and topics, and turns the results into
evidence-linked insights and downloadable reports.

> The bundled demonstration dataset (`data/sample/demo_feedback.csv`) is **synthetic** — written for this project, not
> real student feedback. The sentiment model is trained only on the public labelled dataset described below.

## What it does

| Page | What you can do |
|---|---|
| **Overview** | Feedback indicator, sentiment distribution, aspect-level sentiment, insights, keywords, topics, data-quality and trend views — all driven by the sidebar filters |
| **Feedback Explorer** | Upload a CSV, preview it, map columns, see a validation report, analyse it, search/sort reviews, inspect probabilities, aspect evidence and processed text, analyse a single review, download results, reset to demo data |
| **Model Lab** | Model comparison (baseline, Naive Bayes, Logistic Regression, Linear SVM), confusion matrix, per-class metrics, calibration, top features, training data audit, misclassifications, live classification, deterministic retraining |
| **Aspect Analysis** | Clause-level aspect sentiment across 12 teaching aspects, evidence drill-down, unmatched and ambiguous cases, the editable taxonomy |
| **Topics & Keywords** | Unigram/bigram keywords and noun phrases by sentiment, representative reviews, NMF topic discovery with a selectable topic count |
| **Effectiveness Insights** | The sentiment-derived feedback indicator with formula, minimum-sample warnings, aspect-level and group breakdowns, evidence-linked recommendations |
| **Reports & Methodology** | CSV / Markdown / printable HTML reports, full methodology, limitations, sources and versions |

## Measured model results

Held-out stratified test set (213 comments) from the public training data. Hyper-parameters were chosen by 5-fold
cross-validation on the training split only (848 comments). These are real results produced by `python -m src.models.train`.

| Model | CV macro-F1 (train) | Test accuracy | Test macro-F1 |
|---|---:|---:|---:|
| Majority-class baseline | 0.227 ± 0.001 | 0.516 | 0.227 |
| Multinomial Naive Bayes | 0.579 ± 0.011 | 0.714 | 0.526 |
| **Logistic Regression (primary)** | **0.644 ± 0.034** | **0.653** | **0.529** |
| Linear SVM | 0.640 ± 0.031 | 0.681 | 0.537 |

Logistic Regression per class (test): negative F1 0.662, positive F1 0.726, neutral F1 0.200. Neutral is weak
because the class is small (99 examples in total) and loosely defined in the source data. Expected calibration error 0.062.
Logistic Regression was declared the primary model before evaluation, because it gives class probabilities. It is
not swapped for whichever model scores best on the test set.

## Quick start (local)

Requires **Python 3.11** (tested with 3.11.9).

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
```

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

The app opens at <http://localhost:8501> with the demo dataset already analysed. `requirements.txt` installs the
spaCy `en_core_web_sm` model from the official spaCy release wheel. If you installed dependencies another way, run
`python -m spacy download en_core_web_sm`.

### Retrain and test

```bash
python -m src.models.train
```

```bash
python -m pytest -q
```

Training is deterministic (seed 42) and takes about 10 seconds. It writes `models/sentiment_model.joblib` (~75 KB)
and `models/training_report.json`. If the model artifact is missing or cannot be loaded, the app retrains from
the bundled labelled dataset on first start. If that also fails, the app tells you and keeps working without sentiment.

## Uploading your own data

* CSV with one review per row, up to 10 MB / 10,000 rows. UTF-8, UTF-8-BOM, Windows-1252 and Latin-1 encodings
  and `,` `;` tab `|` delimiters are detected automatically.
* One text column is required (`review`, `feedback`, `comment(s)`, `text`, `response`, …). Optional: course/subject,
  instructor/teacher/faculty, date, semester/term, rating/score. An existing sentiment/label column is kept for
  reference only.
* Empty, non-alphabetic and duplicate reviews are excluded **with a reason** and listed in the validation report.
* Uploads are processed in memory. Sentiq does not write them to disk or log review text.

## Deploying to Streamlit Community Cloud

1. Push this repository to GitHub (see `docs/GIT_CHANGELOG.md` for the current push status).
2. At <https://share.streamlit.io>, create an app from the repository, branch `main`, main file `app.py`.
3. Under **Advanced settings**, select **Python 3.11**.
4. Deploy. No secrets or API keys are needed. The first build installs spaCy and the `en_core_web_sm` wheel.

## Project structure

```
app.py                         Streamlit entry point (navigation, sidebar status, global filters)
pages/                         Seven application pages
src/config.py                  Paths, labels, thresholds, product identity
src/data/                      loader.py (CSV ingestion), schema_mapping.py, validation.py
src/nlp/                       preprocessing.py (spaCy + negation), aspects.py, keywords.py
src/models/                    train.py, evaluate.py, predict.py (single prediction interface)
src/analytics/                 pipeline.py, metrics.py, topics.py, recommendations.py, reports.py
src/ui/                        theme.py (Midnight Intelligence), charts.py, components.py, state.py
config/aspect_taxonomy.json    Editable teaching-aspect lexicon
data/sample/demo_feedback.csv  Synthetic demonstration data (scripts/build_demo_dataset.py)
data/training/                 Public labelled dataset + its GPL-3.0 licence
models/                        Trained pipeline + training report
tests/                         pytest suite (data, NLP, models, analytics, Streamlit AppTest)
docs/                          methodology, architecture, dataset provenance, viva guide, Git changelog
```

## Data sources and licences

* **Training data:** *Student Feedback Data*, <https://github.com/mbalvi/student_feedback_data>. The source
  repository declares **GPL-3.0**, and a copy of that licence is included at `data/training/LICENSE-GPL-3.0.txt`.
  Its 1,086 rows were verified (551 positive, 436 negative, 99 neutral). See `docs/dataset_provenance.md`.
* **Demo data:** synthetic and project-authored.
* **EduRABSA** was reviewed but not used (see provenance document).

## Limitations

* The model is trained on 1,061 short comments from one institution. It reaches about 65% accuracy and 0.53
  macro-F1 on held-out data, and it is weakest on neutral comments. Read the predictions as indicative only.
* Aspect analysis is rule-assisted, not a trained aspect model. No aspect-level accuracy is claimed.
* The feedback indicator summarises predicted opinion. It is not an objective measure of teaching quality and
  should not be used on its own for evaluation decisions.

More detail: `docs/methodology.md`, `docs/architecture.md`, `docs/viva_guide.md`.
