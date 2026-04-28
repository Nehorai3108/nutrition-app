#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף תפריט יומי — המלצות ארוחות לפי בוקר, צהריים, ערב
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import date, datetime
import streamlit as st
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager, get_recipe_inventory_match
from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter
from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
from nutrition_app.agents.agent_11_recipes.recipe_instructions import get_instructions
from nutrition_app.user_manager import get_all_users, load_inventory
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry

from ui.components import inject_global_css, recipe_card_html, bottom_nav
from ui.images import image_data_uri as _image_data_uri
from nutrition_app.agents.agent_3_food import FoodCatalog

USER_ID = "ui_user_001"
_food_log_repo = FoodLogRepository()

st.set_page_config(page_title="תפריט יומי", page_icon="🍽️", layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

@st.cache_resource
def get_mgr():
    return RecipeManager()

@st.cache_resource
def get_catalog():
    return FoodCatalog(db_path=_DB_PATH)

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
    ("BREAKFAST",       "בוקר",      "BREAKFAST"),
    ("MORNING_SNACK",   "חטיף בוקר", "MORNING_SNACK"),
    ("LUNCH",           "צהריים",    "LUNCH"),
    ("AFTERNOON_SNACK", "חטיף צ'",   "AFTERNOON_SNACK"),
    ("DINNER",          "ערב",        "DINNER"),
    ("EVENING_SNACK",   "חטיף ע'",   "EVENING_SNACK"),
]

MEAL_COLOR_MAP = {
    "BREAKFAST":       "#f59e0b",
    "MORNING_SNACK":   "#a78bfa",
    "LUNCH":           "#4f8ef7",
    "AFTERNOON_SNACK": "#34d399",
    "DINNER":          "#f87171",
    "EVENING_SNACK":   "#818cf8",
}

MEAL_DESC = {
    "BREAKFAST":       "ארוחה קלה ומזינה לתחילת היום",
    "MORNING_SNACK":   "משהו קטן בין הבוקר לצהריים",
    "LUNCH":           "הארוחה העיקרית של היום",
    "AFTERNOON_SNACK": "אנרגיה לשעות אחר הצהריים",
    "DINNER":          "ארוחה קלה ומאוזנת לסיום היום",
    "EVENING_SNACK":   "משהו קל לפני השינה",
}

# ── Calorie targets ───────────────────────────────────────────────────────────
has_plan = "last_plan" in st.session_state
if has_plan:
    plan    = st.session_state["last_plan"]["plan"]
    targets = st.session_state["last_plan"]["targets"]
    meal_calories = {m.meal_type.value.upper(): m.total_calories for m in plan.meals}
else:
    meal_calories = {
        "BREAKFAST": 450, "MORNING_SNACK": 200, "LUNCH": 650,
        "AFTERNOON_SNACK": 200, "DINNER": 500, "EVENING_SNACK": 150,
    }

# ── Inventory ─────────────────────────────────────────────────────────────────
inventory_names: set = set()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;'
    f'padding:4px 2px 16px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb">תזונה</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{date.today().strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Meal tab selector ─────────────────────────────────────────────────────────
tab_labels = [label for _, label, _ in MEAL_SECTIONS] + ["חיפוש", "✏️ ידני"]
tabs = st.tabs(tab_labels)

_catalog = get_catalog()
_all_foods = sorted(_catalog.get_all_foods(), key=lambda f: f.name_he)
_food_id_to_name = {f.food_id: f.name_he for f in _all_foods}

MEAL_TYPE_HEB = {
    "breakfast": "ארוחת בוקר", "morning_snack": "חטיף בוקר",
    "lunch": "ארוחת צהריים", "afternoon_snack": "חטיף אחה״צ",
    "dinner": "ארוחת ערב", "evening_snack": "חטיף ערב",
}

