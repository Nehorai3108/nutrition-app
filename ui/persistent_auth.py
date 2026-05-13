"""
ui/persistent_auth.py — Query-param based persistent auth for BiteFit.

Stores user_id in the URL query string (?bf_uid=...) so the session
survives WebSocket reconnects and button clicks.
"""
from __future__ import annotations
import streamlit as st

_PARAM = "bf_uid"
_PARAM_EMAIL = "bf_em"


def setup_persistent_auth() -> None:
    """
    Called at the top of every page.
    If session state has no user_id, tries to restore it from URL params.
    """
    if st.session_state.get("user_id"):
        return  # already in session

    uid = st.query_params.get(_PARAM)
    if uid:
        email = st.query_params.get(_PARAM_EMAIL, "")
        st.session_state["user_id"]      = uid
        st.session_state["user_email"]   = email
        st.session_state["bitefit_user"] = {"id": uid, "email": email}


def save_auth_cookie(user_id: str, email: str = "") -> None:
    """Called right after successful login — saves uid to URL params."""
    st.query_params[_PARAM]       = user_id
    st.query_params[_PARAM_EMAIL] = email


def clear_auth_cookie() -> None:
    """Called on logout — removes uid from URL params."""
    st.query_params.pop(_PARAM,       None)
    st.query_params.pop(_PARAM_EMAIL, None)
