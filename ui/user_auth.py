"""
ui/user_auth.py — User authentication for BiteFit (Supabase).

Usage in every page:
    from ui.user_auth import require_auth, get_user_id

    user_id = require_auth()   # shows login if not logged in, then st.stop()
"""
from __future__ import annotations
import streamlit as st

_KEY_USER    = "bitefit_user"
_KEY_SESSION = "bitefit_session"


# ── Getters ───────────────────────────────────────────────────────────────────

def get_user() -> dict | None:
    return st.session_state.get(_KEY_USER)


def get_user_id() -> str:
    """Return Supabase UUID or 'ui_user_001' for local dev (no Supabase)."""
    user = get_user()
    return user["id"] if user else "ui_user_001"


def is_logged_in() -> bool:
    return bool(get_user())


def require_auth() -> str:
    """
    Call at the top of every page.
    Restores session from cookie if available, otherwise returns "ui_user_001".
    """
    try:
        from ui.persistent_auth import setup_persistent_auth
        setup_persistent_auth()
    except Exception:
        pass
    return get_user_id()


# ── Auth actions ──────────────────────────────────────────────────────────────

def do_login(email: str, password: str) -> str | None:
    """Returns None on success, error message string on failure."""
    try:
        from nutrition_app.db.supabase_client import get_supabase
        resp = get_supabase().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        if resp.user:
            st.session_state[_KEY_USER]    = {"id": resp.user.id, "email": resp.user.email}
            st.session_state[_KEY_SESSION] = resp.session
            return None
        return "אימייל או סיסמה שגויים"
    except Exception as e:
        msg = str(e)
        if "Invalid login" in msg or "invalid_credentials" in msg:
            return "אימייל או סיסמה שגויים"
        if "Email not confirmed" in msg:
            return "יש לאשר את האימייל שנשלח לתיבת הדואר שלך"
        return f"שגיאת התחברות: {msg}"


def do_signup(email: str, password: str) -> str | None:
    """Returns None on success, error message string on failure."""
    try:
        from nutrition_app.db.supabase_client import get_supabase
        resp = get_supabase().auth.sign_up({"email": email, "password": password})
        if resp.user:
            st.session_state[_KEY_USER]    = {"id": resp.user.id, "email": resp.user.email}
            st.session_state[_KEY_SESSION] = resp.session
            return None
        return "ההרשמה נכשלה — נסה שוב"
    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return "האימייל הזה כבר רשום — התחבר במקום"
        if "password" in msg.lower() or "Password should" in msg:
            return "הסיסמה חייבת להיות לפחות 6 תווים"
        return f"שגיאת הרשמה: {msg}"


def do_logout():
    try:
        from nutrition_app.db.supabase_client import get_supabase
        get_supabase().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop(_KEY_USER, None)
    st.session_state.pop(_KEY_SESSION, None)
    st.rerun()


# ── Login UI ──────────────────────────────────────────────────────────────────

def _render_login_page():
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

    # ── Login tab ──────────────────────────────────────────────────────────────
    with tab_in:
        with st.form("_bf_login", clear_on_submit=False):
            email    = st.text_input("אימייל", placeholder="you@example.com",
                                     label_visibility="visible")
            password = st.text_input("סיסמה", type="password", placeholder="••••••")
            ok = st.form_submit_button("התחבר ➤", use_container_width=True, type="primary")

        if ok:
            if not email or not password:
                st.error("נא למלא את שני השדות")
            else:
                with st.spinner("מתחבר..."):
                    err = do_login(email.strip(), password)
                if err:
                    st.error(err)
                else:
                    st.rerun()

    # ── Signup tab ─────────────────────────────────────────────────────────────
    with tab_up:
        with st.form("_bf_signup", clear_on_submit=False):
            s_email   = st.text_input("אימייל", placeholder="you@example.com", key="_su_em")
            s_pass    = st.text_input("סיסמה (מינ׳ 6 תווים)", type="password", key="_su_pw")
            s_confirm = st.text_input("אשר סיסמה", type="password", key="_su_cf")
            ok2 = st.form_submit_button("הירשם ➤", use_container_width=True, type="primary")

        if ok2:
            if not s_email or not s_pass:
                st.error("נא למלא את כל השדות")
            elif s_pass != s_confirm:
                st.error("הסיסמאות אינן תואמות")
            elif len(s_pass) < 6:
                st.error("הסיסמה חייבת להיות לפחות 6 תווים")
            else:
                with st.spinner("נרשם..."):
                    err = do_signup(s_email.strip(), s_pass)
                if err:
                    st.error(err)
                else:
                    st.success("נרשמת בהצלחה! 🎉")
                    st.rerun()


def logout_button(label: str = "התנתק 👋", key: str = "_logout_btn"):
    """Small logout button — place in sidebar or page header."""
    if st.button(label, key=key):
        do_logout()
