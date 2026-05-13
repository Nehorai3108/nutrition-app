"""
auth/supabase_client.py — Supabase client + current-user accessor.

Loads SUPABASE_URL and SUPABASE_ANON_KEY from .env (via python-dotenv when
available) or os.environ. Also falls back to Streamlit secrets for cloud
deployments.

Exports:
    get_supabase() -> Client     — singleton Supabase client
    get_current_user() -> dict | None
                                  — current logged-in user from session_state
                                    or None when not authenticated.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # python-dotenv not installed — fall back to env only
    pass

import streamlit as st
from supabase import create_client, Client


# Session-state keys — kept compatible with ui/user_auth.py
_KEY_USER_ID = "user_id"
_KEY_USER_EMAIL = "user_email"
# Legacy key written by ui/user_auth.py — read for backwards compatibility
_KEY_LEGACY_USER = "bitefit_user"


def _load_creds() -> tuple[Optional[str], Optional[str]]:
    """Read Supabase creds from env first, then Streamlit secrets."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if url and key:
        return url, key
    # Streamlit Cloud fallback
    try:
        url = st.secrets.get("SUPABASE_URL")  # type: ignore[attr-defined]
        key = st.secrets.get("SUPABASE_ANON_KEY")  # type: ignore[attr-defined]
    except Exception:
        return None, None
    return url, key


def is_supabase_configured() -> bool:
    url, key = _load_creds()
    return bool(url and key)


@st.cache_resource
def get_supabase() -> Client:
    """Singleton Supabase client. Cached for the Streamlit session."""
    url, key = _load_creds()
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_ANON_KEY in your .env file or Streamlit secrets."
        )
    return create_client(url, key)


def get_current_user() -> Optional[dict]:
    """
    Return the current user dict (with 'id' and 'email') from session_state,
    or None when not authenticated.

    Reads the new keys (user_id, user_email) first, then falls back to the
    legacy 'bitefit_user' dict written by ui/user_auth.py.
    """
    uid = st.session_state.get(_KEY_USER_ID)
    if uid:
        return {
            "id": uid,
            "email": st.session_state.get(_KEY_USER_EMAIL, ""),
        }
    legacy = st.session_state.get(_KEY_LEGACY_USER)
    if isinstance(legacy, dict) and legacy.get("id"):
        return {"id": legacy["id"], "email": legacy.get("email", "")}
    return None
