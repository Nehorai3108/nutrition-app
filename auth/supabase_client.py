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


# Session-state keys
_KEY_USER_ID = "user_id"
_KEY_USER_EMAIL = "user_email"
_KEY_ACCESS_TOKEN = "_sb_access_token"
_KEY_REFRESH_TOKEN = "_sb_refresh_token"
_KEY_CLIENT = "_sb_client"


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


def get_supabase() -> Client:
    """
    Per-session Supabase client. Each Streamlit session gets its OWN client so
    JWTs don't bleed between concurrent users. Tokens persist in session_state
    so they survive Streamlit reruns and hot reloads.
    """
    client = st.session_state.get(_KEY_CLIENT)
    if client is None:
        url, key = _load_creds()
        if not url or not key:
            raise RuntimeError(
                "Supabase is not configured. Set SUPABASE_URL and "
                "SUPABASE_ANON_KEY in your .env file or Streamlit secrets."
            )
        client = create_client(url, key)
        st.session_state[_KEY_CLIENT] = client

    # Re-attach the session JWT if we have one but the client has lost it
    # (e.g. fresh client after a rerun, code reload, or first call this session).
    # supabase-py 2.x does NOT auto-propagate the user JWT from auth → postgrest,
    # so PostgREST keeps using the anon key and every RLS-protected write fails
    # with "new row violates row-level security policy". Force it explicitly.
    access = st.session_state.get(_KEY_ACCESS_TOKEN)
    refresh = st.session_state.get(_KEY_REFRESH_TOKEN)
    if access and refresh:
        try:
            current = client.auth.get_session()
            if current is None or getattr(current, "access_token", None) != access:
                client.auth.set_session(access, refresh)
        except Exception:
            pass
        # Always force the PostgREST sub-client to use the user JWT.
        try:
            client.postgrest.auth(access)
        except Exception:
            pass
    return client


def get_current_user() -> Optional[dict]:
    """Return {'id', 'email'} from session_state, or None when not authenticated."""
    uid = st.session_state.get(_KEY_USER_ID)
    if uid:
        return {
            "id": uid,
            "email": st.session_state.get(_KEY_USER_EMAIL, ""),
        }
    return None
