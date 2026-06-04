#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף פרטי מתכון — תצוגה מלאה של מתכון בודד
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu,
    kashrut_badge_html, macro_grid_html,
)
from auth.login_ui import require_auth, logout_button
from chatbot.sidebar_widget import render_chatbot_sidebar

#  Page config 

st.set_page_config(
    page_title="BiteFit · מתכון",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_css()

USER_ID = require_auth()

with st.sidebar:
    st.markdown(
        f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">👤 {st.session_state.get("user_email", "")}</div>',
        unsafe_allow_html=True,
    )
    logout_button(key="_recipe_detail_logout_btn")
    st.divider()
    render_chatbot_sidebar()

#  Load recipe 

@st.cache_resource
def get_recipe_manager():
    return RecipeManager()


params = st.query_params
recipe_id = params.get("id", "")

nav_menu(active="מתכונים")

if not recipe_id:
    st.error("לא צוין מזהה מתכון.")
    st.page_link("pages/2_recipes.py", label=" חזור לרשימת המתכונים")
    st.stop()

manager = get_recipe_manager()
recipe = manager.get_recipe(recipe_id)

if not recipe:
    st.error(f"מתכון עם מזהה '{recipe_id}' לא נמצא.")
    st.page_link("pages/2_recipes.py", label=" חזור לרשימת המתכונים")
    st.stop()

#  Header 

name_he = recipe.get("name_he", "")
name_en = recipe.get("name_en", "")
kashrut_raw = (recipe.get("kashrut") or "parve").lower()
portions = max(recipe.get("portions", 1), 1)
prep_time = recipe.get("prep_time_minutes", 0)
tags = recipe.get("tags", [])
ingredients = recipe.get("ingredients", [])
nutrition = recipe.get("total_nutrition", {})

page_header(name_he, icon_name="recipe", subtitle=name_en)
st.markdown(kashrut_badge_html(kashrut_raw), unsafe_allow_html=True)

#  Recipe image 
_image_path = recipe.get("image_path")
if _image_path:
    _abs_img = _image_path if os.path.isabs(_image_path) else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), _image_path
    )
    if os.path.isfile(_abs_img):
        img_col = st.columns([1, 2, 1])[1]
        img_col.image(_abs_img, caption=name_he, use_container_width=True)
        _credit = recipe.get("image_credit")
        if _credit:
            img_col.caption(f" {_credit}")

#  Info row 

info_cols = st.columns(2)
info_cols[0].metric("⏱ זמן הכנה", f"{prep_time} דקות")
info_cols[1].metric(" מנות", str(portions))

st.divider()

#  Nutritional breakdown per portion 

st.markdown("### ערכים תזונתיים למנה")

cal = round(nutrition.get("calories", 0) / portions)
protein = round(nutrition.get("protein", 0) / portions)
carbs = round(nutrition.get("carbs", 0) / portions)
fat = round(nutrition.get("fat", 0) / portions)

macro_cols = st.columns(4)
macro_cols[0].metric(" קלוריות", f"{cal} קק״ל")
macro_cols[1].metric(" חלבון", f"{protein} ג׳")
macro_cols[2].metric(" פחמימות", f"{carbs} ג׳")
macro_cols[3].metric(" שומן", f"{fat} ג׳")

st.divider()

#  Ingredients 

section_header("מרכיבים", "recipe")

for ing in ingredients:
    display = format_ingredient_display(ing)
    st.markdown(f"• {display}")

#  Preparation Instructions 

steps = get_instructions(recipe_id)
if steps:
    st.divider()
    st.markdown("### הוראות הכנה")
    for i, step in enumerate(steps, 1):
        st.markdown(f"**{i}.** {step}")

st.divider()

#  Tags 

if tags:
    section_header("תגיות", "menu")
    tags_html = "".join(f'<span class="nut-chip">{t}</span>' for t in tags)
    st.markdown(tags_html, unsafe_allow_html=True)
