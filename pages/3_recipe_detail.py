#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""דף פרטי מתכון — תצוגה מלאה ואיכותית"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions
from ui.components import inject_global_css
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth

st.set_page_config(page_title="BiteFit · מתכון", page_icon=None,
                   layout="wide", initial_sidebar_state="collapsed")
inject_global_css()
setup_persistent_auth()
require_auth()

# ── Load recipe ─────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@st.cache_resource
def _get_manager():
    return RecipeManager()

@st.cache_data
def _load_images() -> dict:
    try:
        return json.load(open(os.path.join(_ROOT, "data", "recipe_images.json"), encoding="utf-8"))
    except:
        return {}

recipe_id = st.query_params.get("id", "")
if not recipe_id:
    st.error("לא צוין מזהה מתכון.")
    st.page_link("pages/2_recipes.py", label="חזור לרשימת המתכונים")
    st.stop()

recipe = _get_manager().get_recipe(recipe_id)
if not recipe:
    st.error(f"מתכון '{recipe_id}' לא נמצא.")
    st.page_link("pages/2_recipes.py", label="חזור לרשימת המתכונים")
    st.stop()

# ── Data ────────────────────────────────────────────────────────────────────
name_he    = recipe.get("name_he", "")
name_en    = recipe.get("name_en", "")
kashrut    = (recipe.get("kashrut") or "parve").lower()
portions   = max(recipe.get("portions", 1), 1)
prep_time  = recipe.get("prep_time_minutes", 0)
tags       = recipe.get("tags", [])
ingredients= recipe.get("ingredients", [])
nutrition  = recipe.get("total_nutrition", {})
cal   = round(nutrition.get("calories", 0) / portions)
prot  = round(nutrition.get("protein",  0) / portions)
carbs = round(nutrition.get("carbs",    0) / portions)
fat   = round(nutrition.get("fat",      0) / portions)

# Image — Unsplash first, then local
_img_url = _load_images().get(recipe_id, "")
if not _img_url:
    _local = recipe.get("image_path", "")
    if _local:
        _abs = _local if os.path.isabs(_local) else os.path.join(_ROOT, _local)
        if os.path.isfile(_abs):
            _img_url = _abs

# Kashrut colors
_k_colors = {"dairy": "#60a5fa", "meat": "#f87171", "parve": "#4ade80"}
_k_labels = {"dairy": "חלבי", "meat": "בשרי", "parve": "פרווה"}
_k_color  = _k_colors.get(kashrut, "#8892a4")
_k_label  = _k_labels.get(kashrut, kashrut)

steps = get_instructions(recipe_id)

# ── Back button ──────────────────────────────────────────────────────────────
st.markdown(
    '<a href="/recipes" target="_self" style="text-decoration:none">'
    '<div style="display:inline-flex;align-items:center;gap:6px;color:#8892a4;'
    'font-size:0.82rem;margin-bottom:12px">חזור למתכונים</div></a>',
    unsafe_allow_html=True
)

# ── Hero image ───────────────────────────────────────────────────────────────
if _img_url:
    if _img_url.startswith("http"):
        st.markdown(
            f'<div style="width:100%;height:280px;border-radius:20px;overflow:hidden;margin-bottom:20px;'
            f'background:#0d1117 url(\'{_img_url}\') center/cover no-repeat"></div>',
            unsafe_allow_html=True
        )
    else:
        st.image(_img_url, use_container_width=True)

