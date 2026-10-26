"""Central paths and constants for Sentiq."""
from __future__ import annotations

from pathlib import Path

PRODUCT_NAME = "Sentiq"
PRODUCT_DESCRIPTOR = "NLP-Powered Course Feedback Intelligence"
TAGLINE = "Every response tells a story."
ACADEMIC_TITLE = (
    "An Automated Text Mining Dashboard for Evaluating Course Feedback and "
    "Teaching Effectiveness Reviews using spaCy and Streamlit"
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEMO_DATASET = DATA_DIR / "sample" / "demo_feedback.csv"
TRAINING_DATASET = DATA_DIR / "training" / "Student_Feedback.csv"
MODELS_DIR = ROOT / "models"
MODEL_PATH = MODELS_DIR / "sentiment_model.joblib"
METRICS_PATH = MODELS_DIR / "training_report.json"
TAXONOMY_PATH = ROOT / "config" / "aspect_taxonomy.json"

SPACY_MODEL = "en_core_web_sm"

# Sentiment labels used everywhere in the product (dataset codes are mapped onto these).
LABELS = ["negative", "neutral", "positive"]
TRAINING_LABEL_MAP = {0: "negative", 1: "positive", 2: "neutral"}

# Upload / processing limits
MAX_UPLOAD_MB = 10
MAX_ROWS = 10_000
MAX_REVIEW_CHARS = 5_000

# Prediction uncertainty: a prediction is flagged "review needed" when the top
# class probability is below this value, or the gap to the runner-up is small.
LOW_CONFIDENCE_PROB = 0.55
LOW_CONFIDENCE_MARGIN = 0.15

# Evidence thresholds used by insights / recommendations
MIN_ASPECT_MENTIONS = 3
MIN_SAMPLE_WARNING = 30
MIN_TOPIC_REVIEWS = 25

RANDOM_STATE = 42
