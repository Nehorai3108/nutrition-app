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
from nutrition_app.repositories.profile_repository import ProfileRepository

from ui.components import inject_global_css, recipe_card_html, bottom_nav
from ui.images import image_data_uri as _image_data_uri
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.utils.household_units import get_unit_info, grams_to_household, suggested_quantity

USER_ID = "ui_user_001"
_food_log_repo = FoodLogRepository()

# Load user allergies from profile
_profile_repo = ProfileRepository()
_profile = _profile_repo.load(USER_ID)
_user_allergens: list = _profile.get("meal_preferences", {}).get("allergies", [])

st.set_page_config(page_title="BiteFit · תפריט", page_icon="🍽️", layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

@st.cache_resource
def get_mgr(_version=2):
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
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#4f8ef7;letter-spacing:-0.01em">BiteFit</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{date.today().strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Meal tab selector ─────────────────────────────────────────────────────────
tab_labels = [label for _, label, _ in MEAL_SECTIONS] + ["חיפוש", "✏️ ידני", "🍫 נשנוש"]
tabs = st.tabs(tab_labels)

_catalog = get_catalog()
_all_foods = sorted(_catalog.get_all_foods(), key=lambda f: f.name_he)
_food_id_to_name = {f.food_id: f.name_he for f in _all_foods}

MEAL_TYPE_HEB = {
    "breakfast": "ארוחת בוקר", "morning_snack": "חטיף בוקר",
    "lunch": "ארוחת צהריים", "afternoon_snack": "חטיף אחה״צ",
    "dinner": "ארוחת ערב", "evening_snack": "חטיף ערב",
    "snack": "נשנוש",
}

# ── helper: ingredient chips ─────────────────────────────────────────────────
def _ingredient_chips_html(ingredients: list, max_show: int = 5) -> str:
    """Render ingredient list as compact inline chips (like a recipe card)."""
    chips = []
    for ing in ingredients[:max_show]:
        label = format_ingredient_display(ing)
        if label:
            chips.append(
                f'<span style="background:#1a2235;border:1px solid #252d3d;'
                f'border-radius:99px;padding:3px 10px;font-size:0.72rem;'
                f'color:#c4cdd8;white-space:nowrap">{label}</span>'
            )
    if not chips:
        return ""
    more = (f'<span style="font-size:0.7rem;color:#545e70;align-self:center">'
            f'+{len(ingredients)-max_show}</span>') if len(ingredients) > max_show else ""
    return (
        f'<div dir="rtl" style="display:flex;flex-wrap:wrap;gap:5px;margin:8px 0 4px">'
        + "".join(chips) + more + "</div>"
    )


# ── helper: render a nutrition result card + add button ───────────────────────
def _render_search_result(
    name: str, food_id: str, meal_key: str, target_cal: int,
    cal_out: float, prot_out: float, carbs_out: float, fat_out: float,
    portion_label: str, btn_suffix: str, grams: float = 0.0,
    is_recipe: bool = False,
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
        + (
            f'<div dir="rtl" style="flex:1;font-size:0.82rem;color:#c4cdd8;line-height:1.6">{portion_label}</div>'
            if is_recipe else
            f'<div dir="rtl" style="font-size:2.4rem;font-weight:900;color:#f4f6fb;line-height:1">{portion_label}</div>'
            f'<div dir="rtl" style="flex:1"></div>'
        ) +
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
with tabs[-3]:
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

                    _ings = _rec.get("ingredients", [])
                    _ing_chips = _ingredient_chips_html(_ings) if _ings else ""
                    _approx_g  = 200  # ~1 portion
                    _render_search_result(
                        name=_rec_name, food_id=f"recipe_{_rec_id}",
                        meal_key=search_meal, target_cal=_search_target,
                        cal_out=_cal_per_por,
                        prot_out=_prot_per,
                        carbs_out=_carbs_per,
                        fat_out=_fat_per,
                        portion_label=_ing_chips or _rec_name,
                        btn_suffix=f"{_rec_id}_1",
                        grams=float(_approx_g),
                        is_recipe=True,
                    )
                    with st.expander("הוראות הכנה"):
                        _steps = get_instructions(_rec_id)
                        if _steps:
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
            _s_unit_info = get_unit_info(_search_food.name_he)

            if _s_unit_info:
                _s_unit_he, _s_gpunit = _s_unit_info
                _sug_n, _, _ = suggested_quantity(_search_food.name_he, _search_target, _cal100)
                _s_n_units = st.number_input(
                    f"כמות ({_s_unit_he})",
                    min_value=0.5, max_value=30.0,
                    value=float(_sug_n), step=0.5,
                    key="search_portion_units",
                )
                _portion_g = _s_n_units * _s_gpunit
                _s_qty_str = str(int(_s_n_units)) if _s_n_units == int(_s_n_units) else f"{_s_n_units:.1f}"
                _s_plural  = "ות" if _s_unit_he == "יחידה" and _s_n_units > 1 else ""
                _s_plabel  = f"{_s_qty_str} {_s_unit_he}{_s_plural}"
            else:
                _sug_g = max(50, min(round((_search_target / max(_cal100, 1)) * 100 / 10) * 10, 500))
                _portion_g = st.slider("גרמים", min_value=10, max_value=500, step=10,
                                       value=_sug_g, key="search_portion_slider")
                _s_plabel = f"{int(_portion_g)}ג"

            _r = _portion_g / 100.0
            _render_search_result(
                name=_search_food.name_he, food_id=_search_food.food_id,
                meal_key=search_meal, target_cal=_search_target,
                cal_out=_n100.calories_kcal * _r,
                prot_out=_n100.protein_g * _r,
                carbs_out=_n100.carbs_g * _r,
                fat_out=_n100.fat_g * _r,
                portion_label=_s_plabel,
                btn_suffix=str(int(_portion_g)),
                grams=float(_portion_g),
            )

# Manual tab
with tabs[-2]:
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
        _man_meal_opts = [k for k in MEAL_TYPE_HEB.keys() if k != "snack"]
        man_meal  = col_m.selectbox("ארוחה", options=_man_meal_opts,
                                    format_func=lambda k: MEAL_TYPE_HEB[k])
        # Show household equivalent hint (outside the columns, inside form)
        _man_food_obj_hint = _catalog.get_food_by_id(sel_food)
        if _man_food_obj_hint:
            _man_hint = grams_to_household(_man_food_obj_hint.name_he, float(man_grams))
            if not _man_hint.endswith("ג"):  # only show if a real unit was found
                st.markdown(
                    f'<div dir="rtl" style="font-size:0.75rem;color:#8892a4;margin:-6px 0 4px">'
                    f'≈ {_man_hint}</div>',
                    unsafe_allow_html=True,
                )
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
                       "afternoon_snack":"#34d399","dinner":"#f87171","evening_snack":"#818cf8",
                       "snack":"#fb923c"}.get(entry.meal_type,"#545e70")
            # Parse timestamp for display
            try:
                _ts = datetime.fromisoformat(entry.timestamp)
                _time_str = _ts.strftime("%H:%M")
            except Exception:
                _time_str = ""
            _meal_label = MEAL_TYPE_HEB.get(entry.meal_type, entry.meal_type)
            _meta = f'{_meal_label} · {entry.grams:.0f}ג׳'
            if _time_str:
                _meta += f' · {_time_str}'
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                f'padding:12px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px">'
                f'<div dir="rtl" style="width:3px;height:32px;border-radius:99px;background:{m_color};flex-shrink:0"></div>'
                f'<div dir="rtl" style="flex:1">'
                f'<div dir="rtl" style="font-size:0.84rem;font-weight:600;color:#f4f6fb">{entry.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70;margin-top:2px">'
                f'{_meta}</div></div>'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:{m_color}">{int(entry.calories)} קק״ל</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander("ערוך / מחק"):
                food_obj = _catalog.get_food_by_id(entry.food_id)
                with st.form(f"edit_food_form_{entry.entry_id}", clear_on_submit=True):
                    e_grams = st.number_input("גרם", min_value=1, max_value=2000,
                                              value=max(1, int(entry.grams)), step=10)
                    _edit_meal_opts = [k for k in MEAL_TYPE_HEB.keys() if k != "snack"]
                    e_meal  = st.selectbox("ארוחה", options=_edit_meal_opts,
                                           format_func=lambda k: MEAL_TYPE_HEB[k],
                                           index=_edit_meal_opts.index(entry.meal_type)
                                           if entry.meal_type in _edit_meal_opts else 0)
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

for tab, (meal_key, meal_label, _) in zip(tabs[:-3], MEAL_SECTIONS):
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
                allergens=_user_allergens if _user_allergens else None,
            )[:3]
        except Exception as _e:
            st.error(f"שגיאה: {_e}")
            suggestions = []

        if not suggestions:
            st.info("אין מתכונים מתאימים לארוחה זו.")

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

            # ── Ingredient chips ──────────────────────────────────────
            if ingredients:
                st.markdown(_ingredient_chips_html(ingredients), unsafe_allow_html=True)

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

        # ── In-meal food search ───────────────────────────────────────────────
        st.markdown('<div dir="rtl" style="height:10px"></div>', unsafe_allow_html=True)
        with st.expander("🔍 לא מצאת מה שרצית? חפש כאן"):
            _ms_mode = st.radio(
                "",
                options=["ingredient", "recipe"],
                format_func=lambda m: {
                    "ingredient": "🥚 רכיב / מוצר",
                    "recipe":     "🍳 מנה מוכנה",
                }[m],
                horizontal=True,
                key=f"ms_mode_{meal_key}",
                label_visibility="collapsed",
            )

            # ── Ingredient search ─────────────────────────────────────────────
            if _ms_mode == "ingredient":
                _ms_query = st.text_input(
                    "",
                    placeholder="חפש: ביצה, אבוקדו, לחם...",
                    key=f"ms_q_{meal_key}",
                    label_visibility="collapsed",
                )
                _ms_q = _ms_query.strip()
                if _ms_q:
                    _ms_results = _catalog.search_foods(_ms_q, limit=5)
                    if not _ms_results:
                        st.markdown(
                            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                            f'border-radius:12px;padding:14px;text-align:center;color:#545e70;'
                            f'font-size:0.8rem">לא נמצא עבור "{_ms_q}"</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        for _mf in _ms_results:
                            _mn100   = _mf.nutrition_per_100g
                            _mcal100 = _mn100.calories_kcal
                            _unit_info = get_unit_info(_mf.name_he)

                            if _unit_info:
                                _unit_he, _gpunit = _unit_info
                                _sug_n, _, _ = suggested_quantity(
                                    _mf.name_he, target_cal, _mcal100
                                )
                                _n_units = st.number_input(
                                    f"{_mf.name_he} — {_unit_he}",
                                    min_value=0.5, max_value=30.0,
                                    value=float(_sug_n), step=0.5,
                                    key=f"ms_g_{meal_key}_{_mf.food_id}",
                                )
                                _mg = _n_units * _gpunit
                                _qty_str = str(int(_n_units)) if _n_units == int(_n_units) else f"{_n_units:.1f}"
                                _plural = "ות" if _unit_he == "יחידה" and _n_units > 1 else ""
                                _plabel = f"{_qty_str} {_unit_he}{_plural}"
                            else:
                                _msg = max(10, min(
                                    round((target_cal / max(_mcal100, 1)) * 100 / 10) * 10, 500
                                ))
                                _mg = st.slider(
                                    f"{_mf.name_he} — גרמים",
                                    min_value=10, max_value=500, step=10, value=_msg,
                                    key=f"ms_g_{meal_key}_{_mf.food_id}",
                                )
                                _plabel = f"{int(_mg)}ג"

                            _mr = _mg / 100.0
                            _render_search_result(
                                name=_mf.name_he,
                                food_id=_mf.food_id,
                                meal_key=meal_key.lower(),
                                target_cal=target_cal,
                                cal_out=_mn100.calories_kcal * _mr,
                                prot_out=_mn100.protein_g * _mr,
                                carbs_out=_mn100.carbs_g * _mr,
                                fat_out=_mn100.fat_g * _mr,
                                portion_label=_plabel,
                                btn_suffix=f"ms_{meal_key}_{int(_mg)}_{_mf.food_id}",
                                grams=float(_mg),
                            )
                else:
                    st.markdown(
                        '<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                        'border-radius:12px;padding:14px;text-align:center;color:#545e70;'
                        'font-size:0.8rem">הקלד שם מוצר לחיפוש</div>',
                        unsafe_allow_html=True,
                    )

            # ── Recipe search ─────────────────────────────────────────────────
            else:
                _msr_query = st.text_input(
                    "",
                    placeholder="חפש מנה: שקשוקה, חביתה, עוף...",
                    key=f"msr_q_{meal_key}",
                    label_visibility="collapsed",
                )
                _msr_q = _msr_query.strip()
                if _msr_q:
                    _msr_results = recipe_mgr.search_recipes(
                        RecipeFilter(search_text=_msr_q, max_results=5)
                    )
                    if not _msr_results:
                        st.markdown(
                            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                            f'border-radius:12px;padding:14px;text-align:center;color:#545e70;'
                            f'font-size:0.8rem">לא נמצאו מנות עבור "{_msr_q}"</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        for _mrec in _msr_results:
                            _mportions = max(_mrec.get("portions", 1), 1)
                            _mnut      = _mrec.get("total_nutrition", {})
                            _mcpp      = _mnut.get("calories", 0) / _mportions
                            _mppp      = _mnut.get("protein",  0) / _mportions
                            _mcarb     = _mnut.get("carbs",    0) / _mportions
                            _mfat      = _mnut.get("fat",      0) / _mportions
                            _mrid      = _mrec.get("recipe_id", "")
                            _mrname    = _mrec.get("name_he", "מנה")
                            _mrings    = _mrec.get("ingredients", [])
                            _mr_chips  = _ingredient_chips_html(_mrings) if _mrings else _mrname
                            _render_search_result(
                                name=_mrname,
                                food_id=f"recipe_{_mrid}",
                                meal_key=meal_key.lower(),
                                target_cal=target_cal,
                                cal_out=_mcpp,
                                prot_out=_mppp,
                                carbs_out=_mcarb,
                                fat_out=_mfat,
                                portion_label=_mr_chips,
                                btn_suffix=f"ms_{meal_key}_{_mrid}_1",
                                grams=200.0,
                                is_recipe=True,
                            )
                else:
                    st.markdown(
                        '<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                        'border-radius:12px;padding:14px;text-align:center;color:#545e70;'
                        'font-size:0.8rem">הקלד שם מנה לחיפוש</div>',
                        unsafe_allow_html=True,
                    )

# ── Snack tab (last tab) ─────────────────────────────────────────────────────
with tabs[-1]:
    st.markdown(
        '<div dir="rtl" style="font-size:0.9rem;font-weight:700;color:#f4f6fb;margin-bottom:4px">הוסף נשנוש חופשי</div>'
        '<div dir="rtl" style="font-size:0.75rem;color:#8892a4;margin-bottom:16px">אכלת משהו קטן? הוסף אותו כאן ללא קשר לארוחות</div>',
        unsafe_allow_html=True,
    )

    _snack_mode = st.radio(
        "",
        options=["free", "catalog"],
        format_func=lambda m: {"free": "הזנה חופשית (שם + קלוריות)", "catalog": "מהרשימה"}[m],
        horizontal=True,
        key="snack_mode_radio",
        label_visibility="collapsed",
    )

    if _snack_mode == "free":
        with st.form("snack_free_form", clear_on_submit=True):
            _snack_name = st.text_input("שם המאכל", placeholder="לדוגמה: קוביית שוקולד")
            _sc1, _sc2, _sc3, _sc4 = st.columns(4)
            _snack_cal   = _sc1.number_input("קלוריות", min_value=1, max_value=2000, value=100, step=5)
            _snack_prot  = _sc2.number_input("חלבון (g)", min_value=0.0, max_value=200.0, value=0.0, step=0.5)
            _snack_carbs = _sc3.number_input("פחמימות (g)", min_value=0.0, max_value=200.0, value=0.0, step=0.5)
            _snack_fat   = _sc4.number_input("שומן (g)", min_value=0.0, max_value=200.0, value=0.0, step=0.5)
            if st.form_submit_button("הוסף נשנוש", use_container_width=True, type="primary"):
                if _snack_name.strip():
                    _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                        food_id="snack_free",
                        food_name=_snack_name.strip(),
                        grams=0.0,
                        calories=float(_snack_cal),
                        protein=float(_snack_prot),
                        carbs=float(_snack_carbs),
                        fat=float(_snack_fat),
                        meal_type="snack",
                        timestamp=datetime.now().isoformat(),
                    ))
                    st.success(f"נוסף: {_snack_name.strip()} · {_snack_cal} קק״ל")
                    st.rerun()
                else:
                    st.warning("יש להזין שם מאכל")
    else:
        with st.form("snack_catalog_form", clear_on_submit=True):
            _snack_food_id = st.selectbox(
                "בחר מוצר",
                options=[f.food_id for f in _all_foods],
                format_func=lambda fid: _food_id_to_name.get(fid, fid),
            )
            _snack_grams = st.number_input("גרמים", min_value=1, max_value=500, value=30, step=5)
            if st.form_submit_button("הוסף נשנוש", use_container_width=True, type="primary"):
                _sf = _catalog.get_food_by_id(_snack_food_id)
                if _sf:
                    _sr = _snack_grams / 100.0
                    _sn = _sf.nutrition_per_100g
                    _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                        food_id=_sf.food_id,
                        food_name=_sf.name_he,
                        grams=float(_snack_grams),
                        calories=round(_sn.calories_kcal * _sr, 1),
                        protein=round(_sn.protein_g * _sr, 1),
                        carbs=round(_sn.carbs_g * _sr, 1),
                        fat=round(_sn.fat_g * _sr, 1),
                        meal_type="snack",
                        timestamp=datetime.now().isoformat(),
                    ))
                    st.success(f"נוסף: {_sf.name_he} · {round(_sn.calories_kcal * _sr)} קק״ל")
                    st.rerun()

    # Show today's snacks
    _today_snacks = [e for e in _food_log_repo.get_log(USER_ID, date.today()) if e.meal_type == "snack"]
    if _today_snacks:
        st.markdown(
            '<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb;margin:16px 0 8px">נשנושים היום</div>',
            unsafe_allow_html=True,
        )
        _snack_total = sum(e.calories for e in _today_snacks)
        for _se in reversed(_today_snacks):
            try:
                _sts = datetime.fromisoformat(_se.timestamp).strftime("%H:%M")
            except Exception:
                _sts = ""
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                f'padding:11px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px">'
                f'<div dir="rtl" style="width:3px;height:28px;border-radius:99px;background:#fb923c;flex-shrink:0"></div>'
                f'<div dir="rtl" style="flex:1">'
                f'<div dir="rtl" style="font-size:0.84rem;font-weight:600;color:#f4f6fb">{_se.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70;margin-top:2px">'
                f'נשנוש{(" · " + _sts) if _sts else ""}</div></div>'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#fb923c">{int(_se.calories)} קק״ל</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div dir="rtl" style="text-align:left;font-size:0.75rem;color:#8892a4;margin-top:4px">'
            f'סה״כ נשנושים: <strong style="color:#fb923c">{int(_snack_total)} קק״ל</strong></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("food")
