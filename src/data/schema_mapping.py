"""Column-role mapping with support for common alternative column names."""
from __future__ import annotations

import re

# Role -> candidate column names (normalised: lowercase, alphanumerics only).
ROLE_CANDIDATES: dict[str, list[str]] = {
    "text": [
        "review", "reviewtext", "feedback", "feedbacktext", "comment", "comments", "text",
        "response", "responses", "studentfeedback", "studentcomment", "remarks", "opinion",
        "content", "body", "answer",
    ],
    "course": ["course", "coursename", "coursecode", "subject", "module", "class", "paper"],
    "instructor": ["instructor", "instructorname", "teacher", "teachername", "faculty", "professor", "lecturer", "staff", "tutor"],
    "date": ["date", "submitted", "submittedat", "timestamp", "created", "createdat", "responsedate", "time"],
    "semester": ["semester", "term", "session", "academicyear", "year", "batch"],
    "rating": ["rating", "score", "stars", "overallrating", "grade", "satisfaction"],
    "label": ["sentiment", "sentiments", "label", "polarity", "class_label", "classlabel"],
}

ROLE_LABELS = {
    "text": "Review text (required)",
    "course": "Course",
    "instructor": "Instructor",
    "date": "Date",
    "semester": "Semester / term",
    "rating": "Numeric rating",
    "label": "Existing sentiment label (kept for reference only)",
}

OPTIONAL_ROLES = ["course", "instructor", "date", "semester", "rating", "label"]


def normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def suggest_mapping(columns: list[str]) -> dict[str, str | None]:
    """Suggest a column for each role; each column is used at most once."""
    norm = {c: normalise(c) for c in columns}
    used: set[str] = set()
    roles = ["text", *OPTIONAL_ROLES]
    mapping: dict[str, str | None] = {r: None for r in roles}

    def pick(role, test):
        for cand in ROLE_CANDIDATES[role]:
            for col, n in norm.items():
                if col not in used and test(cand, n):
                    return col
        return None

    # pass 1: exact matches for every role; pass 2: substring matches (>= 5 chars,
    # so short words like "time" do not match inside e.g. "sentiments")
    for test in (lambda c, n: n == c, lambda c, n: len(c) >= 5 and c in n):
        for role in roles:
            if mapping[role] is None:
                choice = pick(role, test)
                if choice:
                    mapping[role] = choice
                    used.add(choice)
    return mapping


def guess_text_column(frame) -> str | None:
    """Fallback: pick the column with the longest average string length."""
    best, best_len = None, 0.0
    for col in frame.columns:
        lengths = frame[col].astype(str).str.len()
        avg = float(lengths.mean()) if len(lengths) else 0.0
        if avg > best_len:
            best, best_len = col, avg
    return best
