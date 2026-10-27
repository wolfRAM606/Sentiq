# Sentiq: comprehensive test plan

Every test is run for real: automated tests through pytest, and UI tests by clicking and typing in a browser
against the running app. Results go in `docs/TEST_RESULTS.md`, with the observed output for each test.

Legend: **[auto]** pytest · **[ui]** in-browser, by hand · **[cli]** command line

## A. Environment and startup
| ID | Test | How |
|---|---|---|
| A1 | Fresh Python 3.11 venv installs `requirements.txt` without conflicts | [cli] |
| A2 | Server starts and its health endpoint answers | [cli] |
| A3 | Demo dataset loads automatically on first visit and is labelled synthetic | [ui] |
| A4 | Model loads from the saved artifact (sidebar shows "trained LR") | [ui] |
| A5 | Missing model artifact: app retrains from the bundled data and says so | [cli]+[ui] |
| A6 | Corrupt model artifact: retrains, or shows an explicit "unavailable" state, without crashing | [cli]+[ui] |
| A7 | No API key, secret or network call needed at runtime | [auto]+[cli] |

## B. Data ingestion and validation (through the upload UI)
| ID | Test | How |
|---|---|---|
| B1 | Standard UTF-8 CSV uploads and analyses | [ui] |
| B2 | UTF-8 with BOM | [ui] |
| B3 | Windows-1252 file with accented characters | [ui] |
| B4 | Semicolon, tab and pipe delimiters | [ui] |
| B5 | Empty file: clear error, no crash | [ui] |
| B6 | Header row only: clear error | [ui] |
| B7 | Malformed CSV (unbalanced quotes): clear error | [ui] |
| B8 | Binary file renamed to .csv: clear error | [ui] |
| B9 | File over 10 MB is rejected | [ui] |
| B10 | More than 10,000 rows: truncation warning, first 10,000 analysed | [ui] |
| B11 | Duplicate column names: clear error | [ui] |
| B12 | Alternative column names are auto-mapped correctly | [ui] |
| B13 | Manual remapping of columns changes what is analysed | [ui] |
| B14 | Same column mapped to two roles: error, Analyse blocked | [ui] |
| B15 | Numeric-only column chosen as text: every row excluded with a reason, clear error | [ui] |
| B16 | Empty and whitespace reviews excluded with a reason | [ui] |
| B17 | Duplicate reviews excluded; same text in a different course kept | [ui] |
| B18 | Non-alphabetic reviews excluded | [ui] |
| B19 | Mixed and invalid date formats parsed; failures counted | [ui] |
| B20 | Non-numeric and comma-decimal ratings handled and counted | [ui] |
| B21 | Review over 5,000 characters: truncation warning, original kept in export | [ui] |
| B22 | Unicode and non-English text does not crash | [ui] |
| B23 | HTML/script inside a review is displayed as text, never executed | [ui] |
| B24 | Record accounting: valid + excluded = total, on screen and in the export | [ui]+[auto] |
| B25 | Exported CSV keeps the original review text byte for byte | [ui]+[auto] |

## C. NLP pipeline
| ID | Test | How |
|---|---|---|
| C1 | Tokenisation and lemmatisation | [auto] |
| C2 | Negation marking ("not helpful" becomes `not neg_helpful`) | [auto]+[ui] processed-text view |
| C3 | Informal contractions ("doesnt") | [auto] |
| C4 | Negation scope stops at "but" | [auto] |
| C5 | Empty input | [auto] |
| C6 | Several aspects in one review | [auto]+[ui] single-review analysis |
| C7 | Aspect evidence is the clause, not the whole review | [auto]+[ui] |
| C8 | Ambiguous words need context ("the answer was clear" vs "the lectures were clear") | [auto]+[ui] |
| C9 | Exclusion phrase ("practical knowledge" is not subject knowledge) | [auto] |
| C10 | General statement goes to Overall | [auto] |
| C11 | Unrelated text gets no aspect | [auto]+[ui] |
| C12 | Negation flag is local to the matched word | [auto] |
| C13 | Editing `config/aspect_taxonomy.json` changes results without a restart | [cli]+[ui] |
| C14 | Keyword counts are review counts, split by sentiment | [auto]+[ui] cross-check |
| C15 | Noun phrases extracted | [ui] |
| C16 | Topic discovery skipped with a reason below 25 reviews | [auto]+[ui] |
| C17 | Topic count 2 to 8 each produce non-empty topics | [ui] |
| C18 | Topic review counts + unassigned = selection size | [auto]+[ui] |