# ── Title + badges ───────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="margin-bottom:16px">'
    f'<h1 style="font-size:1.8rem;font-weight:900;color:#f4f6fb;margin:0 0 4px">{name_he}</h1>'
    f'<div style="font-size:0.85rem;color:#8892a4;margin-bottom:10px">{name_en}</div>'
    f'<div style="display:flex;gap:8px;flex-wrap:wrap">'
    f'<span style="background:{_k_color}22;border:1px solid {_k_color}55;color:{_k_color};'
    f'border-radius:99px;padding:3px 12px;font-size:0.75rem;font-weight:600">{_k_label}</span>'
    f'<span style="background:#252d3d;color:#8892a4;border-radius:99px;padding:3px 12px;font-size:0.75rem">'
    f'{prep_time} דקות</span>'
    f'<span style="background:#252d3d;color:#8892a4;border-radius:99px;padding:3px 12px;font-size:0.75rem">'
    f'{portions} מנות</span>'
    + "".join(f'<span style="background:#252d3d;color:#8892a4;border-radius:99px;'
              f'padding:3px 12px;font-size:0.75rem">{t}</span>' for t in tags[:3]) +
    f'</div></div>',
    unsafe_allow_html=True
)

# ── Macros ───────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="display:flex;gap:10px;margin-bottom:20px">'
    f'<div style="flex:1;background:#161b26;border-radius:14px;padding:14px;text-align:center">'
    f'<div style="font-size:1.3rem;font-weight:900;color:#f4f6fb">{cal}</div>'
    f'<div style="font-size:0.65rem;color:#545e70;margin-top:2px">קק״ל</div></div>'
    f'<div style="flex:1;background:#161b26;border-radius:14px;padding:14px;text-align:center">'
    f'<div style="font-size:1.3rem;font-weight:900;color:#4f8ef7">{prot}g</div>'
    f'<div style="font-size:0.65rem;color:#545e70;margin-top:2px">חלבון</div></div>'
    f'<div style="flex:1;background:#161b26;border-radius:14px;padding:14px;text-align:center">'
    f'<div style="font-size:1.3rem;font-weight:900;color:#f59e0b">{carbs}g</div>'
    f'<div style="font-size:0.65rem;color:#545e70;margin-top:2px">פחמימות</div></div>'
    f'<div style="flex:1;background:#161b26;border-radius:14px;padding:14px;text-align:center">'
    f'<div style="font-size:1.3rem;font-weight:900;color:#f472b6">{fat}g</div>'
    f'<div style="font-size:0.65rem;color:#545e70;margin-top:2px">שומן</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

# ── Ingredients ──────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:1rem;font-weight:800;color:#f4f6fb;margin-bottom:10px">מרכיבים</div>',
    unsafe_allow_html=True
)
_ing_html = ""
for ing in ingredients:
    display = format_ingredient_display(ing)
    _ing_html += (
        f'<div style="display:flex;align-items:center;gap:8px;padding:8px 0;'
        f'border-bottom:1px solid #1e2535">'
        f'<div style="width:6px;height:6px;border-radius:50%;background:#4f8ef7;flex-shrink:0"></div>'
        f'<div style="font-size:0.85rem;color:#f4f6fb">{display}</div>'
        f'</div>'
    )
st.markdown(
    f'<div style="background:#161b26;border-radius:16px;padding:14px 16px;margin-bottom:20px">'
    f'{_ing_html}</div>',
    unsafe_allow_html=True
)

# ── Instructions ─────────────────────────────────────────────────────────────
if steps:
    st.markdown(
        '<div style="font-size:1rem;font-weight:800;color:#f4f6fb;margin-bottom:10px">הוראות הכנה</div>',
        unsafe_allow_html=True
    )
    _steps_html = ""
    for i, step in enumerate(steps, 1):
        _steps_html += (
            f'<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #1e2535">'
            f'<div style="width:26px;height:26px;border-radius:50%;background:#4f8ef7;'
            f'display:flex;align-items:center;justify-content:center;flex-shrink:0;'
            f'font-size:0.75rem;font-weight:800;color:#fff">{i}</div>'
            f'<div style="font-size:0.85rem;color:#c4cdd8;line-height:1.5;padding-top:3px">{step}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:#161b26;border-radius:16px;padding:14px 16px">'
        f'{_steps_html}</div>',
        unsafe_allow_html=True
    )
