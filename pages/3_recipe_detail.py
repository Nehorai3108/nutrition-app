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

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="פרטי מתכון",
    page_icon="🍽",
    layout="wide",
)

st.markdown("""
<style>
    .main .block-container { direction: rtl; }
    section[data-testid="stSidebar"] > div { direction: rtl; }
    h1, h2, h3, h4 { text-align: right; }
    .detail-header {
        margin-bottom: 1em;
    }
    .detail-header .name-he {
        font-size: 2em;
        font-weight: 700;
        color: #e0e0ff;
    }
    .detail-header .name-en {
        font-size: 1.1em;
        color: #999;
    }
    .kashrut-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.95em;
        margin: 8px 0;
    }
    .kashrut-meat { background: #c62828; color: #fff; }
    .kashrut-dairy { background: #2e7d32; color: #fff; }
    .kashrut-parve { background: #e65100; color: #fff; }
    .ingredient-item {
        padding: 6px 0;
        border-bottom: 1px solid #333;
        font-size: 1em;
    }
    .tag-chip {
        display: inline-block;
        background: #2a2a4a;
        color: #b0b0ff;
        padding: 4px 12px;
        border-radius: 14px;
        font-size: 0.85em;
        margin: 3px;
    }
</style>
""", unsafe_allow_html=True)

# ── Load recipe ──────────────────────────────────────────────────────────────

@st.cache_resource
def get_recipe_manager():
    return RecipeManager()


params = st.query_params
recipe_id = params.get("id", "")

if not recipe_id:
    st.error("לא צוין מזהה מתכון.")
    st.markdown(
        '<a href="/" target="_self" style="display:inline-block;padding:0.5em 1.5em;'
        "background:#3a3a5a;border-radius:8px;text-decoration:none;color:#e0e0ff;"
        'font-weight:600;margin-top:1em">⬅ חזור לדף הבית</a>',
        unsafe_allow_html=True,
    )
    st.stop()

manager = get_recipe_manager()
recipe = manager.get_recipe(recipe_id)

if not recipe:
    st.error(f"מתכון עם מזהה '{recipe_id}' לא נמצא.")
    st.markdown(
        '<a href="/" target="_self" style="display:inline-block;padding:0.5em 1.5em;'
        "background:#3a3a5a;border-radius:8px;text-decoration:none;color:#e0e0ff;"
        'font-weight:600;margin-top:1em">⬅ חזור לדף הבית</a>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── Back button ──────────────────────────────────────────────────────────────

col_back, col_spacer = st.columns([1, 4])
col_back.markdown(
    '<a href="/recipes" target="_self" style="display:inline-block;padding:0.4em 1.2em;'
    "background:#3a3a5a;border-radius:8px;text-decoration:none;color:#e0e0ff;"
    'font-weight:500">⬅ חזור</a>',
    unsafe_allow_html=True,
)

# ── Header ───────────────────────────────────────────────────────────────────

name_he = recipe.get("name_he", "")
name_en = recipe.get("name_en", "")
kashrut_raw = recipe.get("kashrut", "parve").lower()
portions = max(recipe.get("portions", 1), 1)
prep_time = recipe.get("prep_time_minutes", 0)
tags = recipe.get("tags", [])
ingredients = recipe.get("ingredients", [])
nutrition = recipe.get("total_nutrition", {})

KASHRUT_LABELS = {"meat": "בשרי", "dairy": "חלבי", "parve": "פרווה"}
KASHRUT_CSS = {"meat": "kashrut-meat", "dairy": "kashrut-dairy", "parve": "kashrut-parve"}

kashrut_lbl = KASHRUT_LABELS.get(kashrut_raw, kashrut_raw)
kashrut_css = KASHRUT_CSS.get(kashrut_raw, "kashrut-parve")

st.markdown(
    f'<div class="detail-header">'
    f'<div class="name-he">{name_he}</div>'
    f'<div class="name-en">{name_en}</div>'
    f'<span class="kashrut-badge {kashrut_css}">{kashrut_lbl}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Info row ─────────────────────────────────────────────────────────────────

info_cols = st.columns(2)
info_cols[0].metric("⏱ זמן הכנה", f"{prep_time} דקות")
info_cols[1].metric("🍽 מנות", str(portions))

st.divider()

# ── Nutritional breakdown per portion ────────────────────────────────────────

st.markdown("### ערכים תזונתיים למנה")

cal = round(nutrition.get("calories", 0) / portions)
protein = round(nutrition.get("protein", 0) / portions)
carbs = round(nutrition.get("carbs", 0) / portions)
fat = round(nutrition.get("fat", 0) / portions)

macro_cols = st.columns(4)
macro_cols[0].metric("🔥 קלוריות", f"{cal} קק״ל")
macro_cols[1].metric("💪 חלבון", f"{protein} ג׳")
macro_cols[2].metric("🌾 פחמימות", f"{carbs} ג׳")
macro_cols[3].metric("🫒 שומן", f"{fat} ג׳")

st.divider()

# ── Ingredients ──────────────────────────────────────────────────────────────

st.markdown("### מרכיבים")

for ing in ingredients:
    display = format_ingredient_display(ing)
    food_name = ing.get("food_name", "")
    st.markdown(
        f'<div class="ingredient-item">• {display}</div>',
        unsafe_allow_html=True,
    )

# ── Preparation Instructions ────────────────────────────────────────────────

steps = get_instructions(recipe_id)
if steps:
    st.divider()
    st.markdown("### הוראות הכנה")
    for i, step in enumerate(steps, 1):
        st.markdown(f"**{i}.** {step}")

st.divider()

# ── Tags ─────────────────────────────────────────────────────────────────────

if tags:
    st.markdown("### תגיות")
    tags_html = "".join(f'<span class="tag-chip">{t}</span>' for t in tags)
    st.markdown(tags_html, unsafe_allow_html=True)
