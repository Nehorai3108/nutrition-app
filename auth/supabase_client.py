"""
auth/supabase_client.py — Supabase client + current-user accessor.

Loads SUPABASE_URL and SUPABASE_ANON_KEY from .env (via python-dotenv when
available) or os.environ. Also falls back to Streamlit secrets for cloud
deployments.

Auth survives hard page reloads via encrypted browser cookies so that any
navigation method (raw <a href>, browser back/forward, tab restart) keeps
the user logged in.

Exports:
    get_supabase() -> Client     — per-session Supabase client w/ user JWT
    get_current_user() -> dict | None
    install_cookie_session()     — call at the top of every page; restores
                                   the JWT from cookies into session_state
                                   when the latter is empty.
"""
from __future__ import annotations

import hashlib
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
_KEY_COOKIES = "_sb_cookies_mgr"

# Cookie names (under the prefix below)
_COOKIE_PREFIX = "bitefit_"
_COOKIE_USER_ID = "user_id"
_COOKIE_USER_EMAIL = "user_email"
_COOKIE_ACCESS = "access_token"
_COOKIE_REFRESH = "refresh_token"


def _get_cookies():
    """Return the CookieManager singleton for this session, or None if the
    cookies package isn't installed."""
    mgr = st.session_state.get(_KEY_COOKIES)
    if mgr is not None:
        return mgr
    try:
        import extra_streamlit_components as stx
    except Exception:
        return None
    # key= is required so the component instance is stable across reruns.
    try:
        mgr = stx.CookieManager(key="bitefit_auth_cookies")
    except Exception:
        return None
    st.session_state[_KEY_COOKIES] = mgr
    return mgr


_COOKIES_CHECKED = "_sb_cookies_checked"


def install_cookie_session() -> bool:
    """
    Hydrate session_state from cookies when needed.

    Returns True  — cookies are definitively loaded (or unavailable).
    Returns False — first render of a fresh session; the CookieManager
                    iframe hasn't sent data yet. Caller should show a
                    loading screen and st.stop() so the component can
                    fire its rerun.

    On the very first script run of a new Streamlit session,
    extra_streamlit_components.CookieManager has not yet received the
    browser cookies.  get_all() returns {} at that point and the
    component triggers a rerun asynchronously when ready.
    We track this with _COOKIES_CHECKED in session_state so we only
    wait ONE render — after that we either have cookies or we don't.
    """
    mgr = _get_cookies()
    if mgr is None:
        return True  # No cookie support — fall back to session-only auth.

    already_checked = st.session_state.get(_COOKIES_CHECKED, False)

    try:
        all_cookies = mgr.get_all() or {}
    except Exception:
        st.session_state[_COOKIES_CHECKED] = True
        return True

    # On the very first render of a fresh session (no user yet, never
    # checked before), the component might not have sent cookies yet.
    # If there's nothing in all_cookies, wait one more render.
    if not already_checked and not st.session_state.get(_KEY_USER_ID):
        uid = all_cookies.get(_COOKIE_PREFIX + _COOKIE_USER_ID)
        if not uid:
            # Mark as checked so we don't wait again next render
            st.session_state[_COOKIES_CHECKED] = True
            return False  # Signal: still loading, show spinner

    st.session_state[_COOKIES_CHECKED] = True

    if not st.session_state.get(_KEY_USER_ID):
        uid = all_cookies.get(_COOKIE_PREFIX + _COOKIE_USER_ID)
        access = all_cookies.get(_COOKIE_PREFIX + _COOKIE_ACCESS)
        refresh = all_cookies.get(_COOKIE_PREFIX + _COOKIE_REFRESH)
        if uid and access:
            st.session_state[_KEY_USER_ID] = uid
            st.session_state[_KEY_USER_EMAIL] = all_cookies.get(_COOKIE_PREFIX + _COOKIE_USER_EMAIL) or ""
            st.session_state[_KEY_ACCESS_TOKEN] = access
            if refresh:
                st.session_state[_KEY_REFRESH_TOKEN] = refresh
    return True


def write_session_cookies(user_id: str, email: str, access: str, refresh: str) -> None:
    """Persist the JWT to cookies. Called from _do_login/_do_signup so hard
    reloads (raw <a href>, F5, new tab) restore the session automatically."""
    mgr = _get_cookies()
    if mgr is None:
        return
    try:
        # 7-day session lifetime (matches Supabase default refresh window)
        from datetime import datetime, timedelta, timezone
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        mgr.set(_COOKIE_PREFIX + _COOKIE_USER_ID, user_id or "", expires_at=expires_at, key="set_uid")
        mgr.set(_COOKIE_PREFIX + _COOKIE_USER_EMAIL, email or "", expires_at=expires_at, key="set_email")
        if access:
            mgr.set(_COOKIE_PREFIX + _COOKIE_ACCESS, access, expires_at=expires_at, key="set_access")
        if refresh:
            mgr.set(_COOKIE_PREFIX + _COOKIE_REFRESH, refresh, expires_at=expires_at, key="set_refresh")
    except Exception:
        pass


def clear_session_cookies() -> None:
    """Remove auth cookies on logout."""
    mgr = _get_cookies()
    if mgr is None:
        return
    for k in (_COOKIE_USER_ID, _COOKIE_USER_EMAIL, _COOKIE_ACCESS, _COOKIE_REFRESH):
        try:
            mgr.delete(_COOKIE_PREFIX + k, key=f"del_{k}")
        except Exception:
            pass


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
