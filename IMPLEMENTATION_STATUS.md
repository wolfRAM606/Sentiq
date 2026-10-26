# Implementation status — Sentiq

*Last updated: 2026-10-27*

## Phase summary

| Phase | Status | Notes |
|---|---|---|
| 1 Workspace & dataset audit | ✅ Done | Empty workspace; Python 3.11.9 with all deps present. mbalvi dataset verified (1,086 rows, cp1252, GPL-3.0, 23 duplicates, 1 conflicting text). EduRABSA reviewed and not integrated (Zenodo-hosted, CC BY-NC-SA, quadruplet format) |
| 2 Foundation | ✅ Done | Entry point, navigation, theme, ingestion/validation, synthetic demo data |
| 3 NLP & supervised ML | ✅ Done | spaCy preprocessing with negation scope; baseline/NB/LR/SVM; CV on training split; held-out evaluation; artifact + reload check |
| 4 Core analytics | ✅ Done | Aspects (12, clause-level), keywords, noun phrases, NMF topics, indicator, recommendations |
| 5 Interface | ✅ Done | Midnight Intelligence theme; 7 pages inspected in the in-app browser; defects fixed |
| 6 Exports & docs | ✅ Done | CSV / Markdown / HTML exports; README, methodology, architecture, provenance, viva guide, changelog |
| 7 Testing & hardening | ✅ Done | 62 pytest tests passing; upload → analysis tested in the browser; small-data states checked; clean-venv install verified (see below) |
| 8 Delivery | ⚠️ Partial | All work committed locally on `main`. **Not pushed** (no remote configured). **Not deployed** to Streamlit Cloud |

## Measured results (from `models/training_report.json`)

* Logistic Regression (primary): CV macro-F1 0.644 ± 0.034; test accuracy **0.653**; test macro-F1 **0.529**; ECE 0.062.
* Majority baseline test macro-F1 0.227. Naive Bayes 0.526. Linear SVM 0.537.
* Per-class F1: negative 0.662, neutral 0.200, positive 0.726.

## Verification performed

* `python -m pytest -q` → **62 passed** (data, NLP, model, analytics/export, and Streamlit AppTest for all 7 pages,
  filters, empty selections and single-review analysis).
* App launched locally (`streamlit run app.py`). All 7 pages rendered in the in-app browser with no exceptions and
  no server warnings.
* Browser workflow: CSV upload with non-standard column names and a `;` delimiter → auto-mapping → analysis →
  9 records (7 valid, 2 excluded with reasons) → every page shows small-data states → reset to demo.
* Phone-width check (375 px): no horizontal overflow; the hero collapses to one column.
* Clean virtualenv install of `requirements.txt`: the first attempt **failed**: pip resolved `pyarrow` 26, which needs NumPy ≥ 2 and broke `import sklearn`. Fixed by pinning `pyarrow==24.0.0` and `scipy==1.13.1` (the versions tested locally). After that, a fresh Python 3.11 venv installs cleanly, loads `en_core_web_sm`, passes **62/62 tests**, and serves the app (`/_stcore/health` → ok)
* Retraining is deterministic: a second training run reproduced identical metrics.

## Not verified / known limitations

* Not deployed to Streamlit Community Cloud. No push was made, because the repository has no remote.
* File downloads were verified by unit tests of the export content, not by clicking download buttons in the browser.
* Model performance is modest, especially for the neutral class (see methodology).
* No aspect-level accuracy: there is no aspect-annotated evaluation data.
* Light theme toggle not implemented (optional in the brief). Dark mode only.
* Specification inconsistency resolved by the user: the brief's "70/30" wording would give 100 × (p + 0.3·u), not the
  stated 100 × (p + 0.5·u). The user chose to keep 100 × (p + 0.5·u), documented as 50% positive share + 50% negative
  complement, with the derivation in `docs/methodology.md`.

## Exact next actions for the user

1. Create a GitHub repository, then run `git remote add origin <url>` and `git push -u origin main`.
2. Deploy on <https://share.streamlit.io>: main file `app.py`, Python 3.11.
