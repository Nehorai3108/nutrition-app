#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף מתכונים — חיפוש וצפייה במתכונים
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu, recipe_card_html,
)
from ui.images import image_data_uri

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="מתכונים",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_css()
nav_menu(active="מתכונים")
page_header("מתכונים", icon_name="recipe",
            subtitle="חיפוש וצפייה במתכונים")

# ── Load recipe manager ──────────────────────────────────────────────────────

@st.cache_resource
def get_recipe_manager():
    return RecipeManager()

manager = get_recipe_manager()
stats = manager.get_stats()

# ── Stats bar ────────────────────────────────────────────────────────────────

st.markdown("---")
stat_cols = st.columns(5)
stat_cols[0].metric("סה״כ מתכונים", stats.get("total", 0))
stat_cols[1].metric("בשרי", stats.get("by_kashrut", {}).get("meat", 0))
stat_cols[2].metric("חלבי", stats.get("by_kashrut", {}).get("dairy", 0))
stat_cols[3].metric("פרווה", stats.get("by_kashrut", {}).get("parve", 0))

meal_type_counts = stats.get("by_meal_type", {})
total_meal_slots = sum(meal_type_counts.values())
stat_cols[4].metric("ארוחות", total_meal_slots)

# ── Sidebar filters ──────────────────────────────────────────────────────────

with st.sidebar:
    section_header("סינון מתכונים", "search")

search_text = st.sidebar.text_input("חיפוש חופשי", placeholder="שקשוקה, סלט, עוף...")

MEAL_TYPE_LABELS = {
    "BREAKFAST": "ארוחת בוקר",
    "MORNING_SNACK": "חטיף בוקר",
    "LUNCH": "ארוחת צהריים",
    "AFTERNOON_SNACK": "חטיף אחה״צ",
    "DINNER": "ארוחת ערב",
    "EVENING_SNACK": "חטיף ערב",
}

selected_meal_types = st.sidebar.multiselect(
    "סוג ארוחה",
    options=list(MEAL_TYPE_LABELS.keys()),
    format_func=lambda x: MEAL_TYPE_LABELS[x],
)

KASHRUT_OPTIONS = {"הכל": None, "בשרי": "meat", "חלבי": "dairy", "פרווה": "parve"}
kashrut_label = st.sidebar.radio("כשרות", list(KASHRUT_OPTIONS.keys()), horizontal=True)
kashrut_filter = KASHRUT_OPTIONS[kashrut_label]

cal_col1, cal_col2 = st.sidebar.columns(2)
calorie_min = cal_col1.number_input("קלוריות מינימום", min_value=0, max_value=2000, value=0, step=50)
calorie_max = cal_col2.number_input("קלוריות מקסימום", min_value=0, max_value=2000, value=0, step=50)

max_prep_time = st.sidebar.slider("זמן הכנה מקסימלי (דקות)", 0, 120, 0, step=5)

# Tags
all_tags = sorted(stats.get("by_tag", {}).keys())
selected_tags = st.sidebar.multiselect("תגיות", options=all_tags)

max_results = st.sidebar.slider("מספר תוצאות", 5, 100, 20, step=5)

# ── Build filter and search ──────────────────────────────────────────────────

recipe_filter = RecipeFilter(
    calorie_min=calorie_min if calorie_min > 0 else None,
    calorie_max=calorie_max if calorie_max > 0 else None,
    meal_types=selected_meal_types if selected_meal_types else None,
    kashrut=kashrut_filter,
    tags_include=selected_tags if selected_tags else None,
    max_prep_time_minutes=max_prep_time if max_prep_time > 0 else None,
    search_text=search_text if search_text else None,
    max_results=max_results,
)

results = manager.search_recipes(recipe_filter)

# ── Display results ──────────────────────────────────────────────────────────

st.markdown(f"### נמצאו {len(results)} מתכונים")
st.markdown("---")

for recipe in results:
    _img_uri = image_data_uri(recipe.get("image_path", ""))
    st.markdown(
        recipe_card_html(recipe, image_uri=_img_uri),
        unsafe_allow_html=True,
    )

if not results:
    st.info("לא נמצאו מתכונים התואמים לסינון. נסה להרחיב את החיפוש.")
