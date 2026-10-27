# Sentiq: architecture

Sentiq is a single Python/Streamlit application. It has no separate frontend, API server or database. All
processing runs in the Streamlit process, and no external API is needed at runtime.

```
             ┌──────────────── app.py (st.navigation, sidebar status + global filters) ───────────────┐
             │ pages/1_Overview … 7_Methodology_and_Reports  ──►  src/ui (theme, charts, components)  │
             └──────────────────────────────┬─────────────────────────────────────────────────────────┘
                                            │ src/ui/state.py  (session state, caching, filtered())
                  ┌─────────────────────────┼──────────────────────────────┐
                  ▼                         ▼                              ▼
       src/data (ingestion)       src/analytics/pipeline.py       src/models/predict.py
       loader → schema_mapping    analyze_reviews():               SentimentModel.predict()
       → validation               spaCy parse once per review      (single prediction interface)
                                  → preprocessing (model input)            ▲
                                  → aspects (clause evidence)              │ joblib artifact
                                  → noun phrases                   src/models/train.py
                                  → predict reviews + clauses      (load → clean → CV tune → test → save)
                                            │
                                            ▼
                      src/analytics: metrics · topics · recommendations · reports
```

## Layers

| Layer | Modules | Responsibility |
|---|---|---|
| Data | `src/data/loader.py`, `schema_mapping.py`, `validation.py` | Decode bytes, sniff the delimiter, enforce limits, map column roles, exclude invalid records with reasons, parse dates and ratings |
| NLP | `src/nlp/preprocessing.py` | Load spaCy once, normalise informal text, lemmatise, remove stopwords except negators/intensifiers, mark negation scope, cache results |
| | `src/nlp/aspects.py` | Load the taxonomy, run PhraseMatchers on LEMMA and LOWER, split clauses, check context for ambiguous terms, apply exclusions, flag local negation, assign the overall fallback |
| | `src/nlp/keywords.py` | Document-frequency n-gram and noun-phrase tables by sentiment |
| ML | `src/models/train.py` | Clean the labelled data, run a stratified split, build candidate Pipelines, run GridSearchCV (training folds only), evaluate on test, calibrate-check, extract features, save and reload-check |
| | `src/models/evaluate.py` | Accuracy, macro/weighted F1, per-class P/R/F1, confusion matrix, ECE |
| | `src/models/predict.py` | Load the artifact, fall back to deterministic retraining, or return an explicit "unavailable" model. Prediction output: label, probabilities, confidence, margin, review-needed flag, score |
| Analytics | `src/analytics/pipeline.py` | One function used for demo data, uploads and tests |
| | `metrics.py`, `topics.py`, `recommendations.py`, `reports.py` | KPIs and indicator, NMF topics with guards, rule-based recommendations, Markdown/HTML reports |
| UI | `src/ui/theme.py`, `charts.py`, `components.py`, `state.py` | Design tokens and CSS, Plotly template, HTML components (escaped), caching, filters, export frame |

## Key design decisions

* **Leak-safe pipeline.** `SpacyTextNormalizer` is a stateless scikit-learn transformer inside the `Pipeline`, so
  cross-validation fits TF-IDF and the classifier on each training fold only, and the saved artifact carries its
  own preprocessing.
* **Parse once.** `analyze_reviews` parses each review with spaCy a single time and seeds the preprocessing cache,
  so the classifier, aspect matcher and noun-phrase extractor share that parse.
* **Clause-level aspect sentiment.** Each aspect mention is scored by the same model on the clause that triggered
  it, so a mixed review can carry different sentiment for different aspects.
* **One filter function.** `state.filtered()` returns the review and mention subsets that every page uses, so KPIs,
  charts, recommendations and exports always describe the same data.
* **Caching.** `st.cache_resource` holds the model and the analyzer (keyed on the taxonomy file's mtime).
  `st.cache_data` holds dataset analysis (keyed on a content hash and the model version) and topics (keyed on the
  selected record ids and k). Retraining clears both caches.
* **Graceful degradation.** A missing artifact triggers retraining. If that fails, sentiment shows "unavailable"
  and the other analyses still work. Topic discovery is skipped below 25 reviews or when the vocabulary is too
  small. Every page shows an empty state when filters leave no reviews.
* **Privacy.** Uploads stay in memory. Logs record counts and errors, never review text.
* **Escaping.** All user text rendered through custom HTML components is passed through `html.escape`.

## Deployment

Streamlit Community Cloud with Python 3.11 and `requirements.txt` (pinned versions plus the official
`en_core_web_sm` wheel). The model artifact is 75 KB and committed. It was created with scikit-learn 1.8.0, which
is pinned. If the artifact cannot be unpickled, the app retrains in about 10 seconds from the bundled dataset.

## Web interface (v2)

```
browser ── React + TypeScript (web/) ── fetch /api/... ──► FastAPI (api/main.py) ──► src/ (same core as Streamlit)
            GSAP ScrollTrigger + Lenis (scroll motion)          api/store.py: in-memory uploads (30 min expiry)
            React Three Fiber (3D field, 3D confusion matrix)    and datasets (at most 30, least recently used first)
            TanStack Query (requests), zustand (filters in URL)  FastAPI also serves web/dist as a single-page app
```

* **One engine.** The API calls `analyze_reviews`, `apply_filters`, `aspect_summary`, `build_recommendations`,
  `discover_topics`, `export_frame` and the report builders, exactly as the Streamlit pages do. Filtering was moved
  into `src/analytics/filters.py`, and CSV export rules into `src/analytics/exports.py`, so neither interface has its
  own copy.
* **Filters** live in the URL (`?course=...&confidence=...`), so a view can be reloaded or shared, and every
  request carries them. Page-specific parameters (`focus`, `term`, `review`) use names that cannot collide with filter names.
* **Privacy.** Uploads are parsed in memory, never written to disk, and expire. The unhandled-error handler returns
  a generic message, so stack traces and review text are never sent to the client.
* **3D views are data.** The overview field places every review by sentiment score (x), model confidence (y) and
  aspect lane (z). The Model page extrudes the held-out confusion matrix. Labels are plain HTML positioned by projecting
  3D anchors each frame.
* **Motion** is scroll-triggered (reveals, count-ups, bars growing in) and fully disabled under `prefers-reduced-motion`.
* **Deployment:** a two-stage `Dockerfile` (Node build, then a Python 3.11 runtime) suits any Docker host. The
  Streamlit app continues to deploy on Streamlit Community Cloud from the same repository.
