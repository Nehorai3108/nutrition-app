"""
auth/login_ui.py — Single source of truth for authentication.

Every page (including app_user.py) must call `require_auth()` at the top.
Returns the authenticated user_id. When no user is authenticated or Supabase
is not configured, this function renders the appropriate screen and
`st.stop()`s — it never returns a fallback id.

Session-state keys:
    user_id     — authenticated UUID
    user_email  — authenticated email
    _needs_onboarding — True for users who haven't completed profile setup
"""
from __future__ import annotations

import streamlit as st

from auth.supabase_client import get_supabase, is_supabase_configured, get_current_user

_KEY_USER_ID = "user_id"
_KEY_USER_EMAIL = "user_email"
_KEY_NEEDS_ONBOARDING = "_needs_onboarding"


# ── Public API ────────────────────────────────────────────────────────────────

def require_auth() -> str:
    """
    Gate at the top of every page. Returns user_id when authenticated.

    When Supabase is misconfigured: render error + st.stop().
    When no user is logged in: render login UI + st.stop().
    """
    if not is_supabase_configured():
        st.error("⚠️ השרת אינו מוגדר כראוי — נא לפנות לתמיכה.")
        st.caption("Server misconfigured: Supabase credentials missing.")
        st.stop()
    user = get_current_user()
    if user is None:
        render_login_ui()
        st.stop()
    return user["id"]


def get_user_id() -> str | None:
    """Return authenticated user_id, or None if not logged in."""
    user = get_current_user()
    return user["id"] if user else None


def get_user_email() -> str:
    """Return authenticated user's email, or empty string."""
    user = get_current_user()
    return user.get("email", "") if user else ""


# ── Internal: session bookkeeping ─────────────────────────────────────────────

def _set_session(user) -> None:
    """Write auth state to session_state after successful login/signup."""
    st.session_state[_KEY_USER_ID] = user.id
    st.session_state[_KEY_USER_EMAIL] = user.email


def _clear_session() -> None:
    """Clear all auth + per-user session state. Called on logout."""
    for k in (_KEY_USER_ID, _KEY_USER_EMAIL, _KEY_NEEDS_ONBOARDING):
        st.session_state.pop(k, None)
    # Clear all per-user namespaced keys (chat history, etc.)
    for k in [k for k in st.session_state.keys() if k.startswith("chat_messages_")]:
        st.session_state.pop(k, None)
    # Clear in-flight scan / inventory caches that may bleed across users
    for k in ("scanned_inventory", "_pending_recipe_filter"):
        st.session_state.pop(k, None)


# ── Auth actions ──────────────────────────────────────────────────────────────

def _do_login(email: str, password: str) -> str | None:
    """Return None on success, error message string on failure."""
    try:
        resp = get_supabase().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        if resp.user:
            _set_session(resp.user)
            # Mark onboarding needed if profile is missing/blank
            _check_onboarding_needed(resp.user.id)
            return None
        return "אימייל או סיסמה שגויים"
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "Invalid login" in msg or "invalid_credentials" in msg:
            return "אימייל או סיסמה שגויים"
        if "Email not confirmed" in msg:
            return "יש לאשר את האימייל שנשלח לתיבת הדואר שלך"
        return f"שגיאת התחברות: {msg}"


def _do_signup(email: str, password: str) -> str | None:
    """Return None on success, error message string on failure."""
    try:
        resp = get_supabase().auth.sign_up({"email": email, "password": password})
        if resp.user:
            _set_session(resp.user)
            # Seed an empty profile row so RLS-protected reads later don't
            # 404, then mark the user as needing onboarding.
            _seed_empty_profile(resp.user.id)
            st.session_state[_KEY_NEEDS_ONBOARDING] = True
            return None
        return "ההרשמה נכשלה — נסה שוב"
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return "האימייל הזה כבר רשום — התחבר במקום"
        if "password" in msg.lower() or "Password should" in msg:
            return "הסיסמה חייבת להיות לפחות 6 תווים"
        return f"שגיאת הרשמה: {msg}"


