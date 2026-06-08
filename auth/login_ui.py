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
    _pending_email_confirmation — email of a user who signed up / tried to
                                   log in but hasn't confirmed their address
"""
from __future__ import annotations

import streamlit as st

from auth.supabase_client import (
    get_supabase,
    is_supabase_configured,
    get_current_user,
    install_cookie_session,
    write_session_cookies,
    clear_session_cookies,
)

_KEY_USER_ID = "user_id"
_KEY_USER_EMAIL = "user_email"
_KEY_NEEDS_ONBOARDING = "_needs_onboarding"
_KEY_ACCESS_TOKEN = "_sb_access_token"
_KEY_REFRESH_TOKEN = "_sb_refresh_token"
_KEY_PENDING_CONFIRMATION = "_pending_email_confirmation"


# Public API

def require_auth() -> str:
    """Auth temporarily disabled — returns default user."""
    return "ui_user_001"

    # Successful auth — reset the cookie-wait counter so the next
    # fresh navigation (F5 / direct URL) gets a clean grace period.
    st.session_state.pop("_sb_cookie_wait", None)
    return user["id"]


def get_user_id() -> str | None:
    """Return authenticated user_id, or None if not logged in."""
    user = get_current_user()
    return user["id"] if user else None


def get_user_email() -> str:
    """Return authenticated user's email, or empty string."""
    user = get_current_user()
    return user.get("email", "") if user else ""


# Internal session bookkeeping

def _set_session(user, session=None) -> None:
    """Write auth state to session_state AND browser cookie after successful
    login/signup. Cookie persistence lets hard reloads (raw <a href>) keep
    the user logged in; session_state lets reruns avoid re-decrypting."""
    st.session_state[_KEY_USER_ID] = user.id
    st.session_state[_KEY_USER_EMAIL] = user.email
    access = refresh = ""
    if session is not None:
        access = getattr(session, "access_token", None) or ""
        refresh = getattr(session, "refresh_token", None) or ""
        if access:
            st.session_state[_KEY_ACCESS_TOKEN] = access
        if refresh:
            st.session_state[_KEY_REFRESH_TOKEN] = refresh
    write_session_cookies(user.id, user.email or "", access, refresh)


def _clear_session() -> None:
    """Clear all auth + per-user session state AND browser cookies."""
    clear_session_cookies()
    for k in (_KEY_USER_ID, _KEY_USER_EMAIL, _KEY_NEEDS_ONBOARDING,
              _KEY_ACCESS_TOKEN, _KEY_REFRESH_TOKEN, _KEY_PENDING_CONFIRMATION,
              "_sb_client"):
        st.session_state.pop(k, None)
    # Clear all per-user namespaced keys (chat history, etc.)
    for k in [k for k in st.session_state.keys() if k.startswith("chat_messages_")]:
        st.session_state.pop(k, None)
    # Clear in-flight scan / inventory caches that may bleed across users
    for k in ("scanned_inventory", "_pending_recipe_filter"):
        st.session_state.pop(k, None)


# Auth actions

def _do_login(email: str, password: str) -> str | None:
    """Return None on success, error message string on failure.

    If Supabase returns a user but no session (email confirmation enabled
    and not yet confirmed), enter the pending-confirmation screen instead
    of granting access.
    """
    try:
        resp = get_supabase().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        if resp.user is None:
            return "אימייל או סיסמה שגויים"
        if resp.session is None:
            st.session_state[_KEY_PENDING_CONFIRMATION] = email
            return None
        _set_session(resp.user, resp.session)
        _check_onboarding_needed(resp.user.id)
        return None
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "Invalid login" in msg or "invalid_credentials" in msg:
            return "אימייל או סיסמה שגויים"
        if "Email not confirmed" in msg:
            st.session_state[_KEY_PENDING_CONFIRMATION] = email
            return None
        return f"שגיאת התחברות: {msg}"


