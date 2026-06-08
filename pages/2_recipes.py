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
from nutrition_app.repositories.profile_repository import ProfileRepository

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu, recipe_card_html,
)
from ui.images import image_data_uri
from chatbot.sidebar_widget import render_chatbot_sidebar
from ui.user_auth import require_auth

#  Page config 

st.set_page_config(
    page_title="BiteFit · מתכונים",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_css()

st.markdown("""
<style>
/* כפתור מתכון — נראה כמו חלק מהכרטיס */
div[data-testid="stButton"].recipe-nav > button {
    background: transparent !important;
    border: none !important;
    border-top: 1px solid #252d3d !important;
    border-radius: 0 0 16px 16px !important;
    color: #4f8ef7 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    margin-top: -12px !important;
    padding: 10px 0 !important;
    width: 100% !important;
    box-shadow: none !important;
}
div[data-testid="stButton"].recipe-nav > button:hover {
    background: #161b26 !important;
    color: #7fb3ff !important;
}
</style>
""", unsafe_allow_html=True)
nav_menu(active="מתכונים")

_USER_ID = require_auth()

@st.cache_resource
def get_recipe_manager():
    return RecipeManager()

@st.cache_data(ttl=60)
def _get_user_allergens(user_id: str) -> list:
    return ProfileRepository().load(user_id).get("meal_preferences", {}).get("allergies", [])

manager = get_recipe_manager()
_user_allergens = _get_user_allergens(_USER_ID)
stats = manager.get_stats()

#  Sidebar filters 

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

with st.sidebar:
    if _user_allergens:
        st.markdown(
            f'<div dir="rtl" style="font-size:0.75rem;color:#f87171;padding:4px 0">'
            f'מסנן אלרגיות: {", ".join(_user_allergens)}</div>',
            unsafe_allow_html=True,
        )
    st.divider()
    render_chatbot_sidebar()

#  Build filter and search

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

_all_results = manager.search_recipes(recipe_filter)

# סינון לפי אלרגיות המשתמש
if _user_allergens:
    results = [r for r in _all_results
               if not manager._recipe_contains_allergen(r, _user_allergens)]
else:
    results = _all_results

#  Display results 

st.markdown(f"### נמצאו {len(results)} מתכונים")
st.markdown("---")

for recipe in results:
    _img_uri = image_data_uri(recipe.get("image_path", ""))
    _rid = recipe.get("recipe_id", "")
    st.markdown(
        recipe_card_html(recipe, image_uri=_img_uri),
        unsafe_allow_html=True,
    )
    st.markdown('<div class="recipe-nav">', unsafe_allow_html=True)
    if st.button("לפרטי המתכון ←", key=f"nav_{_rid}", use_container_width=True):
        st.session_state["_nav_recipe_id"] = _rid
        st.session_state["_nav_recipe_from"] = "recipes"
        st.switch_page("pages/3_recipe_detail.py")
    st.markdown('</div>', unsafe_allow_html=True)

if not results:
    st.info("לא נמצאו מתכונים התואמים לסינון. נסה להרחיב את החיפוש.")
