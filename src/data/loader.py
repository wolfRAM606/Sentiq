"""Robust CSV ingestion: encoding detection, delimiter sniffing, size limits."""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import MAX_ROWS, MAX_UPLOAD_MB

logger = logging.getLogger(__name__)

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class DataLoadError(ValueError):
    """Raised with a user-facing message when a CSV cannot be loaded."""


@dataclass
class LoadedCSV:
    frame: pd.DataFrame
    encoding: str
    delimiter: str
    truncated: bool = False
    original_rows: int = 0


def _decode(raw: bytes) -> tuple[str, str]:
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise DataLoadError("The file could not be decoded as text (tried UTF-8, Windows-1252 and Latin-1).")


def _sniff_delimiter(text: str) -> str:
    sample = text[:20_000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def read_csv_bytes(raw: bytes, max_rows: int = MAX_ROWS, max_mb: float = MAX_UPLOAD_MB) -> LoadedCSV:
    """Parse uploaded CSV bytes into a string-typed DataFrame.

    All columns are read as strings so that original review text is preserved
    exactly; type coercion happens later, per mapped column, with reporting.
    """
    if raw is None or len(raw) == 0:
        raise DataLoadError("The uploaded file is empty.")
    if len(raw) > max_mb * 1024 * 1024:
        raise DataLoadError(f"The file is larger than the {max_mb:g} MB limit.")
    if b"\x00" in raw[:4096]:
        raise DataLoadError("This looks like a binary file (e.g. Excel). Please export it as CSV first.")

    text, encoding = _decode(raw)
    if not text.strip():
        raise DataLoadError("The uploaded file contains no data.")
    delimiter = _sniff_delimiter(text)
    # pandas silently renames repeated headers ("review", "review.1"), so check the raw header row first
    try:
        header = next(csv.reader(io.StringIO(text), delimiter=delimiter))
    except (csv.Error, StopIteration):
        header = []
    names = [h.strip() for h in header if h.strip()]
    if len(names) != len(set(names)):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise DataLoadError(f"The CSV has duplicate column names ({', '.join(dupes)}). Please rename them so each is unique.")
    try:
        frame = pd.read_csv(
            io.StringIO(text),
            sep=delimiter,
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=True,
            on_bad_lines="error",
        )
    except pd.errors.EmptyDataError as exc:
        raise DataLoadError("The CSV has no columns or rows.") from exc
    except pd.errors.ParserError as exc:
        raise DataLoadError(
            "The CSV is malformed (inconsistent number of fields). "
            "Check for unquoted commas or line breaks inside reviews."
        ) from exc

    frame.columns = [str(c).strip() for c in frame.columns]
    if frame.shape[1] == 0:
        raise DataLoadError("The CSV has no columns.")
    if len(frame) == 0:
        raise DataLoadError("The CSV has a header row but no records.")
    if len(set(frame.columns)) != len(frame.columns):
        raise DataLoadError("The CSV has duplicate column names. Please rename them so each is unique.")

    original_rows = len(frame)
    truncated = original_rows > max_rows
    if truncated:
        frame = frame.iloc[:max_rows].copy()
    logger.info("Loaded CSV: %d rows, %d columns, encoding=%s", len(frame), frame.shape[1], encoding)
    return LoadedCSV(frame, encoding, delimiter, truncated, original_rows)


def read_csv_path(path: str | Path, **kwargs) -> LoadedCSV:
    return read_csv_bytes(Path(path).read_bytes(), **kwargs)
