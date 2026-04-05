#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app_ui.py — Nutrition app dashboard.
Run: streamlit run app_ui.py
"""

import sys
import os
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal, FoodCategory, MealType
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.agents.agent_6_ai import AILayer
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display

from nutrition_app.agents.agent_5_planner.meal_planner import MEAL_CATEGORY_RULES

from ui_helpers import (
    PLANS_DIR,
    HEBREW_DAY_NAMES,
    save_plan_to_disk,
    load_plan_from_file,
    scan_history_plans,
    reconstruct_plan_from_dict,
    generate_weekly_plans,
    render_meal_card_html,
    render_day_card_html,
)

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="מערכת תזונה חכמה",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── RTL + custom style ───────────────────────────────────────────────────────

st.markdown("""
<style>
    /* RTL */
    .main .block-container { direction: rtl; }
    section[data-testid="stSidebar"] > div { direction: rtl; }
    div[data-testid="metric-container"] { direction: rtl; text-align: right; }
    h1, h2, h3 { text-align: right; }
    input[type="number"] { text-align: right; }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.05em;
        padding: 10px 24px;
        border-radius: 10px 10px 0 0;
    }

    /* Custom metric card */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 14px;
        padding: 18px;
        text-align: center;
        border: 1px solid #333;
    }
    .metric-card .value {
        font-size: 1.8em;
        font-weight: 700;
        margin: 4px 0;
    }
    .metric-card .label {
        font-size: 0.85em;
        color: #999;
    }

    /* History row */
    .history-row {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        border: 1px solid #2a2a3e;
        direction: rtl;
        transition: border-color 0.2s;
    }
    .history-row:hover {
        border-color: #4caf50;
    }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────────

MEAL_LABELS_DISPLAY = {
    "breakfast":       "🌅 ארוחת בוקר",
    "morning_snack":   "☕ חטיף בוקר",
    "lunch":           "🍽️ ארוחת צהריים",
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
    Goal.LOSE_WEIGHT:  "🔽 ירידה במשקל",
    Goal.MAINTAIN:     "⚖️ שמירה על משקל",
    Goal.GAIN_WEIGHT:  "🔼 עלייה במשקל",
}

GENDER_LABELS = {
    Gender.MALE:   "זכר",
    Gender.FEMALE: "נקבה",
}

# ── Food Catalog (loaded once) ───────────────────────────────────────────────

_catalog_instance = FoodCatalog()
ALL_CATALOG_FOODS = _catalog_instance.get_all_foods()
FOOD_LOOKUP = {f.food_id: f for f in ALL_CATALOG_FOODS}
FOODS_BY_CATEGORY = {}
for _f in ALL_CATALOG_FOODS:
    FOODS_BY_CATEGORY.setdefault(_f.category, []).append(_f)

# Sort foods within each category by Hebrew name
for _cat in FOODS_BY_CATEGORY:
    FOODS_BY_CATEGORY[_cat].sort(key=lambda f: f.name_he)

CATEGORY_LABELS = {
    FoodCategory.PROTEIN:      "🥩 חלבון",
    FoodCategory.CARBOHYDRATE: "🍚 פחמימות",
    FoodCategory.FAT:          "🫒 שומן",
    FoodCategory.VEGETABLE:    "🥬 ירקות",
    FoodCategory.FRUIT:        "🍎 פירות",
    FoodCategory.DAIRY:        "🧀 חלבי",
    FoodCategory.GRAIN:        "🌾 דגנים",
    FoodCategory.LEGUME:       "🫘 קטניות",
    FoodCategory.NUT_SEED:     "🥜 אגוזים וזרעים",
    FoodCategory.CONDIMENT:    "🧂 תבלינים",
    FoodCategory.BEVERAGE:     "☕ משקאות",
    FoodCategory.OTHER:        "📦 אחר",
}

