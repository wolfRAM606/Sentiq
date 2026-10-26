"""Data ingestion, mapping and validation tests."""
import pandas as pd
import pytest

from src.data.loader import DataLoadError, read_csv_bytes
from src.data.schema_mapping import suggest_mapping
from src.data.validation import (EXCLUSION_DUPLICATE, EXCLUSION_EMPTY, EXCLUSION_NO_LETTERS, ValidationError,
                                 prepare_dataset)


def test_valid_csv_loading():
    loaded = read_csv_bytes(b"review,course\nGreat class,CS101\nToo fast,CS101\n")
    assert loaded.frame.shape == (2, 2)
    assert loaded.encoding in ("utf-8-sig", "utf-8")


def test_cp1252_and_semicolon_csv():
    raw = "comment;rating\nCaf\xe9 talk was great\xa0indeed;5\n".encode("cp1252")
    loaded = read_csv_bytes(raw)
    assert loaded.encoding == "cp1252"
    assert loaded.delimiter == ";"
    assert "Café" in loaded.frame.iloc[0, 0]


@pytest.mark.parametrize("raw, fragment", [
    (b"", "empty"),
    (b"   \n  \n", "no data"),
    (b"a,b\n", "no records"),
    (b'review,course\n"unterminated,CS1\nx,y,z,w\n', "malformed"),
    (b"\x00\x01\x02PK", "binary"),
])
def test_invalid_csv_handling(raw, fragment):
    with pytest.raises(DataLoadError) as err:
        read_csv_bytes(raw)
    assert fragment in str(err.value).lower()


def test_size_and_row_limits():
    with pytest.raises(DataLoadError):
        read_csv_bytes(b"x" * 2048, max_mb=0.001)
    loaded = read_csv_bytes(("t\n" + "\n".join(f"review {i}" for i in range(50))).encode(), max_rows=10)
    assert loaded.truncated and len(loaded.frame) == 10 and loaded.original_rows == 50


def test_column_mapping_alternatives():
    m = suggest_mapping(["Student Feedback", "Course Code", "Faculty", "Submitted At", "Term", "Score"])
    assert m["text"] == "Student Feedback"
    assert m["course"] == "Course Code"
    assert m["instructor"] == "Faculty"
    assert m["date"] == "Submitted At"
    assert m["semester"] == "Term"
    assert m["rating"] == "Score"


def test_mapping_uses_each_column_once():
    m = suggest_mapping(["comments", "sentiments"])
    assert m["text"] == "comments" and m["label"] == "sentiments"
    used = [v for v in m.values() if v]
    assert len(used) == len(set(used))


def _frame():
    return pd.DataFrame({
        "review": ["Great teacher", "", "   ", "Great teacher", "great  teacher ", "12345 !!", "Clear notes", "Good pace"],
        "course": ["A", "A", "A", "A", "A", "A", "B", "B"],
        "date": ["2025-01-02", "2025-01-03", "", "2025/01/04", "not a date", "2025-02-01", "2025-03-01", "2025-03-02"],
        "rating": ["5", "4", "", "5", "x", "3", "4,5", "4"],
    })


def test_record_accounting_and_exclusion_reasons():
    valid, excluded, report = prepare_dataset(_frame(), {"text": "review", "course": "course", "date": "date", "rating": "rating"})
    assert report.total_records == 8
    assert report.valid_records + report.excluded_records == report.total_records
    assert report.exclusion_reasons[EXCLUSION_EMPTY] == 2
    assert report.exclusion_reasons[EXCLUSION_DUPLICATE] == 2       # exact + whitespace/case variant
    assert report.exclusion_reasons[EXCLUSION_NO_LETTERS] == 1
    assert set(valid["review_text"]) == {"Great teacher", "Clear notes", "Good pace"}
    assert len(excluded) == 5 and excluded["exclusion_reason"].notna().all()


def test_original_text_preserved():
    frame = pd.DataFrame({"t": ["  Wow — the TA's notes were *superb*!!  "]})
    valid, _, _ = prepare_dataset(frame, {"text": "t"})
    assert valid.loc[0, "review_text"] == "  Wow — the TA's notes were *superb*!!  "


def test_duplicates_with_different_metadata_are_kept():
    frame = pd.DataFrame({"t": ["Good class", "Good class"], "course": ["A", "B"]})
    valid, excluded, _ = prepare_dataset(frame, {"text": "t", "course": "course"})
    assert len(valid) == 2 and excluded.empty


def test_unparseable_metadata_reported():
    _, _, report = prepare_dataset(_frame(), {"text": "review", "date": "date", "rating": "rating"})
    assert report.unparseable_dates == 1
    assert report.unparseable_ratings == 1
    assert any("could not be parsed" in w for w in report.warnings)


def test_missing_review_column_and_empty_dataset():
    with pytest.raises(ValidationError):
        prepare_dataset(_frame(), {"text": None})
    with pytest.raises(ValidationError):
        prepare_dataset(_frame(), {"text": "nope"})
    with pytest.raises(ValidationError):
        prepare_dataset(pd.DataFrame({"t": ["", "  "]}), {"text": "t"})
