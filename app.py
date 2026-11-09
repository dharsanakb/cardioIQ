import streamlit as st

from core import auth, model

from pathlib import Path
import streamlit as st

CSS_PATH = Path(__file__).parent / "assets" / "style.css"

if CSS_PATH.exists():
    st.markdown(
        f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True
    )

    
st.set_page_config(
    page_title="CardioIQ",
    page_icon="🫀",
    layout="wide"
)

# Check whether the trained model exists
if not model.MODEL_PATH.exists():
    st.error(
        "Model file not found. Run `python train_model.py` first."
    )
    st.stop()

# Page definitions
home = st.Page(
    "views/home.py",
    title="Home",
    icon="🏠",
    default=True
)

login = st.Page(
    "views/login.py",
    title="Doctor Login",
    icon="🔐"
)

overview = st.Page(
    "views/overview.py",
    title="Overview",
    icon="📋"
)

patient = st.Page(
    "views/patient.py",
    title="Patient Profile",
    icon="🫀"
)

analytics = st.Page(
    "views/analytics.py",
    title="Analytics",
    icon="📊"
)

# Authentication and navigation
if auth.is_authenticated():

    pages = {
        "CardioIQ": [home],
        "Clinic": [overview, patient, analytics]
    }

    with st.sidebar:
        st.caption(f"Signed in as **{auth.current_name()}**")

        if st.button("Log out", width="stretch"):
            auth.logout()
            st.rerun()

else:
    pages = [home, login]

st.sidebar.caption(
    "Prototype · Simulated data · Decision support only."
)

st.navigation(pages).run()