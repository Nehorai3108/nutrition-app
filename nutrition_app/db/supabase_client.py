"""
supabase_client.py — Supabase client for BiteFit.

Two contexts share this module:
  • Streamlit app  → one client per session (session_state), JWT from session.
  • FastAPI backend → one module-level client (env vars), JWT taken from the
    current request via a contextvar (set in api/deps.get_current_user).

In both cases the user's JWT is attached so RLS policies (auth.uid()=user_id)
work and each user only sees their own rows.
"""
from __future__ import annotations

import os
import contextvars
import streamlit as st
from supabase import create_client, Client

# ── API (non-Streamlit) context ──────────────────────────────────────────────
# The current request's Supabase access token, set per-request by the API.
_api_jwt: contextvars.ContextVar[str | None] = contextvars.ContextVar("_api_jwt", default=None)
_api_client: Client | None = None


def set_api_jwt(token: str | None) -> None:
    """Called by the API per request so the data client uses the user's JWT."""
    _api_jwt.set(token)


def _in_streamlit() -> bool:
    """True only inside a live Streamlit run (not when imported by the API)."""
    try:
        return st.runtime.exists()
    except Exception:
        return False


def _api_get_supabase() -> Client:
    """Module-level client for the FastAPI backend, authed with the request JWT."""
    global _api_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError("Supabase credentials missing from env")
    if _api_client is None:
        _api_client = create_client(url, key)
    token = _api_jwt.get()
    # Attach (or clear) the per-request user JWT so RLS sees the right user.
    try:
        _api_client.postgrest.auth(token or key)
    except Exception:
        pass
    return _api_client


def get_supabase() -> Client:
    """Return the right Supabase client for the current context."""
    if not _in_streamlit():
        return _api_get_supabase()
    return _streamlit_get_supabase()


def _streamlit_get_supabase() -> Client:
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
