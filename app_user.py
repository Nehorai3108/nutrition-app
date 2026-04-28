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
    page_title="GYMNET",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system ────────────────────────────────────────────────────────────
inject_global_css()

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
_profile = _profile_repo.load("ui_user_001")

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
_stored_inv = _load_inv("ui_user_001")   # list of {food_id, name_he, quantity_g}
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
        _raw_data = _workout_repo.get_workout_data("ui_user_001")
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
                        _workout_repo.remove_daily_workout("ui_user_001", _today, i)
                        st.rerun()
            if icon_button("נקה הכל", "clear", key="clear_daily_workouts", type="secondary"):
                _workout_repo.clear_daily_workouts("ui_user_001", _today)
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
                        _workout_repo.add_daily_workout("ui_user_001", _today, w)
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
                        _workout_repo.add_daily_workout("ui_user_001", _today, _new_w)
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
                _workout_repo.add_daily_workout("ui_user_001", _today, workout_entry_input)
                st.success("האימון נוסף.")
                st.rerun()

        st.page_link(
            "pages/7_weekly_workout_plan.py",
            label="📅 ערוך תכנית אימונים שבועית",
            use_container_width=True,
        )

    st.divider()

    # ── Water Tracking ───────────────────────────────────────────────────────
    _WATER_USER_ID = "ui_user_001"
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

st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;padding:4px 2px 12px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb;letter-spacing:-0.01em">GYMNET</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{date.today().strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

