"""Sentiq, NLP-Powered Course Feedback Intelligence (Streamlit entry point).

Run with:  streamlit run app.py
"""
from __future__ import annotations

import logging

import streamlit as st

from src.config import PRODUCT_DESCRIPTOR, PRODUCT_NAME, ROOT
from src.ui import components as ui
from src.ui import state
from src.ui.theme import inject_css

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

st.set_page_config(page_title=f"{PRODUCT_NAME} · {PRODUCT_DESCRIPTOR}", page_icon=str(ROOT / "static" / "sentiq_mark.svg"),
                   layout="wide", initial_sidebar_state="expanded")
inject_css()

pages = {
    "Analyse": [
        st.Page("pages/1_Overview.py", title="Overview", default=True),
        st.Page("pages/2_Feedback_Explorer.py", title="Feedback Explorer"),
        st.Page("pages/4_Aspect_Analysis.py", title="Aspect Analysis"),
        st.Page("pages/5_Topics_and_Keywords.py", title="Topics & Keywords"),
        st.Page("pages/6_Effectiveness_Insights.py", title="Effectiveness Insights"),
    ],
    "Model & method": [
        st.Page("pages/3_Model_Lab.py", title="Model Lab"),
        st.Page("pages/7_Methodology_and_Reports.py", title="Reports & Methodology"),
    ],
}

ui.sidebar_brand()
nav = st.navigation(pages, position="sidebar")

try:
    with st.spinner("Analysing the demonstration dataset with spaCy and the trained model..."):
        ds = state.active()
except Exception as exc:  # keep the app usable and explain what went wrong
    logging.exception("Failed to initialise dataset")
    st.error(f"Sentiq could not prepare the demonstration dataset: {type(exc).__name__}: {exc}")
    st.stop()

model = state.get_model()
kind = "Synthetic demo data" if ds.kind == "demo" else "Uploaded data"
st.sidebar.markdown(
    f"<div class='sq-side-status'><div class='sq-label'>{kind}</div><b>{ui.esc(ds.name)}</b><br>"
    f"{ds.report.valid_records} valid, {ds.report.excluded_records} excluded<br>"
    f"Model: {'trained LR' if model.available else 'unavailable'}</div>",
    unsafe_allow_html=True)
state.render_filters(ds)

nav.run()
