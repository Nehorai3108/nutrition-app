"""
auth/login_ui.py — Streamlit login/signup component.

Renders Sign Up + Log In tabs. On successful auth, writes both the new keys
(user_id / user_email) AND the legacy `bitefit_user` dict so existing pages
that read the legacy key keep working.
"""
from __future__ import annotations

import streamlit as st

from auth.supabase_client import get_supabase


_KEY_USER_ID = "user_id"
_KEY_USER_EMAIL = "user_email"
_KEY_LEGACY_USER = "bitefit_user"
_KEY_LEGACY_SESSION = "bitefit_session"


def _set_session(user, session=None) -> None:
    st.session_state[_KEY_USER_ID] = user.id
    st.session_state[_KEY_USER_EMAIL] = user.email
    # Maintain legacy keys so the rest of the codebase (ui/user_auth.py
    # consumers, pages/*) continues working without further changes.
    st.session_state[_KEY_LEGACY_USER] = {"id": user.id, "email": user.email}
    if session is not None:
        st.session_state[_KEY_LEGACY_SESSION] = session


def _do_login(email: str, password: str) -> str | None:
    """Return None on success, error message on failure."""
    try:
        resp = get_supabase().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        if resp.user:
            _set_session(resp.user, resp.session)
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
    """Return None on success, error message on failure."""
    try:
        resp = get_supabase().auth.sign_up({"email": email, "password": password})
        if resp.user:
            _set_session(resp.user, resp.session)
            return None
        return "ההרשמה נכשלה — נסה שוב"
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return "האימייל הזה כבר רשום — התחבר במקום"
        if "password" in msg.lower() or "Password should" in msg:
            return "הסיסמה חייבת להיות לפחות 6 תווים"
        return f"שגיאת הרשמה: {msg}"


def render_login_ui() -> None:
    """Render the full login/signup screen. Caller should st.stop() afterwards."""
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


def logout() -> None:
    """Clear all auth-related session_state keys and rerun."""
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    for k in (
        _KEY_USER_ID,
        _KEY_USER_EMAIL,
        _KEY_LEGACY_USER,
        _KEY_LEGACY_SESSION,
    ):
        st.session_state.pop(k, None)
    st.rerun()


def logout_button(label: str = "התנתק 👋", key: str = "_auth_logout_btn") -> None:
    if st.button(label, key=key):
        logout()
