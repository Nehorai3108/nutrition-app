#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9_history.py — תיעוד כרונולוגי של פעילויות (מזון, מים, אימונים)
"""

import sys
import os
from datetime import date, datetime, timedelta
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, page_header, section_header
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.repositories.water_repository import WaterRepository

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="היסטוריה",
    page_icon="📜",
    layout="wide",
)

# ── Design system ─────────────────────────────────────────────────────────
inject_global_css()

USER_ID = "ui_user_001"

# ── Page header ───────────────────────────────────────────────────────────
page_header(
    "היסטוריה",
    icon_name="history",
    subtitle="רשימה כרונולוגית של כל הפעילויות שלך",
)

# ── Initialize repositories ──────────────────────────────────────────────────

workout_repo = WorkoutRepository()
water_repo = WaterRepository()

# ── Filters Section ──────────────────────────────────────────────────────────

section_header("סינון", icon_name="filter")

col1, col2, col3 = st.columns(3)

with col1:
    days_back = st.slider("ימים אחרונים", min_value=1, max_value=90, value=7, step=1)
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back - 1)

with col2:
    activity_filter = st.multiselect(
        "סוג פעילות",
        options=["מזון", "מים", "אימון"],
        default=["מזון", "מים", "אימון"],
    )

with col3:
    sort_order = st.radio(
        "סדר",
        options=["חדש קודם", "ישן קודם"],
        index=0,
        horizontal=True,
    )

# ── Collect all activities ──────────────────────────────────────────────────

all_activities: List[Tuple[str, dict]] = []

# Collect water intakes
if "מים" in activity_filter:
    water_intakes = water_repo.get_water_intakes_for_period(USER_ID, start_date, end_date)
    for intake in water_intakes:
        intake_date = datetime.fromisoformat(intake.timestamp).date()
        all_activities.append(
            (
                intake.timestamp,  # Sort key
                {
                    "type": "water",
                    "date": intake_date,
                    "time": intake.timestamp[11:16],  # HH:MM
                    "amount": intake.amount_ml,
                    "source": intake.source,
                    "notes": intake.notes,
                },
            )
        )

# Collect workouts
if "אימון" in activity_filter:
    current_date = start_date
    while current_date <= end_date:
        workouts = workout_repo.resolve_workouts_for_date(USER_ID, current_date)
        for workout in workouts:
            all_activities.append(
                (
                    f"{current_date.isoformat()}T12:00:00",  # Approximate time
                    {
                        "type": "workout",
                        "date": current_date,
                        "duration": workout.duration_minutes,
                        "workout_type": workout.workout_type,
                        "intensity": workout.intensity,
                        "calories": workout.estimated_calories_burned,
                        "distance": workout.distance_km,
                        "notes": workout.notes,
                    },
                )
            )
        current_date += timedelta(days=1)

# Sort activities
if sort_order == "חדש קודם":
    all_activities.sort(key=lambda x: x[0], reverse=True)
else:
    all_activities.sort(key=lambda x: x[0])

# ── Display Summary Stats ────────────────────────────────────────────────────

st.divider()
section_header("סטטיסטיקה", icon_name="stats")

# Calculate stats for the period
water_total = 0
water_days = set()
workout_count = 0
workout_days = set()
total_workout_burn = 0

for _, activity in all_activities:
    if activity["type"] == "water":
        water_total += activity["amount"]
        water_days.add(activity["date"].isoformat())
    elif activity["type"] == "workout":
        workout_count += 1
        workout_days.add(activity["date"].isoformat())
        total_workout_burn += activity.get("calories", 0)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "צריכת מים סה״כ",
        f"{water_total:.0f}ml",
        f"ממוצע: {water_total / days_back:.0f}ml/יום",
    )

with col2:
    st.metric(
        "ימים עם מים",
        f"{len(water_days)}/{days_back}",
        f"{len(water_days) / days_back * 100:.0f}%",
    )

with col3:
    st.metric(
        "אימונים סה״כ",
        f"{workout_count}",
        f"ממוצע: {workout_count / days_back:.1f}/יום",
    )

with col4:
    st.metric(
        "קלוריות אימון סה״כ",
        f"{total_workout_burn:.0f}",
        f"ממוצע: {total_workout_burn / days_back:.0f}/יום",
    )

# ── Timeline/History View ────────────────────────────────────────────────────

st.divider()
section_header("ציר הזמן", icon_name="timeline")

if not all_activities:
    st.info("אין פעילויות בתקופה שנבחרה")
else:
    # Group by date for better organization
    from collections import defaultdict

    activities_by_date = defaultdict(list)
    for _, activity in all_activities:
        activities_by_date[activity["date"]].append(activity)

    # Sort dates
    sorted_dates = sorted(activities_by_date.keys(), reverse=(sort_order == "חדש קודם"))

    for activity_date in sorted_dates:
        activities = activities_by_date[activity_date]

        # Date header
        is_today = activity_date == date.today()
        date_label = "היום" if is_today else activity_date.strftime("%A, %d.%m.%Y")
        date_emoji = "📅" if not is_today else "🔥"

        st.markdown(f"### {date_emoji} {date_label}")

        # Display activities for this date
        for activity in activities:
            if activity["type"] == "water":
                st.markdown(
                    f"""
                    💧 **מים** — {activity['time']}
                    - כמות: {activity['amount']:.0f}ml
                    - מקור: {activity['source']}
                    {f"- הערה: {activity['notes']}" if activity['notes'] else ""}
                    """
                )

            elif activity["type"] == "workout":
                workout_type = activity["workout_type"].value if activity["workout_type"] else "אימון"
                intensity = activity["intensity"].value if activity["intensity"] else ""
                distance = f" · {activity['distance']:.1f}ק״מ" if activity.get("distance") else ""

                st.markdown(
                    f"""
                    🏋️ **{workout_type}** {intensity}
                    - משך: {activity['duration']} דקות{distance}
                    - קלוריות: {activity['calories']:.0f}
                    {f"- הערה: {activity['notes']}" if activity['notes'] else ""}
                    """
                )

        st.divider()

# ── Monthly Summary (Bottom) ─────────────────────────────────────────────────

st.divider()
section_header("סיכום חודשי", icon_name="calendar")

# Get current month data
now = date.today()
first_day_of_month = date(now.year, now.month, 1)
if now.month == 12:
    last_day_of_month = date(now.year + 1, 1, 1) - timedelta(days=1)
else:
    last_day_of_month = date(now.year, now.month + 1, 1) - timedelta(days=1)

# Calculate monthly stats
current_date = first_day_of_month
month_water = 0
month_water_days = 0
month_workouts = 0
month_burn = 0

while current_date <= last_day_of_month:
    water_intakes = water_repo.get_water_intakes_for_date(USER_ID, current_date)
    if water_intakes:
        month_water_days += 1
        month_water += sum(w.amount_ml for w in water_intakes)

    workouts = workout_repo.resolve_workouts_for_date(USER_ID, current_date)
    if workouts:
        month_workouts += len(workouts)
        month_burn += sum(w.estimated_calories_burned for w in workouts)

    current_date += timedelta(days=1)

col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_water = month_water / (now.day if now.month != 1 else 1)
    st.metric(f"מים ({now.strftime('%B')})", f"{month_water:.0f}ml", f"ממוצע: {avg_water:.0f}/יום")

with col2:
    water_pct = (month_water_days / now.day * 100) if now.day > 0 else 0
    st.metric("ימים פעילים (מים)", f"{month_water_days}/{now.day}", f"{water_pct:.0f}%")

with col3:
    avg_workouts = month_workouts / now.day if now.day > 0 else 0
    st.metric("אימונים", f"{month_workouts}", f"ממוצע: {avg_workouts:.1f}/יום")

with col4:
    avg_burn = month_burn / now.day if now.day > 0 else 0
    st.metric("קלוריות אימון", f"{month_burn:.0f}", f"ממוצע: {avg_burn:.0f}/יום")
