"""Generate CSV fixtures for the manual/browser test plan (docs/TEST_PLAN.md, section B and M4).

Usage:  python scripts/make_test_fixtures.py <output_dir>
The files are synthetic test inputs and are not committed.
"""
from __future__ import annotations

import csv
import io
import random
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEADER = ["review", "course", "instructor", "date", "semester", "rating"]
BASE = [
    ["The professor explains concepts clearly and the examples are great", "PHY101", "Dr X", "2025-09-03", "T1", "5"],
    ["Assignments are far too long and the deadlines are unrealistic", "PHY101", "Dr X", "03/09/2025", "T1", "2"],
    ["", "PHY101", "Dr X", "2025-09-05", "T1", "3"],
    ["   ", "PHY101", "Dr X", "2025-09-06", "T1", "3"],
    ["The professor explains concepts clearly and the examples are great", "PHY101", "Dr X", "2025-09-07", "T1", "5"],
    ["The professor explains concepts clearly and the examples are great", "CHE201", "Dr Y", "2025-09-08", "T1", "5"],
    ["12345 !!! 678", "CHE201", "Dr Y", "2025-09-09", "T1", "4"],
    ["Lectures are boring and the pace is too fast", "CHE201", "Dr Y", "not a date", "T2", "two"],
    ["Not helpful at all, never answers emails", "CHE201", "Dr Y", "Sept 12 2025", "T2", "1"],
    ["Lab sessions gave us real world practical experience", "CHE201", "Dr Y", "2025-09-13", "T2", "4,5"],
    ["Grading was fair and the rubric was shared in advance", "PHY101", "Dr X", "2025-09-14", "T2", "5"],
    ["Café discussions were great; très bien, el profesor explica muy bien. 讲课很清楚", "PHY101", "Dr X", "2025-09-15", "T2", "4"],
    ['<script>alert("xss")</script><b>bold</b> notes were useful', "PHY101", "Dr X", "2025-09-16", "T2", "4"],
    ["Very long review. " + "The lectures were clear and the notes were well organised. " * 120, "PHY101", "Dr X", "2025-09-17", "T2", "5"],
]


def write(path: Path, rows, header=HEADER, delimiter=",", encoding="utf-8"):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    if header:
        w.writerow(header)
    w.writerows(rows)
    path.write_bytes(buf.getvalue().encode(encoding))


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    write(out / "b01_kitchen_sink_utf8.csv", BASE)
    (out / "b02_utf8_bom.csv").write_bytes("﻿".encode("utf-8") + (out / "b01_kitchen_sink_utf8.csv").read_bytes())
    cp_rows = [["Café lectures were très good and the professor was naïve about deadlines", "FR1", "Mme Zoë", "2025-01-01", "S1", "4"],
               ["The résumé workshop was useful", "FR1", "Mme Zoë", "2025-01-02", "S1", "5"]]
    write(out / "b03_cp1252.csv", cp_rows, encoding="cp1252")
    write(out / "b04_semicolon.csv", BASE[:2] + BASE[7:11], delimiter=";")
    write(out / "b04_tab.csv", BASE[:2] + BASE[7:11], delimiter="\t")
    write(out / "b04_pipe.csv", BASE[:2] + BASE[7:11], delimiter="|")
    (out / "b05_empty.csv").write_bytes(b"")
    (out / "b06_header_only.csv").write_bytes(b"review,course\n")
    (out / "b07_malformed.csv").write_bytes(b'review,course\n"unterminated quote,PHY\nx,y,z,w\n')
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("a.txt", "hello")
    (out / "b08_binary.csv").write_bytes(zbuf.getvalue())
    big_row = "This review is padding text for the size limit test " * 20
    with (out / "b09_over_10mb.csv").open("w", encoding="utf-8") as fh:
        fh.write("review\n")
        while fh.tell() < 10.6 * 1024 * 1024:
            fh.write(big_row + "\n")
    rng = random.Random(1)
    with (out / "b10_12000_rows.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["review", "course"])
        for i in range(12000):
            w.writerow([f"Review number {i}: the lectures were {rng.choice(['clear', 'confusing', 'fine'])}", f"C{i % 7}"])
    (out / "b11_duplicate_columns.csv").write_bytes(b"review,review,course\na,b,c\n")
    write(out / "b12_alt_names.csv",
          [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in BASE[:2] + BASE[7:11]],
          header=["Student Response", "Module", "Tutor", "Timestamp", "Term", "Stars"])
    write(out / "b15_numeric_text.csv", [["101", "5"], ["102", "4"], ["103", "3"]], header=["student_id", "score"])

    # M4: 5,000 realistic reviews built from the public training comments across 6 fictional courses
    train = list(csv.reader(io.StringIO((ROOT / "data/training/Student_Feedback.csv").read_bytes().decode("cp1252"))))[1:]
    texts = list(dict.fromkeys(r[0].strip() for r in train if r and r[0].strip()))
    rows = []
    courses = ["ENG110", "CSE220", "MTH140", "BIO105", "ECO130", "PSY150"]
    for c in courses:
        for t in texts:
            if len(rows) >= 5000:
                break
            rows.append([t, c, f"Instructor {courses.index(c) + 1}", f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                         rng.choice(["Fall 2025", "Spring 2026"]), str(rng.randint(1, 5))])
    write(out / "m4_5000_reviews.csv", rows)
    for p in sorted(out.iterdir()):
        print(f"{p.name:32s} {p.stat().st_size:>10,} bytes")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "static" / "testdata")
