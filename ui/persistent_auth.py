"""
ui/persistent_auth.py — Streamlit Cloud built-in auth for BiteFit.

Uses st.experimental_user (Streamlit Cloud managed login) to identify users.
Each user's email becomes their unique user_id.
No Supabase auth needed — Streamlit handles login/session completely.
"""
from __future__ import annotations
import streamlit as st


def setup_persistent_auth() -> None:
    """
    Called at the top of every page.
    Sets user_id from Streamlit's built-in user identity.
    On Streamlit Cloud (with viewer auth enabled): uses the logged-in email.
    Locally / public app: falls back to "ui_user_001".
    """
    if st.session_state.get("user_id"):
        return  # already set this session

    try:
        user = st.experimental_user
        if user and getattr(user, "is_logged_in", False) and user.email:
            uid   = user.email
            email = user.email
            st.session_state["user_id"]      = uid
            st.session_state["user_email"]   = email
            st.session_state["bitefit_user"] = {"id": uid, "email": email}
    except Exception:
        pass  # local dev or Streamlit version without experimental_user


def save_auth_cookie(user_id: str, email: str = "") -> None:
    """No-op — Streamlit Cloud manages the session itself."""
    pass


def clear_auth_cookie() -> None:
    """No-op — Streamlit Cloud manages the session itself."""
    pass
