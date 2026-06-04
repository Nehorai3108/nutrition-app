"""
ui/persistent_auth.py — Shim: delegates to new cookie-based auth system.

Previously used URL query params for refresh token storage.
Now delegates to auth/supabase_client.py which uses browser cookies (more
secure, survives hard navigation, 7-day lifetime).
"""
from __future__ import annotations


def setup_persistent_auth() -> None:
    """Called at top of every page — now handled by install_cookie_session()
    inside require_auth(). This is a no-op kept for backward compatibility."""
    try:
        from auth.supabase_client import install_cookie_session
        install_cookie_session()
    except Exception:
        pass


def save_auth_cookie(user_id: str = "", email: str = "", refresh_token: str = "") -> None:
    """Legacy shim — cookies are now written in auth/supabase_client.py."""
    pass


def clear_auth_cookie() -> None:
    """Legacy shim — cookies cleared via auth/supabase_client.clear_session_cookies()."""
    try:
        from auth.supabase_client import clear_session_cookies
        clear_session_cookies()
    except Exception:
        pass
