"""In-memory stores for uploads and analysed datasets.

Nothing a user uploads is written to disk: raw uploads expire after ``UPLOAD_TTL`` seconds and at most
``MAX_DATASETS`` analysed datasets are kept (least recently used are dropped first).
"""
from __future__ import annotations

import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

import pandas as pd

from src.analytics.pipeline import AnalysisResult
from src.data.validation import ValidationReport

UPLOAD_TTL = 30 * 60
MAX_UPLOADS = 20
MAX_DATASETS = 30


@dataclass
class Upload:
    frame: pd.DataFrame
    filename: str
    encoding: str
    delimiter: str
    truncated: bool
    original_rows: int
    created: float = field(default_factory=time.time)


@dataclass
class Dataset:
    id: str
    name: str
    kind: str                 # "demo" | "upload"
    valid: pd.DataFrame
    excluded: pd.DataFrame
    report: ValidationReport
    result: AnalysisResult
    created: float = field(default_factory=time.time)


class Store:
    def __init__(self):
        self._lock = threading.Lock()
        self.uploads: OrderedDict[str, Upload] = OrderedDict()
        self.datasets: OrderedDict[str, Dataset] = OrderedDict()

    @staticmethod
    def new_id() -> str:
        return secrets.token_urlsafe(9)

    def put_upload(self, up: Upload) -> str:
        with self._lock:
            self._expire()
            uid = self.new_id()
            self.uploads[uid] = up
            while len(self.uploads) > MAX_UPLOADS:
                self.uploads.popitem(last=False)
            return uid

    def get_upload(self, uid: str) -> Upload | None:
        with self._lock:
            self._expire()
            return self.uploads.get(uid)

    def put_dataset(self, ds: Dataset) -> None:
        with self._lock:
            self.datasets[ds.id] = ds
            self.datasets.move_to_end(ds.id)
            while len(self.datasets) > MAX_DATASETS:
                oldest = next(iter(self.datasets))
                if oldest == "demo":  # the demo dataset is never evicted
                    self.datasets.move_to_end(oldest)
                    oldest = next(iter(self.datasets))
                self.datasets.pop(oldest)

    def get_dataset(self, did: str) -> Dataset | None:
        with self._lock:
            ds = self.datasets.get(did)
            if ds:
                self.datasets.move_to_end(did)
            return ds

    def _expire(self) -> None:
        now = time.time()
        for k in [k for k, u in self.uploads.items() if now - u.created > UPLOAD_TTL]:
            self.uploads.pop(k, None)
