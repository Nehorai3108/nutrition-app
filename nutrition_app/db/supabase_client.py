"""
supabase_client.py — Per-session Supabase client for BiteFit.

Creates one Supabase client per Streamlit session (stored in session_state)
and authenticates it with the current user's JWT so that RLS policies work
correctly and every user sees only their own data.
"""
from __future__ import annotations

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def _base_supabase() -> Client:
    """Cached base client used only for reading credentials."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def get_supabase() -> Client:
    """
    Return a Supabase client for the current Streamlit session.

    Each session gets its own Client instance (stored in session_state)
    so that authenticating one user's session never affects another user.
    The client is authenticated with the current user's access token so
    that Supabase RLS policies (auth.uid() = user_id) work correctly.
    """
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]

    # One client per session — never shared between users
    if "_sb_data_client" not in st.session_state:
        st.session_state["_sb_data_client"] = create_client(url, key)

    client: Client = st.session_state["_sb_data_client"]

    # Authenticate the client with the current user's JWT so RLS works
    session = st.session_state.get("bitefit_session")
    if session:
        try:
            access_token  = getattr(session, "access_token",  None)
            refresh_token = getattr(session, "refresh_token", None) or ""
            if access_token:
                client.auth.set_session(access_token, refresh_token)
        except Exception:
            pass

    return client


def is_supabase_configured() -> bool:
    """True when Supabase credentials are present in secrets."""
    try:
        return bool(
            st.secrets.get("SUPABASE_URL") and
            st.secrets.get("SUPABASE_ANON_KEY")
        )
    except Exception:
        return False
