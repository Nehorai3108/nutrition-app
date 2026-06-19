#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
14_settings.py — הגדרות משתמש · מצב שקט (Calm Mode)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, bottom_nav, theme_toggle
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth, logout_button
from nutrition_app.models.user_meal_preferences import UserMealPreferences
from nutrition_app.repositories.user_meal_preferences_repository import UserMealPreferencesRepository

st.set_page_config(
    page_title="NutriSmart · הגדרות",
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

# ── Appearance section ────────────────────────────────────────────────────────

st.markdown(
    '<h3 style="margin-bottom:2px">מראה</h3>'
    '<p style="color:#8892a4;font-size:0.88rem;margin-top:0">בחר בין מצב בהיר לכהה</p>',
    unsafe_allow_html=True,
)
theme_toggle()
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

# ── New Calm Mode toggles (additive, off by default) ──────────────────────────
new_daily_reminders = st.toggle(
    "תזכורות יומיות",
    value=_prefs.daily_reminders_enabled,
    help="הפעל תזכורות יומיות (לדוגמה לרישום ארוחות). כבוי כברירת מחדל.",
)
if new_daily_reminders != _prefs.daily_reminders_enabled:
    _prefs.daily_reminders_enabled = new_daily_reminders
    _changed = True

new_weekly_email = st.toggle(
    "סיכום שבועי באימייל",
    value=_prefs.weekly_summary_email,
    help="קבל סיכום שבועי באימייל. כבוי כברירת מחדל.",
)
if new_weekly_email != _prefs.weekly_summary_email:
    _prefs.weekly_summary_email = new_weekly_email
    _changed = True

if _changed:
    _repo.save(_prefs)
    st.toast("נשמר ✓")

# ── GLP-1 medication section (feature-flagged) ────────────────────────────────
# Hidden when FF_GLP1_AWARE_TARGETS is OFF. The boolean is persisted whether
# the flag is ON or OFF so toggling the flag later does not lose data.
import json as _json_glp1
from nutrition_app import feature_flags as _ff_glp1
from nutrition_app.repositories.profile_repository import ProfileRepository as _ProfileRepo_GLP1

if getattr(_ff_glp1, "FF_GLP1_AWARE_TARGETS", False):
    st.divider()
    try:
        with open(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config", "strings_he.json",
            ),
            "r",
            encoding="utf-8",
        ) as _f_strs:
            _strings_he = _json_glp1.load(_f_strs)
    except (OSError, ValueError):
        _strings_he = {}

    _q       = _strings_he.get("glp1.question",
                               "האם אתה משתמש בתרופת GLP-1 (אוזמפיק / ויגובי / מונג׳ארו)?")
    _opt_yes = _strings_he.get("glp1.option.yes", "כן")
    _opt_no  = _strings_he.get("glp1.option.no", "לא")
    _opt_na  = _strings_he.get("glp1.option.prefer_not_to_say", "מעדיף לא לענות")

    _profile_repo_glp1 = _ProfileRepo_GLP1()
    _profile_glp1      = _profile_repo_glp1.load(USER_ID)
    _cur_glp1          = _profile_glp1.get("glp1_medication_in_use")

    _label_to_val = {_opt_yes: True, _opt_no: False, _opt_na: None}
    _val_to_label = {True: _opt_yes, False: _opt_no, None: _opt_na}
    _opts         = [_opt_yes, _opt_no, _opt_na]
    _picked = st.radio(
        _q,
        options=_opts,
        index=_opts.index(_val_to_label.get(_cur_glp1, _opt_na)),
        horizontal=True,
        key="glp1_tri_state_settings",
    )
    _new_glp1 = _label_to_val[_picked]

    _card_seen = bool(_profile_glp1.get("glp1_card_seen", False))
    if _new_glp1 is True and not _card_seen:
        _card_title = _strings_he.get(
            "glp1.educational_card.title",
            "שמירה על מסת שריר חשובה במיוחד בתקופת GLP-1",
        )
        _card_disclaimer = _strings_he.get(
            "glp1.educational_card.disclaimer",
            "איננו תחליף לייעוץ רפואי. דבר עם הרופא או התזונאי שלך.",
        )
        st.markdown(
            f'<div dir="rtl" style="background:#1e2433;border:1px solid #f59e0b;'
            f'border-radius:14px;padding:14px 16px;margin-top:10px">'
            f'<div style="font-size:0.95rem;font-weight:700;color:#f4f6fb;margin-bottom:6px">'
            f'{_card_title}</div>'
            f'<div style="font-size:0.78rem;color:#8892a4;line-height:1.5">'
            f'{_card_disclaimer}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if _new_glp1 != _cur_glp1 or (_new_glp1 is True and not _card_seen):
        _profile_glp1["glp1_medication_in_use"] = _new_glp1
        if _new_glp1 is True:
            _profile_glp1["glp1_card_seen"] = True
        _profile_repo_glp1.save(_profile_glp1)
        st.toast("נשמר ✓")

# ── Bottom nav ────────────────────────────────────────────────────────────────

bottom_nav(active="settings")
