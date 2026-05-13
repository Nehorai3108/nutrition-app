"""
ui/persistent_auth.py — Persistent auth via Supabase refresh token.

Stores the Supabase refresh_token in st.query_params so the session
survives button clicks, WebSocket reconnects, and browser restarts.
Refresh tokens last 60 days — users stay logged in automatically.
"""
from __future__ import annotations
import streamlit as st

_PARAM_RT = "bf_rt"   # refresh token in URL


def setup_persistent_auth() -> None:
    """
    Called at the top of every page.
    If session state has no user_id, tries to restore via stored refresh token.
    """
    if st.session_state.get("user_id"):
        return  # already logged in this session

    refresh_token = st.query_params.get(_PARAM_RT)
    if not refresh_token:
        return

    try:
        from auth.supabase_client import get_supabase
        resp = get_supabase().auth.refresh_session(refresh_token)
        if resp and resp.user:
            uid   = resp.user.id
            email = resp.user.email or ""
            st.session_state["user_id"]        = uid
            st.session_state["user_email"]     = email
            st.session_state["bitefit_user"]   = {"id": uid, "email": email}
            # Store session so data client can authenticate with user's JWT
            if resp.session:
                st.session_state["bitefit_session"] = resp.session
            # Rotate the refresh token
            new_rt = getattr(resp.session, "refresh_token", None)
            if new_rt:
                st.query_params[_PARAM_RT] = new_rt
    except Exception:
        # Token expired or invalid — clear it so user sees login
        st.query_params.pop(_PARAM_RT, None)


def save_auth_cookie(user_id: str, email: str = "", refresh_token: str = "") -> None:
    """Called right after successful login — saves refresh token to URL."""
    if refresh_token:
        st.query_params[_PARAM_RT] = refresh_token


def clear_auth_cookie() -> None:
    """Called on logout — removes refresh token from URL."""
    st.query_params.pop(_PARAM_RT, None)
