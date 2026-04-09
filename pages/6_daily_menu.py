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

from ui.components import (
    inject_global_css, page_header, nav_menu, recipe_card_html, meal_badge_html,
)
from ui.images import image_data_uri as _image_data_uri

st.set_page_config(page_title="תפריט יומי", page_icon="🍽️", layout="wide", initial_sidebar_state="collapsed")

inject_global_css()

@st.cache_resource
def get_mgr():
    return RecipeManager()

recipe_mgr = get_mgr()

MEAL_SECTIONS = [
    ("BREAKFAST",       "ארוחת בוקר",       "ארוחה קלה ומזינה לתחילת היום"),
    ("MORNING_SNACK",   "חטיף בוקר",        "משהו קטן בין הבוקר לצהריים"),
    ("LUNCH",           "ארוחת צהריים",      "הארוחה העיקרית של היום"),
    ("AFTERNOON_SNACK", "חטיף אחה\"צ",       "אנרגיה לשעות אחר הצהריים"),
    ("DINNER",          "ארוחת ערב",         "ארוחה קלה ומאוזנת לסיום היום"),
    ("EVENING_SNACK",   "חטיף ערב",          "משהו קל לפני השינה"),
]

# ── כותרת ─────────────────────────────────────────────────────────────────────
nav_menu(active="תפריט יומי")
page_header("תפריט יומי", icon_name="plate",
            subtitle="המלצות מתכונים לכל ארוחה — בחר מה מתאים לך היום")

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
    badge_html = meal_badge_html(meal_key.lower())

    with st.expander(f"{meal_label}  —  יעד {target_cal:.0f} קק\"ל", expanded=True):
        st.markdown(badge_html, unsafe_allow_html=True)
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
            cal = round(nut.get("calories", 0) / portions)
            recipe_id = recipe.get("recipe_id", "")
            ingredients = recipe.get("ingredients", [])

            match_pct = max(0, round(100 - abs(cal - target_cal) / max(target_cal, 1) * 100))
            _img_uri = _image_data_uri(recipe.get("image_path", ""))

            with col:
                st.markdown(
                    recipe_card_html(
                        recipe,
                        image_uri=_img_uri,
                        match_pct=match_pct,
                        show_rank=(idx == 0),
                    ),
                    unsafe_allow_html=True,
                )
                with st.expander("מרכיבים והוראות הכנה"):
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
