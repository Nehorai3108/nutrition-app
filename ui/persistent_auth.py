"""
ui/persistent_auth.py — Cookie-based persistent auth for BiteFit.

Stores user_id + email in a browser cookie so the session survives
WebSocket reconnects (common on mobile).

Usage — call at the top of every page BEFORE require_auth():
    from ui.persistent_auth import setup_persistent_auth, save_auth_cookie, clear_auth_cookie
    setup_persistent_auth()
"""
from __future__ import annotations
import streamlit as st

_COOKIE_UID   = "bf_uid"
_COOKIE_EMAIL = "bf_email"
_MAX_AGE      = 30 * 24 * 3600   # 30 days


def _get_controller():
    try:
        from streamlit_cookies_controller import CookieController
        return CookieController()
    except Exception:
        return None


def setup_persistent_auth() -> None:
    """
    Called at the top of every page.
    If session state has no user_id, tries to restore it from cookie.
    """
    if st.session_state.get("user_id"):
        return   # already logged in this session

    ctrl = _get_controller()
    if ctrl is None:
        return

    try:
        uid   = ctrl.get(_COOKIE_UID)
        email = ctrl.get(_COOKIE_EMAIL) or ""
        if uid:
            st.session_state["user_id"]      = uid
            st.session_state["user_email"]   = email
            st.session_state["bitefit_user"] = {"id": uid, "email": email}
    except Exception:
        pass


def save_auth_cookie(user_id: str, email: str = "") -> None:
    """Called right after successful login."""
    ctrl = _get_controller()
    if ctrl is None:
        return
    try:
        ctrl.set(_COOKIE_UID,   user_id, max_age=_MAX_AGE)
        ctrl.set(_COOKIE_EMAIL, email,   max_age=_MAX_AGE)
    except Exception:
        pass


def clear_auth_cookie() -> None:
    """Called on logout."""
    ctrl = _get_controller()
    if ctrl is None:
        return
    try:
        ctrl.remove(_COOKIE_UID)
        ctrl.remove(_COOKIE_EMAIL)
    except Exception:
        pass
