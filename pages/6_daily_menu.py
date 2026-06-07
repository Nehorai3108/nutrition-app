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
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth, logout_button
from ui.images import image_data_uri as _image_data_uri
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.utils.household_units import get_unit_info, grams_to_household, suggested_quantity

setup_persistent_auth()
USER_ID = require_auth()
_food_log_repo = FoodLogRepository()

#  Recipe image helpers 
_RECIPE_IMG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage_agents", "recipe_images", "approved",
)
_RECIPE_IMAGES_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "recipe_images.json",
)

# Ingredients to skip when choosing representative CDN image
_IMG_SKIP = {"salt", "pepper", "water", "oil", "olive oil", "sugar", "flour"}


@st.cache_data(ttl=3600)
def _load_recipe_images() -> dict:
    """Load recipe_id → image URL mapping from data/recipe_images.json."""
    try:
        with open(_RECIPE_IMAGES_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_RECIPE_IMAGES_DM = _load_recipe_images()

@st.cache_data(ttl=3600)
def _load_manual_images_dm() -> dict:
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "food_images_manual.json")
    try:
        with open(_p, encoding="utf-8") as f:
            d = json.load(f)
            return {**d.get("recipes", {}), **d.get("ingredients", {})}
    except Exception:
        return {}

_MANUAL_IMAGES_DM = _load_manual_images_dm()


def _get_food_img_url_dm(food_id: str, food_name_he: str, food_name_en: str = "") -> str:
    if food_id.startswith("recipe_"):
        _rid = "recipe_" + food_id.split("recipe_")[-1]
        url = _RECIPE_IMAGES_DM.get(_rid, "")
        if url:
            return url
    for _key in [food_name_en.lower(), food_name_he.lower()]:
        if _key and _key in _MANUAL_IMAGES_DM:
            return _MANUAL_IMAGES_DM[_key]
    for _key, _url in _MANUAL_IMAGES_DM.items():
        if _key and ((_key in food_name_en.lower()) or (_key in food_name_he.lower())):
            return _url
    if food_name_en:
        return f"https://www.themealdb.com/images/ingredients/{food_name_en.replace(' ', '%20')}-Small.png"
    return ""


def _get_recipe_img_html(recipe_id: str, recipe: dict = None) -> str:
    """Return a div with the recipe image as CSS background-image.

    CSS background-image silently shows nothing on failure — no broken
    icon, no JavaScript needed.
    Priority:
      1. Local approved JPG (base64 data-URI)
      2. data/recipe_images.json (TheMealDB URL)
    """
    # 1. Local approved image → base64 data-URI
    local_path = os.path.join(_RECIPE_IMG_DIR, f"{recipe_id}.jpg")
    uri = _image_data_uri(local_path)
    img_src = uri

    # 2. Recipe images DB
    if not img_src:
        img_src = _load_recipe_images().get(recipe_id, "")

    if img_src:
        return (
            f'<div style="width:84px;height:84px;border-radius:14px;flex-shrink:0;'
            f'background:#0d1117 url(\'{img_src}\') center/cover no-repeat"></div>'
        )
    return ""

# Load user allergies from profile
_profile_repo = ProfileRepository()
_profile = _profile_repo.load(USER_ID)
_user_allergens: list  = _profile.get("meal_preferences", {}).get("allergies", [])
_user_disliked: list   = _profile.get("meal_preferences", {}).get("disliked_foods", [])

