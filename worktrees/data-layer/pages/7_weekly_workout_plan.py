#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
תכנית אימונים שבועית — ברירת מחדל שלפיה יותאם התפריט בכל יום בשבוע.
תומך במספר אימונים ליום.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from nutrition_app.models.enums import WorkoutIntensity, WorkoutType
from nutrition_app.models.workout import WeeklyWorkoutPlan, WorkoutEntry
from nutrition_app.repositories.workout_repository import WorkoutRepository

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu, icon_button,
)
from chatbot.sidebar_widget import render_chatbot_sidebar

st.set_page_config(page_title="BiteFit · אימונים", page_icon="🏋️", layout="wide", initial_sidebar_state="collapsed")

inject_global_css()

with st.sidebar:
    render_chatbot_sidebar()
nav_menu(active="אימונים")
page_header(
    "תכנית אימונים שבועית",
    icon_name="training",
    subtitle="הגדר פעם אחת — התפריט יותאם אוטומטית לכל יום. ניתן להוסיף מספר אימונים ליום. לוג יומי בדף הראשי עוקף את התכנית.",
)

USER_ID = "ui_user_001"  # Matches app_ui.py

WEEKDAYS_HE = [
    ("monday",    "יום שני"),
    ("tuesday",   "יום שלישי"),
    ("wednesday", "יום רביעי"),
    ("thursday",  "יום חמישי"),
    ("friday",    "יום שישי"),
    ("saturday",  "יום שבת"),
    ("sunday",    "יום ראשון"),
]

INTENSITY_OPTIONS = {
    WorkoutIntensity.LOW:      "נמוכה",
    WorkoutIntensity.MODERATE: "בינונית",
    WorkoutIntensity.HIGH:     "גבוהה",
    WorkoutIntensity.EXTREME:  "עצימה מאוד",
}
TYPE_OPTIONS = {
    # Cardio
    WorkoutType.RUNNING:        "🏃 ריצה",
    WorkoutType.WALKING:        "🚶 הליכה",
    WorkoutType.HIKING:         "🥾 טיול/הייקינג",
    WorkoutType.CYCLING:        "🚴 אופניים",
    WorkoutType.SWIMMING:       "🏊 שחייה",
    WorkoutType.ROWING:         "🚣 חתירה",
    WorkoutType.ELLIPTICAL:     "⚙️ אליפטיקל",
    WorkoutType.STAIR_CLIMBING: "🪜 מדרגות",
    WorkoutType.JUMPING_ROPE:   "🪢 קפיצה בחבל",
    # Strength / studio
    WorkoutType.STRENGTH:       "🏋️ משקולות",
    WorkoutType.CROSSFIT:       "💪 קרוספיט",
    WorkoutType.HIIT:           "🔥 HIIT",
    WorkoutType.PILATES:        "🧘 פילאטיס",
    WorkoutType.YOGA:           "🧘 יוגה",
    WorkoutType.DANCE:          "💃 ריקוד",
    # Combat
    WorkoutType.BOXING:         "🥊 איגרוף",
    WorkoutType.KICKBOXING:     "🥋 קיקבוקסינג",
    WorkoutType.MARTIAL_ARTS:   "🥋 אומנויות לחימה",
    WorkoutType.WRESTLING:      "🤼 היאבקות",
    # Ball sports
    WorkoutType.SOCCER:         "⚽ כדורגל",
    WorkoutType.BASKETBALL:     "🏀 כדורסל",
    WorkoutType.TENNIS:         "🎾 טניס",
    WorkoutType.TABLE_TENNIS:   "🏓 טניס שולחן",
    WorkoutType.BADMINTON:      "🏸 בדמינטון",
    WorkoutType.VOLLEYBALL:     "🏐 כדורעף",
    WorkoutType.BASEBALL:       "⚾ בייסבול",
    WorkoutType.HANDBALL:       "🤾 כדוריד",
    WorkoutType.RUGBY:          "🏉 רוגבי",
    WorkoutType.HOCKEY:         "🏒 הוקי",
    WorkoutType.GOLF:           "⛳ גולף",
    # Outdoor
    WorkoutType.CLIMBING:       "🧗 טיפוס",
    WorkoutType.SKIING:         "⛷️ סקי",
    WorkoutType.SNOWBOARDING:   "🏂 סנובורד",
    WorkoutType.SURFING:        "🏄 גלישה",
    WorkoutType.SKATING:        "⛸️ החלקה",
    WorkoutType.OTHER:          "אחר",
}
DISTANCE_TYPES = {WorkoutType.RUNNING, WorkoutType.WALKING, WorkoutType.HIKING}

repo = WorkoutRepository()

# Load current plan into session_state on first render so edits are incremental
if "weekly_edit" not in st.session_state:
    existing = repo.get_workout_data(USER_ID)
    st.session_state.weekly_edit = {
        day: list(existing.weekly_plan.workouts_by_day.get(day, []))
        if existing.weekly_plan else []
        for day, _ in WEEKDAYS_HE
    }


