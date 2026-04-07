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

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.agents.agent_6_ai import AILayer
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions

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
    /* RTL - only content, not Streamlit chrome */
    .main .block-container { direction: rtl; }
    section[data-testid="stSidebar"] > div { direction: rtl; }
    /* Metric cards */
    div[data-testid="metric-container"] { direction: rtl; text-align: right; }
    /* Headers */
    h1, h2, h3 { text-align: right; }
    /* Fix number inputs alignment */
    input[type="number"] { text-align: right; }
    /* Meal card style */
    .meal-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        border-right: 4px solid #2e7d32;
    }
    .meal-title {
        font-size: 18px;
        font-weight: bold;
        color: #2e7d32;
        margin-bottom: 8px;
    }
    .food-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid #e0e0e0;
        font-size: 14px;
    }
    .summary-box {
        background: #e8f5e9;
        border-radius: 10px;
        padding: 16px;
        margin-top: 8px;
    }
    .inv-tag { color: #388e3c; font-size: 12px; }
    .deviation-ok { color: #2e7d32; font-weight: bold; }
    .deviation-warn { color: #f57f17; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────────

MEAL_LABELS = {
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

# All foods in catalog
ALL_FOODS = [
    ("food_001", "חזה עוף"),
    ("food_002", "אורז לבן"),
    ("food_003", "ביצה"),
    ("food_004", "בננה"),
    ("food_005", "שמן זית"),
    ("food_006", "חלב"),
    ("food_007", "לחם מחיטה מלאה"),
    ("food_008", "עגבנייה"),
    ("food_009", "מלפפון"),
    ("food_010", "גבינת קוטג׳"),
]
FOOD_ID_TO_NAME = {fid: name for fid, name in ALL_FOODS}
FOOD_NAME_TO_ID = {name: fid for fid, name in ALL_FOODS}
FOOD_QUERY_MAP = {
    "food_001": "חזה עוף",
    "food_002": "אורז",
    "food_003": "ביצה",
    "food_004": "בננה",
    "food_005": "שמן זית",
    "food_006": "חלב",
    "food_007": "לחם",
    "food_008": "עגבנייה",
    "food_009": "מלפפון",
    "food_010": "קוטג׳",
}

# ── Sidebar — User Profile ────────────────────────────────────────────────────

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

    with st.expander("🛒 בחירת מזון ומלאי", expanded=False):
        selected_food_names = st.multiselect(
            "בחר מזונות",
            options=[name for _, name in ALL_FOODS],
            default=["חזה עוף", "אורז לבן", "ביצה", "בננה", "שמן זית", "לחם מחיטה מלאה", "עגבנייה", "גבינת קוטג׳", "מלפפון"],
        )
        st.caption("מלאי ראשוני (גרם) — השאר 0 אם אין")
        inventory_inputs = {}
        for food_name in selected_food_names:
            food_id = FOOD_NAME_TO_ID.get(food_name)
            if food_id:
                default_qty = {"food_001": 600, "food_002": 1000, "food_003": 400,
                              "food_004": 360, "food_007": 500, "food_008": 300}.get(food_id, 0)
                qty = st.number_input(
                    food_name, min_value=0, max_value=5000,
                    value=default_qty, step=50, key=f"inv_{food_id}",
                )
                inventory_inputs[food_id] = float(qty)

    st.divider()
    run_btn = st.button("▶ הפק תפריט יומי", type="primary", use_container_width=True)

# ── Main Area ─────────────────────────────────────────────────────────────────

st.markdown(f"# 🥗 מערכת תזונה חכמה")
st.caption(f"📅 {date.today().strftime('%d/%m/%Y')}")
st.divider()

if not run_btn and "last_plan" not in st.session_state:
    # מסך ברוכים הבאים
    st.markdown("""
    <div style="text-align:center; padding: 40px 0 20px 0;">
        <div style="font-size: 5em;">🥗</div>
        <h2 style="color:#e8e8ff; text-align:center">ברוכים הבאים למערכת תזונה חכמה</h2>
        <p style="color:#aaa; font-size:1.1em; text-align:center">
            המערכת תחשב עבורך תפריט יומי מותאם אישית<br>
            בהתבסס על הפרופיל, המטרות והמלאי שלך
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style="background:#1a1a2e;border-radius:12px;padding:32px 20px;text-align:center;cursor:default;border:1px solid #2a2a4a">
            <div style="font-size:3em">👤</div>
            <div style="color:#e8e8ff;font-weight:600;font-size:1.1em;margin-top:10px">פרופיל אישי</div>
            <div style="color:#888;font-size:0.85em;margin-top:6px">הזן גובה, משקל ומטרה<br>בסרגל השמאלי</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <a href="/daily_menu" target="_self" style="text-decoration:none">
        <div style="background:#1a1a2e;border-radius:12px;padding:32px 20px;text-align:center;cursor:pointer;border:1px solid #2a2a4a;transition:all 0.2s"
             onmouseover="this.style.background='#252540';this.style.borderColor='#4a4a8a'"
             onmouseout="this.style.background='#1a1a2e';this.style.borderColor='#2a2a4a'">
            <div style="font-size:3em">🍽️</div>
            <div style="color:#e8e8ff;font-weight:600;font-size:1.1em;margin-top:10px">תפריט יומי</div>
            <div style="color:#888;font-size:0.85em;margin-top:6px">קבל ארוחות מותאמות<br>עם מתכונים והוראות הכנה</div>
        </div>
        </a>""", unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <a href="/inventory" target="_self" style="text-decoration:none">
        <div style="background:#1a1a2e;border-radius:12px;padding:32px 20px;text-align:center;cursor:pointer;border:1px solid #2a2a4a;transition:all 0.2s"
             onmouseover="this.style.background='#252540';this.style.borderColor='#4a4a8a'"
             onmouseout="this.style.background='#1a1a2e';this.style.borderColor='#2a2a4a'">
            <div style="font-size:3em">📦</div>
            <div style="color:#e8e8ff;font-weight:600;font-size:1.1em;margin-top:10px">ניהול מלאי</div>
            <div style="color:#888;font-size:0.85em;margin-top:6px">סרוק קבלות והוסף<br>מוצרים למלאי האישי</div>
        </div>
        </a>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👈  מלא את הפרטים בסרגל השמאלי ולחץ **▶ הפק תפריט יומי**")
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

        # Step 3: Food matching
        catalog = FoodCatalog()
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

# Header summary bar
dev = plan.calorie_deviation_pct
dev_class = "deviation-ok" if abs(dev) <= 5 else "deviation-warn"
col1, col2, col3, col4 = st.columns(4)
col1.metric("👤 שם", user.name)
col2.metric("🎯 יעד קלורי", f"{targets.target_calories_kcal:.0f} קק\"ל")
col3.metric("🍽️ קלוריות בתפריט", f"{plan.total_calories:.0f} קק\"ל")
col4.metric("📊 סטייה", f"{dev:+.1f}%", delta_color="inverse" if dev > 0 else "normal")

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
                        protein = round(nut.get("protein", 0) / portions)
                        carbs = round(nut.get("carbs", 0) / portions)
                        fat = round(nut.get("fat", 0) / portions)
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

                        # Calculate calorie match percentage
                        target_cal = meal.total_calories
                        match_pct = max(0, round(100 - abs(cal - target_cal) / max(target_cal, 1) * 100))
                        if match_pct >= 85:
                            match_color = "#66bb6a"
                            match_icon = "✅"
                        elif match_pct >= 70:
                            match_color = "#ffa726"
                            match_icon = "🟡"
                        else:
                            match_color = "#ef5350"
                            match_icon = "🔴"

                        recipe_link = f"/recipe_detail?id={recipe_id}"

                        # Rank badge for top suggestion
                        rank_badge = ""
                        if i == 0:
                            rank_badge = '<span style="background:#4caf50;color:#fff;padding:2px 8px;border-radius:6px;font-size:0.75em;margin-left:8px">⭐ המלצה ראשית</span>'

                        st.markdown(
                            f'<div style="background:#1a1a2e;border:1px solid #333;border-radius:14px;padding:16px 18px;margin:8px 0;direction:rtl">'
                            # Header row: name + kashrut + match
                            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">'
                            f'<div>'
                            f'<span style="font-size:1.2em;font-weight:700;color:#e8e8ff">{name_he}</span>'
                            f'{rank_badge}'
                            f'</div>'
                            f'<span style="color:{kashrut_clr};font-weight:600;font-size:0.9em">{kashrut_lbl}</span>'
                            f'</div>'
                            # Subtitle
                            f'<div style="font-size:0.85em;color:#888;margin:4px 0 10px 0">{name_en} · ⏱ {prep} דק׳ · '
                            f'{match_icon} <span style="color:{match_color}">{match_pct}% התאמה</span></div>'
                            # Nutrition grid
                            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:8px 0">'
                            f'<div style="background:#2a2a00;padding:6px 10px;border-radius:8px;text-align:center;font-size:0.85em">'
                            f'<div style="color:#ffd54f;font-weight:700">{cal}</div><div style="color:#999;font-size:0.8em">קק״ל</div></div>'
                            f'<div style="background:#002a00;padding:6px 10px;border-radius:8px;text-align:center;font-size:0.85em">'
                            f'<div style="color:#81c784;font-weight:700">{protein}ג</div><div style="color:#999;font-size:0.8em">חלבון</div></div>'
                            f'<div style="background:#00202a;padding:6px 10px;border-radius:8px;text-align:center;font-size:0.85em">'
                            f'<div style="color:#64b5f6;font-weight:700">{carbs}ג</div><div style="color:#999;font-size:0.8em">פחמימות</div></div>'
                            f'<div style="background:#2a0020;padding:6px 10px;border-radius:8px;text-align:center;font-size:0.85em">'
                            f'<div style="color:#e57373;font-weight:700">{fat}ג</div><div style="color:#999;font-size:0.8em">שומן</div></div>'
                            f'</div>'
                            # Ingredients
                            f'<div style="font-size:0.82em;color:#aaa;margin-top:8px;line-height:1.6">🧾 {ingredients_display}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                        # Ingredients list + preparation instructions inline
                        with st.expander("📋 מרכיבים והוראות הכנה", expanded=False):
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
