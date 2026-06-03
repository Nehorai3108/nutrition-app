#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
16_hydration.py — מעקב שתייה יומי
"""

import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from ui.components import inject_global_css, page_header, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth, logout_button
from nutrition_app.repositories.water_repository import WaterRepository
from nutrition_app.repositories.profile_repository import ProfileRepository
from nutrition_app.agents.agent_2_nutrition.nutrition_engine import calculate_hydration_goal
import ui.theme as t

setup_persistent_auth()
USER_ID = require_auth()

st.set_page_config(
    page_title="BiteFit · שתייה",
    page_icon="💧",
    layout="centered",
    initial_sidebar_state="collapsed",
)
inject_global_css()

with st.sidebar:
    st.markdown(
        f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">'
        f'👤 {st.session_state.get("bitefit_user", {}).get("email", "")}'
        f"</div>",
        unsafe_allow_html=True,
    )
    logout_button()

# ── Repositories ──────────────────────────────────────────────────────────────
water_repo   = WaterRepository()
profile_repo = ProfileRepository()

# ── Page header ───────────────────────────────────────────────────────────────
page_header("שתייה", icon_name="water", subtitle="מעקב צריכת נוזלים יומית")

# ── Date picker ───────────────────────────────────────────────────────────────
today = date.today()
selected_date = st.date_input(
    "תאריך",
    value=today,
    max_value=today,
    label_visibility="collapsed",
)
date_str = selected_date.isoformat()
is_today  = selected_date == today

# ── Load data ─────────────────────────────────────────────────────────────────
water_data = water_repo.get_water_data(USER_ID)
goal_ml    = water_data.goal.daily_goal_ml if water_data.goal else 2000.0
total_ml   = water_data.get_daily_total(date_str)
intakes    = water_data.get_intakes_for_date(date_str)

# ── SVG progress ring ─────────────────────────────────────────────────────────
def _water_ring_html(consumed_ml: float, goal_ml: float) -> str:
    import math
    pct = min(consumed_ml / max(goal_ml, 1), 1.0)
    remaining = max(goal_ml - consumed_ml, 0)
    r, cx, cy = 54, 70, 70
    circumference = 2 * math.pi * r
    filled = circumference * pct
    gap    = circumference - filled
    color  = "#4f8ef7" if pct < 0.85 else ("#00d4aa" if pct < 1.0 else "#2dd4bf")

    consumed_l = consumed_ml / 1000
    remain_l   = remaining   / 1000
    goal_l     = goal_ml     / 1000

    return f"""
    <div style="display:flex;align-items:center;gap:24px;padding:16px 0">
      <div style="position:relative;width:140px;height:140px;flex-shrink:0">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle cx="{cx}" cy="{cy}" r="{r}"
            fill="none" stroke="{t.SURFACE_3}" stroke-width="12"/>
          <circle cx="{cx}" cy="{cy}" r="{r}"
            fill="none" stroke="{color}" stroke-width="12"
            stroke-dasharray="{filled:.1f} {gap:.1f}"
            stroke-dashoffset="{circumference * 0.25:.1f}"
            stroke-linecap="round"/>
        </svg>
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;text-align:center">
          <div style="font-size:1.4rem;font-weight:800;color:{t.TEXT};line-height:1">
            {consumed_l:.1f}L
          </div>
          <div style="font-size:0.7rem;color:{t.TEXT_MUTED};margin-top:2px">נשתה</div>
          <div style="font-size:0.65rem;color:{color};margin-top:4px;font-weight:600">
            {remain_l:.1f}L נותרו
          </div>
        </div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:0.8rem;color:{t.TEXT_MUTED}">יעד יומי</span>
          <span style="font-size:0.9rem;font-weight:700;color:{t.TEXT}">{goal_l:.1f}L</span>
        </div>
        <div style="height:1px;background:{t.BORDER}"></div>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:0.8rem;color:{t.TEXT_MUTED}">מנות</span>
          <span style="font-size:0.9rem;font-weight:700;color:{t.TEXT}">{len(intakes)}</span>
        </div>
        <div style="height:1px;background:{t.BORDER}"></div>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:0.8rem;color:{t.TEXT_MUTED}">השלמה</span>
          <span style="font-size:0.9rem;font-weight:700;color:{color}">{pct*100:.0f}%</span>
        </div>
      </div>
    </div>
    """

st.markdown(_water_ring_html(total_ml, goal_ml), unsafe_allow_html=True)

# ── Quick-add buttons (today only) ───────────────────────────────────────────
if is_today:
    st.markdown(
        f'<div style="font-size:0.85rem;font-weight:600;color:{t.TEXT_MUTED};margin-bottom:8px">'
        "הוסף שתייה</div>",
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)

    def _add(ml: float) -> None:
        water_repo.add_water_intake(USER_ID, ml)
        st.rerun()

    with col1:
        if st.button("כוס\n200 מ״ל", use_container_width=True):
            _add(200)
    with col2:
        if st.button("בקבוק\n350 מ״ל", use_container_width=True):
            _add(350)
    with col3:
        if st.button("בקבוק\n500 מ״ל", use_container_width=True):
            _add(500)
    with col4:
        custom_ml = st.number_input(
            "כמות (מ״ל)",
            min_value=50,
            max_value=2000,
            value=250,
            step=50,
            label_visibility="collapsed",
        )
        if st.button("➕ הוסף", use_container_width=True):
            _add(float(custom_ml))

    st.divider()

# ── Today's log ───────────────────────────────────────────────────────────────
if intakes:
    st.markdown(
        f'<div style="font-size:0.85rem;font-weight:600;color:{t.TEXT_MUTED};margin-bottom:8px">'
        f"יומן שתייה — {selected_date.strftime('%d/%m/%Y')}</div>",
        unsafe_allow_html=True,
    )
    for entry in sorted(intakes, key=lambda x: x.timestamp, reverse=True):
        time_str = entry.timestamp[11:16]  # HH:MM
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(
                f'<div style="padding:8px 0;border-bottom:1px solid {t.BORDER};color:{t.TEXT}">'
                f'<span style="color:{t.TEXT_MUTED};font-size:0.75rem">{time_str}</span>'
                f'&nbsp;&nbsp;<strong>{entry.amount_ml:.0f} מ״ל</strong>'
                f"</div>",
                unsafe_allow_html=True,
            )
        with c2:
            if is_today and st.button("🗑", key=f"del_{entry.water_id}"):
                water_repo.remove_water_intake(USER_ID, entry.water_id, date_str)
                st.rerun()
else:
    st.info("אין רישומי שתייה ליום זה.")

# ── Goal settings ─────────────────────────────────────────────────────────────
with st.expander("⚙️ הגדרת יעד יומי"):
    _profile = profile_repo.load(USER_ID)
    _weight = float(_profile.get("weight_kg", 0) or 0)
    suggested = calculate_hydration_goal(_weight)
    st.caption(f"יעד מומלץ לפי משקל גוף: {suggested/1000:.1f}L ({suggested:.0f} מ״ל)")
    new_goal = st.number_input(
        "יעד יומי (מ״ל)",
        min_value=500,
        max_value=6000,
        value=int(goal_ml),
        step=100,
    )
    if st.button("שמור יעד"):
        water_repo.save_water_goal(USER_ID, float(new_goal))
        st.success(f"יעד עודכן: {new_goal/1000:.1f}L")
        st.rerun()

# ── Bottom nav ────────────────────────────────────────────────────────────────
bottom_nav("water")