## D. Sentiment model
| ID | Test | How |
|---|---|---|
| D1 | Training data counts verified (1,086 raw, 1,061 clean) | [auto] |
| D2 | Label mapping 0/1/2 to negative/positive/neutral | [auto] |
| D3 | Training is reproducible (identical metrics on rerun) | [auto]+[cli] |
| D4 | Every trained model beats the majority baseline | [auto] |
| D5 | Accuracy, F1 and confusion-matrix maths | [auto] |
| D6 | Save and reload give identical predictions | [auto] |
| D7 | Probabilities on unseen text sum to 1 | [auto]+[ui] |
| D8 | Negation lowers the positive probability | [auto]+[ui] |
| D9 | Model Lab "Re-run training" button retrains and the page refreshes | [ui] |
| D10 | Low-confidence flag appears exactly below 55% or a 15% margin | [ui] |
| D11 | Report accuracy matches its own confusion matrix | [auto] |
| D12 | Model Lab numbers equal `training_report.json` | [ui] |

## E. Overview page
| ID | Test | How |
|---|---|---|
| E1 | KPI counts and percentages match the analysed data | [ui] vs computed |
| E2 | Indicator value matches the formula on screen | [ui] |
| E3 | Most positive and most negative aspect match the aspect table | [ui] |
| E4 | Every number in the generated insights matches the data | [ui] |
| E5 | Donut, aspect bars, keyword, topic and trend charts render with correct totals | [ui] |

## F. Global filters (each checked on every page)
| ID | Test | How |
|---|---|---|
| F1 | Course filter | [ui] |
| F2 | Instructor filter | [ui] |
| F3 | Semester filter | [ui] |
| F4 | Sentiment filter | [ui] |
| F5 | Aspect filter, including "(no aspect detected)" | [ui] |
| F6 | Confidence filter (confident only / review needed only) | [ui] |
| F7 | Date range filter | [ui] |
| F8 | Combined filters giving zero reviews: every page shows an empty state | [ui] |
| F9 | Clear filters button | [ui] |
| F10 | Filters reset when a new dataset is analysed | [ui] |
| F11 | Exports follow the active filters | [ui] |

## G. Feedback Explorer
| ID | Test | How |
|---|---|---|
| G1 | Search filters the table and cards | [ui] |
| G2 | All four sort orders sort correctly | [ui] |
| G3 | "Cards to show" changes the card count | [ui] |
| G4 | Inspect a review: probabilities, aspects and processed text are correct for that row | [ui] |
| G5 | Download analysed CSV: rows equal the filtered table | [ui] |
| G6 | Single review with empty text: warning | [ui] |
| G7 | Single review with mixed text: two aspects, different clause sentiment | [ui] |
| G8 | Validation report tab shows the mapping, warnings and excluded rows | [ui] |
| G9 | Reset to demonstration data | [ui] |

## H. Model Lab
| ID | Test | How |
|---|---|---|
| H1 | All five tabs open | [ui] |
| H2 | Feature class selector switches the table | [ui] |
| H3 | Error-analysis label filter | [ui] |
| H4 | "Try the model" responds to typed text | [ui] |

## I. Aspect Analysis
| ID | Test | How |
|---|---|---|
| I1 | Summary table counts add up (positive + neutral + negative = reviews) | [ui] |
| I2 | Drill-down aspect selector and sentiment filter | [ui] |
| I3 | Evidence expanders show the full review | [ui] |
| I4 | Unmatched and ambiguous lists are consistent with coverage | [ui] |
| I5 | Taxonomy tab lists all 12 aspects | [ui] |

## J. Topics and Keywords
| ID | Test | How |
|---|---|---|
| J1 | Unigram/bigram switch | [ui] |
| J2 | Minimum-reviews input | [ui] |
| J3 | Top-N slider | [ui] |
| J4 | Hide-generic-words toggle | [ui] |
| J5 | Term selector shows only reviews that contain the term | [ui] |
| J6 | Noun phrase tab | [ui] |
| J7 | Topic slider and topic expanders | [ui] |

## K. Effectiveness Insights
| ID | Test | How |
|---|---|---|
| K1 | Gauge and formula text agree and match a hand calculation | [ui] |
| K2 | Minimum-sample warning under 30 reviews | [ui] |
| K3 | Aspect indicator table and "inspect contributing reviews" | [ui] |
| K4 | Group-by switch; groups under 15 reviews withheld | [ui] |
| K5 | Recommendation filter (All / Issues / Strengths) | [ui] |
| K6 | Every recommendation's counts and review ids exist in the data | [ui]+[auto] |

## L. Reports and Methodology
| ID | Test | How |
|---|---|---|
| L1 | Each of the five downloads has valid content that matches the filters | [ui] (fetched, inspected) |
| L2 | HTML report preview renders | [ui] |
| L3 | Methodology and About tabs show the academic title, sources and versions | [ui] |

## M. Cross-cutting
| ID | Test | How |
|---|---|---|
| M1 | Layout at 375, 768 and 1440 px: no horizontal overflow | [ui] |
| M2 | No browser console errors | [ui] |
| M3 | No server warnings or tracebacks during the whole run | [cli] |
| M4 | Performance: 5,000-review upload analysed in a reasonable time | [ui] timed |
| M5 | Review text never appears in server logs | [cli] |
| M6 | Two browser tabs keep separate datasets | [ui] |
