"""
ui/user_auth.py — Backward-compatible auth shim.

All pages import from here. Delegates to auth/login_ui.py (the canonical
multi-user auth system) so that no page needs to know the internal structure.
"""
from __future__ import annotations

import streamlit as st

from auth.login_ui import (
    require_auth,
    get_user_id,
    get_user_email,
    render_login_ui,
    logout_button,
    logout,
)
from auth.supabase_client import (
    get_supabase,
    get_current_user,
    install_cookie_session,
    clear_session_cookies,
)


def get_user() -> dict | None:
    return get_current_user()


def is_logged_in() -> bool:
    return get_current_user() is not None


def do_logout():
    logout()
