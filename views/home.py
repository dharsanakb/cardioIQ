import streamlit as st

from core import auth

st.markdown(
    """
    <style>
    .hero {background: linear-gradient(135deg, #0e7c86 0%, #14a3a0 100%); color: white;
           padding: 2.5rem 2rem; border-radius: 16px; margin-bottom: 1.5rem;}
    .hero h1 {color: white; margin: 0 0 .4rem 0; font-size: 2.6rem;}
    .hero p {font-size: 1.15rem; opacity: .95; margin: 0;}
    .card {background: #f1f6f7; border-radius: 12px; padding: 1.1rem 1.2rem; height: 100%;}
    .card h4 {margin-top: 0; color: #0e7c86;}
    </style>
    <div class="hero">
      <h1>CardioIQ</h1>
      <p>AI-assisted cardiac risk assessment and monitoring, built for busy clinical teams.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if auth.is_authenticated():
    st.page_link("views/overview.py", label="Go to patient overview", icon="")
else:
    st.page_link("views/login.py", label="Doctor login", icon="")

st.subheader("Why this exists")
st.write(
    "Cardiologists review large amounts of data in very little time. CardioIQ brings a patient's "
    "risk, vitals trends and alerts into one view, and explains *why* the model rated someone "
    "higher or lower risk, so the doctor can focus on judgement rather than data gathering."
    # TODO: replace with your own narrative / rubric-aligned rationale.
)

st.subheader("What it does")
c1, c2, c3 = st.columns(3)
c1.markdown('<div class="card"><h4>Risk assessment</h4>A machine-learning model estimates cardiac '
            'risk and shows the factors driving each score.</div>', unsafe_allow_html=True)
c2.markdown('<div class="card"><h4>Trend monitoring</h4>Vitals are tracked over time and compared '
            'with each patient\'s own baseline.</div>', unsafe_allow_html=True)
c3.markdown('<div class="card"><h4>Smart alerts</h4>Significant changes are flagged with a reason and '
            'severity, so nothing important is missed.</div>', unsafe_allow_html=True)

st.subheader("How it works")
st.markdown(
    "1. **Patient data** (history, test results, vitals) is stored securely.\n"
    "2. **The model** scores risk and explains the contributing factors.\n"
    "3. **Rules** watch vitals for unusual readings or changes.\n"
    "4. **An AI summary** condenses everything for the doctor.\n"
    "5. **The doctor decides.** CardioIQ supports decisions, it never makes them."
)

st.info(
    "**About this prototype:** built for a university course. It uses a public Kaggle dataset "
    "plus simulated vitals history. It contains no real patient data and is not a medical device."
)
