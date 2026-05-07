#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף מעקב אימונים — עיצוב מודרני
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
import streamlit as st

from ui.components import inject_global_css, bottom_nav
from ui.user_auth import require_auth, logout_button
from nutrition_app.models.enums import WorkoutType, WorkoutIntensity
from nutrition_app.models.workout import WorkoutEntry
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.agents.agent_2_nutrition.workout_adjuster import estimate_calories_burned
from nutrition_app.repositories.profile_repository import ProfileRepository

st.set_page_config(page_title="אימונים", page_icon=None, layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

with st.sidebar:
    st.markdown(f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">👤 {st.session_state.get("bitefit_user", {}).get("email", "")}</div>', unsafe_allow_html=True)
    logout_button()

USER_ID = require_auth()
_repo = WorkoutRepository()

# Load user weight for calorie estimation
_prof = ProfileRepository().load(USER_ID)
_weight = float(_prof.get("weight_kg", 80))

today = date.today()

# ── Workout type catalogue ────────────────────────────────────────────────────
TYPES = [
    (WorkoutType.STRENGTH, "כוח",     "#f87171"),
    (WorkoutType.RUNNING,  "ריצה",    "#4ade80"),
    (WorkoutType.CYCLING,  "אופניים", "#f59e0b"),
    (WorkoutType.SWIMMING, "שחייה",   "#38bdf8"),
]

INTENSITY_CONFIG = [
    (WorkoutIntensity.LOW,      "קל",     "#4ade80"),
    (WorkoutIntensity.MODERATE, "בינוני", "#f59e0b"),
    (WorkoutIntensity.HIGH,     "גבוה",   "#f87171"),
    (WorkoutIntensity.EXTREME,  "קיצוני", "#a855f7"),
]

WORKOUT_LABEL = {wt: lbl   for wt, lbl, _   in TYPES}
WORKOUT_COLOR = {wt: color for wt, _,   color in TYPES}


# ── Load today's workouts ──────────────────────────────────────────────────────
workout_data    = _repo.get_workout_data(USER_ID)
today_workouts  = workout_data.daily_log.get(today.isoformat(), [])
total_duration  = sum(w.duration_minutes for w in today_workouts)
total_burned    = sum(
    w.estimated_calories_burned if w.estimated_calories_burned > 0
    else estimate_calories_burned(w, _weight)
    for w in today_workouts
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;padding:4px 2px 16px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb">אימונים</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{today.strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Today stats strip ──────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;gap:8px;margin-bottom:20px">'
    f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:16px;'
    f'padding:14px 10px;text-align:center">'
    f'<div dir="rtl" style="font-size:1.5rem;font-weight:900;color:#4f8ef7">{len(today_workouts)}</div>'
    f'<div dir="rtl" style="font-size:0.65rem;color:#545e70;margin-top:3px">אימונים</div></div>'
    f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:16px;'
    f'padding:14px 10px;text-align:center">'
    f'<div dir="rtl" style="font-size:1.5rem;font-weight:900;color:#f59e0b">{total_duration}</div>'
    f'<div dir="rtl" style="font-size:0.65rem;color:#545e70;margin-top:3px">דקות</div></div>'
    f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:16px;'
    f'padding:14px 10px;text-align:center">'
    f'<div dir="rtl" style="font-size:1.5rem;font-weight:900;color:#f472b6">{int(total_burned)}</div>'
    f'<div dir="rtl" style="font-size:0.65rem;color:#545e70;margin-top:3px">קק״ל</div></div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Today's logged workouts ────────────────────────────────────────────────────
if today_workouts:
    st.markdown(
        '<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb;margin-bottom:10px">אימוני היום</div>',
        unsafe_allow_html=True,
    )
    for i, w in enumerate(reversed(today_workouts)):
        real_i   = len(today_workouts) - 1 - i
        label    = WORKOUT_LABEL.get(w.workout_type, "אימון") if w.workout_type else "אימון"
        w_color  = WORKOUT_COLOR.get(w.workout_type, "#545e70") if w.workout_type else "#545e70"
        kcal     = int(w.estimated_calories_burned if w.estimated_calories_burned > 0
                       else estimate_calories_burned(w, _weight))
        int_lbl, int_color = next(
            ((lbl, clr) for iv, lbl, clr in INTENSITY_CONFIG if iv == w.intensity),
            ("—", "#545e70")
        )

        st.markdown(
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:16px;'
            f'padding:14px 16px;margin-bottom:4px;display:flex;align-items:center;gap:14px">'
            f'<div dir="rtl" style="width:4px;height:44px;border-radius:99px;background:{w_color};flex-shrink:0"></div>'
            f'<div dir="rtl" style="flex:1">'
            f'<div dir="rtl" style="font-size:0.92rem;font-weight:700;color:#f4f6fb">{label}</div>'
            f'<div dir="rtl" style="font-size:0.72rem;color:#8892a4;margin-top:3px">'
            f'{w.duration_minutes} דק׳ &nbsp;·&nbsp; '
            f'<span style="color:{w_color};font-weight:600">{kcal} קק״ל</span> &nbsp;·&nbsp; '
            f'<span style="color:{int_color}">{int_lbl}</span>'
            + (f' &nbsp;·&nbsp; {w.distance_km} ק״מ' if w.distance_km else '')
            + f'</div></div></div>',
            unsafe_allow_html=True,
        )
        with st.expander("ערוך / מחק"):
            with st.form(f"edit_wo_form_{real_i}", clear_on_submit=True):
                e_type = st.selectbox("סוג", options=[wt for wt, _, _ in TYPES],
                                      format_func=lambda wt: WORKOUT_LABEL.get(wt, wt.value),
                                      index=next((j for j,(wt,_,_) in enumerate(TYPES) if wt==w.workout_type), 0))
                ec1, ec2 = st.columns(2)
                e_dur = ec1.number_input("דקות", min_value=1, max_value=300,
                                          value=w.duration_minutes, step=5)
                e_int = ec2.selectbox("עצימות",
                                       options=[iv for iv,_,_ in INTENSITY_CONFIG],
                                       format_func=lambda iv: next(l for v,l,_ in INTENSITY_CONFIG if v==iv),
                                       index=next((j for j,(iv,_,_) in enumerate(INTENSITY_CONFIG) if iv==w.intensity), 1))
                ef1, ef2 = st.columns(2)
                if ef1.form_submit_button("שמור", type="primary", use_container_width=True):
                    _repo.remove_daily_workout(USER_ID, today, real_i)
                    new_entry = WorkoutEntry(duration_minutes=int(e_dur), mode="type",
                                             workout_type=e_type, intensity=e_int)
                    new_entry.estimated_calories_burned = estimate_calories_burned(new_entry, _weight)
                    _repo.add_daily_workout(USER_ID, today, new_entry)
                    st.rerun()
                if ef2.form_submit_button("מחק", use_container_width=True):
                    _repo.remove_daily_workout(USER_ID, today, real_i)
                    st.rerun()

    st.markdown('<div dir="rtl" style="height:8px"></div>', unsafe_allow_html=True)

# ── Add workout ────────────────────────────────────────────────────────────────
st.markdown(
    '<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb;margin-bottom:12px">הוסף אימון</div>',
    unsafe_allow_html=True,
)

# ── Add workout form ───────────────────────────────────────────────────────────
with st.form("add_workout_form", clear_on_submit=True):
    # TYPES = (WorkoutType, label, color)
    sel_type = st.selectbox(
        "סוג אימון",
        options=[wt for wt, _, _ in TYPES],
        format_func=lambda wt: WORKOUT_LABEL.get(wt, wt.value),
    )

    col_dur, col_int = st.columns(2)
    duration = col_dur.number_input("משך (דקות)", min_value=1, max_value=300, value=45, step=5)
    intensity = col_int.selectbox(
        "עצימות",
        options=[i for i, _, _ in INTENSITY_CONFIG],
        format_func=lambda i: next(lbl for iv, lbl, _ in INTENSITY_CONFIG if iv == i),
        index=1,
    )

    DISTANCE_TYPES = {WorkoutType.RUNNING, WorkoutType.WALKING, WorkoutType.HIKING, WorkoutType.CYCLING}
    distance = st.number_input("מרחק (ק״מ) — אופציונלי", min_value=0.0, max_value=200.0,
                                value=0.0, step=0.5)

    if st.form_submit_button("שמור אימון", type="primary", use_container_width=True):
        entry = WorkoutEntry(
            duration_minutes=int(duration),
            mode="type",
            workout_type=sel_type,
            intensity=intensity,
            distance_km=float(distance) if distance > 0 else None,
        )
        entry.estimated_calories_burned = estimate_calories_burned(entry, _weight)
        _repo.add_daily_workout(USER_ID, today, entry)
        st.rerun()

# ── Weekly history ─────────────────────────────────────────────────────────────
st.markdown(
    '<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb;margin:20px 0 12px">7 ימים אחרונים</div>',
    unsafe_allow_html=True,
)

HEB_WD = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}
any_history = False
for delta in range(1, 8):
    d = today - timedelta(days=delta)
    day_workouts = workout_data.daily_log.get(d.isoformat(), [])
    if not day_workouts:
        continue
    any_history = True
    day_dur  = sum(w.duration_minutes for w in day_workouts)
    day_kcal = int(sum(
        w.estimated_calories_burned if w.estimated_calories_burned > 0
        else estimate_calories_burned(w, _weight)
        for w in day_workouts
    ))
    day_label = f"{HEB_WD.get(d.weekday(),'')} {d.strftime('%d/%m')}"

    with st.expander(f"{day_label}  ·  {day_dur} דק׳  ·  {day_kcal} קק״ל"):
        for w in day_workouts:
            label   = WORKOUT_LABEL.get(w.workout_type, "אימון") if w.workout_type else "אימון"
            w_color = WORKOUT_COLOR.get(w.workout_type, "#545e70") if w.workout_type else "#545e70"
            kcal    = int(w.estimated_calories_burned if w.estimated_calories_burned > 0
                          else estimate_calories_burned(w, _weight))
            st.markdown(
                f'<div dir="rtl" style="display:flex;align-items:center;gap:10px;padding:8px 0;'
                f'border-bottom:1px solid #1e2433">'
                f'<div dir="rtl" style="width:3px;height:28px;border-radius:99px;background:{w_color}"></div>'
                f'<span style="font-size:0.84rem;color:#f4f6fb;font-weight:600">{label}</span>'
                f'<span style="font-size:0.72rem;color:#545e70;margin-right:auto">'
                f'{w.duration_minutes} דק׳ · <span style="color:{w_color}">{kcal} קק״ל</span></span>'
                f'</div>',
                unsafe_allow_html=True,
            )

if not any_history:
    st.markdown(
        '<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:16px;'
        'padding:20px;text-align:center;color:#545e70;font-size:0.82rem">'
        'אין היסטוריה עדיין — התחל לתעד!</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("workout")