MEAL_SELECTOR_LABELS = {
    MealType.BREAKFAST:       "🌅 ארוחת בוקר",
    MealType.MORNING_SNACK:   "☕ חטיף בוקר",
    MealType.LUNCH:           "🍽️ ארוחת צהריים",
    MealType.AFTERNOON_SNACK: "🍎 חטיף אחה\"צ",
    MealType.DINNER:          "🌙 ארוחת ערב",
    MealType.EVENING_SNACK:   "🌜 חטיף ערב",
}

# Default foods to pre-select on first load
DEFAULT_FOOD_IDS = [
    "food_001", "food_002", "food_003", "food_004", "food_005",
    "food_007", "food_008", "food_009", "food_010",
]

KASHRUT_LABELS = {"meat": "🥩 בשרי", "dairy": "🧀 חלבי", "parve": "🌿 פרווה"}
KASHRUT_COLORS = {"meat": "#ef5350", "dairy": "#42a5f5", "parve": "#66bb6a"}


# ── Sidebar — User Profile ───────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 👤 פרופיל משתמש")
    st.divider()

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
    st.markdown("## 🛒 בחירת מזון")

    # ── Initialize selected foods in session state ──
    if "selected_foods" not in st.session_state:
        st.session_state["selected_foods"] = {
            fid: FOOD_LOOKUP[fid] for fid in DEFAULT_FOOD_IDS if fid in FOOD_LOOKUP
        }

    # ── Step 1: Meal type ──
    meal_type_pick = st.selectbox(
        "① בחר ארוחה",
        options=list(MEAL_SELECTOR_LABELS.keys()),
        format_func=lambda m: MEAL_SELECTOR_LABELS[m],
        key="food_sel_meal",
    )

    # ── Step 2: Food category (filtered by meal type rules) ──
    valid_categories = MEAL_CATEGORY_RULES.get(meal_type_pick, list(FoodCategory))
    # Only show categories that have foods in catalog
    available_categories = [c for c in valid_categories if c in FOODS_BY_CATEGORY]

    category_pick = st.selectbox(
        "② בחר קטגוריה",
        options=available_categories,
        format_func=lambda c: CATEGORY_LABELS.get(c, c.value),
        key="food_sel_cat",
    )

    # ── Step 3: Specific foods in category ──
    foods_in_cat = FOODS_BY_CATEGORY.get(category_pick, [])
    # Filter out already-selected foods
    already_selected_ids = set(st.session_state["selected_foods"].keys())
    available_foods = [f for f in foods_in_cat if f.food_id not in already_selected_ids]

    if available_foods:
        food_pick_names = st.multiselect(
            "③ בחר מזונות",
            options=[f.name_he for f in available_foods],
            key="food_sel_items",
        )

        if food_pick_names and st.button("➕ הוסף לתפריט", use_container_width=True):
            name_to_food = {f.name_he: f for f in available_foods}
            for fn in food_pick_names:
                food_obj = name_to_food.get(fn)
                if food_obj:
                    st.session_state["selected_foods"][food_obj.food_id] = food_obj
            st.rerun()
    else:
        st.caption("כל המזונות בקטגוריה זו כבר נבחרו ✓")

    # ── Display selected foods with remove buttons ──
    selected = st.session_state["selected_foods"]
    if selected:
        st.divider()
        st.markdown(f"### 🧾 מזונות שנבחרו ({len(selected)})")
        for fid, food_obj in list(selected.items()):
            cat_label = CATEGORY_LABELS.get(food_obj.category, "")
            col_name, col_rm = st.columns([4, 1])
            col_name.markdown(
                f'<span style="font-size:0.9em">{food_obj.name_he} '
                f'<span style="color:#888;font-size:0.78em">{cat_label}</span></span>',
                unsafe_allow_html=True,
            )
            if col_rm.button("✕", key=f"rm_{fid}", use_container_width=True):
                del st.session_state["selected_foods"][fid]
                st.rerun()

    # Derive names list for pipeline compatibility
    selected_food_names = [f.name_he for f in st.session_state["selected_foods"].values()]

    st.divider()
    st.markdown("## 📦 מלאי ראשוני (גרם)")
    st.caption("השאר 0 אם אין מלאי")

    inventory_inputs = {}
    default_inv = {"food_001": 600, "food_002": 1000, "food_003": 400,
                   "food_004": 360, "food_007": 500, "food_008": 300}
    for food_id, food_obj in st.session_state["selected_foods"].items():
        default_qty = default_inv.get(food_id, 0)
        qty = st.number_input(
            food_obj.name_he,
            min_value=0, max_value=5000, value=default_qty, step=50,
            key=f"inv_{food_id}",
        )
        inventory_inputs[food_id] = float(qty)

    st.divider()
    run_daily_btn = st.button("▶ הפק תפריט יומי", type="primary", use_container_width=True)
    run_weekly_btn = st.button("📅 הפק תפריט שבועי", use_container_width=True)

    st.divider()
    st.page_link("pages/2_recipes.py", label="📖 מתכונים", use_container_width=True)
    st.page_link("pages/3_recipe_detail.py", label="🍽 פרטי מתכון", use_container_width=True)
    st.page_link("pages/1_agents_dashboard.py", label="🤖 דאשבורד סוכנים", use_container_width=True)


