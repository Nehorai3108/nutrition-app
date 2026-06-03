#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app_user.py — ממשק משתמש גרפי למערכת תזונה חכמה
הרצה: streamlit run app_user.py
"""

import sys
import os
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu,
    icon_button, recipe_card_html, welcome_card_html, macro_grid_html,
    kashrut_badge_html, meal_badge_html, bottom_nav,
)
from ui.user_auth import require_auth
from ui.images import image_data_uri as _recipe_image_data_uri

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal, WorkoutIntensity, WorkoutType
from nutrition_app.models.workout import WorkoutEntry
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.agents.agent_2_nutrition import NutritionEngine, adjust_targets_for_workouts
from nutrition_app.agents.agent_2_nutrition.workout_adjuster import estimate_calories_burned
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.agents.agent_6_ai import AILayer
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions
from nutrition_app.models.daily_summary import DailySummary
from nutrition_app.repositories.daily_summary_repository import DailySummaryRepository
from nutrition_app.repositories.water_repository import WaterRepository as _WaterRepo
from nutrition_app.repositories.workout_repository import WorkoutRepository as _WorkoutRepo
from nutrition_app.repositories.food_log_repository import FoodLogRepository as _FoodLogRepo, FoodLogEntry as _FoodLogEntry

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "nutrition.db")

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BiteFit",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system ────────────────────────────────────────────────────────────
inject_global_css()

# ── Auth ─────────────────────────────────────────────────────────────────────
_USER_ID: str = require_auth()

# ── Constants ────────────────────────────────────────────────────────────────

MEAL_LABELS = {
    "breakfast":       "🌅 ארוחת בוקר",
    "morning_snack":   "☕ חטיף בוקר",
    "lunch":           "🍽 ארוחת צהריים",
    "afternoon_snack": "🍎 חטיף אחה\"צ",
    "dinner":          "🌙 ארוחת ערב",
    "evening_snack":   "🌜 חטיף ערב",
}

ACTIVITY_LABELS = {
    ActivityLevel.SEDENTARY:         "יושבני (כמעט ללא פעילות)",
    ActivityLevel.LIGHTLY_ACTIVE:    "פעילות קלה (1-3 ימים/שבוע)",
    ActivityLevel.MODERATELY_ACTIVE: "פעילות בינונית (3-5 ימים/שבוע)",
    ActivityLevel.VERY_ACTIVE:       "פעילות גבוהה (6-7 ימים/שבוע)",
    ActivityLevel.EXTRA_ACTIVE:      "פעילות אינטנסיבית / עבודה פיזית",
}

GOAL_LABELS = {
    Goal.LOSE_WEIGHT:  "ירידה במשקל",
    Goal.MAINTAIN:     "שמירה על משקל",
    Goal.GAIN_WEIGHT:  "עלייה במשקל",
}

GENDER_LABELS = {
    Gender.MALE:   "זכר",
    Gender.FEMALE: "נקבה",
}

@st.cache_resource
def _get_catalog() -> FoodCatalog:
    """Load FoodCatalog from nutrition.db. Falls back to static catalog if DB is empty."""
    return FoodCatalog(db_path=_DB_PATH)


_catalog = _get_catalog()
_all_food_items = sorted(_catalog.get_all_foods(), key=lambda f: f.name_he)

ALL_FOODS = [(f.food_id, f.name_he) for f in _all_food_items]
FOOD_ID_TO_NAME = {fid: name for fid, name in ALL_FOODS}
FOOD_NAME_TO_ID = {name: fid for fid, name in ALL_FOODS}
# Query map: food_id → search term (use name_he directly — it's in the catalog)
FOOD_QUERY_MAP = {f.food_id: f.name_he for f in _all_food_items}

_PREFERRED_DEFAULTS = [
    "חזה עוף", "אורז לבן", "ביצה", "בננה", "שמן זית",
    "לחם מחיטה מלאה", "עגבנייה", "גבינת קוטג׳", "מלפפון",
]
_DEFAULT_FOOD_NAMES = [n for n in _PREFERRED_DEFAULTS if n in FOOD_NAME_TO_ID]
if not _DEFAULT_FOOD_NAMES:
    _DEFAULT_FOOD_NAMES = [name for _, name in ALL_FOODS[:5]]

# ── Sidebar — Slim Dashboard ──────────────────────────────────────────────────
from nutrition_app.repositories.profile_repository import ProfileRepository as _ProfileRepo
from nutrition_app.user_manager import load_inventory as _load_inv

_profile_repo = _ProfileRepo()
_profile = _profile_repo.load(_USER_ID)

# Resolve profile values (used by pipeline below)
name          = _profile.get("name", "ישראל ישראלי")
gender_choice = Gender(_profile.get("gender", "male"))
height        = float(_profile.get("height_cm", 178.0))
weight        = float(_profile.get("weight_kg", 82.0))
try:
    dob = date.fromisoformat(_profile.get("date_of_birth", "1990-05-15"))
except ValueError:
    dob = date(1990, 5, 15)
activity_choice = ActivityLevel(_profile.get("activity_level", "moderately_active"))
goal_choice     = Goal(_profile.get("goal", "lose_weight"))

# Build food selection + inventory from stored inventory (managed via inventory page)
_stored_inv = _load_inv(_USER_ID)   # list of {food_id, name_he, quantity_g}
_scanned_inv = st.session_state.get("scanned_inventory", {})

# Merge stored + scanned inventory
inventory_inputs: dict = {}
for _item in _stored_inv:
    _fid = _item.get("food_id", "")
    _qty = float(_item.get("quantity_g", 0))
    if _fid and _qty > 0:
        inventory_inputs[_fid] = _qty
for _fid, _qty in _scanned_inv.items():
    inventory_inputs[_fid] = float(_qty)

# Food names from inventory (for pipeline matching)
selected_food_names = [
    FOOD_ID_TO_NAME[fid] for fid in inventory_inputs if fid in FOOD_ID_TO_NAME
]
if not selected_food_names:
    selected_food_names = _DEFAULT_FOOD_NAMES
    inventory_inputs = {
        FOOD_NAME_TO_ID[n]: float({"חזה עוף": 600, "אורז לבן": 1000, "ביצה": 400,
                                    "בננה": 360, "לחם מחיטה מלאה": 500}.get(n, 300))
        for n in selected_food_names if n in FOOD_NAME_TO_ID
    }

GOAL_LABEL_SHORT = {
    Goal.LOSE_WEIGHT: "ירידה במשקל",
    Goal.MAINTAIN: "שמירה",
    Goal.GAIN_WEIGHT: "עלייה במשקל",
}

with st.sidebar:
    # ── Hebrew navigation ─────────────────────────────────────────────────
    st.page_link("app_user.py",                       label="ראשי",              use_container_width=True)
    st.page_link("pages/0_profile.py",                label="פרופיל",            use_container_width=True)
    st.page_link("pages/2_recipes.py",                label="מתכונים",           use_container_width=True)
    st.page_link("pages/4_inventory.py",              label="מלאי",              use_container_width=True)
    st.page_link("pages/6_daily_menu.py",             label="תפריט יומי",        use_container_width=True)
    st.page_link("pages/7_workout_tracker.py",        label="מעקב אימונים",      use_container_width=True)
    st.page_link("pages/7_weekly_workout_plan.py",    label="תכנית אימונים",     use_container_width=True)
    st.page_link("pages/8_calendar.py",               label="לוח שנה",           use_container_width=True)
    st.page_link("pages/9_history.py",                label="היסטוריה",          use_container_width=True)
    st.divider()

    # ── Profile card ──────────────────────────────────────────────────────
    st.markdown(f"### {name}")
    st.caption(f"⚖️ {weight}ק״ג &nbsp;·&nbsp; 🎯 {GOAL_LABEL_SHORT.get(goal_choice, '')}")
    _user_email_display = st.session_state.get("user_email") or (
        st.session_state.get("bitefit_user", {}) or {}
    ).get("email", "")
    _streamlit_email = getattr(st.experimental_user, "email", "") if hasattr(st, "experimental_user") else ""
    _display_email = _streamlit_email or _user_email_display
    if _display_email:
        st.caption(f"👤 {_display_email}")
    st.page_link("pages/0_profile.py", label="ערוך פרופיל", use_container_width=True)

    st.divider()

    # ── Workout input for today ──────────────────────────────────────────
    WORKOUT_INTENSITY_LABELS = {
        WorkoutIntensity.LOW:      "נמוכה (הליכה קלה)",
        WorkoutIntensity.MODERATE: "בינונית (הליכה מהירה)",
        WorkoutIntensity.HIGH:     "גבוהה (ריצה)",
        WorkoutIntensity.EXTREME:  "עצימה מאוד (HIIT)",
    }
    WORKOUT_TYPE_LABELS = {
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
        WorkoutType.OTHER:          "🏋️ אחר",
    }

    DISTANCE_TYPES = {WorkoutType.RUNNING, WorkoutType.WALKING, WorkoutType.HIKING}

    with st.expander("🏋️ אימוני היום", expanded=False):
        _workout_repo = WorkoutRepository()
        _today = date.today()
        _raw_data = _workout_repo.get_workout_data(_USER_ID)
        _has_daily_override = _today.isoformat() in _raw_data.daily_log
        _plan_workouts = _raw_data.weekly_plan.workouts_by_day.get(
            _today.strftime("%A").lower(), []
        ) if _raw_data.weekly_plan else []

        # ── CONFIRMED workouts (already in daily log) ─────────────────────────
        if _has_daily_override:
            _confirmed = _raw_data.daily_log[_today.isoformat()]
            st.success(f"✅ {len(_confirmed)} אימון(ים) אושר(ו) להיום")
            for i, w in enumerate(_confirmed):
                if w.mode == "intensity" and w.intensity:
                    _desc = f"עצימות {WORKOUT_INTENSITY_LABELS.get(w.intensity, w.intensity.value)}"
                elif w.mode == "type" and w.workout_type:
                    _desc = WORKOUT_TYPE_LABELS.get(w.workout_type, w.workout_type.value)
                    if w.intensity:
                        _desc += f" · {WORKOUT_INTENSITY_LABELS.get(w.intensity, w.intensity.value)}"
                else:
                    _desc = "אימון"
                _metric = f"{w.distance_km} ק\"מ" if w.distance_km else f"{w.duration_minutes} דק׳"
                col_w, col_del = st.columns([4, 1])
                _w_kcal = w.estimated_calories_burned if w.estimated_calories_burned > 0 else estimate_calories_burned(w, weight)
                col_w.markdown(f"✔ **{_desc}** · {_metric} · {_w_kcal:.0f} קק״ל")
                with col_del:
                    if icon_button("מחק", "delete", key=f"del_w_{i}",
                                   help="הסר אימון מהיום", type="secondary"):
                        _workout_repo.remove_daily_workout(_USER_ID, _today, i)
                        st.rerun()
            if icon_button("נקה הכל", "clear", key="clear_daily_workouts", type="secondary"):
                _workout_repo.clear_daily_workouts(_USER_ID, _today)
                st.rerun()
            st.divider()

        # ── PENDING confirmation (weekly plan, not yet confirmed) ─────────────
        elif _plan_workouts:
            st.warning(f"⏳ {len(_plan_workouts)} אימון(ים) מהתכנית השבועית — האם בוצעו?")
            for i, w in enumerate(_plan_workouts):
                if w.mode == "intensity" and w.intensity:
                    _desc = f"עצימות {WORKOUT_INTENSITY_LABELS.get(w.intensity, w.intensity.value)}"
                elif w.mode == "type" and w.workout_type:
                    _desc = WORKOUT_TYPE_LABELS.get(w.workout_type, w.workout_type.value)
                    if w.intensity:
                        _desc += f" · {WORKOUT_INTENSITY_LABELS.get(w.intensity, w.intensity.value)}"
                else:
                    _desc = "אימון"
                _metric = f"{w.distance_km} ק\"מ" if w.distance_km else f"{w.duration_minutes} דק׳"

                st.markdown(f"**{i+1}.** {_desc} · {_metric}")

                _editing_key = f"editing_workout_{i}"
                _is_editing = st.session_state.get(_editing_key, False)

                if not _is_editing:
                    c1, c2, c3 = st.columns(3)
                    # ✅ Confirm as-is
                    if c1.button("✅ בוצע", key=f"confirm_w_{i}", use_container_width=True):
                        w.estimated_calories_burned = estimate_calories_burned(w, weight)
                        _workout_repo.add_daily_workout(_USER_ID, _today, w)
                        st.success(f"✅ {_desc} אושר!")
                        st.rerun()
                    # ✏️ Edit before confirming
                    if c2.button("✏️ שנה", key=f"edit_w_{i}", use_container_width=True):
                        st.session_state[_editing_key] = True
                        st.rerun()
                    # ❌ Skip
                    if c3.button("❌ דלג", key=f"skip_w_{i}", use_container_width=True):
                        # Confirm an empty-ish entry won't work; just mark day so plan is bypassed
                        skipped = st.session_state.get("skipped_workouts_today", set())
                        skipped.add(i)
                        st.session_state["skipped_workouts_today"] = skipped
                        st.info(f"↩️ {_desc} דולג")
                        st.rerun()
                else:
                    # ── Inline edit form ──────────────────────────────────────
                    st.markdown("##### ✏️ ערוך אימון")
                    _e_type = st.selectbox(
                        "סוג אימון",
                        options=list(WORKOUT_TYPE_LABELS.keys()),
                        format_func=lambda x: WORKOUT_TYPE_LABELS[x],
                        index=list(WORKOUT_TYPE_LABELS.keys()).index(w.workout_type)
                              if w.workout_type in WORKOUT_TYPE_LABELS else 0,
                        key=f"edit_type_{i}",
                    )
                    _e_dur = st.number_input(
                        "משך (דקות)", min_value=1, max_value=300,
                        value=w.duration_minutes or 30, step=5,
                        key=f"edit_dur_{i}",
                    )
                    _e_dist = 0.0
                    if _e_type in DISTANCE_TYPES:
                        _e_dist = st.number_input(
                            "מרחק (ק\"מ)", min_value=0.0, max_value=200.0,
                            value=w.distance_km or 0.0, step=0.5,
                            key=f"edit_dist_{i}",
                        )
                    _e_intensity = st.selectbox(
                        "עצימות",
                        options=["none"] + list(WORKOUT_INTENSITY_LABELS.keys()),
                        format_func=lambda x: "רגילה" if x == "none" else WORKOUT_INTENSITY_LABELS[x],
                        key=f"edit_int_{i}",
                    )
                    ce1, ce2 = st.columns(2)
                    if ce1.button("✅ אשר שינוי", key=f"confirm_edit_{i}", use_container_width=True):
                        _new_w = WorkoutEntry(
                            duration_minutes=int(_e_dur),
                            mode="type",
                            workout_type=_e_type,
                            intensity=None if _e_intensity == "none" else _e_intensity,
                            distance_km=float(_e_dist) if _e_dist > 0 else None,
                        )
                        _new_w.estimated_calories_burned = estimate_calories_burned(_new_w, weight)
                        _workout_repo.add_daily_workout(_USER_ID, _today, _new_w)
                        st.session_state[_editing_key] = False
                        st.success("✅ אימון מעודכן נשמר!")
                        st.rerun()
                    if ce2.button("ביטול", key=f"cancel_edit_{i}", use_container_width=True):
                        st.session_state[_editing_key] = False
                        st.rerun()
                st.divider()

        else:
            st.caption("אין אימונים מתוכננים להיום ואין תכנית שבועית ליום זה.")

        # ── Manual add ────────────────────────────────────────────────────────
        st.markdown("**➕ הוסף אימון ידנית**")
        workout_mode_choice = st.radio(
            "איך להזין?",
            options=["intensity", "type"],
            format_func=lambda m: {"intensity": "לפי עצימות",
                                     "type": "לפי סוג אימון"}[m],
            key="workout_mode_choice",
            horizontal=True,
        )

        workout_entry_input: "WorkoutEntry | None" = None
        if workout_mode_choice == "intensity":
            intensity_sel = st.selectbox(
                "עצימות",
                options=list(WORKOUT_INTENSITY_LABELS.keys()),
                format_func=lambda x: WORKOUT_INTENSITY_LABELS[x],
                key="workout_intensity_sel",
            )
            duration_sel = st.number_input(
                "משך (דקות)", min_value=0, max_value=300, value=30, step=5,
                key="workout_duration_intensity",
            )
            if duration_sel > 0:
                workout_entry_input = WorkoutEntry(
                    duration_minutes=int(duration_sel),
                    mode="intensity",
                    intensity=intensity_sel,
                )
        else:  # type
            type_sel = st.selectbox(
                "סוג אימון",
                options=list(WORKOUT_TYPE_LABELS.keys()),
                format_func=lambda x: WORKOUT_TYPE_LABELS[x],
                key="workout_type_sel",
            )
            duration_sel = st.number_input(
                "משך (דקות)", min_value=0, max_value=300, value=30, step=5,
                key="workout_duration_type",
            )
            distance_sel = 0.0
            if type_sel in DISTANCE_TYPES:
                distance_sel = st.number_input(
                    "מרחק (ק\"מ) — אם מוזן, יגבר על משך",
                    min_value=0.0, max_value=200.0, value=0.0, step=0.5,
                    key="workout_distance_type",
                )
            type_intensity_sel = st.selectbox(
                "עצימות (אופציונלי)",
                options=["none"] + list(WORKOUT_INTENSITY_LABELS.keys()),
                format_func=lambda x: "רגילה" if x == "none" else WORKOUT_INTENSITY_LABELS[x],
                key="workout_type_intensity_sel",
            )
            _eff_intensity = None if type_intensity_sel == "none" else type_intensity_sel
            if duration_sel > 0 or distance_sel > 0:
                workout_entry_input = WorkoutEntry(
                    duration_minutes=int(duration_sel),
                    mode="type",
                    workout_type=type_sel,
                    intensity=_eff_intensity,
                    distance_km=float(distance_sel) if distance_sel > 0 else None,
                )

        if icon_button("הוסף אימון לרשימה", "add", key="add_workout_btn"):
            if workout_entry_input is None:
                st.warning("יש להזין משך אימון גדול מ-0.")
            else:
                workout_entry_input.estimated_calories_burned = estimate_calories_burned(workout_entry_input, weight)
                _workout_repo.add_daily_workout(_USER_ID, _today, workout_entry_input)
                st.success("האימון נוסף.")
                st.rerun()

        st.page_link(
            "pages/7_weekly_workout_plan.py",
            label="📅 ערוך תכנית אימונים שבועית",
            use_container_width=True,
        )

    st.divider()

    # ── Water Tracking ───────────────────────────────────────────────────────
    _WATER_USER_ID = _USER_ID
    water_repo = _WaterRepo()
    water_data = water_repo.get_water_data(_WATER_USER_ID)
    today_water = water_repo.get_water_intakes_for_date(_WATER_USER_ID, date.today())
    daily_total = sum(w.amount_ml for w in today_water)
    goal_ml = water_data.goal.daily_goal_ml if water_data.goal else 2000

    with st.expander("💧 מים - היום", expanded=False):
        # Display current progress
        col_metric, col_pct = st.columns([2, 1])
        with col_metric:
            st.metric("צריכת מים", f"{daily_total:.0f}ml / {goal_ml:.0f}ml")
        with col_pct:
            pct = (daily_total / goal_ml * 100) if goal_ml > 0 else 0
            st.metric("התקדמות", f"{pct:.0f}%")

        st.progress(min(daily_total / goal_ml, 1.0))

        # Quick add buttons
        st.markdown("**הוסף מים:**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("250ml", key="water_250", use_container_width=True):
                water_repo.add_water_intake(_WATER_USER_ID, 250, source="bottle")
                st.rerun()

        with col2:
            if st.button("500ml", key="water_500", use_container_width=True):
                water_repo.add_water_intake(_WATER_USER_ID, 500, source="bottle")
                st.rerun()

        with col3:
            if st.button("750ml", key="water_750", use_container_width=True):
                water_repo.add_water_intake(_WATER_USER_ID, 750, source="bottle")
                st.rerun()

        with col4:
            if st.button("1L", key="water_1000", use_container_width=True):
                water_repo.add_water_intake(_WATER_USER_ID, 1000, source="bottle")
                st.rerun()

        st.divider()

        # Custom amount
        st.markdown("**כמות מותאמת:**")
        custom_ml = st.number_input("סמ״ק", min_value=0, max_value=2000, value=250, step=50, key="water_custom_ml")
        water_source = st.selectbox(
            "מקור",
            options=["bottle", "cup", "glass", "tap"],
            format_func=lambda x: {"bottle": "בקבוק", "cup": "כוס", "glass": "גביע", "tap": "ברז"}[x],
            key="water_source",
        )

        if st.button("הוסף כמות מותאמת", key="water_custom_btn", use_container_width=True, type="secondary"):
            if custom_ml > 0:
                water_repo.add_water_intake(_WATER_USER_ID, custom_ml, source=water_source)
                st.rerun()

        st.divider()

        # Recent intakes
        if today_water:
            st.markdown("**צריכות היום:**")
            for intake in today_water[-3:]:  # Last 3 intakes
                time_str = intake.timestamp[11:16]  # HH:MM
                st.caption(f"🕐 {time_str} — {intake.amount_ml:.0f}ml ({intake.source})")

        # Water goal setting
        st.divider()
        st.markdown("**יעד יומי:**")
        new_goal = st.number_input(
            "ליטר מים",
            min_value=0.5,
            max_value=5.0,
            value=goal_ml / 1000,
            step=0.1,
            key="water_goal_input",
        )
        if st.button("עדכן יעד", key="water_goal_btn", use_container_width=True, type="secondary"):
            water_repo.save_water_goal(_WATER_USER_ID, new_goal * 1000)
            st.rerun()
            st.rerun()

    st.divider()

    # ── Quick links ───────────────────────────────────────────────────────
    _inv_count = len([i for i in _stored_inv if i.get("quantity_g", 0) > 0])
    _scanned_count = len(_scanned_inv)
    _inv_label = f"📦 מלאי ({_inv_count} פריטים{f' + {_scanned_count} סרוקים' if _scanned_count else ''})"
    st.page_link("pages/4_inventory.py", label=_inv_label, use_container_width=True)
    st.page_link("pages/2_receipt_scanner.py", label="🧾 סרוק קבלה", use_container_width=True)

    st.divider()
    run_btn = icon_button("הפק תפריט יומי", "play",
                          key="run_pipeline_btn", type="primary")

# ── Main Area ─────────────────────────────────────────────────────────────────

if not run_btn and "last_plan" not in st.session_state:
    # ── Activity Rings dashboard (Apple Watch style) ───────────────────────────
    import math as _math

    _DASH_USER = _USER_ID
    today = date.today()

    # ── Load data ─────────────────────────────────────────────────────────────
    _summary_repo = DailySummaryRepository()
    _water_repo_db = _WaterRepo()
    _workout_repo_db = _WorkoutRepo()
    _food_log_repo = _FoodLogRepo()

    summary      = _summary_repo.get(_DASH_USER, today)
    water_total  = sum(w.amount_ml for w in _water_repo_db.get_water_intakes_for_date(_DASH_USER, today))
    water_goal   = _water_repo_db.get_water_goal(_DASH_USER).daily_goal_ml
    workouts     = _workout_repo_db.get_workout_data(_DASH_USER).daily_log.get(today.isoformat(), [])
    burned       = sum(w.estimated_calories_burned if w.estimated_calories_burned > 0 else estimate_calories_burned(w, weight) for w in workouts)
    _log_totals  = _food_log_repo.get_totals(_DASH_USER, today)
    _food_log    = _food_log_repo.get_log(_DASH_USER, today)
    cal_eaten    = _log_totals["calories"]
    prot_eaten   = _log_totals["protein"]
    carbs_eaten  = _log_totals["carbs"]
    fat_eaten    = _log_totals["fat"]

    _user_obj = UserProfile(user_id=_DASH_USER, name=name, gender=gender_choice,
                            date_of_birth=dob, height_cm=height, weight_kg=weight,
                            activity_level=activity_choice, goal=goal_choice)
    _saved_pace       = _profile.get("pace", "moderate")
    _saved_weekly_kg  = _profile.get("weekly_change_kg")
    _saved_target_w   = _profile.get("target_weight_kg")
    _targets  = NutritionEngine().calculate_targets(
        _user_obj,
        pace=_saved_pace,
        weekly_change_kg=float(_saved_weekly_kg) if _saved_weekly_kg else None,
        target_weight_kg=float(_saved_target_w)  if _saved_target_w  else None,
    )
    # Always use live calculated targets from current profile — never stale summary
    cal_t   = int(_targets.target_calories_kcal)
    prot_t  = int(_targets.protein_g)
    carbs_t = int(_targets.carbs_g)
    fat_t   = int(_targets.fat_g)

    # ── Meal / color / icon maps ──────────────────────────────────────────────
    MEAL_HEB = {"breakfast":"ארוחת בוקר","morning_snack":"חטיף בוקר",
                "lunch":"ארוחת צהריים","afternoon_snack":"חטיף אחה״צ",
                "dinner":"ארוחת ערב","evening_snack":"חטיף ערב"}
    MEAL_COLOR = {"breakfast":"#f59e0b","morning_snack":"#a78bfa",
                  "lunch":"#4f8ef7","afternoon_snack":"#34d399",
                  "dinner":"#f87171","evening_snack":"#818cf8"}
    MEAL_ICON  = {"breakfast":"🌅","morning_snack":"☕",
                  "lunch":"🍽","afternoon_snack":"🍎",
                  "dinner":"🌙","evening_snack":"🌜"}

    # ── Spoonacular CDN food image slugs (no API key needed) ─────────────────
    # URL: https://spoonacular.com/cdn/ingredients_100x100/{slug}.png
    _FOOD_IMG: dict[str, str] = {
        # ── עוף ──
        "חזה עוף":              "chicken-breasts",
        "עוף":                  "whole-chicken",
        "כרעי עוף":             "chicken-legs",
        "שוק עוף":              "chicken-drumstick",
        "כנפי עוף":             "chicken-wings",
        # ── בשר ──
        "בשר בקר":              "beef-sirloin-raw",
        "המבורגר":              "beef-patty",
        "סטייק":                "beef-tenderloin",
        "קציצות":               "meatballs",
        "טורקי":                "turkey",
        "הודו":                 "turkey",
        # ── דגים ──
        "סלמון":                "salmon",
        "טונה":                 "canned-tuna",
        "דג":                   "tilapia",
        "סרדינים":              "sardine",
        "שרימפס":               "shrimp",
        # ── ביצים ודיירי ──
        "ביצה":                 "egg",
        "ביצים":                "egg",
        "חלב":                  "milk",
        "גבינת קוטג׳":          "cottage-cheese",
        "קוטג׳":                "cottage-cheese",
        "גבינה לבנה":           "cream-cheese",
        "גבינה צהובה":          "cheddar-cheese",
        "גבינת צ׳דר":           "cheddar-cheese",
        "יוגורט":               "plain-yogurt",
        "יוגורט יווני":         "plain-yogurt",
        "גבינה":                "cheddar-cheese",
        "חמאה":                 "butter",
        "שמנת":                 "sour-cream",
        # ── דגנים ולחם ──
        "אורז לבן":             "rice",
        "אורז":                 "rice",
        "אורז חום":             "brown-rice",
        "לחם מחיטה מלאה":       "whole-wheat-bread",
        "לחם":                  "bread",
        "פיתה":                 "pita-bread",
        "פסטה":                 "pasta",
        "מקרוני":               "macaroni",
        "שיבולת שועל":          "rolled-oats",
        "גרנולה":               "granola",
        "קוסקוס":               "couscous",
        "קינואה":               "quinoa",
        "קמח":                  "all-purpose-flour",
        "טורטייה":              "flour-tortilla",
        "קרקר":                 "crackers",
        # ── ירקות ──
        "עגבנייה":              "tomatoes",
        "עגבניות":              "tomatoes",
        "מלפפון":               "cucumber",
        "גזר":                  "carrots",
        "ברוקולי":              "broccoli",
        "כרובית":               "cauliflower",
        "תרד":                  "spinach",
        "חסה":                  "romaine-lettuce",
        "כרוב":                 "green-cabbage",
        "פלפל":                 "bell-pepper",
        "פלפל אדום":            "red-pepper",
        "פלפל ירוק":            "green-pepper",
        "בצל":                  "white-onion",
        "שום":                  "garlic",
        "תפוח אדמה":            "potato",
        "בטטה":                 "sweet-potato",
        "זוקיני":               "zucchini",
        "חצילים":               "eggplant",
        "אספרגוס":              "asparagus",
        "תירס":                 "corn",
        "אפונה":                "green-peas",
        "עדשים":                "lentils",
        "שעועית":               "kidney-beans",
        "חומוס":                "chickpeas",
        "פול":                  "fava-beans",
        "טופו":                 "tofu",
        # ── פירות ──
        "בננה":                 "bananas",
        "תפוח":                 "apple",
        "תפוח עץ":              "apple",
        "תפוז":                 "orange",
        "ענבים":                "grapes",
        "תות שדה":              "strawberries",
        "תות":                  "strawberries",
        "אבטיח":                "watermelon",
        "מלון":                 "honeydew-melon",
        "אבוקדו":               "avocado",
        "לימון":                "lemon",
        "ליים":                 "lime",
        "אפרסק":                "peach",
        "שזיף":                 "plums",
        "מנגו":                 "mango",
        "אננס":                 "fresh-pineapple",
        "קיווי":                "kiwi",
        "אוכמניות":             "blueberries",
        "פטל":                  "raspberries",
        "תמר":                  "dates",
        "צימוקים":              "raisins",
        # ── שומנים וממרחים ──
        "שמן זית":              "olive-oil",
        "שמן":                  "vegetable-oil",
        "חמאת בוטנים":          "peanut-butter",
        "טחינה":                "tahini",
        "חומוס (ממרח)":         "hummus",
        "אגוזי מלך":            "walnuts",
        "שקדים":                "almonds",
        "קשיו":                 "cashew",
        "אגוזי ברזיל":          "brazil-nuts",
        "גרעינים":              "sunflower-seeds",
        "זיתים":                "olives",
        # ── שונות ──
        "שוקולד":               "dark-chocolate",
        "דבש":                  "honey",
        "ריבה":                 "strawberry-jam",
        "קפה":                  "coffee",
        "תה":                   "tea",
        "מיץ תפוזים":           "orange-juice",
        "מים":                  "water",
        # ── נוספות ──
        "אורז בר":              "wild-rice",
        "בוטנים":               "peanuts",
        "חמאת שקדים":           "almond-butter",
        "אבקת חרוב":            "carob-powder",
        "אבקת חלבון":           "whey-powder",
        "גבינת ריקוטה":         "ricotta",
        "גבינת פטה":            "feta",
        "קרם גבינה":            "cream-cheese",
        "שמן קוקוס":            "coconut-oil",
        "קוקוס":                "coconut",
        "חמניות":               "sunflower-seeds",
        "פיסטוקים":             "pistachio-nuts",
        "פיסטוק":               "pistachio-nuts",
        "אגוזים":               "mixed-nuts",
        "אגוז":                 "walnuts",
        "פקאן":                 "pecans",
        "קמח שיבולת שועל":      "rolled-oats",
        "חיטה":                 "whole-wheat",
        "כוסמת":                "buckwheat",
        "שעורה":                "barley",
        "גרעיני דלעת":          "pumpkin-seeds",
        "פנקייק":               "pancakes",
        "וופל":                 "waffles",
        "שייק":                 "milkshake",
        "מיץ":                  "orange-juice",
        "סלט":                  "salad",
        "מרק":                  "vegetable-broth",
        "פיצה":                 "pizza",
        "בורגר":                "burger",
        "שניצל":                "schnitzel",
        "חמבה":                 "mango-chutney",
        "הוּמוּס":              "hummus",
        "חומוס ממרח":           "hummus",
        "פלאפל":                "chickpea-flour",
        "שקשוקה":               "egg",
        "לביבות":               "potato-pancakes",
        "קציצה":                "meatballs",
        "כופתאות":              "dumpling",
    }

    # High-priority keywords (proteins / main dishes) that win over longer carb/veggie keys
    _FOOD_IMG_PRIORITY = {
        "חזה עוף", "עוף", "סלמון", "טונה", "בשר בקר", "המבורגר", "סטייק",
        "שרימפס", "דג", "הודו", "טורקי", "קציצות", "שניצל", "ביצה", "ביצים",
    }

    def _get_food_slug(food_name: str) -> str:
        """Return Spoonacular CDN slug — exact match, then partial (protein-priority)."""
        # 1. Exact match
        slug = _FOOD_IMG.get(food_name, "")
        if slug:
            return slug
        # 2. Partial match: priority keys first (proteins), then longest regular key
        for key in _FOOD_IMG_PRIORITY:
            if key in food_name:
                return _FOOD_IMG[key]
        best_key, best_len = "", 0
        for key in _FOOD_IMG:
            if key in food_name and len(key) > best_len:
                best_key, best_len = key, len(key)
        return _FOOD_IMG.get(best_key, "")

    cal_pct     = cal_eaten / max(cal_t, 1)
    _food_log_v = _food_log
    _is_today   = True   # always show today

    # ── Top bar (Cal AI style) ────────────────────────────────────────────────
    _HEB_MONTHS2   = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                      "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    _HEB_DAYS2     = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}
    _date_disp     = f"יום {_HEB_DAYS2[today.weekday()]}, {today.day} ב{_HEB_MONTHS2[today.month-1]}"

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:4px 2px 16px">'
        f'<div style="font-size:1.4rem;font-weight:900;color:#ffffff;'
        f'font-family:-apple-system,BlinkMacSystemFont,\"SF Pro Display\",\"Inter\",sans-serif;'
        f'letter-spacing:-.03em">BiteFit</div>'
        f'<div style="display:flex;gap:10px;align-items:center">'
        f'<div style="font-size:.72rem;color:#8892a4">{_date_disp}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Main calorie card (big number + single ring) ──────────────────────────
    _cal_diff  = cal_t - int(cal_eaten)
    _cal_over  = _cal_diff < 0
    _cal_rem   = abs(_cal_diff)
    _cal_sub   = "חריגה בקלוריות" if _cal_over else "קלוריות נותרות"
    _cal_color = "#ffffff" if cal_pct < 1.0 else "#f87171"

    # Single ring
    _rR, _rSW = 52, 10
    _rC = 2 * _math.pi * _rR
    _rFill = _rC * min(cal_pct, 1.0)
    _rGap  = _rC - _rFill
    _rColor = "#f87171" if _cal_over else "#f87171"   # always red like Cal AI

    st.markdown(
        f'<div style="background:#161b26;border-radius:24px;padding:22px 22px 18px;margin-bottom:10px;'
        f'display:flex;align-items:center;justify-content:space-between">'

        # Left: big number + sub + stats
        f'<div>'
        f'<div style="font-size:3.4rem;font-weight:900;color:{_cal_color};line-height:1;'
        f'letter-spacing:-.04em">{_cal_rem:,}</div>'
        f'<div style="font-size:.78rem;color:#6b7a95;margin-top:5px;font-weight:500">{_cal_sub}</div>'
        f'<div style="display:flex;gap:22px;margin-top:16px">'
        f'<div><div style="font-size:.58rem;color:#6b7a95;margin-bottom:3px">אכלת</div>'
        f'<div style="font-size:.92rem;font-weight:700;color:#f4f6fb">{int(cal_eaten):,}</div></div>'
        f'<div><div style="font-size:.58rem;color:#6b7a95;margin-bottom:3px">שרפת</div>'
        f'<div style="font-size:.92rem;font-weight:700;color:#f4f6fb">{int(burned):,}</div></div>'
        f'<div><div style="font-size:.58rem;color:#6b7a95;margin-bottom:3px">יעד</div>'
        f'<div style="font-size:.92rem;font-weight:700;color:#f4f6fb">{cal_t:,}</div></div>'
        f'</div></div>'

        # Right: single SVG ring
        f'<div style="position:relative;width:118px;height:118px;flex-shrink:0">'
        f'<svg width="118" height="118" viewBox="0 0 118 118">'
        f'<circle cx="59" cy="59" r="{_rR}" fill="none" stroke="#2a1515" stroke-width="{_rSW}"/>'
        f'<circle cx="59" cy="59" r="{_rR}" fill="none" stroke="{_rColor}" stroke-width="{_rSW}" '
        f'stroke-dasharray="{_rFill:.1f} {_rGap:.1f}" stroke-dashoffset="{_rC*0.25:.1f}" '
        f'stroke-linecap="round"/>'
        f'</svg>'
        f'<div style="position:absolute;inset:0;display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;text-align:center">'
        f'<div style="font-size:1.3rem;font-weight:900;color:{_rColor}">{int(cal_pct*100)}%</div>'
        f'<div style="font-size:.5rem;color:#6b7a95;margin-top:2px">מהיעד</div>'
        f'</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Macro row (3 separate mini-ring cards) ────────────────────────────────
    def _macro_card(val, target, color, label):
        pct  = min(val / max(target, 1), 1.0)
        over = val > target
        rem  = abs(int(target) - int(val))
        r, sw = 26, 6
        circ  = 2 * _math.pi * r
        fill  = circ * pct;  gap = circ - fill
        sub   = "חריגה" if over else "נותרו"
        return (
            f'<div style="flex:1;background:#161b26;border-radius:20px;'
            f'padding:14px 8px 12px;display:flex;flex-direction:column;align-items:center;gap:8px">'
            f'<div style="position:relative;width:64px;height:64px">'
            f'<svg width="64" height="64" viewBox="0 0 64 64">'
            f'<circle cx="32" cy="32" r="{r}" fill="none" stroke="#1e2433" stroke-width="{sw}"/>'
            f'<circle cx="32" cy="32" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-dasharray="{fill:.1f} {gap:.1f}" stroke-dashoffset="{circ*0.25:.1f}" stroke-linecap="round"/>'
            f'</svg>'
            f'<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">'
            f'<div style="font-size:.65rem;font-weight:800;color:{color}">{int(pct*100)}%</div>'
            f'</div></div>'
            f'<div style="text-align:center;line-height:1.3">'
            f'<div style="font-size:.95rem;font-weight:800;color:#f4f6fb">{rem}g</div>'
            f'<div style="font-size:.6rem;color:#6b7a95">{sub}</div>'
            f'<div style="font-size:.68rem;font-weight:700;color:{color};margin-top:2px">{label}</div>'
            f'</div></div>'
        )

    st.markdown(
        f'<div style="display:flex;gap:8px;margin-bottom:18px">'
        f'{_macro_card(prot_eaten,  prot_t,  "#f87171", "חלבון")}'
        f'{_macro_card(carbs_eaten, carbs_t, "#f87171", "פחמימות")}'
        f'{_macro_card(fat_eaten,   fat_t,   "#f87171", "שומן")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── "Recently uploaded" food feed ─────────────────────────────────────────
    _log_hdr_c1, _log_hdr_c2 = st.columns([3, 1])
    _log_hdr_c1.markdown(
        '<div style="font-size:.95rem;font-weight:800;color:#f4f6fb;margin-bottom:10px">'
        'אחרון שנרשם</div>',
        unsafe_allow_html=True,
    )
    with _log_hdr_c2:
        if st.button("🗑", key="clear_food_log_btn2", use_container_width=True):
            st.session_state["_confirm_clear_log"] = True

    if st.session_state.get("_confirm_clear_log"):
        st.warning("למחוק את כל נתוני המזון של היום?")
        _cc1x, _cc2x = st.columns(2)
        if _cc1x.button("כן", key="confirm_clear_yes2", use_container_width=True, type="primary"):
            _food_log_repo.clear_day(_DASH_USER, today)
            st.session_state.pop("_confirm_clear_log", None)
            st.rerun()
        if _cc2x.button("ביטול", key="confirm_clear_no2", use_container_width=True):
            st.session_state.pop("_confirm_clear_log", None)
            st.rerun()

    if _food_log_v:
        for _fe in reversed(_food_log_v):
            _fe_color = MEAL_COLOR.get(_fe.meal_type, "#545e70")
            _fe_icon  = MEAL_ICON.get(_fe.meal_type, "🍽")
            _fe_time  = datetime.fromisoformat(_fe.timestamp).strftime("%H:%M") if _fe.timestamp else ""
            _fe_macros = (
                f'{int(_fe.protein)}g חל׳&nbsp;·&nbsp;'
                f'{int(_fe.carbs)}g פח׳&nbsp;·&nbsp;'
                f'{int(_fe.fat)}g שומן'
            )
            # ── Food image via CSS background-image ───────────────────────
            # background-image silently shows nothing on failure — no broken
            # icon, no JavaScript needed. Emoji shows when image is absent.
            _fe_slug = _get_food_slug(_fe.food_name)
            _bg_img  = (
                f"url('https://spoonacular.com/cdn/ingredients_100x100/{_fe_slug}.png')"
                if _fe_slug else "none"
            )
            _icon_html = (
                f'<div style="width:50px;height:50px;border-radius:14px;flex-shrink:0;'
                f'background:#1e2433 {_bg_img} center/cover no-repeat;'
                f'display:flex;align-items:center;justify-content:center;font-size:1.3rem">'
                f'{"" if _fe_slug else _fe_icon}'
                f'</div>'
            )
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border-radius:18px;'
                f'padding:14px 16px;margin-bottom:8px;display:flex;align-items:center;gap:14px">'
                # Food image / icon
                + _icon_html +
                # Text
                f'<div style="flex:1;min-width:0">'
                f'<div style="font-size:.9rem;font-weight:700;color:#f4f6fb;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_fe.food_name}</div>'
                f'<div style="font-size:.65rem;color:#6b7a95;margin-top:4px">'
                f'<span style="color:#f87171;font-weight:700">{int(_fe.calories)} קק״ל</span>'
                f'&nbsp;·&nbsp;{_fe_macros}</div>'
                f'</div>'
                # Time
                f'<div style="font-size:.68rem;color:#6b7a95;flex-shrink:0">{_fe_time}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander("ערוך / מחק"):
                _fe_is_recipe_v = _fe.food_id.startswith("recipe_")
                _fe_food_obj_v  = _catalog.get_food_by_id(_fe.food_id) if not _fe_is_recipe_v else None
                with st.form(f"home_edit_food_v_{_fe.entry_id}", clear_on_submit=True):
                    _fe_grams_v = st.number_input(
                        "גרם" if not _fe_is_recipe_v else "מנות × 100ג",
                        min_value=1, max_value=3000,
                        value=max(1, int(_fe.grams)), step=10 if not _fe_is_recipe_v else 100,
                    )
                    _fe_meal_v = st.selectbox(
                        "ארוחה", options=list(MEAL_HEB.keys()),
                        format_func=lambda k: MEAL_HEB[k],
                        index=list(MEAL_HEB.keys()).index(_fe.meal_type)
                              if _fe.meal_type in MEAL_HEB else 0,
                        key=f"meal_sel_v_{_fe.entry_id}",
                    )
                    _ffv1, _ffv2 = st.columns(2)
                    if _ffv1.form_submit_button("שמור", use_container_width=True, type="primary"):
                        _food_log_repo.remove_entry(_DASH_USER, today, _fe.entry_id)
                        if _fe_food_obj_v:
                            _ratio_v = _fe_grams_v / 100.0
                            _nn_v = _fe_food_obj_v.nutrition_per_100g
                            _food_log_repo.add_entry(_DASH_USER, today, _FoodLogEntry(
                                food_id=_fe_food_obj_v.food_id,
                                food_name=_fe_food_obj_v.name_he,
                                grams=float(_fe_grams_v),
                                calories=round(_nn_v.calories_kcal * _ratio_v, 1),
                                protein=round(_nn_v.protein_g * _ratio_v, 1),
                                carbs=round(_nn_v.carbs_g * _ratio_v, 1),
                                fat=round(_nn_v.fat_g * _ratio_v, 1),
                                meal_type=_fe_meal_v,
                                timestamp=_fe.timestamp,
                            ))
                        else:
                            _scale_v = _fe_grams_v / max(_fe.grams, 1)
                            _food_log_repo.add_entry(_DASH_USER, today, _FoodLogEntry(
                                food_id=_fe.food_id, food_name=_fe.food_name,
                                grams=float(_fe_grams_v),
                                calories=round(_fe.calories * _scale_v, 1),
                                protein=round(_fe.protein * _scale_v, 1),
                                carbs=round(_fe.carbs * _scale_v, 1),
                                fat=round(_fe.fat * _scale_v, 1),
                                meal_type=_fe_meal_v, timestamp=_fe.timestamp,
                            ))
                        st.rerun()
                    if _ffv2.form_submit_button("מחק", use_container_width=True):
                        _food_log_repo.remove_entry(_DASH_USER, today, _fe.entry_id)
                        st.rerun()
    else:
        st.markdown(
            '<div style="background:#161b26;border-radius:18px;padding:24px;'
            'text-align:center;color:#545e70;font-size:.82rem">'
            'לא נרשמו ארוחות</div>',
            unsafe_allow_html=True,
        )

    bottom_nav("home")
    st.stop()

# ── Run Pipeline ──────────────────────────────────────────────────────────────

if run_btn:
    if not selected_food_names:
        st.error("יש לבחור לפחות מזון אחד.")
        st.stop()

    with st.spinner("מחשב תפריט יומי..."):
        errors = []

        # Step 1: User Profile
        user = UserProfile(
            user_id=_USER_ID,
            name=name or "משתמש",
            gender=gender_choice,
            date_of_birth=dob,
            height_cm=height,
            weight_kg=weight,
            activity_level=activity_choice,
            goal=goal_choice,
        )

        # Step 2: Nutrition targets
        engine = NutritionEngine()
        targets = engine.calculate_targets(user)
        target_errors = engine.validate_targets(targets)
        if target_errors:
            errors.extend(target_errors)

        # Step 2b: Workout-based adjustment (weekly plan + daily override, multi-workout)
        workout_repo = WorkoutRepository()
        todays_workouts = workout_repo.resolve_workouts_for_date(user.user_id, date.today())
        if todays_workouts:
            targets = adjust_targets_for_workouts(targets, todays_workouts, user)

        # Step 3: Food matching (uses catalog already loaded from nutrition.db)
        catalog = _get_catalog()
        food_queries = [FOOD_QUERY_MAP.get(FOOD_NAME_TO_ID[n], n) for n in selected_food_names]
        match_result = catalog.match_foods(food_queries)
        food_lookup = {f.food_id: f for f in catalog.get_all_foods()}

        # Step 4: Inventory
        inv_manager = InventoryManager()
        for food_id, qty in inventory_inputs.items():
            if qty > 0:
                inv_manager.add_item(user.user_id, food_id, qty, "gram")
        inv_state = inv_manager.get_state(user.user_id)

        # Step 5: Meal plan
        planner = MealPlanner()
        planner.set_food_lookup(food_lookup)
        run_id = f"ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        plan = planner.generate_plan(
            targets=targets,
            food_matches=match_result,
            inventory=inv_state,
            run_id=run_id,
        )
        plan_errors = planner.validate_plan(plan)
        if plan_errors:
            errors.extend(plan_errors)

        # Inventory deduction
        changeset = inv_manager.deduct_for_plan(user.user_id, plan, plan.run_id)

        # AI explanation
        ai = AILayer()
        target_expl = ai.format_targets_explanation(targets)

        # Store in session
        st.session_state["last_plan"] = {
            "user": user,
            "targets": targets,
            "target_expl": target_expl,
            "match_result": match_result,
            "plan": plan,
            "changeset": changeset,
            "food_lookup": food_lookup,
            "errors": errors,
            "todays_workouts": todays_workouts,
        }

        # ── Persist daily summary for dashboard/history ──────────────────────
        _water_today = _WaterRepo().get_daily_total(user.user_id, date.today())
        _burned = sum(w.estimated_calories_burned for w in todays_workouts)
        DailySummaryRepository().save(DailySummary(
            user_id=user.user_id,
            date=date.today().isoformat(),
            calories_eaten=plan.total_calories,
            protein_eaten=plan.total_protein,
            carbs_eaten=plan.total_carbs,
            fat_eaten=plan.total_fat,
            calories_target=targets.target_calories_kcal,
            protein_target=targets.protein_g,
            carbs_target=targets.carbs_g,
            fat_target=targets.fat_g,
            calories_burned=_burned,
            water_ml=_water_today,
        ))

# ── Display Results ───────────────────────────────────────────────────────────

if "last_plan" not in st.session_state:
    st.stop()

data = st.session_state["last_plan"]
user = data["user"]
targets = data["targets"]
plan = data["plan"]
changeset = data["changeset"]
food_lookup = data["food_lookup"]
errors = data["errors"]

if errors:
    for e in errors:
        st.error(e)

todays_workouts = data.get("todays_workouts") or []
_total_burn = sum(w.estimated_calories_burned for w in todays_workouts)
if _total_workout_count := len(todays_workouts):
    parts = []
    for w in todays_workouts:
        if w.mode == "intensity" and w.intensity:
            d = f"עצימות {w.intensity.value}"
        elif w.mode == "type" and w.workout_type:
            d = w.workout_type.value
            if w.intensity:
                d += f"/{w.intensity.value}"
        else:
            d = "אימון"
        metric = f"{w.distance_km}ק\"מ" if w.distance_km else f"{w.duration_minutes}ד׳"
        parts.append(f"{d} {metric} ({int(w.estimated_calories_burned)}קק\"ל)")
    st.info(
        f"🏋️ יום אימון ({_total_workout_count} אימונים): "
        + " · ".join(parts)
        + f" · סה\"כ +{int(_total_burn)} קק\"ל · חלוקת המאקרו הותאמה (יותר פחמימות וחלבון)"
    )

# Header summary bar
dev = plan.calorie_deviation_pct
col1, col2, col3, col4 = st.columns(4)
col1.metric("שם", user.name)
col2.metric("יעד קלורי", f"{targets.target_calories_kcal:.0f} קק\"ל")
col3.metric("קלוריות בתפריט", f"{plan.total_calories:.0f} קק\"ל")
col4.metric("סטייה", f"{dev:+.1f}%", delta_color="inverse" if dev > 0 else "normal")

st.divider()

# Tabs
tab_targets, tab_plan, tab_summary, tab_inventory = st.tabs([
    "🎯 יעדים תזונתיים",
    "🍽️ תפריט יומי",
    "📊 סיכום יומי",
    "📦 מלאי",
])

# ── Tab 1: Targets ────────────────────────────────────────────────────────────

with tab_targets:
    st.markdown("### יעדים תזונתיים")

    c1, c2, c3 = st.columns(3)
    c1.metric("BMR (מנוחה)", f"{targets.bmr_kcal:.0f} קק\"ל")
    c2.metric("TDEE (פעיל)", f"{targets.tdee_kcal:.0f} קק\"ל")
    c3.metric("יעד יומי", f"{targets.target_calories_kcal:.0f} קק\"ל")

    st.divider()

    c_p, c_c, c_f = st.columns(3)
    with c_p:
        st.markdown("#### 🥩 חלבון")
        st.metric("כמות", f"{targets.protein_g:.0f}ג")
        st.progress(int(targets.protein_pct))
        st.caption(f"{targets.protein_pct:.0f}% מהקלוריות")
    with c_c:
        st.markdown("#### 🍞 פחמימות")
        st.metric("כמות", f"{targets.carbs_g:.0f}ג")
        st.progress(int(targets.carbs_pct))
        st.caption(f"{targets.carbs_pct:.0f}% מהקלוריות")
    with c_f:
        st.markdown("#### 🥑 שומן")
        st.metric("כמות", f"{targets.fat_g:.0f}ג")
        st.progress(int(targets.fat_pct))
        st.caption(f"{targets.fat_pct:.0f}% מהקלוריות")

    st.divider()
    st.caption(f"שיטת חישוב: {targets.calculation_method}")
    with st.expander("הסבר מלא"):
        st.text(data["target_expl"])

# ── Tab 2: Meal Plan ──────────────────────────────────────────────────────────

with tab_plan:
    st.markdown(f"### תפריט יומי — {plan.plan_date}")

    if not plan.meals:
        st.warning("לא נוצרו ארוחות.")
    else:
        try:
            recipe_mgr = RecipeManager()
        except Exception:
            recipe_mgr = None

        KASHRUT_LABELS = {"meat": "🥩 בשרי", "dairy": "🧀 חלבי", "parve": "🌿 פרווה"}
        KASHRUT_COLORS = {"meat": "#ef5350", "dairy": "#42a5f5", "parve": "#66bb6a"}

        for meal in plan.meals:
            label = MEAL_LABELS.get(meal.meal_type.value, meal.meal_type.value)
            meal_type_upper = meal.meal_type.value.upper()

            with st.expander(f"{label}  —  {meal.total_calories:.0f} קק\"ל", expanded=True):
                suggestions = []
                try:
                    if recipe_mgr:
                        suggestions = recipe_mgr.recommend_meal(
                            meal_type=meal_type_upper,
                            target_calories=meal.total_calories,
                        )
                except Exception:
                    pass

                if suggestions:
                    for i, recipe in enumerate(suggestions[:3]):
                        portions = max(recipe.get("portions", 1), 1)
                        nut = recipe.get("total_nutrition", {})
                        cal = round(nut.get("calories", 0) / portions)
                        ingredients = recipe.get("ingredients", [])
                        recipe_id = recipe.get("recipe_id", "")

                        # Calorie match percentage
                        target_cal = meal.total_calories
                        match_pct = max(0, round(100 - abs(cal - target_cal) / max(target_cal, 1) * 100))

                        _img_uri = _recipe_image_data_uri(recipe.get("image_path", ""))
                        st.markdown(
                            recipe_card_html(
                                recipe,
                                image_uri=_img_uri,
                                match_pct=match_pct,
                                show_rank=(i == 0),
                            ),
                            unsafe_allow_html=True,
                        )

                        # Ingredients list + preparation instructions inline
                        with st.expander("מרכיבים והוראות הכנה", expanded=False):
                            if ingredients:
                                st.markdown("**מרכיבים:**")
                                for ing in ingredients:
                                    st.markdown(f"• {format_ingredient_display(ing)}")
                            steps = get_instructions(recipe_id)
                            if steps:
                                st.markdown("---")
                                st.markdown("**הוראות הכנה:**")
                                for step_i, step in enumerate(steps, 1):
                                    st.markdown(f"**{step_i}.** {step}")
                else:
                    st.info("אין מתכונים מתאימים לארוחה זו.")

# ── Tab 3: Daily Summary ──────────────────────────────────────────────────────

with tab_summary:
    st.markdown("### סיכום יומי")

    # Calories
    dev = plan.calorie_deviation_pct
    st.metric(
        "סה\"כ קלוריות",
        f"{plan.total_calories:.0f} קק\"ל",
        delta=f"{dev:+.1f}% מהיעד ({targets.target_calories_kcal:.0f} קק\"ל)",
        delta_color="inverse",
    )

    st.divider()

    # Macro comparison
    def macro_row(label, actual, target, unit="ג"):
        pct = (actual / target * 100) if target > 0 else 0
        col_l, col_a, col_t, col_bar = st.columns([2, 1, 1, 3])
        col_l.write(f"**{label}**")
        col_a.write(f"{actual:.0f}{unit}")
        col_t.write(f"יעד: {target:.0f}{unit}")
        col_bar.progress(min(int(pct), 100))

    macro_row("🥩 חלבון", plan.total_protein, targets.protein_g)
    macro_row("🍞 פחמימות", plan.total_carbs, targets.carbs_g)
    macro_row("🥑 שומן", plan.total_fat, targets.fat_g)

    st.divider()
    st.caption(f"מספר ארוחות: {len(plan.meals)}   |   Run ID: {plan.run_id}")

# ── Tab 4: Inventory ──────────────────────────────────────────────────────────

with tab_inventory:
    st.markdown("### ניכוי מלאי")

    if not changeset.changes:
        st.info("לא בוצע ניכוי מלאי (לא נבחרו פריטים עם מלאי).")
    else:
        for change in changeset.changes:
            food = food_lookup.get(change.food_id)
            food_name = food.name_he if food else change.food_id

            c_name, c_before, c_arrow, c_after, c_delta = st.columns([3, 1, 0.5, 1, 1])
            c_name.write(f"**{food_name}**")
            c_before.write(f"{change.quantity_before:.0f}ג")
            c_arrow.write("→")
            c_after.write(f"{change.quantity_after:.0f}ג")
            remaining_pct = (change.quantity_after / change.quantity_before * 100) if change.quantity_before > 0 else 0
            c_delta.write(f"({change.quantity_delta:+.0f}ג)")

        st.divider()
        st.success(f"✓  {len(changeset.changes)} פריטים עודכנו במלאי")
