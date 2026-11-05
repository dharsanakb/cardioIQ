"""Simple doctor login (demo-grade). Credentials live in secrets, never in the repo."""
import hashlib
import hmac

import streamlit as st

from core.config import get_secret

DEMO_USER = "doctor"
DEMO_PASSWORD = "cardioiq123"


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _users() -> dict:
    users = get_secret("users")
    if users:
        return {str(k).lower(): dict(v) for k, v in users.items()}
    return {DEMO_USER: {"name": "Dr. Demo", "password_sha256": _hash(DEMO_PASSWORD)}}


def is_demo_mode() -> bool:
    return not get_secret("users")


def authenticate(username: str, password: str) -> bool:
    user = _users().get(username.strip().lower())
    if not user:
        return False
    if hmac.compare_digest(_hash(password), user["password_sha256"]):
        st.session_state["authenticated"] = True
        st.session_state["user_name"] = user.get("name", username)
        return True
    return False


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def current_name() -> str:
    return st.session_state.get("user_name", "")


def logout() -> None:
    for key in ("authenticated", "user_name", "selected_patient"):
        st.session_state.pop(key, None)
