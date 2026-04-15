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
from ui.auth import require_admin
from ui.components import inject_global_css, admin_sidebar_menu

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
# This runs on every page load, so unauthorized users never see any content
require_admin(page_title="ניהול המערכת", icon_name="shield")

# ── Main app initialization ──────────────────────────────────────────────────

# Hide Streamlit's auto-discovered pages and render custom menu instead
st.markdown(
    '<style>'
    'section[data-testid="stSidebar"] ul {display:none;}'
    '</style>',
    unsafe_allow_html=True,
)

# Render custom admin sidebar menu
with st.sidebar:
    admin_sidebar_menu(context="admin")

st.title("🛡️ דאשבורד ניהול")
st.markdown("""
ברוכים הבאים לדאשבורד הניהול. בחר דף מהתפריט בצד שמאל:

- **סוכנים** — ניטור משימות וסטטוס מערכת
- **ניהול תמונות** — העלאה וניהול תמונות מתכונים
- **ביקורת לוג** — צפייה בדוחות וביומני ביקורת
- **הגדרות** — הגדרות יישום וניהול מערכת
""")
