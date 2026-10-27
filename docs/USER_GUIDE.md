# Sentiq user guide: what to upload, and how far to trust the results

## What to upload

A CSV file with **one piece of free-text feedback per row**.

| Column | Needed? | Examples of accepted names | Notes |
|---|---|---|---|
| Review text | Required | `review`, `feedback`, `comment(s)`, `response`, `text`, `Student Comment` | Write-in answers such as "What could be improved?" work best |
| Course | Optional | `course`, `subject`, `module`, `course code` | Enables course filters and group breakdowns |
| Instructor | Optional | `instructor`, `teacher`, `faculty`, `tutor`, `lecturer` | Groups under 15 reviews are never given an indicator |
| Date | Optional | `date`, `timestamp`, `submitted at` | Enables the time trend and the date filter |
| Semester / term | Optional | `semester`, `term`, `session` | |
| Rating | Optional | `rating`, `score`, `stars` | Kept for reference; it does not change predictions |

Limits: 10 MB, 10,000 rows, 5,000 characters analysed per review. Excel files must be saved as CSV first.
UTF-8, Windows-1252 and Latin-1 encodings and `,` `;` tab `|` delimiters are detected automatically.

**Good input**
* English, written in full sentences or phrases: "The lectures were clear but the assignments were too long."
* Several reviews per course or instructor. At least 30 in the selection for the indicator, 25 for topics, and 3
  mentions of an aspect before it gets an aspect indicator.

**Input that works poorly**
* Single words or ratings typed as text ("good", "5/5"). Non-alphabetic rows are excluded automatically.
* Languages other than English. The spaCy model and the classifier are English-only.
* Heavy sarcasm, or comments that are mostly about something other than teaching.
* Identifiable personal information. Remove student names and IDs before uploading.

## Is it ready for anyone to use?

It is ready as a working, tested academic tool, with these caveats:

* **It works reliably** in the sense that every feature was tested end to end (see `docs/TEST_RESULTS.md`).
  Invalid files give clear messages, every record is accounted for, and numbers on screen equal an independent
  calculation.
* **It is not highly accurate.** The sentiment model is right about 65% of the time on unseen comments (macro-F1
  0.53), and it is weakest on neutral comments (F1 0.20). Use it to *explore and prioritise* feedback, then read
  the comments it points to. Every page links back to the underlying text for exactly this reason.
* **It is not built for high-stakes use.** Do not use it alone for staff evaluation, ranking or personnel decisions.
* **Hosting is single-server and in-memory.** Uploaded datasets live in the server's memory for the session
  (the web version keeps at most 30). That suits a class or department. It isn't a multi-tenant service with
  accounts and permanent storage.

## How to get more (and better) training and test data

The model is limited mainly by its training data: 1,061 short comments from one institution, with only 99 neutral.
Ordered by impact:

1. **Label your own institution's feedback.** Export past course-evaluation comments (with permission and
   anonymised). Have two people label a random 500–1,000 as positive, neutral or negative, and resolve
   disagreements. Use a clear rule for "neutral", for example "a suggestion or a mixed comment with no overall
   lean". Inter-annotator agreement (Cohen's kappa) is worth reporting in a viva.
2. **Public, licensed datasets** (check each licence before use):
   * *EduRABSA* (CC BY-NC-SA 4.0, Zenodo doi:10.5281/zenodo.16935017): 6,500 aspect-annotated education reviews.
     It is the best source for **evaluating the aspect component**, which currently has no accuracy figure.
   * *Course Reviews University of Waterloo* (Kaggle, CC0) and the *RateMyProfessor* big dataset (Mendeley Data,
     CC BY 4.0): large volumes of course and teacher reviews. They have star ratings rather than sentiment labels,
     so map ratings to sentiment (for example 1–2 negative, 3 neutral, 4–5 positive) and spot-check a sample.
   * Coursera course reviews (Kaggle): large, but consumer MOOC reviews, so mix them in with care.
3. **Use test data that is separate from training data.** Hold out a labelled set from a different course or year.
   That tells you how well the model transfers, which a random split cannot.
4. **Retrain.** Put the new labelled CSV in `data/training/` with `comments` and `sentiments` columns (0 negative,
   1 positive, 2 neutral), or adapt `load_training_data` in `src/models/train.py`. Then run
   `python -m src.models.train` and check the new metrics in the Model Lab. All evaluation numbers update automatically.

## Two interfaces, one engine

* **Streamlit app** (`streamlit run app.py`): the version named in the academic title. Analyst-style pages with
  native tables, and the place to retrain the model.
* **Web interface** (`uvicorn api.main:app`, after `npm run build` in `web/`): a multi-section editorial
  interface with scroll animation and 3D views.

Both use the same Python code for ingestion, NLP, the classifier, aspects, topics, filters, recommendations and
exports, so they give the same numbers. `docs/TEST_RESULTS.md` records them matching on every checked value.