# ── Shared Pipeline Runner ───────────────────────────────────────────────────

def _run_pipeline():
    """Run steps 1-4 of the nutrition pipeline. Returns tuple or None on error."""
    if not selected_food_names:
        st.error("יש לבחור לפחות מזון אחד.")
        return None

    errors = []

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

    engine = NutritionEngine()
    targets = engine.calculate_targets(user)
    target_errors = engine.validate_targets(targets)
    if target_errors:
        errors.extend(target_errors)

    catalog = FoodCatalog()
    food_queries = list(selected_food_names)
    match_result = catalog.match_foods(food_queries)
    food_lookup = dict(FOOD_LOOKUP)

    inv_manager = InventoryManager()
    for food_id, qty_val in inventory_inputs.items():
        if qty_val > 0:
            inv_manager.add_item(user.user_id, food_id, qty_val, "gram")
    inv_state = inv_manager.get_state(user.user_id)

    return user, targets, match_result, food_lookup, inv_state, inv_manager, errors


# ── Handle Button Clicks ─────────────────────────────────────────────────────

if run_daily_btn:
    with st.spinner("מחשב תפריט יומי..."):
        result = _run_pipeline()
        if result:
            user_obj, targets, match_result, food_lookup, inv_state, inv_manager, errors = result

            planner = MealPlanner()
            planner.set_food_lookup(food_lookup)
            planner.load_extended_catalog()
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

            changeset = inv_manager.deduct_for_plan(user_obj.user_id, plan, plan.run_id)

            ai = AILayer()
            target_expl = ai.format_targets_explanation(targets)

            save_plan_to_disk(plan, suffix="daily")

            st.session_state["last_plan"] = {
                "user": user_obj,
                "targets": targets,
                "target_expl": target_expl,
                "match_result": match_result,
                "plan": plan,
                "changeset": changeset,
                "food_lookup": food_lookup,
                "errors": errors,
            }
            st.session_state["gen_daily_done"] = True
            st.session_state.pop("history_plans", None)

if run_weekly_btn:
    with st.spinner("מחשב תפריט שבועי — 7 ימים..."):
        result = _run_pipeline()
        if result:
            user_obj, targets, match_result, food_lookup, inv_state, inv_manager, errors = result

            run_id_prefix = f"week_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            plans = generate_weekly_plans(
                targets=targets,
                food_matches=match_result,
                inventory=inv_state,
                food_lookup=food_lookup,
                run_id_prefix=run_id_prefix,
            )

            st.session_state["weekly_plans"] = plans
            st.session_state["weekly_targets"] = targets
            st.session_state["weekly_user"] = user_obj
            st.session_state["gen_weekly_done"] = True
            st.session_state.pop("history_plans", None)


# ── Main Area ────────────────────────────────────────────────────────────────

st.markdown("# 🥗 מערכת תזונה חכמה")
st.caption(f"תאריך: {date.today().strftime('%d/%m/%Y')}")

