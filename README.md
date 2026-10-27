# Sentiq · NLP-Powered Course Feedback Intelligence

*Every response tells a story.*

**Academic project title:** An Automated Text Mining Dashboard for Evaluating Course Feedback and Teaching Effectiveness Reviews using spaCy and Streamlit

Sentiq analyses free-text student course feedback:
- **spaCy** reads each review, with negation handled explicitly.
- A **trained scikit-learn classifier** predicts sentiment, with class probabilities and a review-needed flag.
- A **configurable lexicon** links what students say to twelve teaching aspects, scored at clause level.
- **Keyword and topic mining** surface recurring themes.
- Insights, recommendations and reports are evidence-linked: every number traces back to the comments behind it.

> The bundled demonstration dataset (`data/sample/demo_feedback.csv`) is **synthetic**: it was written for this
> project, not collected from students. The sentiment model is trained only on the public labelled dataset described below.

## Two interfaces, one engine

| | Streamlit app | Web interface |
|---|---|---|
| Run | `streamlit run app.py` | `uvicorn api.main:app` (serves `web/dist`) |
| Stack | Streamlit + Plotly | FastAPI + React, GSAP scroll animation, Three.js |
| Best for | The version named in the academic title; analyst tables; retraining the model | Presenting: multi-section pages, a 3D view of every review, a 3D confusion matrix |
| Deploy on | Streamlit Community Cloud | Any Docker host (Render, Hugging Face Spaces, Railway) |

Both call the same Python code (`src/`) for ingestion, preprocessing, the classifier, aspects, keywords, topics,
filters, recommendations and exports, so they produce the same numbers. `docs/TEST_RESULTS.md` checks this value by value.

**Rollback point:** the tested Streamlit-only version from before the redesign is preserved as tag `v1.0-streamlit`
and branch `release/v1-streamlit`.

## Measured model results

Held-out stratified test set: 213 comments. Hyper-parameters were chosen by 5-fold cross-validation on the training split only (848 comments).

| Model | CV macro-F1 (train) | Test accuracy | Test macro-F1 |
|---|---:|---:|---:|
| Majority-class baseline | 0.227 ± 0.001 | 0.516 | 0.227 |
| Multinomial Naive Bayes | 0.579 ± 0.011 | 0.714 | 0.526 |
| **Logistic Regression (primary)** | **0.644 ± 0.034** | **0.653** | **0.529** |
| Linear SVM | 0.640 ± 0.031 | 0.681 | 0.537 |

Per-class F1 (Logistic Regression): negative 0.66, positive 0.73, **neutral 0.20**. The neutral class is small and
loosely defined in the source data. Expected calibration error is 0.062. Logistic Regression was declared the primary
model in advance because it gives class probabilities.

## Quick start

Requires **Python 3.11** and, for the web interface, **Node.js 20+**.

```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
```
```bash
pip install -r requirements.txt
```

**Streamlit app** (opens at http://localhost:8501):
```bash
streamlit run app.py
```

**Web interface** (opens at http://localhost:8000):
```bash
cd web && npm ci && npm run build && cd ..
```
```bash
uvicorn api.main:app --port 8000
```

For frontend development with hot reload, run `npm run dev` in `web/` (port 5173, proxies `/api` to port 8000) with uvicorn running.

### Tests and retraining
```bash
python -m pytest -q
```
```bash
python -m src.models.train
```
79 automated tests cover data, NLP, the model, analytics and exports, the web API, and Streamlit pages run
through AppTest. The full manual browser test plan (113 checks per interface) and its results are in
`docs/TEST_PLAN.md` and `docs/TEST_RESULTS.md`.

## What to upload

A CSV with one review per row: a text column is required; course, instructor, date, semester and rating are
optional. The limits are 10 MB, 10,000 rows and 5,000 characters analysed per review. Encodings and delimiters are
detected automatically. Empty, non-alphabetic and duplicate reviews are excluded **with a reason**. Uploads stay in
memory and are never written to disk. See `docs/USER_GUIDE.md` for good and bad input, how far to trust the results,
and where to get more training data.

## Deployment

**Streamlit Community Cloud** (Streamlit app): create an app from `wolfRAM606/Sentiq`, branch `main`, main file
`app.py`, and select **Python 3.11** under Advanced settings. No secrets are needed.

**Docker** (web interface):
```bash
docker build -t sentiq .
```
```bash
docker run -p 8000:8000 sentiq
```
On Render, create a Web Service from the repository with runtime Docker. On Hugging Face Spaces, choose the Docker
SDK and set the `PORT` variable to `7860`.

## Design

Ivory, Burgundy and Sage (`docs/DESIGN_SYSTEM.md`): warm ivory surfaces, oxblood burgundy for emphasis, muted sage
for analytical highlights, ink-charcoal text, and a matching dark mode. Type is Fraunces, IBM Plex Sans and IBM Plex
Mono, all self-hosted. The layout uses square corners, hairline rules and no shadows or gradients. Motion is
scroll-driven, hover only changes colour, and `prefers-reduced-motion` is respected.

## Project structure

```
app.py, pages/                 Streamlit app (seven pages)
api/                           FastAPI web API: main.py (routes), store.py (in-memory uploads), serialize.py
web/                           React + TypeScript web interface (Vite); src/pages, src/charts, src/three, src/styles
src/data/                      CSV loading, column mapping, validation
src/nlp/                       spaCy preprocessing with negation scope, aspect matching, keywords
src/models/                    training, evaluation, prediction (one interface for every page)
src/analytics/                 pipeline, filters, metrics, topics, recommendations, reports, exports
src/ui/                        Streamlit theme, charts, components, state
config/aspect_taxonomy.json    editable teaching-aspect lexicon
data/sample/, data/training/   synthetic demo data; public labelled training data with its GPL-3.0 licence
models/                        trained pipeline and training report
static/                        logo and self-hosted fonts (OFL) for the Streamlit app
tests/                         pytest suite
docs/                          methodology, architecture, provenance, design system, user guide, test plan and
                               results, viva guide, Git changelog
```

## Data sources and licences

* **Training data:** *Student Feedback Data*, https://github.com/mbalvi/student_feedback_data. The source
  repository declares **GPL-3.0** (a copy is in `data/training/`). It has 1,086 rows, verified as 551 positive,
  436 negative and 99 neutral, and 1,061 after cleaning. See `docs/dataset_provenance.md`.
* **Fonts:** Fraunces and IBM Plex, both under the SIL Open Font License (copies in `static/fonts/`).

## Limitations

* About 65% accuracy on held-out comments, and weakest on neutral ones. Use Sentiq to explore and prioritise,
  then read the comments it points to.
* Aspect analysis is rule-assisted, not a trained aspect model, so no aspect-level accuracy is claimed.
* The feedback indicator summarises expressed opinion. It should be read alongside other evidence and not used
  on its own for staff evaluation.
* Datasets are held in server memory, which suits a class or department, not a multi-tenant service.