st.set_page_config(page_title="BiteFit · תפריט", page_icon="", layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

with st.sidebar:
    st.markdown(f'<div style="font-size:0.75rem;color:#8892a4;padding:4px"> {st.session_state.get("bitefit_user", {}).get("email", "")}</div>', unsafe_allow_html=True)
    logout_button()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

@st.cache_resource
def get_mgr(_version=5):
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

#  Groq client (shared with chat page) 
@st.cache_resource
def _get_groq_planner():
    from groq import Groq
    return Groq(api_key=st.secrets["groq_api_key"])


#  Daily calorie target (Mifflin-St Jeor + activity + goal) 
def _calc_tdee(profile: dict) -> int:
    w   = float(profile.get("weight_kg")  or 70)
    h   = float(profile.get("height_cm")  or 170)
    g   = profile.get("gender", "male")
    dob = profile.get("date_of_birth") or ""
    age = 30
    if dob:
        try:
            from datetime import date as _d
            bd  = _d.fromisoformat(str(dob)[:10])
            age = (date.today() - bd).days // 365
        except Exception:
            pass
    bmr = 10 * w + 6.25 * h - 5 * age + (5 if g == "male" else -161)
    act = {"sedentary": 1.2, "lightly_active": 1.375,
           "moderately_active": 1.55, "very_active": 1.725,
           "extra_active": 1.9}.get(profile.get("activity_level", "moderately_active"), 1.55)
    tdee = bmr * act
    goal = profile.get("goal", "maintain")
    if goal == "lose":   tdee -= 500
    elif goal == "gain": tdee += 300
    return max(1200, int(tdee))


#  AI menu generation 
_MENU_SYSTEM = """You are an expert Israeli nutritionist. Generate a realistic daily meal plan for an Israeli adult.
Return ONLY valid JSON — no text before or after.


MEAL STRUCTURE RULES (CRITICAL):

Every MAIN meal (breakfast, lunch, dinner) MUST contain:
  1. PROTEIN source (chicken / egg / fish / beef / cheese / cottage / tuna)
  2. CARB source (bread / rice / pasta / potato / pita) — MAX ONE carb per meal
  3. VEGETABLES (tomato / cucumber / pepper / salad leaves) — at least 1-2 items

Snacks (morning_snack, afternoon_snack, evening_snack) are small:
  - 1-2 items only: fruit + yogurt, or cottage + fruit, or handful of nuts

FORBIDDEN COMBINATIONS:
   Two carbs in the same meal (e.g., rice AND couscous — pick ONE)
   Only carbs with no protein in a main meal
   Salad or vegetables measured in "כוס" — use individual pieces (יחידה/כף)


CORRECT MEASUREMENT UNITS PER FOOD TYPE:

PROTEINS:
  חזה עוף → 1 יחידה (150g, 165 kcal)
  שניצל עוף → 1 יחידה (130g, 220 kcal)
  קציצות עוף → 3 יחידה (75g each, 180 kcal total)
  ירך עוף → 1 יחידה (120g, 190 kcal)
  ביצה → יחידה (1 ביצה = 55 kcal)
  טונה בשמן → 1 קופסה (100g, 200 kcal)
  דג סלמון → 1 יחידה (150g, 250 kcal)
  גבינה לבנה 5% → כף (1 כף = 15g = 10 kcal)
  גבינה צהובה → כף (1 כף = 20g = 60 kcal)
  גבינת קוטג' → גביע (1 גביע = 200g = 140 kcal)

CARBS:
  פרוסת לחם מלא / לחם לבן → פרוסה (1 פרוסה = 30g = 70 kcal)
  פיתה → יחידה (1 = 60g = 160 kcal)
  אורז לבן / אורז מלא → כפות (4 כפות מבושל = 150g = 200 kcal)
  פסטה → כפות (4 כפות מבושלת = 150g = 210 kcal)
  תפוח אדמה → יחידה (1 בינוני = 150g = 120 kcal)
  בטטה → יחידה (1 = 150g = 130 kcal)
  קוסקוס → כפות (4 כפות = 150g = 200 kcal)

VEGETABLES (use יחידה or כף — NEVER כוס):
  עגבנייה → יחידה (1 = 100g = 18 kcal)
  מלפפון → יחידה (1 = 80g = 12 kcal)
  פלפל אדום/ירוק/צהוב → יחידה (1 = 120g = 30 kcal)
  גזר → יחידה (1 = 80g = 33 kcal)
  חסה/עלי תרד → לא נמדד — use "מנה קטנה" or skip calories
  זיתים → כף (1 כף = 5 זיתים = 45 kcal)
  אבוקדו → יחידה (חצי = 80g = 130 kcal) — write quantity=0.5

FATS / SPREADS:
  שמן זית → כפית (1 כפית = 5ml = 45 kcal)
  חמאה → כפית (1 כפית = 5g = 35 kcal)
  טחינה גולמית → כף (1 כף = 15g = 90 kcal)
  חומוס ממרח → כף (1 כף = 30g = 50 kcal)

DAIRY / SNACKS:
  יוגורט 1.5%-3% → גביע (1 = 150g = 90 kcal)
  חלב 1% → כוס (1 = 200ml = 70 kcal)
  בננה → יחידה (1 = 120g = 105 kcal)
  תפוח עץ → יחידה (1 = 150g = 80 kcal)
  אגוזי מלך → כף (1 כף = 15g = 100 kcal)


CALORIE SCALING GUIDE — adjust quantities to hit the target:

To reach a HIGH calorie target (e.g. 2800+ kcal/day), you MUST use larger portions:

BREAKFAST example scaled to ~700 kcal:
  3 ביצה (יחידה, 165 kcal) + 3 פרוסת לחם מלא (פרוסה, 210 kcal)
  + 1 עגבנייה (יחידה, 18 kcal) + 1 מלפפון (יחידה, 12 kcal)
  + 2 גבינה צהובה (כף, 120 kcal) + 1 כף טחינה (כף, 90 kcal) = 615 kcal
  → ADD more items or increase quantities to reach your assigned target.

LUNCH example scaled to ~900 kcal:
  2 חזה עוף (יחידה, 330 kcal) + 6 אורז לבן (כפות, 300 kcal)
  + 1 עגבנייה (יחידה, 18 kcal) + 1 מלפפון (יחידה, 12 kcal)
  + 2 כפית שמן זית (כפית, 90 kcal) + 1 כף טחינה (כף, 90 kcal) = 840 kcal

DINNER example scaled to ~700 kcal:
  2 שניצל עוף (יחידה, 440 kcal) + 1 תפוח אדמה (יחידה, 120 kcal)
  + 1 עגבנייה (יחידה, 18 kcal) + 1 פלפל ירוק (יחידה, 30 kcal)
  + 1 כף טחינה (כף, 90 kcal) = 698 kcal

SNACK example scaled to ~300 kcal:
  1 יוגורט (גביע, 90 kcal) + 1 בננה (יחידה, 105 kcal)
  + 1 כף אגוזי מלך (כף, 100 kcal) = 295 kcal

IMPORTANT: The examples above are just STRUCTURE guides.
You MUST scale portions up or down to match the EXACT calorie target given in the user prompt.
DO NOT copy these examples blindly — calculate calories for each food and verify the total.


JSON FORMAT:

{
  "meals": [
    {
      "time": "07:30",
      "meal_type": "breakfast",
      "meal_name": "ארוחת בוקר",
      "foods": [
        {"name": "ביצה", "quantity": 2, "unit": "יחידה", "calories": 110},
        {"name": "לחם מלא", "quantity": 2, "unit": "פרוסה", "calories": 140},
        {"name": "עגבנייה", "quantity": 1, "unit": "יחידה", "calories": 18},
        {"name": "מלפפון", "quantity": 1, "unit": "יחידה", "calories": 12}
      ],
      "total_calories": 280
    }
  ]
}

meal_type values: breakfast, morning_snack, lunch, afternoon_snack, dinner, evening_snack
total_calories MUST equal the exact sum of all food calories in the meal.
VERIFY before returning: each main meal has protein + one carb + vegetables."""


def _groq_menu_call(prompt: str, groq_client, max_tokens: int = 3000) -> list:
    import re as _re
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _MENU_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    raw = resp.choices[0].message.content.strip()
    m = _re.search(r'\{[\s\S]*\}', raw)
    if m:
        try:
            return json.loads(m.group()).get("meals", [])
        except Exception:
            pass
    return []


def _build_menu_prompt(profile: dict, target_cal: int, extra: str = "") -> str:
    prefs    = profile.get("meal_preferences", {})
    kashrut  = prefs.get("kashrut", "parve")
    allergs  = prefs.get("allergies", [])
    disliked = prefs.get("disliked_foods", [])
    meals_n  = int(prefs.get("meals_per_day", 5))
    goal_he  = {"lose": "הורדת משקל", "gain": "עלייה במסה",
                "maintain": "שמירה"}.get(profile.get("goal", "maintain"), "שמירה")

    #  Calculate per-meal calorie targets 
    # Main meals get 30-35% each, snacks get 10-12% each
    has_morning_snack   = meals_n >= 4
    has_afternoon_snack = meals_n >= 5
    has_evening_snack   = meals_n >= 6

    snack_count = sum([has_morning_snack, has_afternoon_snack, has_evening_snack])
    snack_pct   = 0.11 * snack_count          # 11% per snack
    main_total  = 1.0 - snack_pct
    main_count  = 3
    main_pct    = main_total / main_count      # equal split for breakfast/lunch/dinner

    cal_breakfast = round(target_cal * main_pct)
    cal_lunch     = round(target_cal * main_pct)
    cal_dinner    = round(target_cal * main_pct)
    cal_snack     = round(target_cal * 0.11)

    # Verify total (adjust dinner to absorb rounding diff)
    total_check = cal_breakfast + cal_lunch + cal_dinner
    total_check += cal_snack * snack_count
    diff = target_cal - total_check
    cal_dinner += diff   # absorb rounding

    lines = [
        f"צור תפריט יומי ל-{meals_n} ארוחות. יעד קלורי יומי: {target_cal} קק״ל.",
        f"מטרה: {goal_he}. כשרות: {kashrut}.",
        "",
        "",
        "יעדי קלוריות לכל ארוחה — חובה לעמוד בהם:",
        "",
        f"  ארוחת בוקר:   {cal_breakfast} קק״ל",
    ]
    if has_morning_snack:
        lines.append(f"  חטיף בוקר:    {cal_snack} קק״ל")
    lines.append(f"  ארוחת צהריים: {cal_lunch} קק״ל")
    if has_afternoon_snack:
        lines.append(f"  חטיף אחה״צ:   {cal_snack} קק״ל")
    lines.append(f"  ארוחת ערב:    {cal_dinner} קק״ל")
    if has_evening_snack:
        lines.append(f"  חטיף ערב:     {cal_snack} קק״ל")
    lines += [
        f"  סה״כ:         {target_cal} קק״ל",
        "",
        "חובה בכל ארוחה ראשית (בוקר/צהריים/ערב):",
        "  1. חלבון: עוף / ביצה / דג / גבינה / טונה",
        "  2. פחמימה אחת בלבד: לחם / אורז / פסטה / תפוח אדמה / פיתה",
        "  3. ירקות: עגבנייה / מלפפון / פלפל / גזר — ביחידות, לא כוסות",
        "",
        "כדי להגיע לקלוריות הנדרשות — הגדל כמויות:",
        "  עוף: 1 יחידה=165 קל' → 2 יחידות=330 קל'",
        "  אורז: 4 כפות=200 קל' → 6 כפות=300 קל'",
        "  לחם: 1 פרוסה=70 קל' → 3 פרוסות=210 קל'",
        "  ביצה: 1=55 קל' → 3 ביצים=165 קל'",
        "  הוסף שמן זית, טחינה, גבינה, אגוזים לשומן ולקלוריות",
        "",
        "אסור: שתי פחמימות באותה ארוחה. אסור: ארוחה ראשית ללא חלבון.",
    ]
    if allergs:
        lines.append(f"אלרגיות — הימנע לחלוטין: {', '.join(allergs)}")
    if disliked:
        lines.append(f"מזונות לא רצויים: {', '.join(disliked)}")
    if extra:
        lines.append(extra)
    lines += [
        "",
        f" חשוב: סכום כל הקלוריות בתפריט חייב להיות {target_cal} ± 30 קק״ל.",
        "לפני החזרת ה-JSON — חשב את הסכום ווודא שהוא נכון.",
    ]
    return "\n".join(lines)


#  Natural Hebrew food description 
def _natural_food_text(f: dict) -> str:
    """Convert {quantity, unit, name} → natural Hebrew string.

    Examples:
      1 יחידה עגבנייה  → עגבנייה
      2 יחידה ביצה     → 2 ביצים
      0.5 יחידה עוף    → חצי עוף
      4 כפות אורז      → 4 כפות אורז
      1 כף שמן זית     → כף שמן זית
      1 פרוסה לחם מלא  → פרוסת לחם מלא
      2 פרוסות לחם     → 2 פרוסות לחם
      1 גביע יוגורט    → גביע יוגורט
      1 קופסה טונה     → קופסת טונה
    """
    qty  = f.get("quantity", 1)
    unit = (f.get("unit") or "יחידה").strip()
    name = (f.get("name") or "").strip()

    try:
        qty = float(qty)
    except (TypeError, ValueError):
        qty = 1.0

    if unit == "יחידה":
        if qty == 0.5:
            return f"חצי {name}"
        if qty == 1:
            return name
        qty_int = int(qty) if qty == int(qty) else qty
        return f"{qty_int} {name}"

    if unit in ("כף", "כפות"):
        if qty == 1:
            return f"כף {name}"
        qty_int = int(qty) if qty == int(qty) else qty
        return f"{qty_int} כפות {name}"

    if unit == "כפית":
        if qty == 1:
            return f"כפית {name}"
        qty_int = int(qty) if qty == int(qty) else qty
        return f"{qty_int} כפיות {name}"

    if unit in ("פרוסה", "פרוסות"):
        if qty == 1:
            return f"פרוסת {name}"
        qty_int = int(qty) if qty == int(qty) else qty
        return f"{qty_int} פרוסות {name}"

    if unit in ("גביע", "גביעים"):
        if qty == 1:
            return f"גביע {name}"
        qty_int = int(qty) if qty == int(qty) else qty
        return f"{qty_int} גביעים {name}"

    if unit in ("קופסה", "קופסאות"):
        if qty == 1:
            return f"קופסת {name}"
        qty_int = int(qty) if qty == int(qty) else qty
        return f"{qty_int} קופסאות {name}"

    if unit in ("חבילה", "חבילות"):
        if qty == 1:
            return f"חבילת {name}"
        qty_int = int(qty) if qty == int(qty) else qty
        return f"{qty_int} חבילות {name}"

    # fallback: keep unit but drop trailing ".0"
    qty_int = int(qty) if qty == int(qty) else qty
    return f"{qty_int} {unit} {name}"


#  Render one AI meal card 
def _render_ai_meal(meal: dict, idx: int, target_cal: int) -> None:
    m_color = {
        "breakfast": "#f59e0b", "morning_snack": "#a78bfa",
        "lunch": "#4f8ef7",    "afternoon_snack": "#34d399",
        "dinner": "#f87171",   "evening_snack": "#818cf8",
    }.get(meal.get("meal_type", ""), "#4f8ef7")

    foods     = meal.get("foods", [])
    total_cal = meal.get("total_calories", sum(f.get("calories", 0) for f in foods))
    time_str  = meal.get("time", "")
    mname     = meal.get("meal_name", "")

    food_rows = "".join(
        f'<div dir="rtl" style="display:flex;justify-content:space-between;'
        f'padding:6px 0;border-bottom:1px solid #1a2030">'
        f'<span style="color:#c4cdd8;font-size:0.84rem">'
        f'{_natural_food_text(f)}</span>'
        f'<span style="color:#545e70;font-size:0.76rem;font-weight:500">{f.get("calories",0)} קק״ל</span>'
        f'</div>'
        for f in foods
    )

    st.markdown(
        f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
        f'border-radius:14px;padding:16px;margin-bottom:8px">'
        f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">'
        f'<div dir="rtl">'
        f'<div style="font-size:0.92rem;font-weight:700;color:#f4f6fb">{mname}</div>'
        f'<div style="font-size:0.68rem;color:#545e70;margin-top:2px">{time_str}</div>'
        f'</div>'
        f'<div style="background:{m_color}22;border:1px solid {m_color}55;border-radius:8px;'
        f'padding:4px 12px;font-size:0.82rem;font-weight:700;color:{m_color}">'
        f'{total_cal} קק״ל</div>'
        f'</div>'
        f'{food_rows}'
        f'</div>',
        unsafe_allow_html=True,
    )


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

#  Calorie targets 
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

#  Inventory 
inventory_names: set = set()

#  Header 
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;'
    f'padding:4px 2px 16px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#4f8ef7;letter-spacing:-0.01em">BiteFit</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{date.today().strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# 
# AI DAILY MENU PLANNER
# 
_groq_planner = _get_groq_planner()
_target_cal   = _calc_tdee(_profile)
_profile_ok   = bool(_profile.get("weight_kg") and _profile.get("height_cm"))

st.markdown(
    '<div dir="rtl" style="font-size:1rem;font-weight:800;color:#f4f6fb;'
    'margin-bottom:4px"> תפריט יומי מותאם אישית</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#8892a4;margin-bottom:14px">'
    f'{"יעד: " + str(_target_cal) + " קק״ל ליום" if _profile_ok else "מלא פרופיל כדי לקבל יעד מדויק"}'
    f'</div>',
    unsafe_allow_html=True,
)

if not _profile_ok:
    st.info("מלא את הגובה והמשקל בפרופיל כדי לקבל תפריט מותאם אישית.")

#  State keys 
_AI_MENU_KEY   = f"ai_menu_{USER_ID}"
_AI_TARGET_KEY = f"ai_menu_target_{USER_ID}"

#  Generate button 
_c1, _c2 = st.columns([3, 1])
with _c1:
    _gen_btn = st.button(
        " הכן לי תפריט להיום" if _AI_MENU_KEY not in st.session_state
        else " צור תפריט חדש",
        key="ai_gen_btn",
        use_container_width=True,
        type="primary" if _AI_MENU_KEY not in st.session_state else "secondary",
    )
with _c2:
    _clear_btn = st.button(" נקה", key="ai_clear_btn",
                           use_container_width=True,
                           disabled=_AI_MENU_KEY not in st.session_state)

if _clear_btn:
    for _k in list(st.session_state.keys()):
        if _k.startswith(f"ai_menu_{USER_ID}") or _k.startswith(f"swap_opts_{USER_ID}"):
            st.session_state.pop(_k, None)
    st.rerun()

if _gen_btn:
    # Clear previous menu + swap state
    for _k in list(st.session_state.keys()):
        if _k.startswith(f"ai_menu_{USER_ID}") or _k.startswith(f"swap_opts_{USER_ID}"):
            st.session_state.pop(_k, None)
    with st.spinner("מכין תפריט מותאם אישית..."):
        try:
            _prompt  = _build_menu_prompt(_profile, _target_cal)
            _meals   = _groq_menu_call(_prompt, _groq_planner)
            if _meals:
                st.session_state[_AI_MENU_KEY]   = _meals
                st.session_state[_AI_TARGET_KEY] = _target_cal
        except Exception as _e:
            st.error(f"שגיאה ביצירת התפריט: {_e}")
    st.rerun()

#  Render generated menu 
if _AI_MENU_KEY in st.session_state:
    _ai_meals   = st.session_state[_AI_MENU_KEY]
    _ai_target  = st.session_state.get(_AI_TARGET_KEY, _target_cal)
    _ai_total   = sum(m.get("total_calories",
                       sum(f.get("calories", 0) for f in m.get("foods", [])))
                      for m in _ai_meals)

    # Running total bar
    _pct = min(_ai_total / max(_ai_target, 1) * 100, 100)
    _diff = _ai_total - _ai_target
    _bar_color = "#4ade80" if abs(_diff) <= 50 else ("#f59e0b" if abs(_diff) <= 150 else "#f87171")
    st.markdown(
        f'<div dir="rtl" style="margin-bottom:16px">'
        f'<div dir="rtl" style="display:flex;justify-content:space-between;'
        f'font-size:0.72rem;color:#8892a4;margin-bottom:4px">'
        f'<span>סה״כ תפריט: <strong style="color:{_bar_color}">{_ai_total} קק״ל</strong></span>'
        f'<span>יעד: {_ai_target} קק״ל '
        f'({("+" if _diff >= 0 else "")}{_diff})</span></div>'
        f'<div style="height:4px;background:#252d3d;border-radius:99px">'
        f'<div style="height:100%;width:{_pct:.0f}%;background:{_bar_color};border-radius:99px"></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    for _i, _meal in enumerate(_ai_meals):
        _render_ai_meal(_meal, _i, _ai_target)
        _swap_key = f"swap_opts_{USER_ID}_{_i}"

        # Swap / log buttons
        _sb1, _sb2 = st.columns(2)
        with _sb1:
            if st.button(" החלף ארוחה", key=f"swap_btn_{_i}",
                         use_container_width=True):
                _meal_type = _meal.get("meal_type", "meal")
                _meal_cal  = _meal.get("total_calories", 400)
                _swap_prompt = (
                    f"צור 3 ארוחות חלופיות שונות לחלוטין לסוג '{_meal_type}' "
                    f"עם ~{_meal_cal} קק\"ל. "
                    f"כשרות: {_profile.get('meal_preferences',{}).get('kashrut','parve')}. "
                    f"כל ארוחה שונה מהקודמת. החזר JSON עם meals: [3 ארוחות]."
                )
                with st.spinner("מחפש חלופות..."):
                    try:
                        _alts = _groq_menu_call(_swap_prompt, _groq_planner, max_tokens=1500)
                        st.session_state[_swap_key] = _alts[:3]
                    except Exception as _e:
                        st.error(f"שגיאה: {_e}")
                st.rerun()

        with _sb2:
            _log_key = f"ai_logged_{USER_ID}_{_i}"
            if st.session_state.get(_log_key):
                st.markdown(
                    f'<div dir="rtl" style="background:#0d2b1a;border:1px solid #1a4d2e;'
                    f'border-radius:8px;padding:7px;font-size:0.8rem;font-weight:600;'
                    f'color:#4ade80;text-align:center">אכלתי</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button("אכלתי", key=f"log_meal_{_i}",
                             use_container_width=True, type="primary"):
                    _mtype = _meal.get("meal_type", "snack")
                    for _food in _meal.get("foods", []):
                        _fname = _food.get("name", "")
                        _fcal  = float(_food.get("calories", 0))
                        # Try to match in catalog for accurate macros
                        _hits  = get_catalog().search_foods(_fname, limit=1)
                        if _hits and _fcal > 0:
                            _f0   = _hits[0]
                            _n100 = _f0.nutrition_per_100g
                            _g    = (_fcal / max(_n100.calories_kcal, 1)) * 100
                            _r    = _g / 100
                            _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                                food_id=_f0.food_id, food_name=_fname,
                                grams=round(_g, 1), calories=_fcal,
                                protein=round(_n100.protein_g * _r, 1),
                                carbs=round(_n100.carbs_g * _r, 1),
                                fat=round(_n100.fat_g * _r, 1),
                                meal_type=_mtype,
                                timestamp=datetime.now().isoformat(),
                            ))
                        else:
                            _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                                food_id="ai_food", food_name=_fname,
                                grams=0.0, calories=_fcal,
                                protein=0.0, carbs=0.0, fat=0.0,
                                meal_type=_mtype,
                                timestamp=datetime.now().isoformat(),
                            ))
                    st.session_state[_log_key] = True
                    st.rerun()

        # Show swap alternatives if requested
        if _swap_key in st.session_state:
            _alts = st.session_state[_swap_key]
            if _alts:
                st.markdown(
                    '<div dir="rtl" style="font-size:0.85rem;font-weight:700;'
                    'color:#f4f6fb;margin:14px 0 10px">בחר חלופה:</div>',
                    unsafe_allow_html=True,
                )
                for _j, _alt in enumerate(_alts):
                    _alt_cal  = _alt.get("total_calories",
                                   sum(f.get("calories", 0) for f in _alt.get("foods", [])))
                    _alt_name = _alt.get("meal_name", "חלופה")
                    _alt_prot = sum(f.get("protein", 0) for f in _alt.get("foods", []))
                    _alt_carbs= sum(f.get("carbs", 0) for f in _alt.get("foods", []))
                    _alt_fat  = sum(f.get("fat", 0) for f in _alt.get("foods", []))
                    _alt_foods_list = [
                        _natural_food_text(f) for f in _alt.get("foods", [])[:4]
                    ]
                    _foods_html = "".join(
                        f'<div style="font-size:0.72rem;color:#8892a4;padding:3px 0;'
                        f'border-bottom:1px solid #1e2535">{item}</div>'
                        for item in _alt_foods_list
                    )
                    st.markdown(
                        f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                        f'border-radius:16px;padding:14px 16px;margin-bottom:10px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                        f'<div style="font-size:0.9rem;font-weight:700;color:#f4f6fb">{_alt_name}</div>'
                        f'<div style="font-size:0.85rem;font-weight:800;color:#4f8ef7">{int(_alt_cal)} קק״ל</div>'
                        f'</div>'
                        f'<div style="margin-bottom:10px">{_foods_html}</div>'
                        f'<div style="display:flex;gap:6px">'
                        f'<div style="flex:1;background:#0d1117;border-radius:8px;padding:6px;text-align:center">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#4f8ef7">{int(_alt_prot)}g</div>'
                        f'<div style="font-size:0.58rem;color:#545e70">חלבון</div></div>'
                        f'<div style="flex:1;background:#0d1117;border-radius:8px;padding:6px;text-align:center">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#f59e0b">{int(_alt_carbs)}g</div>'
                        f'<div style="font-size:0.58rem;color:#545e70">פחמימות</div></div>'
                        f'<div style="flex:1;background:#0d1117;border-radius:8px;padding:6px;text-align:center">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#f472b6">{int(_alt_fat)}g</div>'
                        f'<div style="font-size:0.58rem;color:#545e70">שומן</div></div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "בחר ארוחה זו",
                        key=f"pick_alt_{_i}_{_j}",
                        use_container_width=True,
                        type="primary",
                    ):
                        _ai_meals[_i] = _alt
                        st.session_state[_AI_MENU_KEY] = _ai_meals
                        st.session_state.pop(_swap_key, None)
                        st.rerun()

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    # Log entire day button
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    _all_logged = all(st.session_state.get(f"ai_logged_{USER_ID}_{i}")
                      for i in range(len(_ai_meals)))
    if not _all_logged:
        if st.button("סימון הכל כנאכל",
                     key="ai_log_all", use_container_width=True, type="primary"):
            for _i2, _meal2 in enumerate(_ai_meals):
                if not st.session_state.get(f"ai_logged_{USER_ID}_{_i2}"):
                    _mtype2 = _meal2.get("meal_type", "snack")
                    for _food2 in _meal2.get("foods", []):
                        _fname2 = _food2.get("name", "")
                        _fcal2  = float(_food2.get("calories", 0))
                        _hits2  = get_catalog().search_foods(_fname2, limit=1)
                        if _hits2 and _fcal2 > 0:
                            _f2   = _hits2[0]
                            _n2   = _f2.nutrition_per_100g
                            _g2   = (_fcal2 / max(_n2.calories_kcal, 1)) * 100
                            _r2   = _g2 / 100
                            _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                                food_id=_f2.food_id, food_name=_fname2,
                                grams=round(_g2, 1), calories=_fcal2,
                                protein=round(_n2.protein_g * _r2, 1),
                                carbs=round(_n2.carbs_g * _r2, 1),
                                fat=round(_n2.fat_g * _r2, 1),
                                meal_type=_mtype2,
                                timestamp=datetime.now().isoformat(),
                            ))
                        else:
                            _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                                food_id="ai_food", food_name=_fname2,
                                grams=0.0, calories=_fcal2,
                                protein=0.0, carbs=0.0, fat=0.0,
                                meal_type=_mtype2,
                                timestamp=datetime.now().isoformat(),
                            ))
                    st.session_state[f"ai_logged_{USER_ID}_{_i2}"] = True
            st.rerun()
    else:
        st.markdown(
            '<div dir="rtl" style="background:#0d2b1a;border:1px solid #1a4d2e;'
            'border-radius:14px;padding:12px;font-size:0.85rem;color:#4ade80;'
            'text-align:center;margin-bottom:8px">'
            ' כל התפריט נרשם להיום!</div>',
            unsafe_allow_html=True,
        )

