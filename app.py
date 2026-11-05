"""CardioIQ entry point: page registry, auth gate and navigation."""
import streamlit as st

from core import auth, model

st.set_page_config(page_title="CardioIQ", page_icon="", layout="wide")

if not model.MODEL_PATH.exists():
    st.error("Model file not found. Run `python train_model.py` first (see README).")
    st.stop()

home = st.Page("views/home.py", title="Home", default=True)
login = st.Page("views/login.py", title="Doctor Login")
overview = st.Page("views/overview.py", title="Overview")
patient = st.Page("views/patient.py", title="Patient Profile")
analytics = st.Page("views/analytics.py", title="Analytics")

if auth.is_authenticated():
    pages = {"CardioIQ": [home], "Clinic": [overview, patient, analytics]}
    with st.sidebar:
        st.caption(f"Signed in as **{auth.current_name()}**")
        if st.button("Log out", width="stretch"):
            auth.logout()
            st.rerun()
else:
    pages = [home, login]

st.navigation(pages).run()
