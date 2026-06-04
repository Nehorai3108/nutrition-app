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
_p_agents   = st.Page("pages_admin/1_agents_dashboard.py", title="סוכנים",      icon="🤖", default=True)
_p_photos   = st.Page("pages_admin/2_photo_manager.py",    title="מנהל תמונות", icon="🖼️")
_p_audit    = st.Page("pages_admin/3_audit_logs.py",       title="ביקורת לוג",  icon="📋")
_p_settings = st.Page("pages_admin/4_settings.py",         title="הגדרות",      icon="⚙️")
_p_fimages  = st.Page("pages_admin/5_food_images.py",      title="תמונות מזון", icon="🍎")

cols_nav = st.columns(5)
cols_nav[0].page_link(_p_agents,   label="סוכנים",       use_container_width=True)
cols_nav[1].page_link(_p_photos,   label="מנהל תמונות",  use_container_width=True)
cols_nav[2].page_link(_p_audit,    label="ביקורת לוג",   use_container_width=True)
cols_nav[3].page_link(_p_settings, label="הגדרות",       use_container_width=True)
cols_nav[4].page_link(_p_fimages,  label="תמונות מזון",  use_container_width=True)

pg = st.navigation(
    {
        "ניהול מערכת": [
            _p_agents, _p_photos, _p_audit, _p_settings, _p_fimages,
        ],
        "מערכת": [
            st.Page(
                "pages/2_recipes.py",
                title="מתכונים",
                icon="📖",
            ),
            st.Page(
                "pages/7_weekly_workout_plan.py",
                title="אימונים",
                icon="🏃",
            ),
        ],
    }
)

pg.run()
