#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app_admin.py — דאשבורד ניהול למערכת תזונה חכמה
הרצה: streamlit run app_admin.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from ui.auth import require_admin, is_admin
from ui.components import inject_global_css

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="דאשבורד ניהול",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system ────────────────────────────────────────────────────────────
inject_global_css()

# ── Admin Access Gate ────────────────────────────────────────────────────────
# If not authenticated, show login form and stop. Sidebar is hidden on login.
if not is_admin():
    st.markdown(
        '<style>section[data-testid="stSidebar"] {display:none}</style>',
        unsafe_allow_html=True,
    )
    require_admin(page_title="ניהול המערכת", icon_name="shield")
    # require_admin calls st.stop() when not authenticated — code below
    # this block only runs after a successful login + rerun

# ── Navigation — explicitly register admin pages ─────────────────────────────
pg = st.navigation(
    {
        "ניהול מערכת": [
            st.Page(
                "pages_admin/1_agents_dashboard.py",
                title="סוכנים",
                icon="🤖",
                default=True,
            ),
            st.Page(
                "pages_admin/2_photo_manager.py",
                title="מנהל תמונות",
                icon="🖼️",
            ),
            st.Page(
                "pages_admin/3_audit_logs.py",
                title="ביקורת לוג",
                icon="📋",
            ),
            st.Page(
                "pages_admin/4_settings.py",
                title="הגדרות",
                icon="⚙️",
            ),
        ],
        "מערכת": [
            st.Page(
                "pages/2_recipes.py",
                title="מתכונים",
                icon="📖",
            ),
            st.Page(
                "pages/17_weekly_workout_plan.py",
                title="אימונים",
                icon="🏃",
            ),
        ],
    }
)

pg.run()
