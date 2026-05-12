#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pages/11_meal_wizard.py — Guided meal plan wizard (mobile-friendly)
"""
import os, sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from ui.components import inject_global_css, page_header, bottom_nav
from ui.user_auth import require_auth

USER_ID = require_auth()

st.set_page_config(
    page_title="אשף תפריט – BiteFit",
    page_icon="🍽️",
    layout="centered",
    initial_sidebar_state="collapsed",
)
inject_global_css()

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal, FoodCategory, MealType
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.agents.agent_6_ai import AILayer
from nutrition_app.agents.agent_5_planner.meal_planner import MEAL_CATEGORY_RULES
from nutrition_app.repositories.profile_repository import ProfileRepository

try:
    from ui_helpers import (
        save_plan_to_disk, load_plan_from_file, scan_history_plans,
        reconstruct_plan_from_dict, generate_weekly_plans,
        render_meal_card_html, PLANS_DIR,
    )
    _helpers_ok = True
except ImportError:
    _helpers_ok = False

# ── Load user profile ────────────────────────────────────────────────────────
_profile_repo = ProfileRepository()
_profile = _profile_repo.load(USER_ID)

# ── Food catalog (cached) ────────────────────────────────────────────────────
@st.cache_resource
def _load_catalog():
    cat = FoodCatalog()
    foods = cat.get_all_foods()
    by_cat = {}
    for f in foods:
        by_cat.setdefault(f.category, []).append(f)
    for c in by_cat:
        by_cat[c].sort(key=lambda x: x.name_he)
    return {f.food_id: f for f in foods}, by_cat

FOOD_LOOKUP, FOODS_BY_CATEGORY = _load_catalog()

# ── Labels ────────────────────────────────────────────────────────────────────
MEAL_LABELS = {
    MealType.BREAKFAST:       "🌅 ארוחת בוקר",
    MealType.MORNING_SNACK:   "☕ חטיף בוקר",
    MealType.LUNCH:           "🍽️ ארוחת צהריים",
    MealType.AFTERNOON_SNACK: "🍎 חטיף אחה\"צ",
    MealType.DINNER:          "🌙 ארוחת ערב",
}
CAT_LABELS = {
    FoodCategory.PROTEIN:      "🥩 חלבון",
    FoodCategory.CARBOHYDRATE: "🍚 פחמימות",
    FoodCategory.FAT:          "🫒 שומן",
    FoodCategory.VEGETABLE:    "🥬 ירקות",
    FoodCategory.FRUIT:        "🍎 פירות",
    FoodCategory.DAIRY:        "🧀 חלבי",
    FoodCategory.GRAIN:        "🌾 דגנים",
    FoodCategory.LEGUME:       "🫘 קטניות",
    FoodCategory.NUT_SEED:     "🥜 אגוזים",
    FoodCategory.CONDIMENT:    "🧂 תבלינים",
    FoodCategory.BEVERAGE:     "☕ משקאות",
    FoodCategory.OTHER:        "📦 אחר",
}
WIZARD_MEALS = [
    MealType.BREAKFAST, MealType.MORNING_SNACK,
    MealType.LUNCH, MealType.AFTERNOON_SNACK, MealType.DINNER,
]

# ── Wizard helpers ────────────────────────────────────────────────────────────
def _init_wizard():
    st.session_state.update({
        "wiz_active": True, "wiz_meal_idx": 0, "wiz_cat_idx": 0,
        "wiz_selections": {}, "wiz_skipped": set(),
    })
    st.session_state.pop("wiz_completed", None)
    st.session_state.pop("wiz_plan", None)

def _wiz_cats(meal):
    valid = MEAL_CATEGORY_RULES.get(meal, [])
    return [c for c in valid if c in FOODS_BY_CATEGORY and FOODS_BY_CATEGORY[c]]

def _wiz_total_steps():
    return sum(len(_wiz_cats(m)) for m in WIZARD_MEALS)

def _wiz_current_step():
    mi = st.session_state.get("wiz_meal_idx", 0)
    ci = st.session_state.get("wiz_cat_idx", 0)
    step = sum(len(_wiz_cats(WIZARD_MEALS[i])) for i in range(mi))
    return step + ci

def _wiz_advance():
    mi = st.session_state["wiz_meal_idx"]
    ci = st.session_state["wiz_cat_idx"]
    cats = _wiz_cats(WIZARD_MEALS[mi])
    if ci + 1 < len(cats):
        st.session_state["wiz_cat_idx"] = ci + 1
    elif mi + 1 < len(WIZARD_MEALS):
        st.session_state["wiz_meal_idx"] = mi + 1
        st.session_state["wiz_cat_idx"] = 0
    else:
        st.session_state["wiz_completed"] = True
        st.session_state["wiz_active"] = False

def _wiz_skip_meal():
    mi = st.session_state["wiz_meal_idx"]
    st.session_state["wiz_skipped"].add(WIZARD_MEALS[mi].value)
    if mi + 1 < len(WIZARD_MEALS):
        st.session_state["wiz_meal_idx"] = mi + 1
        st.session_state["wiz_cat_idx"] = 0
    else:
        st.session_state["wiz_completed"] = True
        st.session_state["wiz_active"] = False

def _build_user():
    from datetime import date as date_cls
    dob_str = _profile.get("date_of_birth", "1990-01-01")
    try:
        dob = date_cls.fromisoformat(dob_str)
    except Exception:
        dob = date_cls(1990, 1, 1)
    return UserProfile(
        user_id=USER_ID,
        name=_profile.get("name", "משתמש"),
        gender=Gender(_profile.get("gender", "male")),
        date_of_birth=dob,
        height_cm=float(_profile.get("height_cm", 175)),
        weight_kg=float(_profile.get("weight_kg", 75)),
        activity_level=ActivityLevel(_profile.get("activity_level", "moderately_active")),
        goal=Goal(_profile.get("goal", "maintain")),
    )

def _run_pipeline():
    all_ids = set()
    for cats in st.session_state.get("wiz_selections", {}).values():
        for fids in cats.values():
            all_ids.update(fids)
    if not all_ids:
        st.error("בחר לפחות מזון אחד.")
        return None
    user = _build_user()
    engine = NutritionEngine()
    targets = engine.calculate_targets(user)
    food_names = [FOOD_LOOKUP[fid].name_he for fid in all_ids if fid in FOOD_LOOKUP]
    catalog = FoodCatalog()
    match_result = catalog.match_foods(food_names)
    inv_manager = InventoryManager()
    inv_state = inv_manager.get_state(user.user_id)
    planner = MealPlanner()
    planner.set_food_lookup(dict(FOOD_LOOKUP))
    planner.load_extended_catalog()
    plan = planner.generate_plan(
        targets=targets, food_matches=match_result,
        inventory=inv_state, run_id=f"wiz_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    changeset = inv_manager.deduct_for_plan(user.user_id, plan, plan.run_id)
    if _helpers_ok:
        save_plan_to_disk(plan, suffix="daily")
    return user, targets, plan, changeset

# ── Page header ───────────────────────────────────────────────────────────────
page_header("אשף תפריט", "plate", subtitle="בניית תפריט יומי מותאם אישית")

# ── State routing ─────────────────────────────────────────────────────────────
has_plan    = "wiz_plan" in st.session_state
is_active   = st.session_state.get("wiz_active", False)
is_complete = st.session_state.get("wiz_completed", False)

# Reset button (top)
if has_plan or is_complete or is_active:
    if st.button("🔄 התחל מחדש", use_container_width=True):
        for k in ["wiz_active","wiz_meal_idx","wiz_cat_idx","wiz_selections",
                  "wiz_skipped","wiz_completed","wiz_plan"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# START SCREEN
# ══════════════════════════════════════════════════════════════════════════════
if not is_active and not is_complete and not has_plan:
    st.markdown(
        '<div style="text-align:center;padding:32px 0 20px">'
        '<div style="font-size:3em">🍽️</div>'
        '<div style="font-size:1.2em;font-weight:700;margin:12px 0 6px">בוא נבנה לך תפריט מותאם אישית</div>'
        '<div style="color:#888;font-size:0.9em">נעבור יחד על כל ארוחה ותבחר מזונות שאתה אוהב</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("🚀 התחל בבחירת מזון", type="primary", use_container_width=True):
        _init_wizard()
        st.rerun()

    # History
    if _helpers_ok:
        st.divider()
        st.markdown("### 📋 תפריטים קודמים")
        if "wiz_history" not in st.session_state:
            st.session_state["wiz_history"] = scan_history_plans()
        history = st.session_state["wiz_history"]
        if not history:
            st.info("אין תפריטים שמורים עדיין.")
        else:
            for i, entry in enumerate(history[:5]):
                with st.container():
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.markdown(f"**{entry.get('plan_date','?')}**")
                    c2.caption(f"{entry.get('total_calories',0):.0f} קק\"ל")
                    if c3.button("👁", key=f"hist_{i}"):
                        fp = os.path.join(PLANS_DIR, entry["filename"])
                        try:
                            pd = load_plan_from_file(fp)
                            pl = reconstruct_plan_from_dict(pd)
                            st.session_state["wiz_view_hist"] = pl
                            st.rerun()
                        except Exception:
                            st.error("שגיאה בטעינת תפריט")

        if "wiz_view_hist" in st.session_state:
            pl = st.session_state["wiz_view_hist"]
            st.divider()
            if st.button("← חזור"):
                st.session_state.pop("wiz_view_hist", None)
                st.rerun()
            st.markdown(f"#### תפריט {pl.plan_date}")
            c1,c2,c3 = st.columns(3)
            c1.metric("קלוריות", f"{pl.total_calories:.0f}")
            c2.metric("יעד", f"{pl.target_calories_kcal:.0f}")
            c3.metric("סטייה", f"{pl.calorie_deviation_pct:+.1f}%")
            for m in pl.meals:
                st.markdown(render_meal_card_html(m), unsafe_allow_html=True)

    bottom_nav("home")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# ACTIVE WIZARD
# ══════════════════════════════════════════════════════════════════════════════
if is_active:
    mi    = st.session_state["wiz_meal_idx"]
    ci    = st.session_state["wiz_cat_idx"]
    meal  = WIZARD_MEALS[mi]
    cats  = _wiz_cats(meal)
    if ci >= len(cats):
        _wiz_advance(); st.rerun()

    current_cat = cats[ci]
    meal_lbl    = MEAL_LABELS.get(meal, meal.value)
    cat_lbl     = CAT_LABELS.get(current_cat, current_cat.value)

    # Progress bar
    total = _wiz_total_steps()
    cur   = _wiz_current_step()
    st.progress(min(int(cur / max(total,1) * 100), 100))
    st.caption(f"ארוחה {mi+1}/{len(WIZARD_MEALS)} · קטגוריה {ci+1}/{len(cats)}")

    st.markdown(
        f'<div style="background:#1a1a2e;border-radius:14px;padding:18px;margin:8px 0;'
        f'border:1px solid #333;direction:rtl">'
        f'<div style="font-size:1.1em;font-weight:700;color:#ffd54f">{meal_lbl}</div>'
        f'<div style="font-size:0.95em;color:#aaa;margin-top:4px">בחר {cat_lbl}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    foods_here = FOODS_BY_CATEGORY.get(current_cat, [])
    names_here = [f.name_he for f in foods_here]
    selected   = st.multiselect(
        "בחר מזונות:",
        options=names_here,
        key=f"wsel_{meal.value}_{current_cat.value}",
    )

    is_last = (mi == len(WIZARD_MEALS)-1 and ci == len(cats)-1)
    col_skip, col_next = st.columns(2)

    with col_skip:
        if st.button("⏭️ דלג על ארוחה", use_container_width=True):
            _wiz_skip_meal(); st.rerun()

    with col_next:
        if st.button("סיים ✓" if is_last else "הבא ❯",
                     type="primary", use_container_width=True):
            if selected:
                n2f = {f.name_he: f for f in foods_here}
                sel_ids = [n2f[n].food_id for n in selected if n in n2f]
                st.session_state["wiz_selections"].setdefault(meal.value, {})[current_cat.value] = sel_ids
            _wiz_advance(); st.rerun()

    # Show running summary
    sels = st.session_state.get("wiz_selections", {})
    total_sel = sum(len(v) for d in sels.values() for v in d.values())
    if total_sel:
        st.caption(f"נבחרו עד כה: {total_sel} מזונות")

    bottom_nav("home")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# WIZARD COMPLETE — Summary + Generate
# ══════════════════════════════════════════════════════════════════════════════
if is_complete and not has_plan:
    st.markdown("## ✅ סיכום הבחירות")

    sels   = st.session_state.get("wiz_selections", {})
    skip   = st.session_state.get("wiz_skipped", set())
    total_f = 0

    for meal in WIZARD_MEALS:
        lbl = MEAL_LABELS.get(meal, meal.value)
        if meal.value in skip:
            st.markdown(
                f'<div style="background:#2a1a1a;border-radius:10px;padding:10px 14px;margin:6px 0;'
                f'direction:rtl;color:#888">{lbl} — <span style="color:#ef5350">דולג</span></div>',
                unsafe_allow_html=True,
            )
            continue
        cats_d = sels.get(meal.value, {})
        chips  = ""
        cnt    = 0
        for fids in cats_d.values():
            for fid in fids:
                f = FOOD_LOOKUP.get(fid)
                if f:
                    chips += (f'<span style="display:inline-block;background:#1b5e20;color:#a5d6a7;'
                              f'padding:3px 10px;border-radius:16px;font-size:0.82em;margin:2px">'
                              f'{f.name_he}</span>')
                    cnt += 1; total_f += 1
        if cnt:
            st.markdown(
                f'<div style="background:#1a1a2e;border-radius:12px;padding:12px 16px;margin:6px 0;'
                f'border:1px solid #333;direction:rtl">'
                f'<div style="font-weight:700;color:#ffd54f;margin-bottom:6px">'
                f'{lbl} <span style="color:#888;font-size:0.82em">({cnt})</span></div>'
                f'{chips}</div>',
                unsafe_allow_html=True,
            )

    st.markdown(f"**סה\"כ: {total_f} מזונות**")

    if total_f == 0:
        st.warning("לא נבחרו מזונות.")
        if st.button("← חזור לבחירה"):
            _init_wizard(); st.rerun()
    else:
        st.divider()
        if st.button("▶ הפק תפריט יומי", type="primary", use_container_width=True):
            with st.spinner("מחשב תפריט..."):
                result = _run_pipeline()
            if result:
                user_o, targets, plan, changeset = result
                st.session_state["wiz_plan"] = {
                    "user": user_o, "targets": targets,
                    "plan": plan, "changeset": changeset,
                }
                st.rerun()

    bottom_nav("home")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# PLAN RESULTS
# ══════════════════════════════════════════════════════════════════════════════
if has_plan:
    data     = st.session_state["wiz_plan"]
    plan     = data["plan"]
    targets  = data["targets"]
    user_o   = data["user"]
    changeset = data["changeset"]

    st.toast("התפריט נוצר בהצלחה! ✅")

    dev = plan.calorie_deviation_pct
    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 יעד", f"{targets.target_calories_kcal:.0f}")
    c2.metric("🍽️ תפריט", f"{plan.total_calories:.0f}")
    c3.metric("📊 סטייה", f"{dev:+.1f}%")

    st.divider()
    st.markdown("### ארוחות היום")

    for meal in plan.meals:
        meal_lbl = MEAL_LABELS.get(meal.meal_type, meal.meal_type.value if hasattr(meal.meal_type,'value') else str(meal.meal_type))
        st.markdown(
            f'<div style="background:#1a1a2e;border-radius:14px;padding:14px 16px;margin:8px 0;'
            f'border:1px solid #333;direction:rtl">'
            f'<div style="font-weight:700;color:#ffd54f;margin-bottom:8px">{meal_lbl} · '
            f'<span style="color:#aaa;font-weight:400">{meal.total_calories:.0f} קק"ל</span></div>'
            + "".join(
                f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
                f'border-bottom:1px solid #222;font-size:0.9em">'
                f'<span style="color:#e0e0e0">{item.food_name}</span>'
                f'<span style="color:#888">{item.grams:.0f}g · {item.calories:.0f} קק"ל</span></div>'
                for item in meal.items
            )
            + '</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    p1, p2, p3 = st.columns(3)
    p1.metric("🥩 חלבון", f"{plan.total_protein:.0f}g")
    p2.metric("🍞 פחמימות", f"{plan.total_carbs:.0f}g")
    p3.metric("🥑 שומן", f"{plan.total_fat:.0f}g")

bottom_nav("home")
