"""Minimal admin password gate for protected pages.

Usage:
    from ui.auth import require_admin, admin_logout_button

    require_admin(page_title="דאשבורד סוכנים", icon_name="agent")
    # ... rest of the page only renders if authenticated
"""

import hmac
from typing import Optional

import streamlit as st

from .components import inject_global_css, page_header, icon_button

_SESSION_KEY = "is_admin"


def is_admin() -> bool:
    return bool(st.session_state.get(_SESSION_KEY))


def _expected_password() -> Optional[str]:
    """Read the configured admin password from secrets, env, or fallback."""
    try:
        pw = st.secrets.get("admin_password")
        if pw:
            return str(pw)
    except Exception:
        pass
    import os
    return os.environ.get("NUTRITION_ADMIN_PASSWORD")


def login(password: str) -> bool:
    """Compare a submitted password with the configured one (constant-time)."""
    expected = _expected_password()
    if not expected:
        return False
    if hmac.compare_digest(password, expected):
        st.session_state[_SESSION_KEY] = True
        return True
    return False


def logout() -> None:
    st.session_state.pop(_SESSION_KEY, None)


def require_admin(page_title: str = "אזור מנהל", icon_name: str = "lock") -> None:
    """Block the page until the user authenticates as admin.

    Renders a page header and a centered login form. Calls ``st.stop()``
    when the visitor is not yet authenticated, so caller code below this
    function only runs for admins.
    """
    inject_global_css()
    if is_admin():
        return

    page_header(page_title, icon_name=icon_name,
                subtitle="גישה מוגבלת — נדרשת התחברות מנהל")

    st.markdown('<div class="nut-login-card">', unsafe_allow_html=True)

    with st.form("admin_login_form", clear_on_submit=False):
        st.markdown(
            "<h3 style='margin-top:0;text-align:center'>התחברות מנהל</h3>"
            "<p style='text-align:center;color:#a0a0c0;font-size:0.9rem'>"
            "הזן סיסמה כדי לצפות בלוח הבקרה הפנימי.</p>",
            unsafe_allow_html=True,
        )
        password = st.text_input(
            "סיסמת מנהל",
            type="password",
            key="_admin_pw_input",
            placeholder="••••••••",
        )
        submitted = st.form_submit_button(
            "🔓 התחבר",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if login(password):
            st.success("התחברת בהצלחה.")
            st.rerun()
        else:
            st.error("סיסמה שגויה.")

    if _expected_password() is None:
        st.warning(
            "לא הוגדרה סיסמת מנהל. הוסף ``admin_password`` לקובץ "
            "``.streamlit/secrets.toml`` (ראה ``secrets.toml.example``)."
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


def admin_logout_button(key: str = "admin_logout_btn") -> None:
    """Render a small logout button. Call after the page header."""
    if not is_admin():
        return
    if icon_button("התנתק", "logout", key=key, type="secondary",
                   use_container_width=False):
        logout()
        st.rerun()
