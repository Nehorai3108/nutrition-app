#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pages/13_meal_preferences.py — First-login meal-preferences picker.

A six-step wizard that turns a fresh user into a fully-populated
UserMealPreferences + weekly plan:

  0. Welcome
  1. Liked ingredients — macro-grouped multiselects over the food catalog.
     Used to soft-rank meal suggestions in step 2 (allergies/dislikes still
     hard-filter, this only changes ordering).
  2. Pick per category (breakfast, lunch, dinner, post-workout, treat)
     Each card: Pick or Adjust (ingredient quantity overrides) → variant.
  3. Fixed-day overrides ("every Friday breakfast = treat")
  4. Weekly review with live macro deltas vs. daily targets
  5. Save & redirect to pages/6_daily_menu.py

All mutations route through MealAdjustmentService so the same logic powers
a future AI agent.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from ui.components import (
    inject_global_css, page_header, section_header,
    macro_delta_html, meal_picker_card_html, kashrut_badge_html, macro_grid_html,
)
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth, logout_button

from nutrition_app.repositories.profile_repository import ProfileRepository
from nutrition_app.services.meal_adjustment_service import (
    MealAdjustmentService, compute_variant_nutrition,
)
from nutrition_app.services.recipe_suggestion_service import (
    RecipeSuggestionService, INGREDIENT_GROUPS,
)
from nutrition_app.agents.agent_5_planner.weekly_planner import WeeklyPlanner
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.models.user_meal_preferences import MEAL_TYPE_KEYS, WEEKDAYS

# ── Page setup ──────────────────────────────────────────────────────────────
setup_persistent_auth()
USER_ID = require_auth()

