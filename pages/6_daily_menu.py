#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף תפריט יומי — המלצות ארוחות לפי בוקר, צהריים, ערב
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import streamlit as st
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager, get_recipe_inventory_match
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions
from nutrition_app.user_manager import get_all_users, load_inventory

from ui.components import (
    inject_global_css, page_header, nav_menu, recipe_card_html, meal_badge_html,
)
from ui.images import image_data_uri as _image_data_uri

st.set_page_config(page_title="תפריט יומי", page_icon="🍽️", layout="wide", initial_sidebar_state="collapsed")

inject_global_css()

@st.cache_resource
def get_mgr():
    return RecipeManager()

@st.cache_data
def load_catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "nutrition_app", "data", "foods_extended.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

recipe_mgr = get_mgr()
CATALOG = load_catalog()

def build_inventory_names(user_id: str) -> set:
    items = load_inventory(user_id)
    if not items:
        return set()
    catalog_by_id = {f["food_id"]: f for f in CATALOG}
    names = set()
    for item in items:
        food = catalog_by_id.get(item["food_id"])
        if food:
            names.add(food["name_en"].lower())
            for a in food.get("aliases_en", []):
                names.add(a.lower())
            names.add(food["name_he"].lower())
            for a in food.get("aliases_he", []):
                names.add(a.lower())
        names.add(item["name_he"].lower())
    return names

MEAL_SECTIONS = [
    ("BREAKFAST",       "ארוחת בוקר",       "ארוחה קלה ומזינה לתחילת היום"),
    ("MORNING_SNACK",   "חטיף בוקר",        "משהו קטן בין הבוקר לצהריים"),
    ("LUNCH",           "ארוחת צהריים",      "הארוחה העיקרית של היום"),
    ("AFTERNOON_SNACK", "חטיף אחה\"צ",       "אנרגיה לשעות אחר הצהריים"),
    ("DINNER",          "ארוחת ערב",         "ארוחה קלה ומאוזנת לסיום היום"),
    ("EVENING_SNACK",   "חטיף ערב",          "משהו קל לפני השינה"),
]

# ── Sidebar — בחירת לקוח ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👤 לקוח")
    all_users = get_all_users()
    if all_users:
        user_options = {u["user_id"]: u["name"] for u in all_users}
        selected_user_id = st.selectbox(
            "בחר לקוח לסינון לפי מלאי",
            options=[""] + list(user_options.keys()),
            format_func=lambda uid: "— ללא סינון מלאי —" if uid == "" else user_options[uid],
            key="menu_user_id",
        )
    else:
        selected_user_id = ""
        st.info("אין לקוחות. הוסף לקוח בדף המלאי.")

inventory_names: set = set()
if selected_user_id:
    inventory_names = build_inventory_names(selected_user_id)

# ── כותרת ─────────────────────────────────────────────────────────────────────
nav_menu(active="תפריט יומי")
page_header("תפריט יומי", icon_name="plate",
            subtitle="המלצות מתכונים לכל ארוחה — בחר מה מתאים לך היום")

if inventory_names:
    user_name = next((u["name"] for u in all_users if u["user_id"] == selected_user_id), "")
    st.success(f"🛒 מציג מתכונים לפי מלאי של **{user_name}** — {len(load_inventory(selected_user_id))} פריטים זמינים")

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
                inventory_names=inventory_names if inventory_names else None,
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

            # Inventory availability for this recipe
            inv_info = None
            inv_badge_html = ""
            if inventory_names:
                inv_info = get_recipe_inventory_match(recipe, inventory_names)
                inv_pct = inv_info["match_pct"]
                inv_clr = "#66bb6a" if inv_pct >= 80 else ("#ffa726" if inv_pct >= 50 else "#ef5350")
                inv_badge_html = f'<span style="background:{inv_clr};color:#fff;padding:1px 7px;border-radius:6px;font-size:0.72em">🛒 {inv_pct}% במלאי</span>'

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
                if inv_badge_html:
                    st.markdown(inv_badge_html, unsafe_allow_html=True)
                with st.expander("מרכיבים והוראות הכנה"):
                    if ingredients:
                        st.markdown("**מרכיבים:**")
                        for ing in ingredients:
                            if inv_info:
                                is_avail = any(
                                    ing.get("food_name_en") == a.get("food_name_en")
                                    for a in inv_info["available"]
                                )
                                icon = "✅" if is_avail else "❌"
                                st.markdown(f"{icon} {format_ingredient_display(ing)}")
                            else:
                                st.markdown(f"• {format_ingredient_display(ing)}")
                        if inv_info and inv_info["missing"]:
                            st.markdown(f"**חסר במלאי:** {', '.join(i.get('food_name','') or i.get('food_name_en','') for i in inv_info['missing'])}")
                    steps = get_instructions(recipe_id)
                    if steps:
                        st.markdown("---")
                        st.markdown("**הוראות הכנה:**")
                        for i, step in enumerate(steps, 1):
                            st.markdown(f"**{i}.** {step}")

        st.divider()
