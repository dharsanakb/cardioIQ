"""Read config from Streamlit secrets, falling back to environment variables."""
import os

import streamlit as st


def get_secret(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:  # no secrets file present
        pass
    return os.environ.get(key, default)