st.set_page_config(
    page_title="BiteFit · בחירת ארוחות",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()

with st.sidebar:
    st.markdown(
        f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">👤 '
        f'{st.session_state.get("bitefit_user", {}).get("email", "")}</div>',
        unsafe_allow_html=True,
    )
    logout_button()

# ── Hebrew labels for the five picker categories ────────────────────────────
MEAL_TYPE_LABELS_HE = {
    "breakfast":   "🌅 ארוחת בוקר",
    "lunch":       "🍽 ארוחת צהריים",
    "dinner":      "🌙 ארוחת ערב",
    "post_workout": "💪 ארוחה אחרי אימון",
    "treat":       "🍪 פינוק מתוק",
}

MEAL_TYPE_HELP_HE = {
    "breakfast":   "בחר 2–4 אפשרויות בוקר. נסובב ביניהן במהלך השבוע.",
    "lunch":       "בחר 2–4 אפשרויות צהריים שמתאימות לך.",
    "dinner":      "בחר 2–4 אפשרויות ערב.",
    "post_workout": "ארוחה עשירה בחלבון לימים שיש אימון. אפשרות אחת או יותר.",
    "treat":       "פינוק מתוק לסוף השבוע או יום קשה. אופציונלי — בחר אחד אם תרצה.",
}

WEEKDAYS_HE = {
    "monday": "שני", "tuesday": "שלישי", "wednesday": "רביעי",
    "thursday": "חמישי", "friday": "שישי", "saturday": "שבת", "sunday": "ראשון",
}

MIN_PICKS = {
    "breakfast": 2, "lunch": 2, "dinner": 2, "post_workout": 1, "treat": 0,
}

# ── Cached services ─────────────────────────────────────────────────────────
@st.cache_resource
def _svc() -> MealAdjustmentService:
    return MealAdjustmentService()

@st.cache_resource
def _suggest_svc() -> RecipeSuggestionService:
    return RecipeSuggestionService()

@st.cache_resource
def _recipe_mgr() -> RecipeManager:
    return RecipeManager()

svc = _svc()
sugg = _suggest_svc()
mgr = _recipe_mgr()

# ── Load profile + initialize prefs ─────────────────────────────────────────
profile_repo = ProfileRepository()
profile = profile_repo.load(USER_ID) or {}

# Bail out if user hasn't completed the profile yet — they need allergies
# and kashrut before we can filter properly.
if not profile.get("name"):
    st.warning("יש להשלים תחילה את פרופיל המשתמש.")
    if st.button("המשך לפרופיל"):
        st.switch_page("pages/0_profile.py")
    st.stop()

prefs = svc.load_or_init(USER_ID)

# ── Daily targets (best-effort) ─────────────────────────────────────────────
def _compute_targets() -> dict:
    """Use NutritionEngine when the profile has the required fields."""
    try:
        from datetime import date as _date
        from nutrition_app.models.user import UserProfile
        from nutrition_app.models.enums import Gender, ActivityLevel, Goal
        from nutrition_app.agents.agent_2_nutrition import NutritionEngine

        dob_raw = profile.get("date_of_birth")
        if not dob_raw:
            raise ValueError("missing dob")
        dob = _date.fromisoformat(dob_raw) if isinstance(dob_raw, str) else dob_raw
        user = UserProfile(
            user_id=USER_ID,
            name=profile.get("name", ""),
            gender=Gender(profile.get("gender", "male")),
            date_of_birth=dob,
            height_cm=float(profile.get("height_cm") or 170),
            weight_kg=float(profile.get("weight_kg") or 70),
            activity_level=ActivityLevel(profile.get("activity_level", "moderately_active")),
            goal=Goal(profile.get("goal", "maintain")),
        )
        targets = NutritionEngine().calculate_targets(
            user,
            pace=profile.get("pace") or "moderate",
            weekly_change_kg=profile.get("weekly_change_kg") or None,
        )
        return {
            "calories": targets.target_calories_kcal,
            "protein": targets.protein_g,
            "carbs": targets.carbs_g,
            "fat": targets.fat_g,
        }
    except Exception:
        return {"calories": 2000.0, "protein": 120.0, "carbs": 250.0, "fat": 65.0}

if "mp_targets" not in st.session_state:
    st.session_state["mp_targets"] = _compute_targets()
TARGETS = st.session_state["mp_targets"]

# ── Step state ──────────────────────────────────────────────────────────────
if "mp_step" not in st.session_state:
    st.session_state["mp_step"] = 0

# Each meal-type gets its own sub-step inside step 1 so we don't render all
# five categories on one giant page.
if "mp_picker_idx" not in st.session_state:
    st.session_state["mp_picker_idx"] = 0

# Which recipe (in the candidate list) is being adjusted, keyed by meal-type.
# Value is recipe_id or None.
if "mp_adjusting" not in st.session_state:
    st.session_state["mp_adjusting"] = {}


def _go(step: int) -> None:
    st.session_state["mp_step"] = step
    st.rerun()


def _save_now() -> None:
    svc.save(prefs)


# ── Header ──────────────────────────────────────────────────────────────────
page_header("בחירת ארוחות שבועיות", "menu")
total_steps = 6
st.progress((st.session_state["mp_step"] + 1) / total_steps,
            text=f"שלב {st.session_state['mp_step'] + 1} מתוך {total_steps}")

# ===========================================================================
# STEP 0 — Welcome
# ===========================================================================
if st.session_state["mp_step"] == 0:
    _existing_picks = sum(len(v) for v in (prefs.picks or {}).values())
    if prefs.is_onboarded:
        _heading = f"עריכת התפריט של {profile.get('name','')} ✏️"
        _body = (
            f"כרגע יש לך {_existing_picks} בחירות שמורות. "
            "באשף תוכל להוסיף בחירות חדשות, להסיר ישנות, או לעדכן כמויות. "
            "כל שינוי ישפיע על התפריט השבועי שלך מיד."
        )
        _cta = "המשך לעריכה ➜"
    else:
        _heading = f"שלום {profile.get('name','')}, בוא נבנה את התפריט שלך 👋"
        _body = (
            "ניצור יחד תפריט שבועי המבוסס על הארוחות האהובות עליך. "
            "לכל סוג ארוחה (בוקר, צהריים, ערב, אחרי אימון, פינוק) תוצגו כמה אפשרויות, "
            "תוכל לבחור כמה שתרצה ולכוון את הכמויות (למשל מספר ביצים בחביתה). "
            "אנחנו כבר יודעים את האלרגיות וההעדפות שלך מהפרופיל — ארוחות שלא מתאימות "
            "לא יוצגו מלכתחילה."
        )
        _cta = "המשך ➜"

    st.markdown(f"""
    <div style='background:#1e2433;border-radius:14px;padding:22px;direction:rtl;border:1px solid #252d3d'>
      <h3 style='color:#f4f6fb;margin:0 0 8px 0'>{_heading}</h3>
      <p style='color:#8892a4;line-height:1.6;margin:0'>{_body}</p>
      <p style='color:#00d4aa;margin-top:14px;font-weight:600'>
        זמן משוער: 3–5 דקות.
      </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button(_cta, type="primary", use_container_width=True):
            _go(1)
    if prefs.is_onboarded:
        with col1:
            if st.button("← חזור לפרופיל", use_container_width=True, key="back_to_profile"):
                st.switch_page("pages/0_profile.py")

# ===========================================================================
# STEP 1 — Liked ingredients (soft-ranks the meal candidates in step 2)
# ===========================================================================
elif st.session_state["mp_step"] == 1:
    section_header("מצרכים שאתה אוהב", "menu")
    st.caption(
        "סמן את המרכיבים שאתה אוהב — נשתמש בהם כדי לדרג את הצעות הארוחות "
        "בשלב הבא. אפשר לדלג ולסמן בהמשך."
    )

    @st.cache_resource
    def _food_catalog() -> FoodCatalog:
        return FoodCatalog()

    _catalog = _food_catalog()
    _all_foods = list(_catalog.get_all_foods())

    # Group foods by macro category per INGREDIENT_GROUPS mapping.
    _by_id = {f.food_id: f for f in _all_foods}
    _foods_by_group: dict = {}
    for group_key, _label, cat_values in INGREDIENT_GROUPS:
        bucket = []
        cat_set = {c.lower() for c in cat_values}
        for f in _all_foods:
            cat = getattr(f, "category", None)
            cat_str = (cat.value if hasattr(cat, "value") else str(cat or "")).lower()
            if cat_str in cat_set:
                bucket.append(f)
        bucket.sort(key=lambda x: x.name_he or x.name_en or "")
        _foods_by_group[group_key] = bucket

    # Render: one tab per macro group, each with a multiselect of foods.
    _tab_labels = [label for _, label, _ in INGREDIENT_GROUPS]
    _tabs = st.tabs(_tab_labels)
    _already_liked = set(prefs.liked_ingredients or [])

    _selected_ids_this_render: set = set()
    for (group_key, _label, _cats), tab in zip(INGREDIENT_GROUPS, _tabs):
        with tab:
            options = _foods_by_group.get(group_key, [])
            default = [f for f in options if f.food_id in _already_liked]
            picked = st.multiselect(
                f"מה אתה אוהב מקבוצת {_label}?",
                options=options,
                default=default,
                format_func=lambda f: f.name_he or f.name_en,
                key=f"mp_liked_{group_key}",
            )
            _selected_ids_this_render.update(f.food_id for f in picked)

    # Preserve any previously-liked foods whose category isn't in the picker
    # (e.g., legacy data, "other" bucket) — don't silently drop them.
    _picker_food_ids = {f.food_id for foods in _foods_by_group.values() for f in foods}
    _retained = [fid for fid in (prefs.liked_ingredients or []) if fid not in _picker_food_ids]
    _final_liked = list(dict.fromkeys(list(_selected_ids_this_render) + _retained))

    st.caption(f"סך הכל סימנת {len(_final_liked)} מצרכים")

    st.markdown("---")
    _nav1, _, _nav3 = st.columns([1, 1, 1])
    with _nav1:
        if st.button("◀ חזרה", use_container_width=True, key="liked_back"):
            svc.set_liked_ingredients(prefs, _final_liked)
            _go(0)
    with _nav3:
        if st.button("המשך ➜", type="primary", use_container_width=True, key="liked_next"):
            svc.set_liked_ingredients(prefs, _final_liked)
            _go(2)

# ===========================================================================
# STEP 2 — Pick per category (sub-stepped across MEAL_TYPE_KEYS)
# ===========================================================================
elif st.session_state["mp_step"] == 2:
    picker_idx = st.session_state["mp_picker_idx"]
    if picker_idx >= len(MEAL_TYPE_KEYS):
        _go(3)
        st.stop()

    meal_type = MEAL_TYPE_KEYS[picker_idx]
    section_header(MEAL_TYPE_LABELS_HE[meal_type], "menu")
    st.caption(MEAL_TYPE_HELP_HE[meal_type])

    # Skip toggle — lets users opt out of a whole meal type
    is_skipped = meal_type in (prefs.skipped_meal_types or [])
    skip_toggled = st.checkbox(
        "דלג על סוג ארוחה זה — לא אוכל אותה בדרך כלל",
        value=is_skipped,
        key=f"skip_toggle_{meal_type}",
    )
    if skip_toggled != is_skipped:
        if skip_toggled:
            svc.skip_meal_type(prefs, meal_type)
        else:
            svc.unskip_meal_type(prefs, meal_type)
        _save_now()
        st.rerun()

    if is_skipped:
        st.info("ארוחה זו מסומנת כדילוג — לא תופיע בתפריט השבועי שלך.")
    else:
        # Show how many already picked.
        current_picks = prefs.picks.get(meal_type, [])
        min_required = MIN_PICKS[meal_type]
        msg = f"בחרת {len(current_picks)} עד עכשיו · מינימום {min_required}"
        if len(current_picks) >= min_required:
            st.success(msg)
        else:
            st.info(msg)

    current_picks = prefs.picks.get(meal_type, [])

    # Render existing picks (with remove + adjust buttons) — only when not skipped
    if not is_skipped and current_picks:
        with st.expander(f"הבחירות הנוכחיות ({len(current_picks)})", expanded=False):
            for vid in list(current_picks):
                variant = prefs.variant_by_id(vid)
                if not variant:
                    continue
                cols = st.columns([5, 1, 1])
                with cols[0]:
                    nut = variant.total_nutrition or {}
                    st.markdown(
                        f"**{variant.name}** · {round(nut.get('calories',0))} קק״ל · "
                        f"{round(nut.get('protein',0))}g חלבון"
                    )
                with cols[1]:
                    if st.button("עריכה", key=f"edit_{vid}"):
                        st.session_state["mp_adjusting"][meal_type] = ("variant", vid)
                        st.rerun()
                with cols[2]:
                    if st.button("הסר", key=f"rm_{vid}"):
                        svc.unpick_variant(prefs, vid)
                        _save_now()
                        st.rerun()

    # Adjustment panel and candidate list — hidden when meal type is skipped.
    if not is_skipped:
        adj = st.session_state["mp_adjusting"].get(meal_type)
        if adj is not None:
            kind, ref = adj
            if kind == "recipe":
                recipe = mgr.get_recipe(ref)
                base_overrides: dict = {}
                existing_variant_id = None
                display_name = recipe.get("name_he") or recipe.get("name_en") if recipe else ""
            else:  # variant
                existing_variant_id = ref
                variant = prefs.variant_by_id(ref)
                recipe = mgr.get_recipe(variant.base_recipe_id) if variant else None
                base_overrides = dict((variant.ingredient_overrides if variant else {}) or {})
                display_name = variant.name if variant else ""

            if not recipe:
                st.session_state["mp_adjusting"].pop(meal_type, None)
                st.rerun()

            st.markdown("---")
            st.markdown(f"### ✏️ התאמת מנה: {display_name}")
            st.caption("שנה את הכמויות לפי הצורך. ערך הסעיף נשאר במקום אם לא תשנה אותו.")

            # Inputs for each ingredient
            new_overrides: dict = {}
            cols = st.columns(2)
            for i, ing in enumerate(recipe.get("ingredients", [])):
                col = cols[i % 2]
                with col:
                    food_he = ing.get("food_name", "") or ing.get("food_name_en", "")
                    food_en = ing.get("food_name_en", "")
                    base_qty = float(ing.get("quantity") or 0)
                    unit = ing.get("unit", "grams")
                    init_val = float(base_overrides.get(food_en, base_qty))
                    new_qty = st.number_input(
                        f"{food_he} ({unit})",
                        min_value=0.0,
                        max_value=base_qty * 5 if base_qty > 0 else 1000.0,
                        value=init_val,
                        step=max(base_qty / 10, 1.0) if base_qty > 0 else 1.0,
                        key=f"adj_{meal_type}_{food_en}_{existing_variant_id or recipe['recipe_id']}",
                    )
                    if abs(new_qty - base_qty) > 0.001:
                        new_overrides[food_en] = float(new_qty)

            # Live nutrition preview
            nut_before = recipe.get("total_nutrition", {})
            portions = max(recipe.get("portions", 1), 1)
            before_per_portion = {k: (nut_before.get(k, 0) / portions) for k in ("calories","protein","carbs","fat")}
            nut_after = compute_variant_nutrition(recipe, new_overrides)
            st.markdown(macro_delta_html(before_per_portion, nut_after, targets=None,
                                         label_before="מקור", label_after="לאחר התאמה"),
                        unsafe_allow_html=True)

            name_default = display_name
            new_name = st.text_input("שם המנה שלך", value=name_default,
                                     key=f"name_{existing_variant_id or recipe['recipe_id']}")

            b1, b2, b3 = st.columns([1, 1, 2])
            with b1:
                if st.button("💾 שמור", type="primary",
                             key=f"save_adj_{existing_variant_id or recipe['recipe_id']}"):
                    if existing_variant_id:
                        res = svc.adjust_variant(prefs, existing_variant_id, new_overrides, new_name=new_name)
                    else:
                        res = svc.pick_recipe(prefs, meal_type, recipe["recipe_id"],
                                              ingredient_overrides=new_overrides, name=new_name)
                    if not res.ok:
                        st.error(" ".join(res.warnings) or "שגיאה")
                    else:
                        _save_now()
                        st.session_state["mp_adjusting"].pop(meal_type, None)
                        st.rerun()
            with b2:
                if st.button("ביטול", key=f"cancel_adj_{existing_variant_id or recipe['recipe_id']}"):
                    st.session_state["mp_adjusting"].pop(meal_type, None)
                    st.rerun()

        else:
            # Candidate list — soft-ranked by the user's liked ingredients
            # (allergies/dislikes still hard-filter inside the service).
            candidates = sugg.suggest_for_meal_type(
                meal_type, profile=profile, n=6,
                liked_ingredients=list(prefs.liked_ingredients or []),
            )
            picked_recipe_ids = {prefs.variant_by_id(vid).base_recipe_id
                                 for vid in current_picks
                                 if prefs.variant_by_id(vid) is not None}

            if not candidates:
                st.warning("לא נמצאו ארוחות שמתאימות להעדפות שלך. בדוק את הפרופיל.")
            elif len(candidates) < 3:
                st.info("מעט אפשרויות בגלל ההעדפות שלך. ניתן לערוך אותן בפרופיל.")

            for i, recipe in enumerate(candidates):
                already_picked = recipe["recipe_id"] in picked_recipe_ids
                st.markdown(
                    meal_picker_card_html(recipe, selected=already_picked, adjusted=False),
                    unsafe_allow_html=True,
                )
                cc1, cc2, cc3 = st.columns([1, 1, 4])
                with cc1:
                    if st.button("בחר כפי שהוא", key=f"pick_{meal_type}_{recipe['recipe_id']}",
                                 disabled=already_picked, use_container_width=True):
                        res = svc.pick_recipe(prefs, meal_type, recipe["recipe_id"])
                        if res.ok:
                            _save_now()
                            st.rerun()
                with cc2:
                    if st.button("התאם", key=f"adj_btn_{meal_type}_{recipe['recipe_id']}",
                                 use_container_width=True):
                        st.session_state["mp_adjusting"][meal_type] = ("recipe", recipe["recipe_id"])
                        st.rerun()

    # Navigation footer
    st.markdown("---")
    nav1, nav2, nav3 = st.columns([1, 1, 1])
    with nav1:
        if picker_idx > 0:
            if st.button("◀ הקודם", use_container_width=True):
                st.session_state["mp_picker_idx"] -= 1
                st.session_state["mp_adjusting"].pop(meal_type, None)
                st.rerun()
        else:
            if st.button("◀ חזרה", use_container_width=True):
                _go(1)
    with nav3:
        meets_min = is_skipped or len(current_picks) >= MIN_PICKS[meal_type]
        next_label = "סיום ➜" if picker_idx == len(MEAL_TYPE_KEYS) - 1 else "המשך ➜"
        if st.button(next_label, type="primary", disabled=not meets_min,
                     use_container_width=True):
            if picker_idx == len(MEAL_TYPE_KEYS) - 1:
                _go(3)
            else:
                st.session_state["mp_picker_idx"] += 1
                st.session_state["mp_adjusting"].pop(meal_type, None)
                st.rerun()

# ===========================================================================
# STEP 3 — Fixed-day overrides
# ===========================================================================
elif st.session_state["mp_step"] == 3:
    section_header("ימים קבועים (אופציונלי)", "menu")
    st.caption("רוצה שכל יום שישי בבוקר תאכל פינוק? אפשר לקבע כאן.")

    # Build options once: variant_id → label, grouped by meal-type.
    options_by_mt: dict = {}
    for mt in MEAL_TYPE_KEYS:
        options_by_mt[mt] = [(vid, prefs.variant_by_id(vid).name)
                             for vid in prefs.picks.get(mt, [])
                             if prefs.variant_by_id(vid) is not None]

    for weekday in WEEKDAYS:
        with st.expander(f"יום {WEEKDAYS_HE[weekday]}", expanded=False):
            for mt in MEAL_TYPE_KEYS:
                key = f"{weekday}.{mt}"
                current = prefs.fixed_day_overrides.get(key)
                opts = [(None, "ברירת מחדל (סבב אוטומטי)")] + options_by_mt[mt]
                labels = [lbl for _, lbl in opts]
                ids = [vid for vid, _ in opts]
                try:
                    idx = ids.index(current)
                except ValueError:
                    idx = 0
                chosen_label = st.selectbox(
                    MEAL_TYPE_LABELS_HE[mt],
                    options=labels,
                    index=idx,
                    key=f"fixed_{weekday}_{mt}",
                )
                chosen_id = ids[labels.index(chosen_label)]
                if chosen_id != current:
                    svc.set_fixed_override(prefs, weekday, mt, chosen_id)
                    _save_now()

    st.markdown("---")
    nav1, _, nav3 = st.columns([1, 1, 1])
    with nav1:
        if st.button("◀ הקודם", use_container_width=True):
            st.session_state["mp_picker_idx"] = len(MEAL_TYPE_KEYS) - 1
            _go(2)
    with nav3:
        if st.button("הצג תפריט שבועי ➜", type="primary", use_container_width=True):
            _go(4)

# ===========================================================================
# STEP 4 — Weekly review
# ===========================================================================
elif st.session_state["mp_step"] == 4:
    section_header("תפריט השבוע שלך", "menu")

    planner = WeeklyPlanner()
    plan = planner.generate(
        USER_ID, prefs,
        target_calories_kcal=TARGETS["calories"],
        target_protein_g=TARGETS["protein"],
        target_carbs_g=TARGETS["carbs"],
        target_fat_g=TARGETS["fat"],
    )

    # Daily-average vs. daily-target macro panel
    after = {
        "calories": plan.avg_daily_calories,
        "protein": plan.avg_daily_protein,
        "carbs": plan.avg_daily_carbs,
        "fat": plan.avg_daily_fat,
    }
    st.markdown("**ממוצע יומי לעומת היעד שלך**")
    st.markdown(
        macro_delta_html({"calories":0,"protein":0,"carbs":0,"fat":0}, after,
                         targets=TARGETS, label_before="יעד", label_after="ממוצע יומי"),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("**פירוט יומי**")
    for weekday in WEEKDAYS:
        day = plan.day_plan(weekday)
        if day is None:
            continue
        with st.expander(
            f"יום {WEEKDAYS_HE[weekday]} · {round(day.total_calories)} קק״ל",
            expanded=False,
        ):
            for meal in day.meals:
                first = meal.items[0] if meal.items else None
                if not first:
                    continue
                meal_label = meal.meal_type.value
                st.markdown(
                    f"<div style='direction:rtl;padding:6px 0'>"
                    f"<b>{meal_label}</b> · {first.food_name} · "
                    f"{round(first.calories_kcal)} קק״ל · "
                    f"{round(first.protein_g)}g חלבון</div>",
                    unsafe_allow_html=True,
                )

    st.info("ניתן להחליף מנות יומיות מעמוד התפריט היומי לאחר השמירה.")

    st.markdown("---")
    nav1, _, nav3 = st.columns([1, 1, 1])
    with nav1:
        if st.button("◀ חזור לערוך", use_container_width=True):
            _go(3)
    with nav3:
        if st.button("שמור והמשך ➜", type="primary", use_container_width=True):
            svc.mark_onboarded(prefs)
            _go(5)

# ===========================================================================
# STEP 5 — Done
# ===========================================================================
elif st.session_state["mp_step"] == 5:
    st.success("העדפות נשמרו! 🎉")
    st.markdown(
        "<div style='direction:rtl;padding:10px 0'>"
        "מכאן והלאה תופיע ההמלצה היומית בעמוד התפריט. ניתן לעדכן את ההעדפות מתפריט הפרופיל."
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("פתח את התפריט שלי", type="primary"):
        # Clear wizard state so a re-entry is clean.
        for k in list(st.session_state.keys()):
            if k.startswith("mp_"):
                del st.session_state[k]
        st.switch_page("pages/6_daily_menu.py")