if not run_btn and "last_plan" not in st.session_state:
    # ── Cal AI style home dashboard ───────────────────────────────────────────
    import math as _math
    from ui import theme as _t

    _DASH_USER = "ui_user_001"
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
    _targets  = NutritionEngine().calculate_targets(_user_obj)
    cal_t     = int(summary.calories_target)   if summary and summary.calories_target   else int(_targets.bmr_kcal)
    prot_t    = int(summary.protein_target)    if summary and summary.protein_target    else int(_targets.protein_g)
    carbs_t   = int(summary.carbs_target)      if summary and summary.carbs_target      else int(_targets.carbs_g)
    fat_t     = int(summary.fat_target)        if summary and summary.fat_target        else int(_targets.fat_g)

    _cal_diff     = cal_t - int(cal_eaten)
    cal_over      = _cal_diff < 0
    cal_remaining = abs(_cal_diff)
    cal_pct       = cal_eaten / max(cal_t, 1)
    cal_color     = "#00d4aa" if cal_pct < 0.85 else ("#f59e0b" if cal_pct < 1.0 else "#f87171")

    # ── Week strip ────────────────────────────────────────────────────────────
    HEB_WD = {0:"ב׳",1:"ג׳",2:"ד׳",3:"ה׳",4:"ו׳",5:"ש׳",6:"א׳"}
    week_start = today - timedelta(days=today.weekday())
    week_strip = ""
    for i in range(7):
        d = week_start + timedelta(days=i)
        is_t = d == today
        bg    = "#f59e0b" if is_t else "#1e2433"
        fg    = "#0d0f14" if is_t else "#545e70"
        fw    = "800" if is_t else "500"
        week_strip += (
            f'<div dir="rtl" style="display:flex;flex-direction:column;align-items:center;gap:4px">'
            f'<div dir="rtl" style="font-size:0.58rem;color:#545e70;font-weight:500">{HEB_WD[d.weekday()]}</div>'
            f'<div dir="rtl" style="width:30px;height:30px;border-radius:50%;background:{bg};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:0.75rem;font-weight:{fw};color:{fg}">{d.day}</div>'
            f'</div>'
        )

    # ── Main calorie ring (big) ───────────────────────────────────────────────
    r1,cx1,cy1,sz1,sw1 = 68,80,80,160,12
    c1 = 2*_math.pi*r1
    _ring_pct = min(cal_pct, 1.0)          # visual fill capped at full circle
    f1 = c1*_ring_pct; g1 = c1-f1

    # ── Macro mini-ring helper ────────────────────────────────────────────────
    def _mrng(val, total, color, label):
        pct  = min(val/max(total,1),1.0)
        r,cx,cy,sz,sw = 24,30,30,60,5
        circ = 2*_math.pi*r; filled=circ*pct; gap=circ-filled
        rem  = max(int(total)-int(val),0)
        return (
            f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:16px;'
            f'padding:12px 6px;display:flex;flex-direction:column;align-items:center;gap:6px">'
            f'<div dir="rtl" style="position:relative;width:{sz}px;height:{sz}px">'
            f'<svg width="{sz}" height="{sz}" viewBox="0 0 {sz} {sz}">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#252d3d" stroke-width="{sw}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-dasharray="{filled:.1f} {gap:.1f}" stroke-dashoffset="{circ*0.25:.1f}" stroke-linecap="round"/>'
            f'</svg>'
            f'<div dir="rtl" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">'
            f'<div dir="rtl" style="font-size:0.6rem;font-weight:800;color:{color}">{int(pct*100)}%</div>'
            f'</div></div>'
            f'<div dir="rtl" style="text-align:center">'
            f'<div dir="rtl" style="font-size:0.8rem;font-weight:800;color:#f4f6fb">{rem}g</div>'
            f'<div dir="rtl" style="font-size:0.58rem;color:#545e70;margin-top:1px">נותר</div>'
            f'<div dir="rtl" style="font-size:0.62rem;color:#8892a4;margin-top:2px;font-weight:600">{label}</div>'
            f'</div></div>'
        )

    # ── Feed items ────────────────────────────────────────────────────────────
    MEAL_HEB = {"breakfast":"ארוחת בוקר","morning_snack":"חטיף בוקר",
                "lunch":"ארוחת צהריים","afternoon_snack":"חטיף אחה״צ",
                "dinner":"ארוחת ערב","evening_snack":"חטיף ערב"}
    MEAL_COLOR = {"breakfast":"#f59e0b","morning_snack":"#a78bfa",
                  "lunch":"#4f8ef7","afternoon_snack":"#34d399",
                  "dinner":"#f87171","evening_snack":"#818cf8"}
    feed_items_html = ""
    if _food_log:
        for entry in reversed(_food_log[-4:]):
            t_str   = entry.timestamp[11:16] if len(entry.timestamp)>15 else ""
            meal_h  = MEAL_HEB.get(entry.meal_type, entry.meal_type)
            m_color = MEAL_COLOR.get(entry.meal_type, "#545e70")
            feed_items_html += (
                f'<div dir="rtl" style="display:flex;align-items:center;gap:12px;'
                f'background:#161b26;border:1px solid #252d3d;border-radius:16px;'
                f'padding:12px 14px;margin-bottom:8px">'
                f'<div dir="rtl" style="width:4px;height:40px;border-radius:99px;background:{m_color};flex-shrink:0"></div>'
                f'<div dir="rtl" style="flex:1;min-width:0">'
                f'<div dir="rtl" style="font-size:0.88rem;font-weight:600;color:#f4f6fb;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{entry.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.72rem;color:#8892a4;margin-top:3px">'
                f'<span style="color:{cal_color};font-weight:600">{int(entry.calories)} קק״ל</span>'
                f' &nbsp;·&nbsp; {meal_h}</div>'
                f'</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70;flex-shrink:0">{t_str}</div>'
                f'</div>'
            )
    else:
        feed_items_html = (
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:16px;'
            f'padding:20px;text-align:center;color:#545e70;font-size:0.82rem">'
            f'לא נרשמו ארוחות היום</div>'
        )

    # ── Render full dashboard ─────────────────────────────────────────────────
    dashboard_html = (
        # Week strip
        f'<div dir="rtl" style="display:flex;justify-content:space-between;margin:0 2px 16px">'
        f'{week_strip}</div>'

        # Main calorie card
        f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:24px;'
        f'padding:20px 20px 18px;margin-bottom:10px;'
        f'display:flex;align-items:center;justify-content:space-between;gap:12px">'

        # Left: numbers
        f'<div>'
        f'<div dir="rtl" style="font-size:3rem;font-weight:900;color:{cal_color};line-height:1;letter-spacing:-0.04em">'
        f'{cal_remaining}</div>'
        f'<div dir="rtl" style="font-size:0.78rem;color:#8892a4;margin-top:5px;font-weight:500">'
        f'{"חריגה" if cal_over else "קלוריות נותרות"}</div>'
        f'<div dir="rtl" style="display:flex;gap:18px;margin-top:14px">'
        f'<div><div dir="rtl" style="font-size:0.62rem;color:#545e70;margin-bottom:2px">אכלת</div>'
        f'<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb">{int(cal_eaten)}</div></div>'
        f'<div><div dir="rtl" style="font-size:0.62rem;color:#545e70;margin-bottom:2px">שרפת</div>'
        f'<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb">{int(burned)}</div></div>'
        f'<div><div dir="rtl" style="font-size:0.62rem;color:#545e70;margin-bottom:2px">יעד</div>'
        f'<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb">{cal_t}</div></div>'
        f'</div></div>'

        # Right: ring
        f'<div dir="rtl" style="position:relative;width:{sz1}px;height:{sz1}px;flex-shrink:0">'
        f'<svg width="{sz1}" height="{sz1}" viewBox="0 0 {sz1} {sz1}" '
        f'style="filter:drop-shadow(0 0 8px {cal_color}55)">'
        f'<circle cx="{cx1}" cy="{cy1}" r="{r1}" fill="none" stroke="#252d3d" stroke-width="{sw1}"/>'
        f'<circle cx="{cx1}" cy="{cy1}" r="{r1}" fill="none" stroke="{cal_color}" stroke-width="{sw1}" '
        f'stroke-dasharray="{f1:.1f} {g1:.1f}" stroke-dashoffset="{c1*0.25:.1f}" stroke-linecap="round"/>'
        f'</svg>'
        f'<div dir="rtl" style="position:absolute;inset:0;display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:{cal_color}">{int(cal_pct*100)}%</div>'
        f'<div dir="rtl" style="font-size:0.5rem;color:{"#f87171" if cal_over else "#545e70"};margin-top:2px">'
        f'{"חריגה" if cal_over else "מהיעד"}</div>'
        f'</div></div>'
        f'</div>'

        # Macro row
        f'<div dir="rtl" style="display:flex;gap:8px;margin-bottom:16px">'
        f'{_mrng(prot_eaten, prot_t,  "#4f8ef7", "חלבון")}'
        f'{_mrng(carbs_eaten, carbs_t, "#f59e0b", "פחמימות")}'
        f'{_mrng(fat_eaten,  fat_t,   "#f472b6", "שומן")}'
        f'</div>'

        # Water strip
        f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:16px;'
        f'padding:10px 16px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between">'
        f'<div dir="rtl" style="display:flex;align-items:center;gap:10px">'
        f'<div dir="rtl" style="width:8px;height:8px;border-radius:50%;background:#4f8ef7"></div>'
        f'<div><div dir="rtl" style="font-size:0.78rem;font-weight:600;color:#f4f6fb">{int(water_total)} מ״ל</div>'
        f'<div dir="rtl" style="font-size:0.62rem;color:#545e70">מתוך {int(water_goal)} מ״ל</div></div>'
        f'</div>'
        f'<div dir="rtl" style="width:80px;height:6px;background:#252d3d;border-radius:99px;overflow:hidden">'
        f'<div dir="rtl" style="height:100%;width:{min(water_total/max(water_goal,1),1)*100:.0f}%;'
        f'background:#4f8ef7;border-radius:99px"></div>'
        f'</div></div>'

        # Recently logged
        f'<div dir="rtl" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
        f'<div dir="rtl" style="font-size:0.95rem;font-weight:700;color:#f4f6fb">אחרון שנרשם</div>'
        f'</div>'
        f'{feed_items_html}'
    )

    st.markdown(dashboard_html, unsafe_allow_html=True)

    # ── Water quick-add ───────────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb;margin:4px 0 8px">מים</div>',
        unsafe_allow_html=True,
    )
    _water_repo_home = _WaterRepo()
    _w1, _w2, _w3, _w4 = st.columns(4)
    if _w1.button("250 מ״ל", use_container_width=True, key="hw_250"):
        _water_repo_home.add_water_intake(_DASH_USER, 250, source="bottle")
        st.rerun()
    if _w2.button("500 מ״ל", use_container_width=True, key="hw_500"):
        _water_repo_home.add_water_intake(_DASH_USER, 500, source="bottle")
        st.rerun()
    if _w3.button("750 מ״ל", use_container_width=True, key="hw_750"):
        _water_repo_home.add_water_intake(_DASH_USER, 750, source="bottle")
        st.rerun()
    if _w4.button("1 ליטר", use_container_width=True, key="hw_1000"):
        _water_repo_home.add_water_intake(_DASH_USER, 1000, source="bottle")
        st.rerun()

    # ── Water entries edit/delete ─────────────────────────────────────────────
    _today_water_entries = _water_repo_home.get_water_intakes_for_date(_DASH_USER, today)
    if _today_water_entries:
        for _wi in reversed(_today_water_entries):
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                f'padding:10px 14px;margin-bottom:4px;display:flex;align-items:center;gap:10px">'
                f'<div dir="rtl" style="width:3px;height:28px;border-radius:99px;background:#4f8ef7;flex-shrink:0"></div>'
                f'<div dir="rtl" style="flex:1">'
                f'<div dir="rtl" style="font-size:0.84rem;font-weight:600;color:#f4f6fb">{int(_wi.amount_ml)} מ״ל</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70;margin-top:2px">{_wi.timestamp[11:16]}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("ערוך / מחק"):
                with st.form(f"edit_water_form_{_wi.water_id}", clear_on_submit=True):
                    _new_ml = st.number_input("מ״ל", min_value=50, max_value=2000,
                                              value=int(_wi.amount_ml), step=50)
                    _wf1, _wf2 = st.columns(2)
                    if _wf1.form_submit_button("שמור", use_container_width=True, type="primary"):
                        _water_repo_home.remove_water_intake(_DASH_USER, _wi.water_id,
                                                              today.isoformat())
                        _water_repo_home.add_water_intake(_DASH_USER, _new_ml, source="bottle")
                        st.rerun()
                    if _wf2.form_submit_button("מחק", use_container_width=True):
                        _water_repo_home.remove_water_intake(_DASH_USER, _wi.water_id,
                                                              today.isoformat())
                        st.rerun()

    # ── Food log edit/delete ──────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb;margin:20px 0 8px">ארוחות היום</div>',
        unsafe_allow_html=True,
    )
    _today_food = _food_log_repo.get_log(_DASH_USER, today)
    if _today_food:
        for _fe in reversed(_today_food):
            _fe_color = MEAL_COLOR.get(_fe.meal_type, "#545e70")
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                f'padding:10px 14px;margin-bottom:4px;display:flex;align-items:center;gap:10px">'
                f'<div dir="rtl" style="width:3px;height:32px;border-radius:99px;background:{_fe_color};flex-shrink:0"></div>'
                f'<div dir="rtl" style="flex:1">'
                f'<div dir="rtl" style="font-size:0.84rem;font-weight:600;color:#f4f6fb">{_fe.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70;margin-top:2px">'
                f'{MEAL_HEB.get(_fe.meal_type, _fe.meal_type)} · {_fe.grams:.0f}ג׳</div></div>'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:{_fe_color}">{int(_fe.calories)} קק״ל</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander("ערוך / מחק"):
                _fe_is_recipe = _fe.food_id.startswith("recipe_")
                _fe_food_obj  = _catalog.get_food_by_id(_fe.food_id) if not _fe_is_recipe else None
                with st.form(f"home_edit_food_{_fe.entry_id}", clear_on_submit=True):
                    _fe_grams = st.number_input(
                        "גרם" if not _fe_is_recipe else "מנות × 100ג",
                        min_value=1, max_value=3000,
                        value=int(_fe.grams), step=10 if not _fe_is_recipe else 100,
                    )
                    _fe_meal = st.selectbox(
                        "ארוחה", options=list(MEAL_HEB.keys()),
                        format_func=lambda k: MEAL_HEB[k],
                        index=list(MEAL_HEB.keys()).index(_fe.meal_type)
                              if _fe.meal_type in MEAL_HEB else 0,
                    )
                    _ff1, _ff2 = st.columns(2)
                    if _ff1.form_submit_button("שמור", use_container_width=True, type="primary"):
                        _food_log_repo.remove_entry(_DASH_USER, today, _fe.entry_id)
                        if _fe_food_obj:
                            _ratio = _fe_grams / 100.0
                            _nn = _fe_food_obj.nutrition_per_100g
                            _food_log_repo.add_entry(_DASH_USER, today, _FoodLogEntry(
                                food_id=_fe_food_obj.food_id,
                                food_name=_fe_food_obj.name_he,
                                grams=float(_fe_grams),
                                calories=round(_nn.calories_kcal * _ratio, 1),
                                protein=round(_nn.protein_g * _ratio, 1),
                                carbs=round(_nn.carbs_g * _ratio, 1),
                                fat=round(_nn.fat_g * _ratio, 1),
                                meal_type=_fe_meal,
                                timestamp=_fe.timestamp,
                            ))
                        else:
                            # recipe entry: scale proportionally
                            _scale = _fe_grams / max(_fe.grams, 1)
                            _food_log_repo.add_entry(_DASH_USER, today, _FoodLogEntry(
                                food_id=_fe.food_id, food_name=_fe.food_name,
                                grams=float(_fe_grams),
                                calories=round(_fe.calories * _scale, 1),
                                protein=round(_fe.protein * _scale, 1),
                                carbs=round(_fe.carbs * _scale, 1),
                                fat=round(_fe.fat * _scale, 1),
                                meal_type=_fe_meal, timestamp=_fe.timestamp,
                            ))
                        st.rerun()
                    if _ff2.form_submit_button("מחק", use_container_width=True):
                        _food_log_repo.remove_entry(_DASH_USER, today, _fe.entry_id)
                        st.rerun()
    else:
        st.markdown(
            '<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
            'padding:16px;text-align:center;color:#545e70;font-size:0.78rem">לא נרשמו ארוחות היום</div>',
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
            user_id="ui_user_001",
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
