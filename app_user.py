#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app_ui.py — ממשק משתמש גרפי למערכת תזונה חכמה
הרצה: streamlit run app_ui.py
"""

import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu,
    icon_button, recipe_card_html, welcome_card_html, macro_grid_html,
    kashrut_badge_html, meal_badge_html,
)
from ui.images import image_data_uri as _recipe_image_data_uri

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal, WorkoutIntensity, WorkoutType
from nutrition_app.models.workout import WorkoutEntry
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.agents.agent_2_nutrition import NutritionEngine, adjust_targets_for_workouts
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.agents.agent_6_ai import AILayer
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "nutrition.db")

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="מערכת תזונה חכמה",
    page_icon="🥗",
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

# ── Sidebar — User Profile ────────────────────────────────────────────────────

with st.sidebar:
    section_header("פרופיל משתמש", "user")

    name = st.text_input("שם מלא", value="ישראל ישראלי")

    gender_choice = st.radio(
        "מגדר",
        options=list(GENDER_LABELS.keys()),
        format_func=lambda g: GENDER_LABELS[g],
        horizontal=True,
    )

    col_h, col_w = st.columns(2)
    with col_h:
        height = st.number_input("גובה (ס\"מ)", min_value=130.0, max_value=220.0, value=178.0, step=0.5)
    with col_w:
        weight = st.number_input("משקל (ק\"ג)", min_value=35.0, max_value=200.0, value=82.0, step=0.5)

    dob = st.date_input(
        "תאריך לידה",
        value=date(1990, 5, 15),
        min_value=date(1930, 1, 1),
        max_value=date(date.today().year - 10, 1, 1),
    )

    activity_choice = st.selectbox(
        "רמת פעילות",
        options=list(ACTIVITY_LABELS.keys()),
        format_func=lambda a: ACTIVITY_LABELS[a],
        index=2,
    )

    goal_choice = st.selectbox(
        "מטרה",
        options=list(GOAL_LABELS.keys()),
        format_func=lambda g: GOAL_LABELS[g],
        index=0,
    )

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
        _today_workouts = _workout_repo.resolve_workouts_for_date("ui_user_001", _today)

        # Determine if the shown list is from the daily log (overriding) or from the weekly plan
        _raw_data = _workout_repo.get_workout_data("ui_user_001")
        _has_daily_override = _today.isoformat() in _raw_data.daily_log

        if _today_workouts:
            _src = "רשום להיום" if _has_daily_override else "מתכנית שבועית"
            st.caption(f"📋 {len(_today_workouts)} אימונים ({_src}):")
            for i, w in enumerate(_today_workouts):
                if w.mode == "intensity" and w.intensity:
                    _desc = f"עצימות {WORKOUT_INTENSITY_LABELS.get(w.intensity, w.intensity.value)}"
                elif w.mode == "type" and w.workout_type:
                    _desc = WORKOUT_TYPE_LABELS.get(w.workout_type, w.workout_type.value)
                    if w.intensity:
                        _desc += f" · עצימות {WORKOUT_INTENSITY_LABELS.get(w.intensity, w.intensity.value)}"
                else:
                    _desc = "אימון"
                _metric = f"{w.distance_km} ק\"מ" if w.distance_km else f"{w.duration_minutes} דק׳"
                col_w, col_del = st.columns([4, 1])
                col_w.markdown(f"• **{_desc}** · {_metric}")
                if _has_daily_override:
                    with col_del:
                        if icon_button("מחק", "delete", key=f"del_w_{i}",
                                       help="מחק אימון", type="secondary"):
                            _workout_repo.remove_daily_workout("ui_user_001", _today, i)
                            st.rerun()
            if _has_daily_override:
                if icon_button("נקה את כל אימוני היום", "clear",
                               key="clear_daily_workouts"):
                    _workout_repo.clear_daily_workouts("ui_user_001", _today)
                    st.rerun()
        else:
            st.caption("לא נרשמו אימונים להיום (ואין תכנית שבועית ליום זה).")

        st.markdown("**➕ הוסף אימון**")
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
            # Distance input (only for run/walk/hike) — overrides duration when > 0
            distance_sel = 0.0
            if type_sel in DISTANCE_TYPES:
                distance_sel = st.number_input(
                    "מרחק (ק\"מ) — אם מוזן, יגבר על משך",
                    min_value=0.0, max_value=200.0, value=0.0, step=0.5,
                    key="workout_distance_type",
                )
            # Optional intensity modifier for the sport
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
                _workout_repo.add_daily_workout("ui_user_001", _today, workout_entry_input)
                st.success("האימון נוסף.")
                st.rerun()

        st.caption("💡 תכנית שבועית משמשת כברירת מחדל. לוג יומי (גם אימון אחד) עוקף אותה ליום הזה.")
        st.page_link(
            "pages/7_weekly_workout_plan.py",
            label="📅 ערוך תכנית אימונים שבועית",
            use_container_width=True,
        )

    st.divider()

    with st.expander("🛒 בחירת מזון ומלאי", expanded=False):
        selected_food_names = st.multiselect(
            "בחר מזונות",
            options=[name for _, name in ALL_FOODS],
            default=_DEFAULT_FOOD_NAMES,
        )

        scanned_inv = st.session_state.get("scanned_inventory", {})
        if scanned_inv:
            st.success(f"🧾 {len(scanned_inv)} מוצרים נטענו מסריקה")
        else:
            st.caption("מלאי ראשוני (גרם) — השאר 0 אם אין")

        st.page_link("pages/2_receipt_scanner.py", label="🧾 סרוק קבלה / רשימת קניות", use_container_width=True)

        # Merge scanned foods into the selected list so they appear in inventory
        scanned_names = []
        for fid in scanned_inv:
            name = FOOD_ID_TO_NAME.get(fid)
            if name and name not in selected_food_names:
                scanned_names.append(name)
        effective_food_names = list(selected_food_names) + scanned_names

        inventory_inputs = {}
        for food_name in effective_food_names:
            food_id = FOOD_NAME_TO_ID.get(food_name)
            if food_id:
                default_qty = scanned_inv.get(
                    food_id,
                    {"food_001": 600, "food_002": 1000, "food_003": 400,
                     "food_004": 360, "food_007": 500, "food_008": 300}.get(food_id, 0)
                )
                qty = st.number_input(
                    food_name,
                    min_value=0,
                    max_value=10000,
                    value=int(default_qty),
                    step=50,
                    key=f"inv_{food_id}",
                )
                inventory_inputs[food_id] = float(qty)

    st.divider()
    run_btn = icon_button("הפק תפריט יומי", "play",
                          key="run_pipeline_btn", type="primary")

# ── Main Area ─────────────────────────────────────────────────────────────────

nav_menu(active="ראשי")
page_header(
    "מערכת תזונה חכמה",
    icon_name="plate",
    subtitle=f"היום: {date.today().strftime('%d/%m/%Y')}",
)

if not run_btn and "last_plan" not in st.session_state:
    # מסך ברוכים הבאים
    st.markdown(
        '<div class="nut-welcome-grid">'
        + welcome_card_html("/", "user", "פרופיל אישי",
                            "הזן גובה, משקל ומטרה בסרגל הצדי")
        + welcome_card_html("/daily_menu", "plate", "תפריט יומי",
                            "קבל ארוחות מותאמות עם מתכונים והוראות הכנה")
        + welcome_card_html("/inventory", "inventory", "ניהול מלאי",
                            "סרוק קבלות והוסף מוצרים למלאי האישי")
        + welcome_card_html("/weekly_workout_plan", "training", "אימונים שבועיים",
                            "תכנן את האימונים — התפריט יותאם לפי השריפה")
        + "</div>",
        unsafe_allow_html=True,
    )
    st.info("מלא את הפרטים בסרגל הצדי ולחץ **הפק תפריט יומי**")
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
