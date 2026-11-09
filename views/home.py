
import streamlit as st
from core import auth

st.set_page_config(
    page_title="CardioIQ",
    page_icon="❤️",
    layout="wide"
)

# ---------- Compact homepage styling ----------
st.markdown("""
<style>

/* Reduce overall page spacing */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 0.5rem !important;
    max-width: 1500px;
}

/* Hero section */
.hero {
    background: linear-gradient(115deg, #142C43, #087F8C);
    color: white;
    padding: 28px 38px;
    border-radius: 0 0 18px 18px;
    margin-bottom: 18px;
}

.hero h1 {
    color: white !important;
    font-size: 2.5rem !important;
    margin-bottom: 8px;
}

.hero p {
    color: #E4F1F5;
    font-size: 1.05rem;
    margin-bottom: 0;
}

/* Login CTA */
.login-box {
    background: linear-gradient(115deg, #142C43, #087F8C);
    border: 1px solid #B8DDDF;
    border-left: 5px solid #087F8C;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0 18px 0;
}

.login-box h3 {
    color: #142C43;
    margin: 0 0 5px 0;
    font-size: 1.15rem;
}

.login-box p {
    color: #526B7C;
    margin: 0;
    font-size: 0.9rem;
}

/* Feature cards */
.feature-card {
    background: white;
    border: 1px solid #E1E9EF;
    border-radius: 12px;
    padding: 15px 17px;
    min-height: 130px;
    box-shadow: 0 2px 6px rgba(20,44,67,0.04);
}

.feature-icon {
    font-size: 25px;
    margin-bottom: 5px;
}

.feature-card h3 {
    color: #142C43;
    font-size: 1.05rem;
    margin: 0 0 6px 0;
}

.feature-card p {
    color: #718096;
    font-size: 0.85rem;
    line-height: 1.4;
    margin: 0;
}

/* ---------- Doctor Login Button ---------- */
div[data-testid="stPageLink"] a[href*="login"] {
    background: linear-gradient(115deg, #142C43, #087F8C);
    color: #FFFFFF !important;
    border: 1px solid #142C43 !important;
    border-radius: 9px;
    padding: 12px 24px !important;
    font-weight: 700 !important;
    box-shadow: 0 3px 8px rgba(20, 44, 67, 0.15);
    transition: all 0.2s ease;
}

/* Ensure icon and text are white */
div[data-testid="stPageLink"] a[href*="login"] * {
    color: #FFFFFF !important;
}

/* Hover effect */
div[data-testid="stPageLink"] a[href*="login"]:hover {
    background: #087F8C !important;
    border-color: #087F8C !important;
    color: #FFFFFF !important;
}

/* Hide unnecessary vertical gaps */
[data-testid="stVerticalBlock"] {
    gap: 0.65rem;
}

</style>
""", unsafe_allow_html=True)


# ---------- Hero section ----------
st.markdown("""
<div class="hero">
    <h1>CardioIQ 🫀</h1>
    <p>
        AI-powered cardiac risk assessment and patient monitoring
        for smarter clinical review.
    </p>
</div>
""", unsafe_allow_html=True)


# ---------- Doctor Login CTA ----------
if auth.is_authenticated():

    st.page_link(
        "views/overview.py",
        label="Open Clinical Workspace",
        icon=":material/arrow_forward:"
    )

else:

    st.page_link(
        "views/login.py",
        label=" Doctor Login",
        icon=":material/login:"
    )


# ---------- Features ----------
st.markdown("### What CardioIQ offers")

c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🫀</div>
        <h3>Risk Assessment</h3>
        <p>
            AI/ML-generated cardiac risk scores,
            categories and contributing factors.
        </p>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📈</div>
        <h3>Vitals & Trends</h3>
        <p>
            Monitor blood pressure, heart rate
            and cholesterol changes over time.
        </p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🔔</div>
        <h3>Clinical Alerts</h3>
        <p>
            Identify unusual readings and
            review alerts by severity.
        </p>
    </div>
    """, unsafe_allow_html=True)