tab_today, tab_weekly, tab_history = st.tabs([
    "🍽️ תפריט היום",
    "📅 תפריט שבועי",
    "📋 היסטוריה",
])


# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Today's Plan
# ══════════════════════════════════════════════════════════════════════════════

with tab_today:
    if st.session_state.pop("gen_daily_done", False):
        st.toast("התפריט היומי נוצר בהצלחה!", icon="✅")
        st.balloons()

    if "last_plan" not in st.session_state:
        st.info("מלא את הפרטים בסרגל הצד ולחץ **הפק תפריט יומי**.")
    else:
        data = st.session_state["last_plan"]
        user_d = data["user"]
        targets = data["targets"]
        plan = data["plan"]
        changeset = data["changeset"]
        food_lookup = data["food_lookup"]
        errors = data["errors"]

        if errors:
            for e in errors:
                st.error(e)

        # ── Top metrics ──
        dev = plan.calorie_deviation_pct
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👤 שם", user_d.name)
        c2.metric("🎯 יעד קלורי", f"{targets.target_calories_kcal:.0f} קק\"ל")
        c3.metric("🍽️ בתפריט", f"{plan.total_calories:.0f} קק\"ל")
        c4.metric("📊 סטייה", f"{dev:+.1f}%",
                  delta_color="inverse" if dev > 0 else "normal")

        st.divider()

        # ── Two-column layout ──
        col_main, col_side = st.columns([5, 2])

        with col_main:
            # Targets summary
            with st.expander("🎯 יעדים תזונתיים", expanded=False):
                tc1, tc2, tc3 = st.columns(3)
                tc1.metric("BMR (מנוחה)", f"{targets.bmr_kcal:.0f} קק\"ל")
                tc2.metric("TDEE (פעיל)", f"{targets.tdee_kcal:.0f} קק\"ל")
                tc3.metric("יעד יומי", f"{targets.target_calories_kcal:.0f} קק\"ל")
                st.caption(f"שיטת חישוב: {targets.calculation_method}")
                with st.expander("הסבר מלא"):
                    st.text(data["target_expl"])

            st.markdown("### ארוחות היום")

            # Recipe manager
            try:
                recipe_mgr = RecipeManager()
            except Exception:
                recipe_mgr = None

            for meal in plan.meals:
                st.markdown(render_meal_card_html(meal), unsafe_allow_html=True)

                # Recipe suggestions
                suggestions = []
                try:
                    if recipe_mgr:
                        suggestions = recipe_mgr.recommend_meal(
                            meal_type=meal.meal_type.value.upper(),
                            target_calories=meal.total_calories,
                        )
                except Exception:
                    pass

                if suggestions:
                    with st.expander(f"💡 מתכונים מומלצים ({len(suggestions[:3])})", expanded=False):
                        for i, recipe in enumerate(suggestions[:3]):
                            portions = max(recipe.get("portions", 1), 1)
                            nut = recipe.get("total_nutrition", {})
                            cal = round(nut.get("calories", 0) / portions)
                            protein = round(nut.get("protein", 0) / portions)
                            carbs_val = round(nut.get("carbs", 0) / portions)
                            fat_val = round(nut.get("fat", 0) / portions)
                            prep = recipe.get("prep_time_minutes", 0)
                            kashrut_raw = recipe.get("kashrut", "parve").lower()
                            kashrut_lbl = KASHRUT_LABELS.get(kashrut_raw, kashrut_raw)
                            kashrut_clr = KASHRUT_COLORS.get(kashrut_raw, "#555")
                            ingredients = recipe.get("ingredients", [])
                            ingredients_display = " · ".join(
                                format_ingredient_display(ing) for ing in ingredients
                            )
                            name_he = recipe.get("name_he", "")
                            name_en = recipe.get("name_en", "")
                            recipe_id = recipe.get("recipe_id", "")

                            target_cal = meal.total_calories
                            match_pct = max(0, round(100 - abs(cal - target_cal) / max(target_cal, 1) * 100))
                            if match_pct >= 85:
                                match_color, match_icon = "#66bb6a", "✅"
                            elif match_pct >= 70:
                                match_color, match_icon = "#ffa726", "🟡"
                            else:
                                match_color, match_icon = "#ef5350", "🔴"

                            rank_badge = ""
                            if i == 0:
                                rank_badge = ('<span style="background:#4caf50;color:#fff;padding:2px 8px;'
                                              'border-radius:6px;font-size:0.75em;margin-left:8px">'
                                              '⭐ המלצה ראשית</span>')

                            recipe_link = f"/recipe_detail?id={recipe_id}"

                            st.markdown(
                                f'<div style="background:#1a1a2e;border:1px solid #333;border-radius:14px;'
                                f'padding:16px 18px;margin:8px 0;direction:rtl">'
                                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                                f'flex-wrap:wrap;gap:6px">'
                                f'<div><span style="font-size:1.1em;font-weight:700;color:#e8e8ff">'
                                f'{name_he}</span>{rank_badge}</div>'
                                f'<span style="color:{kashrut_clr};font-weight:600;font-size:0.9em">'
                                f'{kashrut_lbl}</span></div>'
                                f'<div style="font-size:0.82em;color:#888;margin:4px 0 8px 0">'
                                f'{name_en} · ⏱ {prep} דק׳ · '
                                f'{match_icon} <span style="color:{match_color}">{match_pct}% התאמה</span></div>'
                                f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:6px 0">'
                                f'<div style="background:#2a2a00;padding:5px 8px;border-radius:8px;text-align:center;'
                                f'font-size:0.82em"><div style="color:#ffd54f;font-weight:700">{cal}</div>'
                                f'<div style="color:#999;font-size:0.78em">קק״ל</div></div>'
                                f'<div style="background:#002a00;padding:5px 8px;border-radius:8px;text-align:center;'
                                f'font-size:0.82em"><div style="color:#81c784;font-weight:700">{protein}ג</div>'
                                f'<div style="color:#999;font-size:0.78em">חלבון</div></div>'
                                f'<div style="background:#00202a;padding:5px 8px;border-radius:8px;text-align:center;'
                                f'font-size:0.82em"><div style="color:#64b5f6;font-weight:700">{carbs_val}ג</div>'
                                f'<div style="color:#999;font-size:0.78em">פחמימות</div></div>'
                                f'<div style="background:#2a0020;padding:5px 8px;border-radius:8px;text-align:center;'
                                f'font-size:0.82em"><div style="color:#e57373;font-weight:700">{fat_val}ג</div>'
                                f'<div style="color:#999;font-size:0.78em">שומן</div></div></div>'
                                f'<div style="font-size:0.8em;color:#aaa;margin-top:6px;line-height:1.6">'
                                f'🧾 {ingredients_display}</div>'
                                f'<div style="margin-top:8px;text-align:left">'
                                f'<a href="{recipe_link}" target="_self" style="color:#90caf9;font-size:0.85em;'
                                f'text-decoration:none;border:1px solid #90caf9;padding:4px 12px;border-radius:8px">'
                                f'📖 צפה במתכון</a></div></div>',
                                unsafe_allow_html=True,
                            )

        with col_side:
            st.markdown("### 📊 סיכום יומי")

            # Macro progress
            def _macro_bar(label, icon, actual, target, color):
                pct = (actual / target * 100) if target > 0 else 0
                pct_clamped = min(int(pct), 100)
                diff = actual - target
                diff_color = "#66bb6a" if abs(diff) <= target * 0.1 else "#ffa726"
                st.markdown(f"**{icon} {label}**")
                st.progress(pct_clamped)
                st.caption(f"{actual:.0f}g / {target:.0f}g ({pct:.0f}%)")

            _macro_bar("חלבון", "🥩", plan.total_protein, targets.protein_g, "#4caf50")
            _macro_bar("פחמימות", "🍞", plan.total_carbs, targets.carbs_g, "#2196f3")
            _macro_bar("שומן", "🥑", plan.total_fat, targets.fat_g, "#f44336")

            st.divider()

            # Inventory changes
            st.markdown("### 📦 מלאי")
            if not changeset.changes:
                st.info("לא בוצע ניכוי מלאי.")
            else:
                for change in changeset.changes:
                    food = food_lookup.get(change.food_id)
                    food_name_inv = food.name_he if food else change.food_id
                    remaining_pct = (change.quantity_after / change.quantity_before * 100) if change.quantity_before > 0 else 0
                    st.markdown(
                        f'<div style="background:#1a1a2e;border-radius:8px;padding:8px 12px;margin:4px 0;'
                        f'border:1px solid #2a2a3e;direction:rtl;font-size:0.88em">'
                        f'<div style="display:flex;justify-content:space-between">'
                        f'<span style="color:#e0e0e0">{food_name_inv}</span>'
                        f'<span style="color:#ffa726">{change.quantity_delta:+.0f}g</span></div>'
                        f'<div style="display:flex;justify-content:space-between;color:#888;font-size:0.85em">'
                        f'<span>{change.quantity_before:.0f}g → {change.quantity_after:.0f}g</span>'
                        f'<span>{remaining_pct:.0f}% נותר</span></div></div>',
                        unsafe_allow_html=True,
                    )
                st.success(f"✓ {len(changeset.changes)} פריטים עודכנו")

            st.divider()
            st.caption(f"ארוחות: {len(plan.meals)} | Run: {plan.run_id}")


# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Weekly Plan
# ══════════════════════════════════════════════════════════════════════════════

with tab_weekly:
    if st.session_state.pop("gen_weekly_done", False):
        st.toast("תפריט שבועי נוצר בהצלחה!", icon="📅")
        st.balloons()

    if "weekly_plans" not in st.session_state:
        st.info("לחץ על **הפק תפריט שבועי** בסרגל הצד.")
    else:
        plans_w = st.session_state["weekly_plans"]
        targets_w = st.session_state["weekly_targets"]

        # Weekly summary metrics
        avg_cal = sum(p.total_calories for p in plans_w) / 7
        avg_dev = sum(abs(p.calorie_deviation_pct) for p in plans_w) / 7
        avg_protein = sum(p.total_protein for p in plans_w) / 7
        avg_carbs = sum(p.total_carbs for p in plans_w) / 7
        avg_fat = sum(p.total_fat for p in plans_w) / 7

        wc1, wc2, wc3, wc4 = st.columns(4)
        wc1.metric("📊 ממוצע קלוריות", f"{avg_cal:.0f} קק\"ל")
        wc2.metric("🎯 סטייה ממוצעת", f"{avg_dev:.1f}%")
        wc3.metric("🥩 ממוצע חלבון", f"{avg_protein:.0f}g")
        wc4.metric("📅 ימים", "7")

        st.divider()

        # 7-column day grid
        cols_w = st.columns(7)
        active_day = st.session_state.get("active_week_day", 0)

        for i, col in enumerate(cols_w):
            with col:
                p = plans_w[i]
                d = date.today() + timedelta(days=i)
                day_name = HEBREW_DAY_NAMES.get(d.weekday(), "")
                is_sel = (i == active_day)

                st.markdown(
                    render_day_card_html(
                        day_name=day_name,
                        day_date=d,
                        calories=p.total_calories,
                        deviation=p.calorie_deviation_pct,
                        protein=p.total_protein,
                        carbs=p.total_carbs,
                        fat=p.total_fat,
                        is_selected=is_sel,
                    ),
                    unsafe_allow_html=True,
                )
                if st.button(
                    "📖 פרטים" if not is_sel else "✅ נבחר",
                    key=f"wd_{i}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary",
                ):
                    st.session_state["active_week_day"] = i
                    st.rerun()

        # Selected day detail
        st.divider()
        sel_plan = plans_w[active_day]
        sel_date = date.today() + timedelta(days=active_day)
        sel_day_name = HEBREW_DAY_NAMES.get(sel_date.weekday(), "")

        st.markdown(f"### {sel_day_name} — {sel_date.strftime('%d/%m/%Y')}")

        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("קלוריות", f"{sel_plan.total_calories:.0f} קק\"ל")
        dc2.metric("חלבון", f"{sel_plan.total_protein:.0f}g")
        dc3.metric("פחמימות", f"{sel_plan.total_carbs:.0f}g")
        dc4.metric("שומן", f"{sel_plan.total_fat:.0f}g")

        dev_w = sel_plan.calorie_deviation_pct
        dev_color_w = "#66bb6a" if abs(dev_w) <= 5 else "#ffa726" if abs(dev_w) <= 10 else "#ef5350"
        st.markdown(
            f'<div style="text-align:right;color:{dev_color_w};font-weight:600;margin-bottom:12px">'
            f'סטייה מהיעד: {dev_w:+.1f}%</div>',
            unsafe_allow_html=True,
        )

        for meal in sel_plan.meals:
            st.markdown(render_meal_card_html(meal), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — History
# ══════════════════════════════════════════════════════════════════════════════

with tab_history:
    col_ht, col_hr = st.columns([4, 1])
    col_ht.markdown("### 📋 היסטוריית תפריטים")
    if col_hr.button("🔄 רענן", use_container_width=True):
        st.session_state.pop("history_plans", None)
        st.session_state.pop("selected_history", None)
        st.rerun()

    if "history_plans" not in st.session_state:
        st.session_state["history_plans"] = scan_history_plans()

    history = st.session_state["history_plans"]

    if not history:
        st.info("אין תפריטים שמורים עדיין. הפק תפריט יומי או שבועי כדי להתחיל.")
    else:
        st.caption(f"נמצאו {len(history)} תפריטים שמורים")

        for i, entry in enumerate(history):
            dev_h = entry.get("deviation", 0)
            dev_h_color = "#66bb6a" if abs(dev_h) <= 5 else "#ffa726" if abs(dev_h) <= 10 else "#ef5350"
            cal_h = entry.get("total_calories", 0)
            target_h = entry.get("target_calories", 0)

            cols_h = st.columns([2.5, 1.5, 1, 1, 1, 1])
            cols_h[0].markdown(f"**{entry.get('plan_date', 'N/A')}**")
            cols_h[1].markdown(f"{cal_h:.0f} קק\"ל")
            cols_h[2].markdown(f"P: {entry.get('total_protein', 0):.0f}")
            cols_h[3].markdown(f"C: {entry.get('total_carbs', 0):.0f}")
            cols_h[4].markdown(f"F: {entry.get('total_fat', 0):.0f}")
            if cols_h[5].button("👁 צפה", key=f"hist_{i}", use_container_width=True):
                st.session_state["selected_history"] = entry["filename"]
                st.rerun()

        # Detail view for selected plan
        selected_hist = st.session_state.get("selected_history")
        if selected_hist:
            st.divider()
            filepath_h = os.path.join(PLANS_DIR, selected_hist)
            try:
                plan_data_h = load_plan_from_file(filepath_h)
                plan_h = reconstruct_plan_from_dict(plan_data_h)

                col_back, col_title_h = st.columns([1, 5])
                if col_back.button("← חזור"):
                    st.session_state.pop("selected_history", None)
                    st.rerun()
                col_title_h.markdown(f"#### תפריט מתאריך {plan_h.plan_date}")

                hc1, hc2, hc3, hc4 = st.columns(4)
                hc1.metric("קלוריות", f"{plan_h.total_calories:.0f} קק\"ל")
                hc2.metric("יעד", f"{plan_h.target_calories_kcal:.0f} קק\"ל")
                hc3.metric("סטייה", f"{plan_h.calorie_deviation_pct:+.1f}%")
                hc4.metric("ארוחות", len(plan_h.meals))

                for meal_h in plan_h.meals:
                    st.markdown(render_meal_card_html(meal_h), unsafe_allow_html=True)

            except (FileNotFoundError, KeyError, ValueError) as exc:
                st.error(f"שגיאה בטעינת תפריט: {exc}")
