"""Single prediction interface used by every page of the application."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config import LABELS, LOW_CONFIDENCE_MARGIN, LOW_CONFIDENCE_PROB, METRICS_PATH, MODEL_PATH, TRAINING_DATASET

logger = logging.getLogger(__name__)

PRED_COLUMNS = ["sentiment", "prob_negative", "prob_neutral", "prob_positive", "confidence", "margin",
                "review_needed", "sentiment_score"]


@dataclass
class ModelStatus:
    available: bool
    source: str            # "artifact" | "trained_at_startup" | "unavailable"
    message: str
    trained_at: str | None = None
    details: dict = field(default_factory=dict)


class SentimentModel:
    def __init__(self, pipeline, status: ModelStatus):
        self.pipeline = pipeline
        self.status = status
        self.classes = list(pipeline.classes_) if pipeline is not None else []

    @property
    def available(self) -> bool:
        return self.pipeline is not None

    def predict(self, texts: list[str]) -> pd.DataFrame:
        """Predict sentiment with class probabilities and an uncertainty flag.

        ``confidence`` is the largest class probability from Logistic Regression.
        It is *not* a calibrated guarantee; calibration on the held-out test set
        is reported separately in the Model Lab.
        ``sentiment_score`` = P(positive) - P(negative), ranging from -1 to +1.
        """
        texts = list(texts)
        if not self.available:
            out = pd.DataFrame({c: [np.nan] * len(texts) for c in PRED_COLUMNS})
            out["sentiment"] = "unavailable"
            out["review_needed"] = True
            return out
        if not texts:
            return pd.DataFrame(columns=PRED_COLUMNS)
        proba = self.pipeline.predict_proba(texts)
        idx = {c: i for i, c in enumerate(self.classes)}
        frame = pd.DataFrame({f"prob_{lab}": proba[:, idx[lab]] if lab in idx else 0.0 for lab in LABELS})
        order = np.sort(proba, axis=1)
        frame["confidence"] = order[:, -1]
        frame["margin"] = order[:, -1] - order[:, -2] if proba.shape[1] > 1 else 1.0
        frame["sentiment"] = np.asarray(self.classes)[proba.argmax(axis=1)]
        frame["review_needed"] = (frame["confidence"] < LOW_CONFIDENCE_PROB) | (frame["margin"] < LOW_CONFIDENCE_MARGIN)
        frame["sentiment_score"] = frame["prob_positive"] - frame["prob_negative"]
        return frame[PRED_COLUMNS]


def load_report(path: Path = METRICS_PATH) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_model(model_path: Path = MODEL_PATH, allow_training: bool = True) -> SentimentModel:
    """Load the persisted model; if missing/incompatible, retrain deterministically
    from the bundled labelled dataset; otherwise return an explicit unavailable model."""
    model_path = Path(model_path)
    load_error = None
    if model_path.exists():
        try:
            bundle = joblib.load(model_path)
            pipe = bundle["pipeline"]
            pipe.predict_proba(["sanity check"])
            return SentimentModel(pipe, ModelStatus(True, "artifact", "Loaded trained model artifact.",
                                                    bundle.get("trained_at"), {"path": str(model_path.name)}))
        except Exception as exc:  # incompatible pickle, corrupted file, missing spaCy model...
            load_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Model artifact could not be loaded: %s", load_error)
    if allow_training and TRAINING_DATASET.exists():
        try:
            from src.models.train import load_training_data, save_artifacts, train_and_evaluate

            df, log = load_training_data()
            result = train_and_evaluate(df, log)
            try:
                save_artifacts(result, model_path)
            except OSError:
                logger.warning("Could not persist retrained model (read-only filesystem?)")
            msg = "Model artifact was missing or incompatible, so it was retrained from the bundled labelled dataset."
            return SentimentModel(result.pipeline, ModelStatus(True, "trained_at_startup", msg,
                                                               result.report["trained_at"], {"load_error": load_error}))
        except Exception as exc:
            load_error = f"{load_error or ''} | training failed: {type(exc).__name__}: {exc}"
            logger.error("Fallback training failed: %s", exc)
    return SentimentModel(None, ModelStatus(False, "unavailable",
                                            "No trained sentiment model is available. Sentiment-dependent views are disabled; "
                                            "aspect detection, keywords and topics still work.",
                                            details={"load_error": load_error}))