def _seed_empty_profile(user_id: str) -> None:
    """Create a blank profiles row so the new user has a record from the start."""
    try:
        from nutrition_app.repositories.profile_repository import ProfileRepository
        repo = ProfileRepository()
        # Only seed if no row exists yet (idempotent in case of replay).
        existing = repo.load(user_id)
        if existing and existing.get("name"):
            return
        repo.save({
            "user_id": user_id,
            "name": "",
            "gender": "male",
            "date_of_birth": "",
            "height_cm": 0,
            "weight_kg": 0,
            "activity_level": "moderately_active",
            "goal": "maintain",
            "meal_preferences": {
                "kashrut": "parve",
                "allergies": [],
                "preferred_foods": [],
                "disliked_foods": [],
                "meals_per_day": 5,
            },
        })
    except Exception:
        # Don't block signup if seed insert fails — onboarding will re-attempt.
        pass


def _check_onboarding_needed(user_id: str) -> None:
    """Set _needs_onboarding flag if profile is blank/missing."""
    try:
        from nutrition_app.repositories.profile_repository import ProfileRepository
        profile = ProfileRepository().load(user_id)
        if not profile or not profile.get("name"):
            st.session_state[_KEY_NEEDS_ONBOARDING] = True
    except Exception:
        pass


def logout() -> None:
    """Sign out of Supabase, clear all session state, rerun."""
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    _clear_session()
    st.rerun()


def logout_button(label: str = "התנתק 👋", key: str = "_auth_logout_btn") -> None:
    if st.button(label, key=key):
        logout()


# ── Login UI ──────────────────────────────────────────────────────────────────

def render_login_ui() -> None:
    """Render the login/signup screen. Caller should st.stop() afterwards."""
    st.markdown(
        """<style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {max-width:440px !important; padding-top:3rem !important;}
        </style>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="text-align:center;padding:12px 0 4px">'
        '<span style="font-size:3rem">🥗</span><br>'
        '<span style="font-size:1.8rem;font-weight:800;color:#f4f6fb">BiteFit</span><br>'
        '<span style="font-size:0.82rem;color:#8892a4">מעקב תזונה חכם</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    tab_in, tab_up = st.tabs(["🔑  התחברות", "✨  הרשמה"])

    with tab_in:
        with st.form("auth_login_form", clear_on_submit=False):
            email = st.text_input(
                "אימייל", placeholder="you@example.com", key="auth_login_email"
            )
            password = st.text_input(
                "סיסמה", type="password", placeholder="••••••", key="auth_login_pw"
            )
            ok = st.form_submit_button(
                "התחבר ➤", use_container_width=True, type="primary"
            )
        if ok:
            if not email or not password:
                st.error("נא למלא את שני השדות")
            else:
                with st.spinner("מתחבר..."):
                    err = _do_login(email.strip(), password)
                if err:
                    st.error(err)
                else:
                    st.rerun()

    with tab_up:
        with st.form("auth_signup_form", clear_on_submit=False):
            s_email = st.text_input(
                "אימייל", placeholder="you@example.com", key="auth_signup_email"
            )
            s_pass = st.text_input(
                "סיסמה (מינ׳ 6 תווים)", type="password", key="auth_signup_pw"
            )
            s_confirm = st.text_input(
                "אשר סיסמה", type="password", key="auth_signup_pw_confirm"
            )
            ok2 = st.form_submit_button(
                "הירשם ➤", use_container_width=True, type="primary"
            )
        if ok2:
            if not s_email or not s_pass:
                st.error("נא למלא את כל השדות")
            elif s_pass != s_confirm:
                st.error("הסיסמאות אינן תואמות")
            elif len(s_pass) < 6:
                st.error("הסיסמה חייבת להיות לפחות 6 תווים")
            else:
                with st.spinner("נרשם..."):
                    err = _do_signup(s_email.strip(), s_pass)
                if err:
                    st.error(err)
                else:
                    st.success("נרשמת בהצלחה! 🎉")
                    st.rerun()