# ── helper: render a nutrition result card + add button ───────────────────────
def _render_search_result(
    name: str, food_id: str, meal_key: str, target_cal: int,
    cal_out: float, prot_out: float, carbs_out: float, fat_out: float,
    portion_label: str, btn_suffix: str, grams: float = 0.0,
):
    _cal_diff   = round(cal_out) - target_cal
    _diff_color = "#4ade80" if abs(_cal_diff) <= 40 else ("#f59e0b" if abs(_cal_diff) <= 100 else "#f87171")
    _meal_color = MEAL_COLOR_MAP.get(meal_key.upper(), "#4f8ef7")
    _cal_pct    = min(cal_out / max(target_cal, 1) * 100, 100)

    st.markdown(
        f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:20px;'
        f'padding:20px;margin:10px 0 14px">'
        f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">'
        f'<div dir="rtl" style="font-size:1rem;font-weight:800;color:#f4f6fb">{name}</div>'
        f'<div dir="rtl" style="background:{_meal_color}22;border:1px solid {_meal_color}55;border-radius:99px;'
        f'padding:3px 10px;font-size:0.7rem;color:{_meal_color};font-weight:600">'
        f'{MEAL_TYPE_HEB[meal_key]}</div></div>'
        f'<div dir="rtl" style="display:flex;align-items:flex-end;gap:6px;margin-bottom:14px">'
        f'<div dir="rtl" style="font-size:2.4rem;font-weight:900;color:#f4f6fb;line-height:1">{portion_label}</div>'
        f'<div dir="rtl" style="flex:1"></div>'
        f'<div dir="rtl" style="text-align:right">'
        f'<div dir="rtl" style="font-size:2rem;font-weight:900;color:{_diff_color};line-height:1">{round(cal_out)}</div>'
        f'<div dir="rtl" style="font-size:0.7rem;color:#8892a4">קק״ל</div>'
        f'</div></div>'
        f'<div dir="rtl" style="display:flex;align-items:center;gap:8px;margin-bottom:14px">'
        f'<div dir="rtl" style="height:4px;flex:1;background:#252d3d;border-radius:99px;overflow:hidden">'
        f'<div dir="rtl" style="height:100%;width:{_cal_pct:.0f}%;background:{_diff_color};border-radius:99px"></div></div>'
        f'<div dir="rtl" style="font-size:0.7rem;color:{_diff_color};font-weight:600;white-space:nowrap">'
        f'יעד {target_cal} &nbsp;({("+" if _cal_diff >= 0 else "")}{_cal_diff} קק״ל)</div></div>'
        f'<div dir="rtl" style="display:flex;gap:8px">'
        f'<div dir="rtl" style="flex:1;background:#0d1117;border-radius:12px;padding:10px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:0.9rem;font-weight:800;color:#4f8ef7">{prot_out:.1f}g</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">חלבון</div></div>'
        f'<div dir="rtl" style="flex:1;background:#0d1117;border-radius:12px;padding:10px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:0.9rem;font-weight:800;color:#f59e0b">{carbs_out:.1f}g</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">פחמימות</div></div>'
        f'<div dir="rtl" style="flex:1;background:#0d1117;border-radius:12px;padding:10px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:0.9rem;font-weight:800;color:#f472b6">{fat_out:.1f}g</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">שומן</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    _sadd_key   = f"sadd_{food_id}_{meal_key}_{btn_suffix}"
    _sadded_key = f"sadded_{food_id}_{meal_key}_{btn_suffix}"
    if st.session_state.get(_sadded_key):
        st.markdown(
            '<div dir="rtl" style="background:#0d2b1a;border:1px solid #1a4d2e;border-radius:12px;'
            'padding:8px 14px;font-size:0.82rem;color:#4ade80;text-align:center;margin-bottom:8px">'
            'נוסף לתפריט היומי</div>',
            unsafe_allow_html=True,
        )
    else:
        if st.button(f"הוסף לתפריט היומי · {round(cal_out)} קק״ל",
                     key=_sadd_key, use_container_width=True, type="primary"):
            _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                food_id=food_id, food_name=name,
                grams=grams if grams > 0 else round(cal_out),
                calories=float(round(cal_out)),
                protein=float(round(prot_out, 1)),
                carbs=float(round(carbs_out, 1)),
                fat=float(round(fat_out, 1)),
                meal_type=meal_key, timestamp=datetime.now().isoformat(),
            ))
            st.session_state[_sadded_key] = True
            st.rerun()