# ── Shopping List ──────────────────────────────────────────────────────────
if _AI_MENU_KEY in st.session_state:
    _ai_meals_sl = st.session_state[_AI_MENU_KEY]
    with st.expander("רשימת קניות לתפריט היומי"):
        # Aggregate ingredients from all meals
        from collections import defaultdict
        _shopping = defaultdict(float)  # name_he → grams
        _shopping_en = {}               # name_he → name_en
        for _meal_sl in _ai_meals_sl:
            for _food_sl in _meal_sl.get("foods", []):
                _fname_sl    = _food_sl.get("name", "")
                _fname_en_sl = _food_sl.get("name_en", "")
                _grams_sl    = float(_food_sl.get("quantity", 0) or _food_sl.get("grams", 0))
                if _fname_sl:
                    _shopping[_fname_sl] += _grams_sl
                    if _fname_en_sl:
                        _shopping_en[_fname_sl] = _fname_en_sl

        if _shopping:
            # Group by category using catalog
            _cat_map = {"protein": "חלבונים", "grain": "דגנים", "vegetable": "ירקות",
                        "fruit": "פירות", "dairy": "חלב וגבינה", "fat": "שומנים",
                        "legume": "קטניות", "condiment": "תבלינים ורטבים", "other": "שונות"}
            _by_cat = defaultdict(list)
            _catalog_sl = get_catalog()
            for _item, _g in sorted(_shopping.items()):
                _hits = _catalog_sl.search_foods(_item, limit=1)
                _cat = _hits[0].category if _hits else "other"
                _by_cat[_cat].append((_item, _g))

            # Copy-to-clipboard text
            _list_text = "רשימת קניות BiteFit\n\n"
            for _cat_key, _items in sorted(_by_cat.items()):
                _cat_label = _cat_map.get(_cat_key, _cat_key)
                _list_text += f"── {_cat_label} ──\n"
                for _n, _g in _items:
                    _list_text += f"• {_n}" + (f" ({int(_g)}ג)" if _g > 0 else "") + "\n"
                _list_text += "\n"

            # Display
            for _cat_key, _items in sorted(_by_cat.items()):
                _cat_label = _cat_map.get(_cat_key, _cat_key)
                st.markdown(
                    f'<div style="font-size:0.78rem;font-weight:700;color:#4f8ef7;'
                    f'margin:10px 0 4px;text-transform:uppercase">{_cat_label}</div>',
                    unsafe_allow_html=True
                )
                for _n, _g in _items:
                    _g_str = f" — {int(_g)}ג" if _g > 0 else ""
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;'
                        f'padding:5px 8px;background:#161b26;border-radius:8px;'
                        f'margin-bottom:3px;font-size:0.82rem">'
                        f'<span style="color:#f4f6fb">{_n}</span>'
                        f'<span style="color:#545e70">{_g_str}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            st.code(_list_text, language=None)
            st.caption("העתק את הטקסט למעלה לשליחה בוואטסאפ")
        else:
            st.info("הפק תפריט יומי כדי לראות רשימת קניות")

