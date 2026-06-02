#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
14_settings.py — הגדרות משתמש · מצב שקט (Calm Mode)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth, logout_button
from nutrition_app.models.user_meal_preferences import UserMealPreferences
from nutrition_app.repositories.user_meal_preferences_repository import UserMealPreferencesRepository

st.set_page_config(
    page_title="BiteFit · הגדרות",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()

with st.sidebar:
    st.markdown(
        f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">👤 {st.session_state.get("user_email", "")}</div>',
        unsafe_allow_html=True,
    )
    logout_button()

setup_persistent_auth()
USER_ID = require_auth()

_repo = UserMealPreferencesRepository()
_prefs = _repo.load(USER_ID) or UserMealPreferences.empty(USER_ID)

# ── Page header ───────────────────────────────────────────────────────────────

st.markdown(
    '<h2 style="margin-bottom:2px">⚙️ הגדרות</h2>',
    unsafe_allow_html=True,
)
st.divider()

# ── Calm Mode section ─────────────────────────────────────────────────────────

st.markdown(
    '<h3 style="margin-bottom:2px">מצב שקט</h3>'
    '<p style="color:#8892a4;font-size:0.88rem;margin-top:0">כל ההגדרות כבויות כברירת מחדל — אין חובה להפעיל</p>',
    unsafe_allow_html=True,
)

_changed = False

new_show_streaks = st.toggle(
    "הצג סטריקים",
    value=_prefs.show_streaks,
    help="הצג מונה רצף ימי בדף הבית",
)
if new_show_streaks != _prefs.show_streaks:
    _prefs.show_streaks = new_show_streaks
    _changed = True

new_daily = st.toggle(
    "התראות יומיות",
    value=_prefs.daily_notifications,
    help="קבל תזכורות יומיות לרישום ארוחות",
)
if new_daily != _prefs.daily_notifications:
    _prefs.daily_notifications = new_daily
    _changed = True

new_weekly = st.toggle(
    "סיכום שבועי",
    value=_prefs.weekly_summary,
    help="קבל סיכום שבועי אוטומטי של התזונה שלך",
)
if new_weekly != _prefs.weekly_summary:
    _prefs.weekly_summary = new_weekly
    _changed = True

if _changed:
    _repo.save(_prefs)
    st.toast("נשמר ✓")

# ── Bottom nav ────────────────────────────────────────────────────────────────

bottom_nav(active="settings")
