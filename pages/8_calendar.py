#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8_calendar.py — לוח שנה עם עקיבות מזון, מים ואימונים
"""

import sys
import os
from datetime import date, datetime, timedelta
import calendar as cal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, page_header, section_header
from ui.user_auth import require_auth, logout_button
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.repositories.water_repository import WaterRepository

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BiteFit · יומן",
    page_icon="📅",
    layout="wide",
)

# ── Design system ─────────────────────────────────────────────────────────
inject_global_css()

with st.sidebar:
    st.markdown(f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">👤 {st.session_state.get("bitefit_user", {}).get("email", "")}</div>', unsafe_allow_html=True)
    logout_button()

USER_ID = require_auth()

# ── Page header ───────────────────────────────────────────────────────────
page_header(
    "לוח שנה",
    icon_name="calendar",
    subtitle="עקוב אחר מזון, מים ואימונים",
)

# ── Initialize repositories ──────────────────────────────────────────────────

workout_repo = WorkoutRepository()
water_repo = WaterRepository()

# ── Month/Year selection ─────────────────────────────────────────────────────

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    current_month = st.session_state.get("calendar_month", date.today().month)
    month = st.number_input("חודש", min_value=1, max_value=12, value=current_month, step=1)
    st.session_state["calendar_month"] = month

with col2:
    current_year = st.session_state.get("calendar_year", date.today().year)
    year = st.number_input("שנה", min_value=2020, max_value=2050, value=current_year, step=1)
    st.session_state["calendar_year"] = year

with col3:
    if st.button("חודש זה", use_container_width=True):
        today = date.today()
        st.session_state["calendar_month"] = today.month
        st.session_state["calendar_year"] = today.year
        st.rerun()

st.divider()

# ── Helper functions ─────────────────────────────────────────────────────────

def get_day_data(d):
    """Get activity data for a specific day."""
    workouts = workout_repo.resolve_workouts_for_date(USER_ID, d)
    water_intakes = water_repo.get_water_intakes_for_date(USER_ID, d)
    water_total = sum(w.amount_ml for w in water_intakes)
    water_goal = water_repo.get_water_goal(USER_ID).daily_goal_ml

    return {
        "workouts": workouts,
        "water_intakes": water_intakes,
        "water_total": water_total,
        "water_goal": water_goal,
        "water_pct": (water_total / water_goal * 100) if water_goal > 0 else 0,
    }


# ── Calendar Grid ────────────────────────────────────────────────────────────

section_header(f"{cal.month_name[month]} {year}", icon_name="calendar")

# Create calendar structure
calendar_matrix = cal.monthcalendar(year, month)

# Day names in Hebrew
day_names = ["ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳", "א׳"]

# Display day names
cols = st.columns(7)
for i, col in enumerate(cols):
    col.markdown(f"### {day_names[i]}")

# Display calendar days
for week in calendar_matrix:
    cols = st.columns(7)
    for day_idx, day_num in enumerate(week):
        col = cols[day_idx]

        if day_num == 0:
            col.empty()
        else:
            current_date = date(year, month, day_num)
            day_data = get_day_data(current_date)

            # Build day card content
            card_content = f"**{day_num}**\n\n"

            # Water indicator
            water_pct = day_data["water_pct"]
            if water_pct >= 100:
                water_emoji = "💧💧"
            elif water_pct >= 50:
                water_emoji = "💧"
            else:
                water_emoji = "🌧️"

            card_content += f"{water_emoji} {day_data['water_total']:.0f}ml\n\n"

            # Workout indicator
            if day_data["workouts"]:
                workout_count = len(day_data["workouts"])
                card_content += f"🏋️ {workout_count} אימון(ים)\n\n"

            # Button to view details
            if col.button(
                card_content,
                key=f"day_{day_num}_{month}_{year}",
                use_container_width=True,
                help=f"לחץ לצפייה בפרטים",
            ):
                st.session_state["selected_date"] = current_date.isoformat()

st.divider()

# ── Day Details Panel ────────────────────────────────────────────────────────

selected_date_str = st.session_state.get("selected_date")

if selected_date_str:
    selected_date = datetime.fromisoformat(selected_date_str).date()
    day_data = get_day_data(selected_date)

    st.markdown(f"### 📋 פרטים - {selected_date.strftime('%d/%m/%Y')}")

    # Create tabs for different views
    tab_water, tab_workouts, tab_summary = st.tabs(["💧 מים", "🏋️ אימונים", "📊 סיכום"])

    # ── Water Tab ────────────────────────────────────────────────────────
    with tab_water:
        st.markdown("#### צריכת מים")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "סה״כ מים",
                f"{day_data['water_total']:.0f} ml",
                f"{day_data['water_pct']:.0f}% מהיעד",
            )
        with col2:
            st.metric("יעד יומי", f"{day_data['water_goal']:.0f} ml")
        with col3:
            remaining = max(0, day_data["water_goal"] - day_data["water_total"])
            st.metric("נותר", f"{remaining:.0f} ml")

        st.progress(min(day_data["water_pct"] / 100, 1.0))

        # Water intakes list
        if day_data["water_intakes"]:
            st.markdown("**צריכות היום:**")
            for intake in day_data["water_intakes"]:
                time_str = intake.timestamp[11:16]  # HH:MM
                st.markdown(
                    f"🕐 **{time_str}** — {intake.amount_ml:.0f}ml "
                    f"({intake.source}){f' — {intake.notes}' if intake.notes else ''}"
                )
        else:
            st.info("אין צריכות מים רשומות ליום זה")

    # ── Workouts Tab ─────────────────────────────────────────────────────
    with tab_workouts:
        st.markdown("#### אימונים")

        if day_data["workouts"]:
            for i, workout in enumerate(day_data["workouts"], 1):
                with st.expander(
                    f"**{i}.** {workout.workout_type.value if workout.workout_type else 'אימון'}"
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("משך", f"{workout.duration_minutes} דק׳")
                    with col2:
                        st.metric("קלוריות", f"{workout.estimated_calories_burned:.0f}")
                    with col3:
                        if workout.distance_km:
                            st.metric("מרחק", f"{workout.distance_km:.1f} ק״מ")

                    if workout.intensity:
                        st.markdown(f"**עצימות:** {workout.intensity.value}")
                    if workout.notes:
                        st.markdown(f"**הערות:** {workout.notes}")
        else:
            st.info("אין אימונים רשומים ליום זה")

    # ── Summary Tab ──────────────────────────────────────────────────────
    with tab_summary:
        st.markdown("#### סיכום היום")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("אימונים", len(day_data["workouts"]))

        with col2:
            total_burn = sum(w.estimated_calories_burned for w in day_data["workouts"])
            st.metric("קלוריות אימון", f"{total_burn:.0f}")

        with col3:
            st.metric("צריכת מים", f"{day_data['water_total']:.0f}ml")

        with col4:
            pct = day_data["water_pct"]
            st.metric("מטרת מים", f"{pct:.0f}%")

        st.divider()

        # Summary text
        summary_parts = []

        if len(day_data["workouts"]) > 0:
            summary_parts.append(
                f"🏋️ **{len(day_data['workouts'])} אימון(ים)** בסך ~{sum(w.duration_minutes for w in day_data['workouts'])} דקות"
            )

        if day_data["water_pct"] >= 100:
            summary_parts.append(f"💧 **הגעת ליעד המים** ({day_data['water_pct']:.0f}%)")
        else:
            summary_parts.append(
                f"💧 **עוד {max(0, day_data['water_goal'] - day_data['water_total']):.0f}ml מים** להשלמת היעד"
            )

        if summary_parts:
            st.info(" | ".join(summary_parts))

else:
    st.info("בחר יום בלוח השנה לצפייה בפרטים")

# ── Legend ───────────────────────────────────────────────────────────────────

st.divider()
st.markdown("### 📖 מקרא")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**💧 מים:**")
    st.markdown("- 💧💧 יעד הושג")
    st.markdown("- 💧 חלק מהיעד")
    st.markdown("- 🌧️ פחות מחצי יעד")

with col2:
    st.markdown("**🏋️ אימונים:**")
    st.markdown("- מספר האימונים לאותו יום")

with col3:
    st.markdown("**📊 סטטוס:**")
    st.markdown("- צבע תא = פעילות")
    st.markdown("- בחר יום לפרטים מלאים")
