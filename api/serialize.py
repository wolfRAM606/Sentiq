"""Convert pandas/numpy objects into JSON-safe Python values."""
from __future__ import annotations

import math
from datetime import date, datetime

import numpy as np
import pandas as pd


def clean(v):
    if v is None:
        return None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(v, (pd.Timestamp, datetime)):
        return None if pd.isna(v) else v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.isoformat()
    if v is pd.NaT:
        return None
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, np.ndarray):
        return [clean(x) for x in v.tolist()]
    return v


def records(df: pd.DataFrame, columns: list[str] | None = None) -> list[dict]:
    if df is None or len(df) == 0:
        return []
    cols = [c for c in (columns or list(df.columns)) if c in df.columns]
    return [{c: clean(v) for c, v in zip(cols, row)} for row in df[cols].itertuples(index=False, name=None)]