def _format_entry(e: WorkoutEntry) -> str:
    if e.mode == "intensity" and e.intensity:
        return f"עצימות {INTENSITY_OPTIONS[e.intensity]} · {e.duration_minutes} דק׳"
    if e.mode == "type" and e.workout_type:
        label = TYPE_OPTIONS.get(e.workout_type, e.workout_type.value)
        if e.intensity:
            label += f" · עצימות {INTENSITY_OPTIONS[e.intensity]}"
        metric = f"{e.distance_km} ק\"מ" if e.distance_km else f"{e.duration_minutes} דק׳"
        return f"{label} · {metric}"
    return f"אימון · {e.duration_minutes} דק׳"


for day_key, day_label in WEEKDAYS_HE:
    section_header(day_label, "training")
    entries = st.session_state.weekly_edit[day_key]

    if entries:
        for i, e in enumerate(entries):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"• {_format_entry(e)}")
            with c2:
                if icon_button("מחק", "delete", key=f"del_{day_key}_{i}",
                               type="secondary", help="הסר אימון"):
                    entries.pop(i)
                    st.rerun()
    else:
        st.caption("מנוחה (אין אימונים מתוכננים)")

    with st.expander("➕ הוסף אימון", expanded=False):
        mode = st.radio(
            "סוג הזנה",
            options=["intensity", "type"],
            format_func=lambda m: {"intensity": "לפי עצימות",
                                     "type": "לפי סוג אימון"}[m],
            key=f"addmode_{day_key}",
            horizontal=True,
        )

        new_entry: WorkoutEntry | None = None
        if mode == "intensity":
            cc1, cc2 = st.columns(2)
            with cc1:
                intensity = st.selectbox(
                    "עצימות",
                    options=list(INTENSITY_OPTIONS.keys()),
                    format_func=lambda x: INTENSITY_OPTIONS[x],
                    key=f"int_{day_key}",
                )
            with cc2:
                duration = st.number_input(
                    "משך (דק׳)",
                    min_value=0, max_value=300, value=30, step=5,
                    key=f"dur_int_{day_key}",
                )
            if duration > 0:
                new_entry = WorkoutEntry(
                    duration_minutes=int(duration),
                    mode="intensity",
                    intensity=intensity,
                )
        else:
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                wtype = st.selectbox(
                    "סוג",
                    options=list(TYPE_OPTIONS.keys()),
                    format_func=lambda x: TYPE_OPTIONS[x],
                    key=f"type_{day_key}",
                )
            with cc2:
                duration = st.number_input(
                    "משך (דק׳)",
                    min_value=0, max_value=300, value=30, step=5,
                    key=f"dur_type_{day_key}",
                )
            with cc3:
                t_int = st.selectbox(
                    "עצימות",
                    options=["none"] + list(INTENSITY_OPTIONS.keys()),
                    format_func=lambda x: "רגילה" if x == "none" else INTENSITY_OPTIONS[x],
                    key=f"tint_{day_key}",
                )

            # Distance input (only for run/walk/hike) on a separate row
            distance = 0.0
            if wtype in DISTANCE_TYPES:
                distance = st.number_input(
                    "מרחק (ק\"מ) — אם מוזן, מחליף משך",
                    min_value=0.0, max_value=200.0, value=0.0, step=0.5,
                    key=f"dist_{day_key}",
                )

            if duration > 0 or distance > 0:
                new_entry = WorkoutEntry(
                    duration_minutes=int(duration),
                    mode="type",
                    workout_type=wtype,
                    intensity=None if t_int == "none" else t_int,
                    distance_km=float(distance) if distance > 0 else None,
                )

        if icon_button("הוסף", "add", key=f"add_{day_key}"):
            if new_entry is None:
                st.warning("יש להזין משך או מרחק גדול מ-0.")
            else:
                entries.append(new_entry)
                st.rerun()

    st.divider()

col_save, col_clear, _ = st.columns([1, 1, 2])
with col_save:
    if icon_button("שמור תכנית שבועית", "save",
                   key="save_weekly_plan_btn", type="primary"):
        plan = WeeklyWorkoutPlan(
            user_id=USER_ID,
            workouts_by_day={
                day: list(entries)
                for day, entries in st.session_state.weekly_edit.items()
                if entries
            },
        )
        repo.save_weekly_plan(USER_ID, plan)
        total = sum(len(v) for v in st.session_state.weekly_edit.values())
        st.success(f"התכנית נשמרה ({total} אימונים בסך הכל).")
with col_clear:
    if icon_button("נקה תכנית", "clear", key="clear_weekly_plan_btn"):
        st.session_state.weekly_edit = {day: [] for day, _ in WEEKDAYS_HE}
        repo.save_weekly_plan(USER_ID, WeeklyWorkoutPlan(user_id=USER_ID, workouts_by_day={}))
        st.success("התכנית נוקתה.")
        st.rerun()

st.divider()
st.caption("ℹ️ ניתן להוסיף כמה אימונים שתרצה ליום — מתאים למי שמשלב אימון כוח ואירובי באותו יום. השריפה מכל האימונים מתווספת לקלוריות היום וחלוקת המאקרו מותאמת.")
