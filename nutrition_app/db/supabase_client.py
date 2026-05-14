"""
supabase_client.py — Per-session Supabase client for BiteFit.

Creates one Supabase client per Streamlit session (stored in session_state)
and authenticates it with the current user's JWT so that RLS policies work
correctly and every user sees only their own data.

Reads JWT from the new auth system keys (_sb_access_token / _sb_refresh_token)
and also forces postgrest.auth() which supabase-py v2 requires for RLS.
"""
from __future__ import annotations

import streamlit as st
from supabase import create_client, Client


def get_supabase() -> Client:
    """
    Return a Supabase client for the current Streamlit session.

    Each session gets its own Client instance so JWTs never bleed between
    concurrent users. Forces client.postgrest.auth(token) so supabase-py v2
    RLS policies (auth.uid() = user_id) work on every write.
    """
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
    except Exception:
        import os
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not url or not key:
        raise RuntimeError("Supabase credentials missing from secrets / env")

    # One client per session
    if "_sb_data_client" not in st.session_state:
        st.session_state["_sb_data_client"] = create_client(url, key)

    client: Client = st.session_state["_sb_data_client"]

    # ── Attach user JWT ────────────────────────────────────────────────────────
    # New auth system stores tokens under these keys:
    access  = st.session_state.get("_sb_access_token")
    refresh = st.session_state.get("_sb_refresh_token", "")

    # Legacy fallback: old bitefit_session object
    if not access:
        session = st.session_state.get("bitefit_session")
        if session:
            access  = getattr(session, "access_token",  None)
            refresh = getattr(session, "refresh_token", None) or ""

    if access:
        try:
            # Sync auth state (refresh token rotation, session checks)
            current = client.auth.get_session()
            if current is None or getattr(current, "access_token", None) != access:
                client.auth.set_session(access, refresh)
        except Exception:
            pass

        # CRITICAL for supabase-py v2: force PostgREST sub-client to use
        # the user JWT — without this every write fails RLS even if
        # set_session succeeds.
        try:
            client.postgrest.auth(access)
        except Exception:
            pass

    return client


def is_supabase_configured() -> bool:
    """True when Supabase credentials are present in secrets or env."""
    try:
        return bool(
            st.secrets.get("SUPABASE_URL") and
            st.secrets.get("SUPABASE_ANON_KEY")
        )
    except Exception:
        import os
        return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY"))
