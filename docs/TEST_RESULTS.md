# Sentiq v1 (Streamlit): test results

Run on 2026-10-27 against the plan in `docs/TEST_PLAN.md`. UI tests were performed in a real browser against the
running app (`streamlit run app.py`): selecting options, typing, clicking buttons, uploading files and fetching
the exact files that download buttons serve. Expected values came from an independent Python calculation on the
same data, not from the UI. Table contents that the browser draws on a canvas were checked by running the real app
script through Streamlit's AppTest (`tests/test_ui_tables.py`).

**Totals: 113 planned checks. 5 defects found (4 functional bugs and 1 wording error), fixed and re-tested. 1 known model limitation recorded.
Automated suite: 70 passed.**

## Bugs found and fixed during testing

| # | Found by | Bug | Fix | Re-test |
|---|---|---|---|---|
| 1 | B11 | A CSV with two columns of the same name was accepted silently (pandas renamed the second to `review.1`) | Raw header row checked before parsing; clear error naming the column | Pass (browser + new unit test) |
| 2 | F9/F10 | "Clear filters" and loading a new dataset reset the stored values but not the widgets, so stale selections came back on the next change and combined into "0 of 84 reviews" | Filter widgets now use versioned keys; clearing creates fresh widgets | Pass (all filters re-run in browser + new regression test) |
| 3 | G7 | Single-review analysis listed an aspect twice when two clauses matched it | One row per aspect, keeping the most confident clause, the same rule as dataset analysis | Pass (AppTest assertion) |
| 4 | M3 | Report preview used `st.components.v1.html`, deprecated with a removal date already passed (2026-06-01) | Replaced with `st.iframe` | Pass (preview renders, warning gone) |
| 5 | E4 | Insight text said "1 reviews … they are"; same for "1 predictions" | Singular/plural wording | Pass |

## Known limitation (not a code bug)

* G7: in "The lectures were clear **but** the assignment instructions were confusing", the second clause is
  classified neutral (51%), not negative. This is the classifier's measured weakness (neutral F1 0.20), shown
  honestly with a low-confidence flag.

## Results by area

### A. Environment and startup: all pass
| ID | Result | Evidence |
|---|---|---|
| A1 | Pass | Fresh Python 3.11.9 venv: `pip check` "No broken requirements found". (The earlier pyarrow/NumPy conflict was already fixed by pinning) |
| A2 | Pass | Health endpoint `ok` |
| A3 | Pass | Demo loads on first visit with the synthetic-data notice |
| A4 | Pass | Sidebar "Model: trained LR" |
| A5 | Pass | Artifact deleted: app retrained in about 7 s and said so in the Model Lab; no exception |
| A6 | Pass | Artifact replaced with garbage: load error logged, retrained, no exception |
| A7 | Pass | `test_no_api_key_dependency`; no network calls in the server log |

### B. Ingestion and validation: all pass (after fix #1)
| ID | Result | Evidence |
|---|---|---|
| B1 | Pass | 14 rows gave 10 valid and 4 excluded |
| B2 | Pass | BOM file: encoding utf-8-sig, same 10/4 result |
| B3 | Pass | Detected cp1252; accented text read correctly |
| B4 | Pass | `;`, tab and `|` each detected; 6 valid each |
| B5–B8 | Pass | Empty, header-only, malformed and binary files each give a specific error and no Analyse button |
| B9 | Pass | 10.6 MB file refused: "File must be 10.0MB or smaller" |
| B10 | Pass | 12,000 rows: warning, first 10,000 analysed in 20.4 s |
| B11 | Pass after fix | "The CSV has duplicate column names (review)" |
| B12 | Pass | Student Response / Module / Tutor / Timestamp / Term / Stars all auto-mapped |
| B13 | Pass | Remapping the text column to Tutor analysed the tutor names |
| B14 | Pass | "Each column can be mapped to only one role." Analyse hidden |
| B15 | Pass | Numeric-only text column: "No valid reviews remain…"; previous dataset kept |
| B16–B18 | Pass | 2 empty, 1 duplicate (same course) and 1 non-alphabetic row excluded with reasons; same text in another course kept |
| B19 | Pass | "not a date" counted as unparseable; `03/09/2025` and `Sept 12 2025` parsed |
| B20 | Pass | "two" counted as non-numeric; "4,5" read as 4.5 |
| B21 | Pass | Truncation warning; the export keeps all 7,098 characters |
| B22 | Pass | Chinese, French and Spanish text displayed and exported intact |
| B23 | Pass | `<script>` shown as escaped text; no script or `<b>` elements injected; exported verbatim |
| B24 | Pass | 14 = 10 + 4 on screen; the export has 10 rows |
| B25 | Pass | Exported review text is identical to the input |

