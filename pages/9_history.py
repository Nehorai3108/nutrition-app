#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""9_history.py — היסטוריה יומית מסוכמת"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
import streamlit as st

from ui.components import inject_global_css, bottom_nav
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.repositories.water_repository import WaterRepository
from nutrition_app.repositories.food_log_repository import FoodLogRepository

st.set_page_config(page_title="היסטוריה", page_icon=None, layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

USER_ID      = "ui_user_001"
workout_repo = WorkoutRepository()
water_repo   = WaterRepository()
food_repo    = FoodLogRepository()
today        = date.today()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;padding:4px 2px 16px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb">היסטוריה</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{today.strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Range ──────────────────────────────────────────────────────────────────────
days_back = st.radio("", ["7 ימים", "14 ימים", "30 ימים"],
                     horizontal=True, index=0, label_visibility="collapsed")
days_back = {"7 ימים": 7, "14 ימים": 14, "30 ימים": 30}[days_back]

# ── Period averages ────────────────────────────────────────────────────────────
workout_data = workout_repo.get_workout_data(USER_ID)
tot_cal = tot_water = tot_wo = 0
for delta in range(days_back):
    d = today - timedelta(days=delta)
    tot_cal   += food_repo.get_totals(USER_ID, d)["calories"]
    tot_water += sum(w.amount_ml for w in water_repo.get_water_intakes_for_date(USER_ID, d))
    tot_wo    += len(workout_data.daily_log.get(d.isoformat(), []))

st.markdown(
    f'<div dir="rtl" style="display:flex;gap:8px;margin-bottom:20px">'
    f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
    f'<div dir="rtl" style="font-size:1.2rem;font-weight:900;color:#4f8ef7">{int(tot_cal/days_back)}</div>'
    f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">קק״ל ממוצע</div></div>'
    f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
    f'<div dir="rtl" style="font-size:1.2rem;font-weight:900;color:#38bdf8">{round(tot_water/days_back/1000,1)}L</div>'
    f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">מים ממוצע</div></div>'
    f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
    f'<div dir="rtl" style="font-size:1.2rem;font-weight:900;color:#f59e0b">{tot_wo}</div>'
    f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">אימונים</div></div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Day rows ───────────────────────────────────────────────────────────────────
HEB_WD = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}

for delta in range(days_back):
    d   = today - timedelta(days=delta)
    cal = int(food_repo.get_totals(USER_ID, d)["calories"])
    wtr = int(sum(w.amount_ml for w in water_repo.get_water_intakes_for_date(USER_ID, d)))
    wos = len(workout_data.daily_log.get(d.isoformat(), []))

    if cal == 0 and wtr == 0 and wos == 0:
        continue

    label      = "היום" if delta == 0 else f"{HEB_WD.get(d.weekday(),'')} {d.strftime('%d/%m')}"
    cal_color  = "#4f8ef7" if cal > 0 else "#545e70"
    wtr_color  = "#38bdf8" if wtr > 0 else "#545e70"
    wo_color   = "#f59e0b" if wos > 0 else "#545e70"

    st.markdown(
        f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:16px;'
        f'padding:14px 16px;margin-bottom:8px;display:flex;align-items:center;gap:0">'
        f'<div dir="rtl" style="font-size:0.84rem;font-weight:700;color:#f4f6fb;min-width:80px">{label}</div>'
        f'<div dir="rtl" style="flex:1;display:flex;gap:16px;justify-content:flex-end">'
        f'<div dir="rtl" style="text-align:center">'
        f'<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:{cal_color}">{cal}</div>'
        f'<div dir="rtl" style="font-size:0.58rem;color:#545e70">קק״ל</div></div>'
        f'<div dir="rtl" style="text-align:center">'
        f'<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:{wtr_color}">{wtr}</div>'
        f'<div dir="rtl" style="font-size:0.58rem;color:#545e70">מ״ל</div></div>'
        f'<div dir="rtl" style="text-align:center">'
        f'<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:{wo_color}">{wos}</div>'
        f'<div dir="rtl" style="font-size:0.58rem;color:#545e70">אימונים</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("history")
