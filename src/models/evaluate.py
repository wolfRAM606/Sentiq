"""Evaluation helpers: classification metrics and calibration diagnostics."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support


def classification_metrics(y_true, y_pred, labels: list[str]) -> dict:
    y_true = list(y_true)
    y_pred = list(y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "per_class": {
            lab: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, lab in enumerate(labels)
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": list(labels),
    }


def reliability(y_true, proba: np.ndarray, classes: list[str], n_bins: int = 10) -> dict:
    """Expected calibration error of the top-class probability, plus bin data."""
    proba = np.asarray(proba)
    y_true = np.asarray(list(y_true))
    top = proba.max(axis=1)
    pred = np.asarray(classes)[proba.argmax(axis=1)]
    correct = (pred == y_true).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    bins, ece = [], 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (top > lo) & (top <= hi)
        if not mask.any():
            continue
        conf, acc, n = float(top[mask].mean()), float(correct[mask].mean()), int(mask.sum())
        ece += (n / len(top)) * abs(acc - conf)
        bins.append({"lower": float(lo), "upper": float(hi), "confidence": conf, "accuracy": acc, "count": n})
    return {"ece": float(ece), "bins": bins}