# Smart search tab
with tabs[-2]:
    # ── Mode toggle ───────────────────────────────────────────────────────────
    _search_mode = st.radio(
        "",
        options=["recipe", "ingredient"],
        format_func=lambda m: {"recipe": "מנה מוכנה (שקשוקה, חביתה...)",
                               "ingredient": "רכיב (ביצה, אבוקדו...)"}[m],
        horizontal=True,
        key="search_mode_radio",
        label_visibility="collapsed",
    )

    st.markdown('<div dir="rtl" style="height:6px"></div>', unsafe_allow_html=True)

    # ── Meal selector (shared) ────────────────────────────────────────────────
    search_meal = st.selectbox(
        "ארוחה",
        options=list(MEAL_TYPE_HEB.keys()),
        format_func=lambda k: MEAL_TYPE_HEB[k],
        key="search_meal_sel",
    )
    _search_target = meal_calories.get(search_meal.upper(), 400)

    # ═══════════════════════════════════════════════════════════════════════════
    if _search_mode == "recipe":
    # ═══════════════════════════════════════════════════════════════════════════
        _recipe_query = st.text_input(
            "",
            placeholder="חפש מנה: שקשוקה, חביתה, עוף, אורז...",
            key="recipe_search_text",
            label_visibility="collapsed",
        )

        _q = _recipe_query.strip()
        if not _q:
            st.markdown(
                '<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                'padding:20px;text-align:center;color:#545e70;font-size:0.82rem;margin-top:8px">'
                'הקלד שם מנה כדי לחפש<br>'
                '<span style="font-size:0.7rem;color:#3d4a5c">ניתן לחפש בעברית או אנגלית</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            # Search by both the exact query and also try English equivalent
            _recipe_results = recipe_mgr.search_recipes(
                RecipeFilter(search_text=_q, max_results=6)
            )
            # Also search by English in case Hebrew morphology limits results
            _recipe_results_en = recipe_mgr.search_recipes(
                RecipeFilter(search_text=_q, max_results=6)
            )
            # Merge unique by recipe_id
            _seen_ids = set()
            _merged = []
            for _r in _recipe_results + _recipe_results_en:
                _rid = _r.get("recipe_id", "")
                if _rid not in _seen_ids:
                    _seen_ids.add(_rid)
                    _merged.append(_r)

            if not _merged:
                st.markdown(
                    '<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                    'padding:16px;text-align:center;color:#545e70;font-size:0.82rem;margin-top:8px">'
                    f'לא נמצאו מנות עבור "{_q}"<br>'
                    '<span style="font-size:0.7rem;color:#3d4a5c">נסה מילה אחרת (לדוגמה: omelette)</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                for _rec in _merged[:5]:
                    _portions    = max(_rec.get("portions", 1), 1)
                    _nut         = _rec.get("total_nutrition", {})
                    _cal_per_por = _nut.get("calories", 0) / _portions
                    _prot_per    = _nut.get("protein",  0) / _portions
                    _carbs_per   = _nut.get("carbs",    0) / _portions
                    _fat_per     = _nut.get("fat",      0) / _portions
                    _rec_id      = _rec.get("recipe_id", "")
                    _rec_name    = _rec.get("name_he", "מנה")

                    _sug_por = max(1, min(round(_search_target / max(_cal_per_por, 1)), 4))
                    _col_name, _col_por = st.columns([3, 1])
                    _col_name.markdown(
                        f'<div dir="rtl" style="font-size:0.88rem;font-weight:700;color:#f4f6fb;'
                        f'padding-top:8px">{_rec_name}</div>',
                        unsafe_allow_html=True,
                    )
                    _n_portions = _col_por.number_input(
                        "מנות", min_value=1, max_value=6, value=_sug_por, step=1,
                        key=f"rec_por_{_rec_id}",
                        label_visibility="visible",
                    )
                    _render_search_result(
                        name=_rec_name, food_id=f"recipe_{_rec_id}",
                        meal_key=search_meal, target_cal=_search_target,
                        cal_out=_cal_per_por * _n_portions,
                        prot_out=_prot_per * _n_portions,
                        carbs_out=_carbs_per * _n_portions,
                        fat_out=_fat_per * _n_portions,
                        portion_label=f"{_n_portions} מנות",
                        btn_suffix=f"{_rec_id}_{_n_portions}",
                        grams=float(_n_portions * 100),
                    )
                    with st.expander("מרכיבים והוראות"):
                        _ings = _rec.get("ingredients", [])
                        if _ings:
                            for _ing in _ings:
                                st.markdown(f"• {format_ingredient_display(_ing)}")
                        _steps = get_instructions(_rec_id)
                        if _steps:
                            st.markdown("---")
                            for _si, _step in enumerate(_steps, 1):
                                st.markdown(f"**{_si}.** {_step}")
                    st.markdown('<div dir="rtl" style="height:4px"></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    else:  # ingredient mode
    # ═══════════════════════════════════════════════════════════════════════════
        search_food_id = st.selectbox(
            "",
            options=[f.food_id for f in _all_foods],
            format_func=lambda fid: _food_id_to_name.get(fid, fid),
            key="search_food_sel",
            label_visibility="collapsed",
        )
        _search_food = _catalog.get_food_by_id(search_food_id)

        if _search_food:
            _n100   = _search_food.nutrition_per_100g
            _cal100 = _n100.calories_kcal
            _sug_g  = max(50, min(round((_search_target / max(_cal100, 1)) * 100 / 10) * 10, 500))

            _portion_g = st.slider("גרמים", min_value=50, max_value=500, step=10,
                                   value=_sug_g, key="search_portion_slider")
            _r = _portion_g / 100.0
            _render_search_result(
                name=_search_food.name_he, food_id=_search_food.food_id,
                meal_key=search_meal, target_cal=_search_target,
                cal_out=_n100.calories_kcal * _r,
                prot_out=_n100.protein_g * _r,
                carbs_out=_n100.carbs_g * _r,
                fat_out=_n100.fat_g * _r,
                portion_label=f"{_portion_g}ג",
                btn_suffix=str(_portion_g),
                grams=float(_portion_g),
            )

# Manual tab
with tabs[-1]:
    st.markdown(
        '<div dir="rtl" style="font-size:0.78rem;color:#8892a4;margin-bottom:14px">הוסף מוצר ידנית לפי גרמים</div>',
        unsafe_allow_html=True,
    )
    with st.form("manual_food_form", clear_on_submit=True):
        sel_food = st.selectbox(
            "מוצר", options=[f.food_id for f in _all_foods],
            format_func=lambda fid: _food_id_to_name.get(fid, fid),
        )
        col_g, col_m = st.columns(2)
        man_grams = col_g.number_input("גרם", min_value=1, max_value=2000, value=100, step=10)
        man_meal  = col_m.selectbox("ארוחה", options=list(MEAL_TYPE_HEB.keys()),
                                    format_func=lambda k: MEAL_TYPE_HEB[k])
        if st.form_submit_button("הוסף", use_container_width=True, type="primary"):
            food_obj = _catalog.get_food_by_id(sel_food)
            if food_obj:
                ratio = man_grams / 100.0
                n = food_obj.nutrition_per_100g
                _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                    food_id=food_obj.food_id,
                    food_name=food_obj.name_he,
                    grams=float(man_grams),
                    calories=round(n.calories_kcal * ratio, 1),
                    protein=round(n.protein_g * ratio, 1),
                    carbs=round(n.carbs_g * ratio, 1),
                    fat=round(n.fat_g * ratio, 1),
                    meal_type=man_meal,
                    timestamp=datetime.now().isoformat(),
                ))
                st.success(f"✅ {food_obj.name_he} נוסף!")
                st.rerun()

    # Show today's log with edit/delete
    today_log = _food_log_repo.get_log(USER_ID, date.today())
    if today_log:
        st.markdown(
            '<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb;margin:14px 0 8px">נרשם היום</div>',
            unsafe_allow_html=True,
        )
        for entry in reversed(today_log):
            m_color = {"breakfast":"#f59e0b","morning_snack":"#a78bfa","lunch":"#4f8ef7",
                       "afternoon_snack":"#34d399","dinner":"#f87171","evening_snack":"#818cf8"}.get(entry.meal_type,"#545e70")
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                f'padding:12px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px">'
                f'<div dir="rtl" style="width:3px;height:32px;border-radius:99px;background:{m_color};flex-shrink:0"></div>'
                f'<div dir="rtl" style="flex:1">'
                f'<div dir="rtl" style="font-size:0.84rem;font-weight:600;color:#f4f6fb">{entry.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70;margin-top:2px">'
                f'{MEAL_TYPE_HEB.get(entry.meal_type,entry.meal_type)} · {entry.grams:.0f}ג׳</div></div>'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:{m_color}">{int(entry.calories)} קק״ל</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander("ערוך / מחק"):
                food_obj = _catalog.get_food_by_id(entry.food_id)
                with st.form(f"edit_food_form_{entry.entry_id}", clear_on_submit=True):
                    e_grams = st.number_input("גרם", min_value=1, max_value=2000,
                                              value=int(entry.grams), step=10)
                    e_meal  = st.selectbox("ארוחה", options=list(MEAL_TYPE_HEB.keys()),
                                           format_func=lambda k: MEAL_TYPE_HEB[k],
                                           index=list(MEAL_TYPE_HEB.keys()).index(entry.meal_type)
                                           if entry.meal_type in MEAL_TYPE_HEB else 0)
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("שמור", use_container_width=True, type="primary"):
                        _food_log_repo.remove_entry(USER_ID, date.today(), entry.entry_id)
                        if food_obj:
                            ratio = e_grams / 100.0
                            n = food_obj.nutrition_per_100g
                            _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                                food_id=food_obj.food_id, food_name=food_obj.name_he,
                                grams=float(e_grams),
                                calories=round(n.calories_kcal * ratio, 1),
                                protein=round(n.protein_g * ratio, 1),
                                carbs=round(n.carbs_g * ratio, 1),
                                fat=round(n.fat_g * ratio, 1),
                                meal_type=e_meal,
                                timestamp=entry.timestamp,
                            ))
                        st.rerun()
                    if c2.form_submit_button("מחק", use_container_width=True):
                        _food_log_repo.remove_entry(USER_ID, date.today(), entry.entry_id)
                        st.rerun()