def _do_signup(email: str, password: str) -> str | None:
    """Return None on success, error message string on failure.

    Handles two Supabase response shapes:
    1. resp.user and resp.session both present -> email confirmation OFF.
       Treat as a real login: write session, seed profile, enter onboarding.
    2. resp.user present but resp.session is None -> email confirmation ON.
       User is created but cannot act yet. Do NOT write user_id to
       session_state (otherwise require_auth() would let them in but every
       RLS-protected query would silently return empty). Store the email
       in a pending flag so render_login_ui() can show a "check your inbox"
       screen.
    """
    try:
        resp = get_supabase().auth.sign_up({"email": email, "password": password})
        if resp.user is None:
            return "ההרשמה נכשלה - נסה שוב"
        if resp.session is None:
            st.session_state[_KEY_PENDING_CONFIRMATION] = email
            return None
        _set_session(resp.user, resp.session)
        _seed_empty_profile(resp.user.id)
        st.session_state[_KEY_NEEDS_ONBOARDING] = True
        return None
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return "האימייל הזה כבר רשום - התחבר במקום"
        if "password" in msg.lower() or "Password should" in msg:
            return "הסיסמה חייבת להיות לפחות 6 תווים"
        return f"שגיאת הרשמה: {msg}"


def _seed_empty_profile(user_id: str) -> None:
    """Create a blank profiles row so the new user has a record from the start."""
    try:
        from nutrition_app.repositories.profile_repository import ProfileRepository
        repo = ProfileRepository()
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


def logout_button(label: str = "התנתק \U0001f44b", key: str = "_auth_logout_btn") -> None:
    if st.button(label, key=key):
        logout()


def _render_pending_confirmation_screen(email: str) -> None:
    """Shown after signup (or after attempting login with an unconfirmed account)
    when Supabase has email confirmation enabled. The user must click the link
    in their inbox before they can enter the app."""
    st.markdown(
        '<div style="text-align:center;padding:24px 0 4px">'
        '<span style="font-size:3rem">\U0001f4ec</span><br>'
        '<span style="font-size:1.4rem;font-weight:800;color:#f4f6fb">'
        'נשלח אליך מייל לאישור'
        '</span><br>'
        f'<span style="font-size:0.92rem;color:#8892a4">{email}</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.info(
        "בדוק את תיבת הדואר שלך (כולל ספאם) "
        "ולחץ על הקישור לאישור הכתובת. "
        "לאחר אישור, חזור לכאן והתחבר."
    )
    col_resend, col_back = st.columns(2)
    with col_resend:
        if st.button("\U0001f4e8 שלח שוב",
                     use_container_width=True, key="auth_resend_confirmation"):
            try:
                get_supabase().auth.resend({"type": "signup", "email": email})
                st.success("מייל אישור נשלח שוב.")
            except Exception as e:
                st.error(f"שגיאה בשליחה חוזרת: {e}")
    with col_back:
        if st.button(" חזרה להתחברות",
                     use_container_width=True, key="auth_back_to_login"):
            st.session_state.pop(_KEY_PENDING_CONFIRMATION, None)
            st.rerun()


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
        '<span style="font-size:3rem">\U0001f957</span><br>'
        '<span style="font-size:1.8rem;font-weight:800;color:#f4f6fb">BiteFit</span><br>'
        '<span style="font-size:0.82rem;color:#8892a4">מעקב תזונה חכם</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    # Pending email-confirmation flow takes over the screen entirely so the
    # user can't accidentally enter the app with an unconfirmed account.
    pending_email = st.session_state.get(_KEY_PENDING_CONFIRMATION)
    if pending_email:
        _render_pending_confirmation_screen(pending_email)
        return

    tab_in, tab_up = st.tabs(["\U0001f511  התחברות",
                              "  הרשמה"])

    with tab_in:
        with st.form("auth_login_form", clear_on_submit=False):
            email = st.text_input("אימייל",
                                  placeholder="you@example.com", key="auth_login_email")
            password = st.text_input("סיסמה", type="password",
                                     placeholder="••••••",
                                     key="auth_login_pw")
            ok = st.form_submit_button("התחבר ",
                                       use_container_width=True, type="primary")
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
            s_email = st.text_input("אימייל",
                                    placeholder="you@example.com", key="auth_signup_email")
            s_pass = st.text_input("סיסמה (מין' 6 תווים)",
                                   type="password", key="auth_signup_pw")
            s_confirm = st.text_input("אשר סיסמה",
                                      type="password", key="auth_signup_pw_confirm")
            ok2 = st.form_submit_button("הירשם ",
                                        use_container_width=True, type="primary")
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
                    if st.session_state.get(_KEY_PENDING_CONFIRMATION):
                        st.rerun()
                    else:
                        st.success("נרשמת בהצלחה! \U0001f389")
                        st.rerun()
