import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def nlp():
    from src.nlp.preprocessing import get_nlp

    return get_nlp()


@pytest.fixture(scope="session")
def model():
    from src.models.predict import load_model

    m = load_model()
    assert m.available, m.status.message
    return m


@pytest.fixture(scope="session")
def analyzer(nlp):
    from src.nlp.aspects import AspectAnalyzer

    return AspectAnalyzer(nlp)


@pytest.fixture(scope="session")
def demo_analysis(model, analyzer):
    from src.analytics.pipeline import analyze_reviews
    from src.config import DEMO_DATASET
    from src.data.loader import read_csv_path
    from src.data.schema_mapping import suggest_mapping
    from src.data.validation import prepare_dataset

    loaded = read_csv_path(DEMO_DATASET)
    valid, excluded, report = prepare_dataset(loaded.frame, suggest_mapping(list(loaded.frame.columns)))
    return valid, excluded, report, analyze_reviews(valid, model, analyzer)
