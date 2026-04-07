#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף תפריט יומי — המלצות ארוחות לפי בוקר, צהריים, ערב
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions

st.set_page_config(page_title="תפריט יומי", page_icon="🍽️", layout="wide")

st.markdown("""
<style>
    .main .block-container { direction: rtl; }
    section[data-testid="stSidebar"] > div { direction: rtl; }
    h1,h2,h3,h4 { text-align: right; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_mgr():
    return RecipeManager()

recipe_mgr = get_mgr()

MEAL_SECTIONS = [
    ("BREAKFAST",       "🌅 ארוחת בוקר",      "ארוחה קלה ומזינה לתחילת היום"),
    ("MORNING_SNACK",   "☕ חטיף בוקר",        "משהו קטן בין הבוקר לצהריים"),
    ("LUNCH",           "🍽️ ארוחת צהריים",     "הארוחה העיקרית של היום"),
    ("AFTERNOON_SNACK", "🍎 חטיף אחה\"צ",       "אנרגיה לשעות אחר הצהריים"),
    ("DINNER",          "🌙 ארוחת ערב",         "ארוחה קלה ומאוזנת לסיום היום"),
    ("EVENING_SNACK",   "🌜 חטיף ערב",          "משהו קל לפני השינה"),
]

KASHRUT_LABELS = {"meat": "🥩 בשרי", "dairy": "🧀 חלבי", "parve": "🌿 פרווה"}
KASHRUT_COLORS = {"meat": "#ef5350", "dairy": "#42a5f5", "parve": "#66bb6a"}

# ── כותרת ─────────────────────────────────────────────────────────────────────
st.markdown("# 🍽️ תפריט יומי")
st.caption("המלצות מתכונים לכל ארוחה — בחר מה מתאים לך היום")
st.divider()

# ── בדוק אם יש תפריט מותאם אישית מהדף הראשי ────────────────────────────────
has_plan = "last_plan" in st.session_state
if has_plan:
    plan = st.session_state["last_plan"]["plan"]
    targets = st.session_state["last_plan"]["targets"]
    st.success(f"✅ מציג תפריט מותאם אישית — יעד: {targets.target_calories_kcal:.0f} קק\"ל")
    meal_calories = {m.meal_type.value.upper(): m.total_calories for m in plan.meals}
else:
    st.info("💡 מציג המלצות כלליות — כדי לקבל תפריט מותאם אישית, מלא פרופיל בדף הבית")
    meal_calories = {
        "BREAKFAST": 450, "MORNING_SNACK": 200, "LUNCH": 650,
        "AFTERNOON_SNACK": 200, "DINNER": 500, "EVENING_SNACK": 150,
    }

st.divider()

# ── ארוחות ───────────────────────────────────────────────────────────────────
for meal_key, meal_label, meal_desc in MEAL_SECTIONS:
    target_cal = meal_calories.get(meal_key, 400)

    with st.expander(f"{meal_label}  —  יעד {target_cal:.0f} קק\"ל", expanded=True):
        st.caption(meal_desc)

        try:
            suggestions = recipe_mgr.recommend_meal(
                meal_type=meal_key,
                target_calories=target_cal,
            )[:3]
        except Exception:
            suggestions = []

        if not suggestions:
            st.info("אין מתכונים מתאימים לארוחה זו.")
            continue

        cols = st.columns(len(suggestions))
        for idx, (recipe, col) in enumerate(zip(suggestions, cols)):
            portions = max(recipe.get("portions", 1), 1)
            nut = recipe.get("total_nutrition", {})
            cal   = round(nut.get("calories", 0) / portions)
            prot  = round(nut.get("protein", 0) / portions)
            carbs = round(nut.get("carbs", 0) / portions)
            fat   = round(nut.get("fat", 0) / portions)
            prep  = recipe.get("prep_time_minutes", 0)
            kash  = recipe.get("kashrut", "parve").lower()
            kash_lbl = KASHRUT_LABELS.get(kash, kash)
            kash_clr = KASHRUT_COLORS.get(kash, "#888")
            name_he   = recipe.get("name_he", "")
            name_en   = recipe.get("name_en", "")
            recipe_id = recipe.get("recipe_id", "")
            ingredients = recipe.get("ingredients", [])

            match_pct = max(0, round(100 - abs(cal - target_cal) / max(target_cal, 1) * 100))
            match_clr = "#66bb6a" if match_pct >= 85 else ("#ffa726" if match_pct >= 70 else "#ef5350")
            rank_badge = ' <span style="background:#4caf50;color:#fff;padding:1px 7px;border-radius:6px;font-size:0.72em">⭐ מומלץ</span>' if idx == 0 else ""

            with col:
                st.markdown(
                    f'<div style="background:#1a1a2e;border:1px solid #333;border-radius:14px;padding:14px;direction:rtl;height:100%">'
                    f'<div style="font-size:1.05em;font-weight:700;color:#e8e8ff">{name_he}{rank_badge}</div>'
                    f'<div style="font-size:0.78em;color:#888;margin:3px 0 8px 0">{name_en} · ⏱ {prep} דק׳ · '
                    f'<span style="color:{kash_clr}">{kash_lbl}</span> · '
                    f'<span style="color:{match_clr}">{match_pct}% התאמה</span></div>'
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:10px">'
                    f'<div style="background:#2a2a00;padding:5px;border-radius:7px;text-align:center">'
                    f'<div style="color:#ffd54f;font-weight:700;font-size:1em">{cal}</div><div style="color:#999;font-size:0.7em">קק״ל</div></div>'
                    f'<div style="background:#002a00;padding:5px;border-radius:7px;text-align:center">'
                    f'<div style="color:#81c784;font-weight:700;font-size:1em">{prot}ג</div><div style="color:#999;font-size:0.7em">חלבון</div></div>'
                    f'<div style="background:#00202a;padding:5px;border-radius:7px;text-align:center">'
                    f'<div style="color:#64b5f6;font-weight:700;font-size:1em">{carbs}ג</div><div style="color:#999;font-size:0.7em">פחמימות</div></div>'
                    f'<div style="background:#2a0020;padding:5px;border-radius:7px;text-align:center">'
                    f'<div style="color:#e57373;font-weight:700;font-size:1em">{fat}ג</div><div style="color:#999;font-size:0.7em">שומן</div></div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                with st.expander("📋 מרכיבים והוראות"):
                    if ingredients:
                        st.markdown("**מרכיבים:**")
                        for ing in ingredients:
                            st.markdown(f"• {format_ingredient_display(ing)}")
                    steps = get_instructions(recipe_id)
                    if steps:
                        st.markdown("---")
                        st.markdown("**הוראות הכנה:**")
                        for i, step in enumerate(steps, 1):
                            st.markdown(f"**{i}.** {step}")

        st.divider()

st.page_link("app_ui.py", label="← חזור לדף הבית", use_container_width=False)
