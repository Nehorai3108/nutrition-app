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

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="מתכונים",
    page_icon="📖",
    layout="wide",
)

st.markdown("""
<style>
    .main .block-container { direction: rtl; }
    section[data-testid="stSidebar"] > div { direction: rtl; }
    h1, h2, h3, h4 { text-align: right; }
    .recipe-card {
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        direction: rtl;
    }
    .recipe-title {
        font-size: 1.2em;
        font-weight: 700;
        color: #1a237e;
        margin-bottom: 4px;
    }
    .recipe-subtitle {
        font-size: 0.85em;
        color: #757575;
        margin-bottom: 8px;
    }
    .recipe-tag {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        margin: 2px;
    }
    .kashrut-dairy { background: #e8f5e9; color: #2e7d32; }
    .kashrut-meat { background: #fce4ec; color: #c62828; }
    .kashrut-parve { background: #fff3e0; color: #e65100; }
    .macro-box {
        display: inline-block;
        text-align: center;
        padding: 4px 10px;
        margin: 2px;
        border-radius: 8px;
        font-size: 0.85em;
    }
    .macro-cal { background: #fff9c4; }
    .macro-protein { background: #e8f5e9; }
    .macro-carbs { background: #e3f2fd; }
    .macro-fat { background: #fce4ec; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────

col_title, col_nav = st.columns([3, 1])
col_title.markdown("# 📖 מתכונים")
col_nav.markdown(
    '<a href="/" target="_self" style="display:inline-block;padding:0.4em 1em;'
    "background:#f0f2f6;border-radius:8px;text-decoration:none;color:#262730;"
    'font-weight:500;text-align:center;width:100%">🏠 דף הבית</a>',
    unsafe_allow_html=True,
)

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

st.sidebar.markdown("## 🔍 סינון מתכונים")

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

KASHRUT_LABELS = {"dairy": "חלבי", "meat": "בשרי", "parve": "פרווה"}
KASHRUT_CSS = {"dairy": "kashrut-dairy", "meat": "kashrut-meat", "parve": "kashrut-parve"}

for recipe in results:
    name_he = recipe.get("name_he", "")
    name_en = recipe.get("name_en", "")
    kashrut = recipe.get("kashrut", "parve")
    kashrut_label_text = KASHRUT_LABELS.get(kashrut, kashrut)
    kashrut_css = KASHRUT_CSS.get(kashrut, "")
    portions = recipe.get("portions", 1)
    prep_time = recipe.get("prep_time_minutes", 0)
    tags = recipe.get("tags", [])
    ingredients = recipe.get("ingredients", [])
    nutrition = recipe.get("total_nutrition", {})
    meal_types = recipe.get("meal_types", [])

    # Per-portion nutrition
    cal_per_portion = round(nutrition.get("calories", 0) / max(portions, 1))
    protein_per_portion = round(nutrition.get("protein", 0) / max(portions, 1))
    carbs_per_portion = round(nutrition.get("carbs", 0) / max(portions, 1))
    fat_per_portion = round(nutrition.get("fat", 0) / max(portions, 1))

    meal_labels = [MEAL_TYPE_LABELS.get(mt, mt) for mt in meal_types]

    # Build card HTML
    tags_html = "".join(f'<span class="recipe-tag">{t}</span>' for t in tags)
    meals_html = "".join(f'<span class="recipe-tag">{m}</span>' for m in meal_labels)
    ingredients_text = " · ".join(
        format_ingredient_display(ing)
        for ing in ingredients
    )

    recipe_link = f"/recipe_detail?id={recipe.get('recipe_id', '')}"
    card_html = f"""
    <a href="{recipe_link}" target="_self" style="text-decoration:none;color:inherit">
    <div class="recipe-card" style="cursor:pointer;transition:border-color 0.2s" onmouseover="this.style.borderColor='#999'" onmouseout="this.style.borderColor='#e0e0e0'">
        <div class="recipe-title">{name_he}</div>
        <div class="recipe-subtitle">{name_en} · <span class="{kashrut_css}" style="padding:2px 6px;border-radius:8px">{kashrut_label_text}</span> · ⏱ {prep_time} דק׳ · 🍽 {portions} מנות</div>
        <div style="margin:6px 0">
            <span class="macro-box macro-cal">🔥 {cal_per_portion} קק״ל</span>
            <span class="macro-box macro-protein">💪 {protein_per_portion}ג חלבון</span>
            <span class="macro-box macro-carbs">🌾 {carbs_per_portion}ג פחמ׳</span>
            <span class="macro-box macro-fat">🫒 {fat_per_portion}ג שומן</span>
        </div>
        <div style="margin:4px 0;font-size:0.85em;color:#555">
            <b>מרכיבים:</b> {ingredients_text}
        </div>
        <div style="margin:4px 0">{meals_html}</div>
        <div style="margin:4px 0">{tags_html}</div>
    </div>
    </a>
    """
    st.markdown(card_html, unsafe_allow_html=True)

if not results:
    st.info("לא נמצאו מתכונים התואמים לסינון. נסה להרחיב את החיפוש.")