st.divider()

#  Meal tab selector
tab_labels = [label for _, label, _ in MEAL_SECTIONS] + ["חיפוש", " ידני", " נשנוש"]
tabs = st.tabs(tab_labels)

_catalog = get_catalog()
# Full list (used only for id→name lookups, NOT for selectbox options directly)
_all_foods = sorted(_catalog.get_all_foods(), key=lambda f: f.name_he)
_food_id_to_name = {f.food_id: (f.name_he or f.name_en or f.food_id) for f in _all_foods}
# Default short list shown before the user types a search query:
# Hebrew-DB foods (source='json') with valid calories, sorted by name
_default_foods = sorted(
    [f for f in _all_foods if f.nutrition_per_100g.calories_kcal and f.source in ("json", "manual")],
    key=lambda f: f.name_he or "",
)

MEAL_TYPE_HEB = {
    "breakfast": "ארוחת בוקר", "morning_snack": "חטיף בוקר",
    "lunch": "ארוחת צהריים", "afternoon_snack": "חטיף אחה״צ",
    "dinner": "ארוחת ערב", "evening_snack": "חטיף ערב",
    "snack": "נשנוש",
}

#  Nutrition fallback for ingredients not in catalog (kcal/100g) 
_INGREDIENT_FALLBACK = {
    "breadcrumbs":   {"kcal": 395, "prot": 13.0, "carbs": 73.0, "fat": 5.0},
    "ground turkey": {"kcal": 149, "prot": 19.0, "carbs":  0.0, "fat": 7.5},
    "cumin":         {"kcal": 375, "prot": 18.0, "carbs": 44.0, "fat": 22.0},
    "fried onion":   {"kcal":  40, "prot":  1.1, "carbs":  9.3, "fat": 0.1},
    "raisins":       {"kcal": 299, "prot":  3.1, "carbs": 79.0, "fat": 0.5},
    "cinnamon":      {"kcal": 247, "prot":  4.0, "carbs": 81.0, "fat": 1.2},
    "turmeric":      {"kcal": 312, "prot":  9.7, "carbs": 68.0, "fat": 3.3},
    "paprika":       {"kcal": 282, "prot": 14.1, "carbs": 54.0, "fat": 13.0},
    "salt":          {"kcal":   0, "prot":  0.0, "carbs":  0.0, "fat": 0.0},
    "pepper":        {"kcal": 255, "prot": 10.4, "carbs": 64.0, "fat": 3.3},
}