for tab, (meal_key, meal_label, _) in zip(tabs[:-2], MEAL_SECTIONS):
    with tab:
        target_cal = meal_calories.get(meal_key, 400)

        m_color = MEAL_COLOR_MAP.get(meal_key, "#545e70")
        st.markdown(
            f'<div dir="rtl" style="display:flex;align-items:center;gap:8px;margin-bottom:14px">'
            f'<div dir="rtl" style="width:3px;height:18px;border-radius:99px;background:{m_color}"></div>'
            f'<div dir="rtl" style="font-size:0.78rem;color:#8892a4">'
            f'{MEAL_DESC[meal_key]} · יעד: <strong style="color:{m_color}">{int(target_cal)} קק״ל</strong>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

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

        for idx, recipe in enumerate(suggestions):
            portions    = max(recipe.get("portions", 1), 1)
            nut         = recipe.get("total_nutrition", {})
            cal_total   = nut.get("calories", 0)
            prot_total  = nut.get("protein",  0)
            carbs_total = nut.get("carbs",    0)
            fat_total   = nut.get("fat",      0)
            cal         = round(cal_total   / portions)
            prot        = round(prot_total  / portions, 1)
            carbs       = round(carbs_total / portions, 1)
            fat_        = round(fat_total   / portions, 1)
            recipe_id   = recipe.get("recipe_id", "")
            name_he     = recipe.get("name_he", "מתכון")
            ingredients = recipe.get("ingredients", [])

            match_pct = max(0, round(100 - abs(cal - target_cal) / max(target_cal, 1) * 100))
            _img_uri  = _image_data_uri(recipe.get("image_path", ""))

            st.markdown(
                recipe_card_html(
                    recipe,
                    image_uri=_img_uri,
                    match_pct=match_pct,
                    show_rank=(idx == 0),
                ),
                unsafe_allow_html=True,
            )

            # ── Add to food log ───────────────────────────────────────────
            btn_key    = f"add_{meal_key}_{recipe_id}_{idx}"
            added_key  = f"added_{meal_key}_{recipe_id}_{idx}"

            if st.session_state.get(added_key):
                st.markdown(
                    '<div dir="rtl" style="background:#0d2b1a;border:1px solid #1a4d2e;border-radius:12px;'
                    'padding:8px 14px;margin-bottom:8px;font-size:0.82rem;color:#4ade80;text-align:center">'
                    'נוסף לתפריט היומי</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(
                    f"הוסף לתפריט היומי · {cal} קק״ל",
                    key=btn_key,
                    use_container_width=True,
                    type="primary",
                ):
                    meal_type_lower = meal_key.lower()
                    _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                        food_id=f"recipe_{recipe_id}",
                        food_name=name_he,
                        grams=float(portions * 100),
                        calories=float(cal),
                        protein=float(prot),
                        carbs=float(carbs),
                        fat=float(fat_),
                        meal_type=meal_type_lower,
                        timestamp=datetime.now().isoformat(),
                    ))
                    st.session_state[added_key] = True
                    st.rerun()

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

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("food")