### C. NLP: all pass
C1–C5, C9, C10 and C12 are automated (pass). In the browser:
| ID | Result | Evidence |
|---|---|---|
| C2 | Pass | Processed text `too assignment no neg_time neg_actually neg_learn …` shown for record 12 |
| C6, C7 | Pass | Mixed review: clarity evidence "The lectures were clear"; assignments evidence is the "but…" clause |
| C8 | Pass | "The answer was clear.": no aspect; listed as an ambiguous 'clear' |
| C11 | Pass | Unrelated sentence: "No teaching aspect detected." |
| C13 | Pass | Adding "canteen" to the taxonomy changed the result with no restart; reverting changed it back |
| C14 | Pass | Keyword counts (assignment 8, help 7, clear 6, good 6, exam 5) equal the independent calculation |
| C15 | Pass | Noun phrases instructor / class / course / lecture equal the independent calculation |
| C16 | Pass | Small selections show "Topic discovery needs at least 25 reviews" |
| C17, C18 | Pass | k = 2…8 set with the real slider: topic sizes equal the independent calculation for every k and sum to 84 |

### D. Model: all pass
D1–D8 and D11 are automated (pass).
| ID | Result | Evidence |
|---|---|---|
| D9 | Pass | Retrain button: progress bar, finished in under 5 s, macro-F1 0.529 again; only timestamps changed in the artifact |
| D10 | Pass | Flagged at 47% and at 50% with a 14% margin; not flagged at 57% with a 24% margin |
| D12 | Pass | 0.529 / 0.653 / 213 / 0.227 / ECE 0.062 / 74 errors / SVM 0.537: all equal the JSON report |

### E. Overview: all pass
E1–E3: 84 reviews; 53 / 5 / 26 (63 / 6 / 31%); indicator 66.1; average +0.16; most positive "Overall course
experience", most negative "Assignments & workload". All equal the independent values.
E4: all 7 insight sentences match the independent values. E5: donut, topic and trend charts each total 84.

### F. Filters: all pass (after fix #2)
| ID | Value | Shown | Expected |
|---|---|---|---|
| F1 | Course CS305 | 22; 14/0/8; 63.6; +0.13 | identical |
| F2 | Instructor C | 20; 15/0/5; 75.0; +0.24 | identical |
| F3 | Spring 2026 | 42; 20/3/19; 51.2; +0.02 | identical |
| F4 | neutral | 5; 0/5/0; 50.0 | identical |
| F5 | Teaching pace / no aspect | 9; 4/1/4; 50.0 / 1; 100.0 | identical |
| F6 | confident / review needed | 57; 39/1/17; 69.3 / 27; 14/4/9; 59.3 | identical |
| F7 | 1 Sep – 31 Dec 2025 | 42; 81.0 | identical |
| F8 | Fall 2025 + CS305 + neutral | empty state on all 6 pages, 0 errors | as specified |
| F9 | Clear filters | widgets reset to All, "all 84" | as specified |
| F10 | New dataset after a filter | all widgets reset | as specified |
| F11 | CS305, then exports | CSV has 22 rows, all CS305; Markdown "Selection: 22 of 84" | as specified |

Every filter was also checked on all six pages (the "N of 84" chip is identical everywhere).

### G–L. Page controls: all pass (G7 after fix #3)
G1 search (8 matches, all contain the term), G2 four sort orders, G3 card count, G4 inspector (22 / 6 / 72%
matches the pipeline), G5 download (8 rows = 8 matches), G6 empty warning, G8 validation report, G9 reset.
H1 five tabs, H2 feature class switch, H3 error filter (only neutral rows), H4 "not helpful…" gives Negative 93%.
I1 all 12 aspect rows equal the independent values, I2 drill-down (9 mentions; 4 negative clauses), I3 expander
shows the full review, I4 unmatched/ambiguous tables equal the pipeline counts, I5 12 aspects.
J1–J7 (unigram/bigram, minimum reviews 5 gives 9 terms, slider 15→10, generic toggle, term reviews, noun phrases, topics).
K1 66.07 = 100 × (53/84 + 0.5 × 5/84), K2 warning at 22 but not at 84, K3 contributing reviews, K4 groups under 15 withheld,
K5 11 / 5 / 6 recommendations, K6 every evidence id is a valid (non-excluded) record.
L1 five downloads (84-row CSV, HTML report with the title and no scripts, Markdown with 11 recommendations, 120
aspect mentions, 5 excluded rows), L2 preview, L3 methodology title, formula, source and licence.

### M. Cross-cutting: all pass (M3 after fix #4)
| ID | Result | Evidence |
|---|---|---|
| M1 | Pass | 375, 768 and 1440 px: no horizontal overflow on any of the 7 pages |
| M2 | Pass | No application errors in the console. The only 404s came from the test re-fetching expired download links |
| M3 | Pass after fix | Only warning was the deprecation (fixed); no tracebacks |
| M4 | Pass | 5,000 reviews analysed (4,998 valid); 10,000 uncached in 20.4 s |
| M5 | Pass | No review text anywhere in the server log |
| M6 | Pass | A second tab gets its own demo dataset while the first keeps its upload |

---

# Sentiq v2 (web interface): test results

Run on 2026-10-27 against the same plan, adapted to the web interface (`uvicorn api.main:app`, built from `web/`).
Every check was done in a real browser by uploading fixture files, typing, selecting, clicking, pressing keys and
fetching the files that download links serve. Expected values are the same independent Python calculations used for v1.
API behaviour is also covered by `tests/test_api.py` (9 tests).

