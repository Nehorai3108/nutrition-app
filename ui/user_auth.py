"""
ui/user_auth.py — Backward-compatible auth shim.

All pages import from here. Delegates to auth/login_ui.py (the new
multi-user system) so that no page needs touching.
"""
from __future__ import annotations

import streamlit as st

#  Delegate to new auth system 
from auth.login_ui import (
    require_auth,
    get_user_id,
    get_user_email,
    render_login_ui,
)
from auth.supabase_client import (
    get_supabase,
    get_current_user,
    install_cookie_session,
    clear_session_cookies,
)


#  Legacy helpers (keep old callers working) 

def get_user() -> dict | None:
    return get_current_user()


def is_logged_in() -> bool:
    return get_current_user() is not None


def do_logout():
    """Logout: clear Supabase session + cookies + session_state."""
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    clear_session_cookies()
    for key in ("user_id", "user_email", "_sb_access_token", "_sb_refresh_token",
                "_sb_client", "bitefit_user", "bitefit_session", "_sb_cookies_mgr"):
        st.session_state.pop(key, None)
    st.rerun()


def logout_button(label: str = "התנתק ", key: str = "_logout_btn"):
    if st.button(label, key=key):
        do_logout()
