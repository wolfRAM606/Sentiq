# Git changelog — Sentiq

This is an audit trail of every commit and push made while building Sentiq.

## Starting state

* Workspace `C:\Users\smart\Coding_Programming\Sentiq` was **empty** and **not a Git repository** (no prior work to preserve).
* `git init -b main` was run on 2026-10-27. Branch: `main`.
* At the start there was no remote. `origin` = <https://github.com/wolfRAM606/Sentiq.git> was added on 2026-10-27, once the user provided the URL. See "Push status" below.
* Commit author: the machine's global Git identity `R.Sriram <sriram.r.work@gmail.com>`, which the user has confirmed is the correct author for this project.

## Milestone 1 — Foundation, data, NLP/ML, analytics, UI, tests (2026-10-27 01:33)

| Commit | Message | Material changes | Why |
|---|---|---|---|
| `08429db` | chore: establish Sentiq project structure and dependencies | `.gitignore`, `requirements.txt` (pinned, official spaCy model wheel), `.streamlit/config.toml` (Midnight theme, 10 MB upload limit), `src/config.py`, package `__init__`s | Reproducible environment and central constants |
| `086ade4` | feat: add validated feedback ingestion and synthetic demo dataset | `src/data/loader.py`, `schema_mapping.py`, `validation.py`, `scripts/build_demo_dataset.py`, `data/sample/demo_feedback.csv` | Robust CSV ingestion that accounts for every record; synthetic demo data that is clearly labelled |
| `4fa5fe3` | feat: implement spaCy preprocessing and supervised sentiment models | `src/nlp/preprocessing.py`, `src/models/{train,evaluate,predict}.py`, `data/training/` (CSV + GPL-3.0 licence + source README), `models/` artifact + report | Genuine supervised classifier with leak-safe CV, baselines, held-out evaluation and persistence |
| `5759bbf` | feat: add aspect analytics, topics and evidence-linked insights | `config/aspect_taxonomy.json`, `src/nlp/{aspects,keywords}.py`, `src/analytics/{pipeline,metrics,topics,recommendations,reports}.py` | Clause-level aspect analysis, keywords, NMF topics, indicator, recommendations, reports |
| `59c77d0` | feat: build interactive Sentiq dashboard | `app.py`, `pages/1–7`, `src/ui/{theme,charts,components,state}.py`, `static/` logo | Seven-page Streamlit product with shared filters and the Midnight Intelligence design |
| `dae5dd8` | test: add data, NLP, model and app smoke tests | `tests/` (conftest + 4 modules) | Automated verification |

**Tests before these commits:** `python -m pytest -q` → **62 passed**. The first run found one real failure: the
column-mapping heuristic matched "sentiments" as a date column because it contains "time". The matcher was fixed
before `086ade4` was committed, and the rerun passed.

**Pushed:** no (no remote configured).

## Milestone 2 — Visual polish and documentation (2026-10-27 01:44)

| Commit | Message | Material changes | Why |
|---|---|---|---|
| `eb37ef1` | fix: polish dashboard visuals found during browser inspection | `src/ui/charts.py`, `src/ui/state.py`, `pages/6_Effectiveness_Insights.py`, `src/models/train.py`, `models/` | Browser inspection found stray "undefined" chart titles, crowded legends, clipped labels, an overflowing formula and badly ordered table columns. The training report now records the full spaCy model name; retraining reproduced identical metrics |
| `e0e23d1` | docs: add README, methodology, architecture, dataset provenance and viva guide | `README.md`, `docs/*.md` | Setup, deployment, academic documentation |

These two commits were first created with an inaccurate message: the earlier fix commit claimed the
column-mapping change, which was already in `086ade4`. Because they had never been pushed, they were recreated
locally with accurate messages using `git reset --soft`. No published history was rewritten.

**Tests:** `python -m pytest -q` → **62 passed** (after the UI fixes and retraining).
**Pushed:** no (no remote configured).

## Milestone 3 — Deployment hardening, formula documentation, status files

The commit that adds this section (`chore: pin deployment dependencies and add status and changelog`; see `git log`
for its hash) contains:

* `requirements.txt`: pins `pyarrow==24.0.0` and `scipy==1.13.1`. A clean-virtualenv install had resolved pyarrow 26,
  which requires NumPy ≥ 2 and broke `import sklearn` alongside the pinned `numpy==1.26.4`.
* The effectiveness indicator is documented as 50% positive share + 50% negative complement, with the derivation and
  the 70/30 discrepancy (user decision), in the methodology doc, viva guide, in-app methodology, Effectiveness page
  caption and report text. The formula itself is unchanged.
* `IMPLEMENTATION_STATUS.md` and this changelog.

**Tests:** 62 passed in the development environment, and 62 passed in a fresh Python 3.11 virtualenv built from
`requirements.txt`. The clean-environment server started and returned `/_stcore/health` → ok.
**Pushed:** no (no remote configured).

## Push status

| Date | Remote | Branch | Result | Commits included |
|---|---|---|---|---|
| 2026-10-27 02:02 | `origin` (https://github.com/wolfRAM606/Sentiq.git, empty before the push) | `main` → `main` (new branch, upstream set) | ✅ Succeeded. `git ls-remote origin main` = `1a55121` | `08429db` … `1a55121` (all 9 commits above) |
| 2026-10-27 | `origin` | `main` | See `git log origin/main` | `docs: record GitHub push` (this changelog update) |

The "Pushed: no" notes in Milestones 1–3 describe the state when each milestone was committed. All of those commits
were included in the first push above.

Pushing to GitHub does **not** deploy the app. Streamlit Community Cloud deployment is a separate manual step
(see README → Deploying). **The app has not been deployed yet.**