**Defects found and fixed during this pass: 6. Automated suite after fixes: 79 passed.**

| # | Found by | Defect | Fix | Re-test |
|---|---|---|---|---|
| 1 | B10 | After a failed analysis, its error message stayed under the next file's mapping step | The analysis state resets when a new file is read | Pass |
| 2 | F (URL) | Navigating between pages dropped `?dataset=` and filter parameters, so a reload lost them | Navigation keeps the current query string | Pass |
| 3 | G5 | "Download analysed CSV" ignored the search box (exported 84 rows while 8 were shown) | The export endpoint accepts the search text; the button reads "Download these reviews (CSV)" when searching | Pass (8 rows; new API assertion) |
| 4 | J/I (URL) | The Aspects page used `?aspect=` for the open aspect, which collides with the global aspect filter; reloading showed 0 reviews | Renamed to `?focus=` | Pass (reload and overview link) |
| 5 | H (visual) | The 3D confusion-matrix labels overlapped at the original camera angle | Reframed camera and label anchors | Pass |
| 6 | M2 | drei `<Html>` labels mounted unreliably (one or all missing; React `removeChild` errors in the console) | Replaced with HTML labels projected from 3D each frame; drei removed | Pass (all six labels inside the stage; console clean) |

## Results by area (web)

| Area | Result | Key evidence |
|---|---|---|
| A startup and theme | Pass | Demo loads with the synthetic notice; Light/Dark switch changes the tokens (dark `#1D1B1F`) and persists in localStorage; unknown route shows the 404 page |
| B ingestion | Pass | Empty, header-only, malformed, binary, duplicate-header and over-10 MB files each give a specific error; UTF-8, BOM, cp1252 and `;` tab `|` detected; kitchen-sink file 14 rows, 10 valid, 4 excluded with reasons and warnings; alternative headers auto-mapped; remapping works; double mapping blocks Analyse; numeric-only text column is rejected and the active dataset is kept; 12,000 rows truncated to 10,000; 5,000 reviews analysed in 3.9 s |
| C NLP | Pass | Single-comment box: two clause-level aspects; ambiguous "clear" listed; unrelated text has no aspect; processed text shows `neg_` |
| D model | Pass | Model page equals `training_report.json` (0.529 / 0.653 / ECE 0.062 / confusion matrix / all four models); class switch, error filter and "try the model" (Negative 93%) work |
| E overview | Pass | 66.1; 53/5/26; 84; +0.16; 27 flagged; 83 with an aspect; most positive/negative aspect; all 7 insights word for word; 12 aspect rows; trend total 84 |
| F filters | Pass | Course 22 (63.6), instructor 20 (75.0), semester 42 (51.2), neutral 5 (50.0), pace 9 (50.0), no aspect 1, confident 57 (69.3), review 27 (59.3), date range 42 (81.0): all equal v1 and the independent values; tokens remove one filter; Clear works; zero-result selection shows empty states on every page; filters survive a page reload; a new dataset clears them; exports follow them (22 rows) |
| G explore | Pass | Search 8; four sort orders; paging 20 → 40; inspector for #12 equals the pipeline; search-aware CSV; deep link `?review=12` |
| 3D field | Pass | Real mouse hover on a block showed "Review #18 · negative · confidence 81% · Course materials & resources"; clicking opened review #18 ("The resources shared were outdated…") |
| I aspects | Pass | All 12 rows and indicators equal v1; keyboard Enter on a row opens its evidence (9 clauses; 4 negative); full review expands; 1 unmatched, 7 ambiguous, 12 taxonomy entries |
| J topics | Pass | Top terms, bigrams, minimum reviews 5 gives 9 terms, top-N 10, generic toggle, "exam" gives 5 reviews, noun phrases, k = 2…8 topic sizes equal the independent values |
| K insights | Pass | Formula text and 66.1; minimum-sample warning at 22; course and semester group tables; Fall 2025 withholds every course indicator; recommendations 11 / 5 / 6; the same 28 evidence ids as v1 |
| L method | Pass | Five downloads (84-row CSV, HTML report in the new palette with the academic title and no scripts, Markdown with 11 recommendations and no em dashes, 120 mentions, 5 excluded); academic title, formula, source and licence shown |
| M cross-cutting | Pass | 375 px: no horizontal overflow on any of the 8 pages, mobile menu opens and closes; dark mode checked visually; clean console in a fresh session (only a library deprecation notice); no review text in the server log. The only server tracebacks are Windows asyncio `WinError 10054` notices when the browser aborts a request, which is not Sentiq code |
| Clean environment | Pass | `npm ci` + build from the lockfile in a scratch copy; API from a fresh Python 3.11 venv serves the app and the demo numbers |

## Not verified

* `prefers-reduced-motion`: the code path exists (animations and auto-rotation are skipped), but the browser tool
  cannot emulate the setting, so it was not observed.
* The Docker image: Docker Desktop was not running, so `docker build` was not executed. Each step it runs
  (`npm ci && npm run build`, `pip install -r requirements.txt`, `uvicorn api.main:app`) was verified separately as above.
* Hosting the web version on a public server (Render or Hugging Face Spaces) has not been done.
