import streamlit as st

from core import auth

st.title("Doctor login")

_, col, _ = st.columns([1, 2, 1])
with col:
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
    if submitted:
        if auth.authenticate(username, password):
            st.rerun()
        else:
            st.error("Incorrect username or password.")
    if auth.is_demo_mode():
        st.caption(f"Demo mode: username `{auth.DEMO_USER}`, password `{auth.DEMO_PASSWORD}`")