#  helper: scale recipe to calorie target 
def _scale_recipe(recipe: dict, target_cal: float) -> tuple:
    """
    Scale a recipe's ingredients to hit target_cal.
    Calories are calculated from FoodCatalog (not the recipe DB totals,
    which are often inaccurate). Falls back to recipe DB if catalog miss.
    Returns (scaled_ingredients, cal, prot, carbs, fat, approx_grams).
    """
    ingredients = recipe.get("ingredients", [])
    portions = max(recipe.get("portions", 1), 1)

    #  Step 1: calculate REAL calories from catalog (total for whole recipe)
    base_cal = base_prot = base_carbs = base_fat = 0.0
    for ing in ingredients:
        qty_g   = ing.get("quantity", 0)
        name_en = ing.get("food_name_en", "")
        name_he = ing.get("food_name", "")
        # Try English first, then Hebrew
        hits = _catalog.search_foods(name_en, limit=1) if name_en else []
        if not hits and name_he:
            hits = _catalog.search_foods(name_he, limit=1)
        if hits:
            n = hits[0].nutrition_per_100g
            r = qty_g / 100.0
            base_cal   += n.calories_kcal * r
            base_prot  += n.protein_g     * r
            base_carbs += n.carbs_g       * r
            base_fat   += n.fat_g         * r
        else:
            # Try fallback nutrition table for common missing ingredients
            fb = _INGREDIENT_FALLBACK.get(name_en.lower())
            if fb:
                r = qty_g / 100.0
                base_cal   += fb["kcal"]  * r
                base_prot  += fb["prot"]  * r
                base_carbs += fb["carbs"] * r
                base_fat   += fb["fat"]   * r

    # Normalize to per-portion BEFORE scaling
    if base_cal >= 1:
        base_cal   /= portions
        base_prot  /= portions
        base_carbs /= portions
        base_fat   /= portions

    # Fall back to recipe DB if catalog lookup gave nothing
    if base_cal < 1:
        portions  = max(recipe.get("portions", 1), 1)
        nut       = recipe.get("total_nutrition", {})
        base_cal   = nut.get("calories", 0) / portions
        base_prot  = nut.get("protein",  0) / portions
        base_carbs = nut.get("carbs",    0) / portions
        base_fat   = nut.get("fat",      0) / portions

    #  Step 2: scale to target (nearest 0.5, min 0.5) 
    raw_scale = target_cal / max(base_cal, 1)
    scale     = max(0.5, round(raw_scale * 2) / 2)

    #  Step 3: scale ingredient quantities 
    scaled_ings = [
        {**ing, "quantity": ing.get("quantity", 0) * scale}
        for ing in ingredients
    ]

    return (
        scaled_ings,
        round(base_cal   * scale, 1),
        round(base_prot  * scale, 1),
        round(base_carbs * scale, 1),
        round(base_fat   * scale, 1),
        round(scale * 200),
    )


#  helper: ingredient chips 
def _ingredient_chips_html(ingredients: list, max_show: int = 6) -> str:
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


#  helper: render a nutrition result card + add button 
def _render_search_result(
    name: str, food_id: str, meal_key: str, target_cal: int,
    cal_out: float, prot_out: float, carbs_out: float, fat_out: float,
    portion_label: str, btn_suffix: str, grams: float = 0.0,
    is_recipe: bool = False, img_html: str = "",
):
    _cal_diff   = round(cal_out) - target_cal
    _diff_color = "#4ade80" if abs(_cal_diff) <= 40 else ("#f59e0b" if abs(_cal_diff) <= 100 else "#f87171")
    _meal_color = MEAL_COLOR_MAP.get(meal_key.upper(), "#4f8ef7")
    _cal_pct    = min(cal_out / max(target_cal, 1) * 100, 100)

    # Header: image thumbnail (right in RTL) + name + meal badge
    _img_block = (
        f'<div dir="rtl" style="width:84px;height:84px;border-radius:14px;overflow:hidden;'
        f'flex-shrink:0;background:#0d1117">{img_html}</div>'
        if img_html else ""
    )
    _badge = (
        f'<div dir="rtl" style="background:{_meal_color}22;border:1px solid {_meal_color}55;'
        f'border-radius:99px;padding:3px 10px;font-size:0.7rem;color:{_meal_color};'
        f'font-weight:600;white-space:nowrap">{MEAL_TYPE_HEB[meal_key]}</div>'
    )
    _header = (
        f'<div dir="rtl" style="display:flex;align-items:center;gap:12px;margin-bottom:14px">'
        f'{_img_block}'
        f'<div dir="rtl" style="flex:1;min-width:0">'
        f'<div dir="rtl" style="font-size:1rem;font-weight:800;color:#f4f6fb;margin-bottom:6px;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{name}</div>'
        f'{_badge}'
        f'</div></div>'
    )

    st.markdown(
        f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:20px;'
        f'padding:20px;margin:10px 0 14px">'
        + _header +
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
    #  Mode toggle 
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

    #  Meal selector (shared) 
    search_meal = st.selectbox(
        "ארוחה",
        options=list(MEAL_TYPE_HEB.keys()),
        format_func=lambda k: MEAL_TYPE_HEB[k],
        key="search_meal_sel",
    )
    _search_target = meal_calories.get(search_meal.upper(), 400)

    # 
    if _search_mode == "recipe":
    # 
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

                    _render_search_result(
                        name=_rec_name, food_id=f"recipe_{_rec_id}",
                        meal_key=search_meal, target_cal=_search_target,
                        cal_out=_cal_per_por, prot_out=_prot_per,
                        carbs_out=_carbs_per, fat_out=_fat_per,
                        portion_label=_rec_name,
                        btn_suffix=f"{_rec_id}_s",
                        grams=float(_portions * 100),
                        is_recipe=True,
                        img_html=_get_recipe_img_html(_rec_id, _rec),
                    )
                    st.markdown('<div dir="rtl" style="height:4px"></div>', unsafe_allow_html=True)

    # 
    else:  # ingredient mode
    # 
        _ing_q = st.text_input(
            "",
            placeholder="חפש מוצר: עוף, אורז, בננה, יוגורט...",
            key="ingredient_search_text",
            label_visibility="collapsed",
        )
        _ing_results = (
            _catalog.search_foods(_ing_q.strip(), limit=20)
            if _ing_q.strip()
            else _default_foods
        )
        _ing_opts = [f.food_id for f in _ing_results]
        search_food_id = st.selectbox(
            "",
            options=_ing_opts if _ing_opts else [""],
            format_func=lambda fid: _food_id_to_name.get(fid, fid) if fid else "—",
            key="search_food_sel",
            label_visibility="collapsed",
        )
        _search_food = _catalog.get_food_by_id(search_food_id) if search_food_id else None

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
    _man_search_q = st.text_input(
        "",
        placeholder="חפש מוצר: עוף, אורז, גבינה...",
        key="manual_food_search",
        label_visibility="collapsed",
    )
    _man_results = (
        _catalog.search_foods(_man_search_q.strip(), limit=20)
        if _man_search_q.strip()
        else _default_foods
    )
    with st.form("manual_food_form", clear_on_submit=True):
        _man_opts = [f.food_id for f in _man_results]
        sel_food = st.selectbox(
            "מוצר",
            options=_man_opts if _man_opts else [""],
            format_func=lambda fid: _food_id_to_name.get(fid, fid) if fid else "—",
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
                st.success(f" {food_obj.name_he} נוסף!")
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
            # Build food image URL
            _food_obj_img = _catalog.get_food_by_id(entry.food_id) if not entry.food_id.startswith("recipe_") else None
            _img_url_entry = _get_food_img_url_dm(entry.food_id, entry.food_name, _food_obj_img.name_en if _food_obj_img else "")
            _img_html = (
                f'<img src="{_img_url_entry}" '
                f'style="width:44px;height:44px;object-fit:cover;border-radius:10px;flex-shrink:0;" '
                f'onerror="this.style.display=\'none\'" />'
            ) if _img_url_entry else ""
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:14px;'
                f'padding:12px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px">'
                f'{_img_html}'
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

        _seed_key = f"meal_seed_{meal_key}"
        if _seed_key not in st.session_state:
            import datetime as _dt
            st.session_state[_seed_key] = _dt.date.today().toordinal()

        _col1, _col2 = st.columns([4, 1])
        with _col2:
            if st.button("רענן", key=f"refresh_{meal_key}", use_container_width=True):
                import random as _r
                st.session_state[_seed_key] = _r.randint(1, 99999)
                st.rerun()

        try:
            suggestions = recipe_mgr.recommend_meal(
                meal_type=meal_key,
                target_calories=target_cal,
                inventory_names=inventory_names if inventory_names else None,
                allergens=_user_allergens if _user_allergens else None,
                disliked_foods=_user_disliked if _user_disliked else None,
                variation_seed=st.session_state[_seed_key],
            )[:3]
        except Exception as _e:
            st.error(f"שגיאה: {_e}")
            suggestions = []

        if not suggestions:
            st.info("אין מתכונים מתאימים לארוחה זו.")

        for idx, recipe in enumerate(suggestions):
            recipe_id  = recipe.get("recipe_id", "")
            name_he    = recipe.get("name_he", "מתכון")

            # Per-portion nutrition — what the user sees = what gets logged
            _portions  = max(recipe.get("portions", 1), 1)
            _nut       = recipe.get("total_nutrition", {}) or {}
            p_cal      = round(_nut.get("calories", 0) / _portions)
            p_prot     = round(_nut.get("protein",  0) / _portions, 1)
            p_carbs    = round(_nut.get("carbs",    0) / _portions, 1)
            p_fat      = round(_nut.get("fat",      0) / _portions, 1)

            match_pct = max(0, round(100 - abs(p_cal - target_cal) / max(target_cal, 1) * 100))

            # Image priority: local approved → recipe_images.json (TheMealDB)
            _img_uri = _image_data_uri(recipe.get("image_path", ""))
            if not _img_uri:
                _img_uri = _load_recipe_images().get(recipe_id, "")

            st.markdown(
                recipe_card_html(
                    recipe,
                    image_uri=_img_uri,
                    match_pct=match_pct,
                    show_rank=(idx == 0),
                ),
                unsafe_allow_html=True,
            )
            if st.button("לפרטי המתכון ←", key=f"detail_{meal_key}_{recipe_id}_{idx}",
                         use_container_width=True):
                st.session_state["_nav_recipe_id"] = recipe_id
                st.session_state["_nav_recipe_from"] = "daily_menu"
                st.switch_page("pages/3_recipe_detail.py")

            #  Add to food log
            btn_key   = f"add_{meal_key}_{recipe_id}_{idx}"
            added_key = f"added_{meal_key}_{recipe_id}_{idx}"

            if st.session_state.get(added_key):
                st.markdown(
                    '<div dir="rtl" style="background:#0d2b1a;border:1px solid #1a4d2e;border-radius:12px;'
                    'padding:8px 14px;margin-bottom:8px;font-size:0.82rem;color:#4ade80;text-align:center">'
                    'נוסף לתפריט היומי</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(
                    f"הוסף לתפריט היומי · {p_cal} קק״ל",
                    key=btn_key,
                    use_container_width=True,
                    type="primary",
                ):
                    _food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                        food_id=f"recipe_{recipe_id}",
                        food_name=name_he,
                        grams=float(_portions * 100),
                        calories=float(p_cal),
                        protein=float(p_prot),
                        carbs=float(p_carbs),
                        fat=float(p_fat),
                        meal_type=meal_key.lower(),
                        timestamp=datetime.now().isoformat(),
                    ))
                    st.session_state[added_key] = True
                    st.rerun()

        #  In-meal food search
        st.markdown('<div dir="rtl" style="height:10px"></div>', unsafe_allow_html=True)
        with st.expander(" לא מצאת מה שרצית? חפש כאן"):
            _ms_mode = st.radio(
                "",
                options=["ingredient", "recipe"],
                format_func=lambda m: {
                    "ingredient": " רכיב / מוצר",
                    "recipe":     " מנה מוכנה",
                }[m],
                horizontal=True,
                key=f"ms_mode_{meal_key}",
                label_visibility="collapsed",
            )

            #  Ingredient search 
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

            #  Recipe search 
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
                            _render_search_result(
                                name=_mrname,
                                food_id=f"recipe_{_mrid}",
                                meal_key=meal_key.lower(),
                                target_cal=target_cal,
                                cal_out=_mcpp,
                                prot_out=_mppp,
                                carbs_out=_mcarb,
                                fat_out=_mfat,
                                portion_label=_mrname,
                                btn_suffix=f"ms_{meal_key}_{_mrid}_s",
                                grams=float(_mportions * 100),
                                is_recipe=True,
                                img_html=_get_recipe_img_html(_mrid, _mrec),
                            )
                else:
                    st.markdown(
                        '<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                        'border-radius:12px;padding:14px;text-align:center;color:#545e70;'
                        'font-size:0.8rem">הקלד שם מנה לחיפוש</div>',
                        unsafe_allow_html=True,
                    )

#  Snack tab (last tab) 
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
