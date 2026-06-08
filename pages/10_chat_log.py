#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10_chat_log.py — צאט תזונה מבוסס Groq AI (llama-3.3-70b)
"""

import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
import streamlit as st
from groq import Groq

from ui.components import inject_global_css, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth, logout_button
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry

st.set_page_config(page_title="BiteFit · הזנה", page_icon="", layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

with st.sidebar:
    st.markdown(f'<div style="font-size:0.75rem;color:#8892a4;padding:4px"> {st.session_state.get("bitefit_user", {}).get("email", "")}</div>', unsafe_allow_html=True)
    logout_button()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

@st.cache_resource
def _get_catalog(_v=4):
    return FoodCatalog(db_path=_DB_PATH)

@st.cache_resource
def _get_groq():
    api_key = (
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("groq_api_key")
        or st.secrets.get("groq_api_key", "")
    )
    if not api_key:
        return None
    return Groq(api_key=api_key)

@st.cache_resource
def _get_recipe_mgr():
    return RecipeManager()

@st.cache_resource
def _build_food_list(_v=5) -> str:
    """Build food + recipe catalog string for the AI system prompt.
    Sends Hebrew-first names, capped at ~3000 chars.
    """
    cat = FoodCatalog(db_path=_DB_PATH)
    # Get all foods sorted: Hebrew DB first, then by name
    all_foods = cat.get_all_foods()
    all_foods.sort(key=lambda f: (
        0 if f.source == "json" else 1,
        f.name_he or f.name_en or "",
    ))
    # Only foods with calorie data
    all_foods = [f for f in all_foods if f.nutrition_per_100g.calories_kcal]

    # Send up to 600 food names (Hebrew preferred)
    lines = []
    for f in all_foods[:600]:
        name = f.name_he or f.name_en
        if name:
            lines.append(name)

    # Add recipe names so AI recognises complex dishes
    try:
        mgr = RecipeManager()
        recipes = mgr.search_recipes(RecipeFilter(max_results=30))
        for r in recipes:
            name_he = r.get("name_he", "")
            if name_he:
                lines.append(f"{name_he} [מתכון]")
    except Exception:
        pass

    result = ", ".join(lines)
    if len(result) > 3000:
        result = result[:3000]
    return result

catalog       = _get_catalog()
recipe_mgr    = _get_recipe_mgr()
groq_client   = _get_groq()
food_log_repo = FoodLogRepository()
USER_ID       = require_auth()
FOOD_LIST     = _build_food_list()

if groq_client is None:
    st.error(" מפתח Groq API חסר. בדוק את הגדרות ה-Secrets ב-Streamlit Cloud.")
    st.stop()

MEAL_HEB = {
    "breakfast":       "ארוחת בוקר",
    "morning_snack":   "חטיף בוקר",
    "lunch":           "ארוחת צהריים",
    "afternoon_snack": "חטיף אחה״צ",
    "dinner":          "ארוחת ערב",
    "evening_snack":   "חטיף ערב",
    "snack":           "נשנוש",
}

def _build_system_prompt(food_list: str, profile_ctx: str = "") -> str:
    return f"""You are "Biti" — a precise Israeli nutrition assistant inside BiteFit.
Always reply in Hebrew. Be warm, brief, accurate. Your job: identify food correctly and log it.

{profile_ctx}
=== FOODS IN DATABASE (use exact Hebrew names in JSON) ===
{food_list}

=== STANDARD PORTIONS — use exactly when user does not specify a quantity ===
עוף ובשר:
  חזה עוף    = 1 יחידה (150g)
  שניצל עוף  = 1 יחידה (130g) — ONLY for "שניצל"
  קציצות עוף = 3 יחידות (75g each) — for "קציצות/קציצה/קציצה אחת/קציצת עוף"
  ירך עוף    = 1 יחידה (120g)
  המבורגר    = 1 יחידה (150g)
  קבב        = 2 יחידות (80g each)
  שווארמה    = 1 מנה (200g עוף/טלה + פיתה + סלט + טחינה) ← אין גבינה! ~500 קל'
  פלאפל      = 3 כדורים (75g) + פיתה אחת
  שאורמה     = שווארמה (שם נרדף)

ביצים:
  ביצה = 1 יחידה (55g) [חביתה / שקשוקה / ביצת עין / מקושקשת = 2 ביצים]

דגים ופירות ים:
  טונה    = 1 קופסה (100g)  ← reply: "קופסת טונה"
  סלמון   = 1 מנה (150g)
  סרדינים = 1 קופסה (100g)

לחם ופחמימות:
  פרוסת לחם  = 1 פרוסה (30g) [כריך = 2 פרוסות]
  פיתה        = 1 יחידה (60g)
  אורז לבן    = 4 כפות מבושל (80g)
  פסטה        = 4 כפות מבושל (100g)
  קוסקוס      = 4 כפות (80g)
  קינואה      = 4 כפות (80g)
  תפוח אדמה  = 1 יחידה בינונית (150g)
  בטטה        = 1 יחידה בינונית (130g)
  שיבולת שועל = 4 כפות יבש (40g)

חלב ומוצריו:
  יוגורט         = 1 גביע (125g)
  גבינה בולגרית  = 1 כף (20g)
  גבינה צהובה    = 1 פרוסה (20g)
  קוטג'          = 1 גביע (150g)
  חלב             = 1 כוס (200ml)
  שמנת חמוצה     = 1 כף (20g)

ירקות — ALWAYS use יחידה, NEVER כוסות:
  עגבנייה = 1 יחידה (100g)
  מלפפון  = 1 יחידה (80g) ← completely different from תפוח
  גזר     = 1 יחידה (80g)
  פלפל    = 1 יחידה (100g)
  אבוקדו  = חצי יחידה (80g)
  חציל    = 1 יחידה (200g)
  קישוא   = 1 יחידה (150g)

פירות — completely different from ירקות:
  תפוח עץ = 1 יחידה (150g) ← NOT מלפפון, NOT קישוא
  בננה    = 1 יחידה (120g)
  תפוז    = 1 יחידה (130g)
  אגס     = 1 יחידה (150g)
  ענבים   = 1 אשכול קטן (100g)

שמנים וממרחים:
  שמן זית = 1 כף (15g)
  טחינה   = 1 כף (15g)
  חמאה    = 1 כף (10g)
  חומוס   = 2 כפות (30g)
  ריבה    = 1 כף (20g)
  דבש     = 1 כף (20g)

שונות:
  ביסלי/במבה/חטיף = 1 אריזה (30g)
  שוקולד מריר     = 1 קוביה (10g)
  קפה שחור        = 1 כוס (0 קל')
  קולה/שתייה      = 1 פחית (330ml)

=== WHEN FOOD IS LOGGED — return ONLY this JSON ===
```json
{{
  "meal_type": "breakfast|morning_snack|lunch|afternoon_snack|dinner|evening_snack",
  "foods": [{{"name": "שם מהמאגר", "quantity": 1, "unit": "יחידה|גרם|פרוסה|כוס|כף|כפית|גביע|קופסה"}}],
  "reply": "תגובה טבעית קצרה בעברית"
}}
```

=== HOW TO WRITE THE REPLY ===
Write naturally, like a dietitian would speak. Examples:
  "קופסת טונה — כ-90 קל', 20 גר' חלבון. תוספת מצוינת לצהריים."
  "נרשמה ביצה (55 קל'). בוקר טוב!"
  "2 מלפפונים — ירק מצוין, כמעט ללא קלוריות."
  "חזה עוף — 165 קל', 31 גר' חלבון. מקור חלבון מעולה."
Do NOT say "X גרם" as the main description — say the food name naturally.
Add calorie info in parentheses, naturally.
Be brief — 1-2 sentences max.

=== COMPOSITE DISHES — log as ONE single item (do NOT split!) ===
These are complete dishes — return as ONE food item with unit=מנה qty=1:
- קבב בפיתה / קבב עם פיתה  → name:"קבב בפיתה"  unit=מנה qty=1  (~550 קל')
- שווארמה בפיתה / שווארמה  → name:"שווארמה בפיתה" unit=מנה qty=1 (~500 קל')
- פלאפל בפיתה / פלאפל      → name:"פלאפל בפיתה"  unit=מנה qty=1 (~400 קל')
- סביח בפיתה / סביח         → name:"סביח בפיתה"   unit=מנה qty=1 (~450 קל')
- המבורגר / המבורגר בלחמנייה → name:"המבורגר"    unit=מנה qty=1 (~550 קל')
- שניצל בפיתה               → name:"שניצל בפיתה"  unit=מנה qty=1 (~500 קל')
- כריך גבינה / כריך טונה / כריך עוף → name:"כריך [מילוי]" unit=מנה qty=1

=== CRITICAL FOOD RULES ===
- קציצות/קציצה/קציצת עוף → name:"קציצות עוף" (unit=יחידה, default qty=3)
  QUANTITY OVERRIDE: "קציצה אחת"=qty=1, "שתי קציצות"=qty=2, "5 קציצות"=qty=5
  NEVER confuse with שניצל
- שניצל/שניצל עוף → name:"שניצל עוף" (unit=יחידה, qty=1) ← NEVER קציצות
- חביתה / ביצת עין / מקושקשת / שקשוקה = SINGLE food item name:"ביצה"
  • "חביתה" alone → qty=2; "חביתה עם X ביצים" → qty=X (ONE item only)
  • NEVER return both "חביתה" AND "ביצה" — they are the same thing
- מלפפון ≠ תפוח ≠ קישוא — COMPLETELY different foods, never compare or confuse
- ירקות ≠ פירות — never mix them up
- Dish marked [מתכון] → use exact recipe name
- Unknown dish → split into individual ingredients
- Corrections → return FULL updated JSON with ALL items
- QUANTITY WORDS: אחד/אחת=1, שניים/שתיים=2, שלוש/שלושה=3, ארבע=4, חמש=5

=== ALWAYS LOG THESE — always return JSON, never just describe ===
- קפה / קפה שחור / אספרסו / מקפה / אמריקנו → name:"קפה שחור" unit=כוס qty=1
- קפוצינו / לאטה / קפה הפוך / קפה עם חלב → name:"קפה הפוך" unit=כוס qty=1
- חלב → name:"חלב" unit=כוס qty=1
- מים (even "שתיתי מים") → name:"מים" unit=כוס qty=1
- סלמון / דג סלמון → name:"דג סלמון" unit=יחידה qty=1
- טונה → name:"טונה בשמן" unit=קופסה qty=1
- סרדינים → name:"סרדינים" unit=קופסה qty=1
- קוואקר / שיבולת שועל / פתיתי שיבולת → name:"שיבולת שועל" unit=כפות qty=4
- קוסקוס → name:"קוסקוס" unit=כפות qty=4
- אורז / אורז לבן → name:"אורז לבן" unit=כפות qty=4
- ספגטי / פסטה → name:"פסטה ספגטי" unit=כפות qty=4
- קוטג' / קוטג → name:"גבינת קוטג'" unit=גביע qty=1
- חומוס (as food) → name:"חומוס מוכן" unit=כפות qty=2
- שניצל / שניצל עוף → name:"שניצל עוף" unit=יחידה qty=1
- שניצל תירס → name:"שניצל תירס" unit=יחידה qty=1
- שניצל כרובית → name:"שניצל כרובית" unit=יחידה qty=1
- נאגטס / נגטס → name:"נאגטס עוף" unit=יחידה qty=3
- לביבות / לביבה → name:"לביבות תפוחי אדמה" unit=יחידה qty=3
- שקשוקה → name:"שקשוקה" unit=גרם qty=300
- מג'דרה / מגדרה → name:"מג'דרה" unit=גרם qty=200
- סביח → name:"סביח" unit=יחידה qty=1
- חסה → name:"חסה" unit=יחידה qty=1
- חציל → name:"חציל" unit=יחידה qty=1
- ריבה → name:"ריבה" unit=כף qty=1
- קרקר / קרקרים → name:"קרקרים" unit=יחידה qty=5
- לאפה / לאפות → name:"פיתה" unit=יחידה qty=1
- תפוח אדמה (FULL NAME, not "תפוח") → name:"תפוח אדמה" unit=יחידה qty=1
- שמן זית → name:"שמן זית" unit=כף qty=1
- לבן / גבינת לבן → name:"גבינה לבנה" unit=כף qty=2
- גבינה בולגרית / גבינה מלוחה → name:"גבינה בולגרית" unit=גרם qty=30
- ביסלי → name:"ביסלי" unit=גרם qty=30
- במבה → name:"במבה" unit=גרם qty=30
- מרק עוף → name:"מרק עוף" unit=כוס qty=1
- "שתיתי X" → log X as drink
- "ארוחת X: Y" → set meal_type=X, log food Y
- "בבוקר..." → meal_type=breakfast
- "לצהריים..." / "בצהריים..." → meal_type=lunch
- "בערב..." / "בלילה..." → meal_type=dinner
- "אחה''צ..." / "חטיף..." → meal_type=afternoon_snack

=== CRITICAL CONFUSION PREVENTION — these mistakes are FORBIDDEN ===
- אספרסו = COFFEE (קפה שחור) ← NOT אספרגוס (vegetable!)
- סטייק = בשר בקר ← NOT עוף! Never map סטייק to chicken.
- תפוז = orange fruit ← NOT תפוח (apple)!
- חציל = eggplant ← NOT חזה עוף!
- מקושקשת = scrambled eggs (ביצה) ← NOT שניצל!
- המבורגר = בשר בקר (name:"בשר בקר טחון") ← never return name:"המבורגר"
- קבב = grilled meat → name:"קבב בקר" unit=יחידה (NEVER לחם or טונה!)
- שניצל תירס ≠ שניצל עוף — COMPLETELY DIFFERENT! תירס=corn schnitzel
- כריך טונה → foods=[לחם x2 פרוסות, טונה x1 קופסה]
- "N ביצים" → qty=N, name="ביצה" (one item)
- "חביתה עם N ביצים" → qty=N, name="ביצה" (ONE item only)
- "ארוחת צהריים שניצל" → meal_type=lunch, log שניצל עוף
- לביבות ≠ פנקייק ← לביבות = potato pancakes, פנקייק = sweet pancakes
- פרגית / ירך עוף → name:"פרגית" unit=יחידה qty=1 (NOT חזה עוף!)
- מרק = soup → name:"מרק עוף" or "מרק ירקות" by context
- "X, Y, Z" or "X עם Y ועם Z" → log ALL foods as separate items in foods array
- If foods array would be EMPTY → do NOT return JSON at all

=== IF NO FOOD AT ALL (pure question, greeting, or vague) — plain Hebrew only (no JSON) ===
Examples of NO-JSON inputs:
  "תודה", "כן", "לא", "בסדר", "אוקיי" → just reply warmly, NO JSON
  "מה כדאי לאכול?" / "מה אני יכול לאכול?" → give advice, NO JSON
  "אכלתי קצת" / "אכלתי הרבה" (no specific food) → ask "מה בדיוק אכלת?", NO JSON
  "שאלה..." / "יש לי שאלה..." → answer the question, NO JSON"""


#  Food aliases: common Israeli names → searchable DB terms 
FOOD_ALIASES = {
    "טוסט":          "לחם",
    "לחם לבן":       "לחם",
    "לחם מלא":       "לחם",
    "לחם שחור":      "לחם",
    "לחם פרוס":      "לחם",
    "כריך":          "לחם",
    "לחמנייה":       "לחמנייה",
    "באגט":          "לחם",
    "פוקצ'ה":        "לחם",
    "חביתה":         "ביצה",
    "שקשוקה":        "ביצה",
    "עין":           "ביצה",       # ביצת עין
    "מקושקשת":       "ביצה",
    "קוטג'":         "גבינת קוטג'",
    "קוטג׳":         "גבינת קוטג'",
    "בולגרית":       "גבינה בולגרית",
    "צהובה":         "גבינה צהובה",
    "לבנה":          "גבינה לבנה",
    "שמנת":          "שמנת",
    "לבן":           "גבינה לבנה",
    "גבינת לבן":     "גבינה לבנה",
    "קציצה":         "קציצות עוף",   # singular → canonical plural name
    "חזה":           "חזה עוף",
    "שניצל":         "שניצל עוף",
    "כנפיים":        "כנפי עוף",
    "ירך":           "ירך עוף",
    "פרגית":         "עוף",
    "קבב":           "בשר בקר",
    "המבורגר":       "בשר בקר טחון",
    "סטייק":         "סטייק בקר",
    "שווארמה":       "שווארמה עוף",
    "שאורמה":        "שווארמה עוף",
    "פלאפל":         "פלאפל",
    "טונה":          "טונה בשמן",
    "סלמון":         "דג סלמון",
    "לוקוס":         "דג לוקוס",
    "אורז":          "אורז לבן",
    "פסטה":          "פסטה",
    "ספגטי":         "פסטה ספגטי",
    "פנה":           "פסטה פנה",
    "קינואה":        "קינואה",
    "קוסקוס":        "קוסקוס",
    "עדשים":         "עדשים כתומות",
    "חומוס גרגרים":  "גרגרי חומוס",
    "גרנולה":        "גרנולה",
    "שיבולת שועל":   "שיבולת שועל",
    "קוואקר":        "שיבולת שועל",
    "יוגורט":        "יוגורט",

    "חלב":           "חלב",
    "תפוח":          "תפוח עץ",
    "בננה":          "בננה",
    "תפוז":          "תפוז",
    "אבוקדו":        "אבוקדו",
    "עגבנייה":       "עגבנייה",
    "מלפפון":        "מלפפון",
    "גזר":           "גזר",
    "חסה":           "חסה",
    "פלפל":          "פלפל אדום",
    "ברוקולי":       "ברוקולי",
    "תרד":           "תרד",
    "תפוח אדמה":     "תפוח אדמה",
    "בטטה":          "בטטה",
    "חציל":          "חציל",
    "חצילים":        "חציל",
    "קישוא":         "קישוא",
    "שמן זית":       "שמן זית",
    "חמאה":          "חמאה",
    "טחינה":         "טחינה גולמית",
    "חומוס":         "חומוס מוכן",
    "גואקמולה":      "ממרח אבוקדו",
    "ריבה":          "ריבה",
    "דבש":           "דבש",
    "שוקולד":        "שוקולד מריר",
    "גלידה":         "גלידה",
    "קפה":           "קפה שחור",
    "אספרסו":        "קפה שחור",
    "מקפה":          "קפה שחור",
    "אמריקנו":       "קפה שחור",
    "לאטה":          "קפה עם חלב",
    "קפוצינו":       "קפה עם חלב",
    "קפה נס":        "קפה שחור",
    "שוקו":          "משקה שוקולד",
    "מיץ תפוזים":    "מיץ תפוזים",
    "פיתה":          "פיתה",
    "לאפה":          "פיתה",
    "טורטיה":        "טורטייה",
    "במבה":          "במבה",
    "ביסלי":         "ביסלי",
    "קרקר":          "קרקר",
}

UNIT_TO_GRAMS = {
    "גרם": 1, "גר": 1, "ג": 1,
    "קילוגרם": 1000, "קילו": 1000,
    "כוס": 240, "כוסות": 240,
    "כף": 15, "כפות": 15,
    "כפית": 5, "כפיות": 5,
    "מל": 1, "מ״ל": 1, "מיליליטר": 1,
    "ליטר": 1000,
    "פרוסה": 30, "פרוסות": 30,
    "קציצה": 80, "קציצות": 80,
    "עוגייה": 15, "עוגיות": 15,
    "פחית": 330, "פחיות": 330,
    "קופסה": 100, "קופסת": 100,  # קופסת טונה/סרדינים = 100g
    "בקבוק": 500,
    "גביע": 125, "גביעים": 125,
    "לחמנייה": 50,
}

# מנות מורכבות — ערכים משוערים לכל מנה
_COMPOSITE_DISHES = {
    "קבב בפיתה":       {"cal": 550, "prot": 30, "carbs": 55, "fat": 20, "grams": 300},
    "שווארמה בפיתה":   {"cal": 500, "prot": 28, "carbs": 50, "fat": 18, "grams": 280},
    "פלאפל בפיתה":     {"cal": 400, "prot": 14, "carbs": 58, "fat": 14, "grams": 260},
    "סביח בפיתה":      {"cal": 450, "prot": 18, "carbs": 52, "fat": 18, "grams": 270},
    "המבורגר":         {"cal": 550, "prot": 32, "carbs": 38, "fat": 28, "grams": 280},
    "שניצל בפיתה":     {"cal": 500, "prot": 28, "carbs": 50, "fat": 18, "grams": 270},
    "כריך גבינה":      {"cal": 320, "prot": 14, "carbs": 40, "fat": 12, "grams": 180},
    "כריך טונה":       {"cal": 300, "prot": 20, "carbs": 38, "fat":  8, "grams": 180},
    "כריך עוף":        {"cal": 350, "prot": 24, "carbs": 38, "fat": 10, "grams": 200},
}

_STOPWORDS = {"עם","של","ה","ו","ל","מ","ב","את","שחור","טרי","מבושל","מטוגן"}

def _resolve_alias(name: str) -> str:
    """Map common food names/slang to DB-searchable terms."""
    # Exact match
    if name in FOOD_ALIASES:
        return FOOD_ALIASES[name]
    # Partial match — longest wins
    best, best_len = name, 0
    for alias, canonical in FOOD_ALIASES.items():
        if alias in name and len(alias) > best_len:
            best, best_len = canonical, len(alias)
    return best

def _match_food(name: str, quantity: float, unit: str):
    # 0. Check composite dishes first
    for dish_name, vals in _COMPOSITE_DISHES.items():
        if dish_name in name or name in dish_name:
            n_portions = max(1, int(round(quantity)))
            return {
                "food_id":   f"composite_{dish_name}",
                "food_name": dish_name,
                "grams":     float(vals["grams"] * n_portions),
                "calories":  float(vals["cal"] * n_portions),
                "protein":   float(vals["prot"] * n_portions),
                "carbs":     float(vals["carbs"] * n_portions),
                "fat":       float(vals["fat"] * n_portions),
                "nutrition_per_100g": {
                    "calories_kcal": round(vals["cal"] / vals["grams"] * 100, 1),
                    "protein_g":     round(vals["prot"] / vals["grams"] * 100, 1),
                    "carbs_g":       round(vals["carbs"] / vals["grams"] * 100, 1),
                    "fat_g":         round(vals["fat"] / vals["grams"] * 100, 1),
                },
            }

    # 1. Try alias on full name first
    resolved = _resolve_alias(name)

    # 2. Build search candidates (no alias on sub-words — avoids false matches)
    candidates = []
    if resolved != name:
        candidates.append(resolved)   # aliased full name
    candidates.append(name)           # original full name

    # Sub-word candidates from ORIGINAL name only (no alias resolution)
    orig_words = [w for w in name.split() if len(w) > 1]
    if len(orig_words) >= 2:
        candidates.append(" ".join(orig_words[:2]))   # first 2 words
        candidates.append(" ".join(orig_words[-2:]))  # last 2 words
        candidates.append(" ".join(orig_words[:-1]))  # all but last
    for w in orig_words:
        if w not in _STOPWORDS and len(w) > 2:
            candidates.append(w)

    food = None
    for cand in candidates:
        results = catalog.search_foods(cand.strip(), limit=1)
        if results:
            food = results[0]
            break

    #  Ingredient found in catalog 
    if food:
        unit_g = UNIT_TO_GRAMS.get(unit)
        if unit_g:
            grams = unit_g * quantity
        else:
            grams = food.default_serving_g * quantity

        grams = max(1.0, round(grams, 0))
        n = food.nutrition_per_100g
        ratio = grams / 100.0
        return {
            "food_id":   food.food_id,
            "food_name": food.name_he,
            "grams":     grams,
            "calories":  round(n.calories_kcal * ratio, 1),
            "protein":   round(n.protein_g     * ratio, 1),
            "carbs":     round(n.carbs_g       * ratio, 1),
            "fat":       round(n.fat_g         * ratio, 1),
            "nutrition_per_100g": {
                "calories_kcal": n.calories_kcal,
                "protein_g":     n.protein_g,
                "carbs_g":       n.carbs_g,
                "fat_g":         n.fat_g,
            },
        }

    #  Fallback: search recipes (complex dishes) 
    for cand in candidates:
        recipe_results = recipe_mgr.search_recipes(
            RecipeFilter(search_text=cand.strip(), max_results=1)
        )
        if recipe_results:
            rec = recipe_results[0]
            portions   = max(rec.get("portions", 1), 1)
            nut        = rec.get("total_nutrition", {})
            cal_per    = nut.get("calories", 0) / portions
            prot_per   = nut.get("protein",  0) / portions
            carbs_per  = nut.get("carbs",    0) / portions
            fat_per    = nut.get("fat",      0) / portions
            rec_id     = rec.get("recipe_id", "")
            rec_name   = rec.get("name_he", name)

            # quantity here means number of portions
            n_portions = max(1, int(round(quantity)))
            approx_g   = n_portions * 200  # ~200g per portion estimate

            return {
                "food_id":   f"recipe_{rec_id}",
                "food_name": rec_name,
                "grams":     float(approx_g),
                "calories":  round(cal_per  * n_portions, 1),
                "protein":   round(prot_per * n_portions, 1),
                "carbs":     round(carbs_per* n_portions, 1),
                "fat":       round(fat_per  * n_portions, 1),
                "nutrition_per_100g": {
                    "calories_kcal": round(cal_per  / 2, 1),
                    "protein_g":     round(prot_per / 2, 1),
                    "carbs_g":       round(carbs_per/ 2, 1),
                    "fat_g":         round(fat_per  / 2, 1),
                },
            }

    return None


@st.cache_data(ttl=300)
def _build_profile_context(user_id: str) -> str:
    """Load user profile and build a short context string for the AI."""
    try:
        from nutrition_app.repositories.profile_repository import ProfileRepository
        profile = ProfileRepository().load(user_id)
        if not profile:
            return ""
        name   = profile.get("name", "")
        goal   = profile.get("goal", "")
        allergs = profile.get("meal_preferences", {}).get("allergies", [])
        # Estimate TDEE (simplified)
        weight = float(profile.get("weight_kg", 0) or 0)
        height = float(profile.get("height_cm", 0) or 0)
        gender = profile.get("gender", "male")
        dob    = profile.get("date_of_birth", "")
        age    = 30
        try:
            from datetime import date as _d
            birth = _d.fromisoformat(dob)
            age   = (_d.today() - birth).days // 365
        except Exception:
            pass
        if weight > 0 and height > 0:
            if gender == "female":
                bmr = 10*weight + 6.25*height - 5*age - 161
            else:
                bmr = 10*weight + 6.25*height - 5*age + 5
            act = {"sedentary":1.2,"lightly_active":1.375,"moderately_active":1.55,
                   "very_active":1.725,"extremely_active":1.9}
            mult = act.get(profile.get("activity_level","moderately_active"), 1.55)
            tdee = round(bmr * mult)
            goal_adj = {"lose_weight":-300,"gain_weight":+300}.get(goal, 0)
            target = tdee + goal_adj
        else:
            target = 0

        lines = ["=== USER PROFILE ==="]
        if name:
            lines.append(f"Name: {name}")
        if target:
            lines.append(f"Daily calorie target: {target} kcal")
        if allergs:
            lines.append(f"Allergies (NEVER suggest): {', '.join(allergs)}")
        goal_map = {"lose_weight":"ירידה במשקל","gain_weight":"עלייה במשקל","maintain":"שמירה על משקל"}
        if goal:
            lines.append(f"Goal: {goal_map.get(goal, goal)}")
        lines.append("")
        return "\n".join(lines)
    except Exception:
        return ""


##  Hebrew → router key mappings 
_HE_CONDITION_MAP = {
    "דיסליפידמיה / כולסטרול גבוה": "dyslipidemia",
    "כולסטרול":     "dyslipidemia",
    "סוכרת סוג 2":  "diabetes",
    "סוכרת":        "diabetes",
    "ibs / מעי רגיז": "ibs",
    "ibs":          "ibs",
    "מעי רגיז":     "ibs",
    "gerd / ריפלוקס": "gerd",
    "gerd":         "gerd",
    "ריפלוקס":      "gerd",
    "צליאק":        "celiac",
    "מחלת לב":      "dyslipidemia",
    "יתר לחץ דם":   "dyslipidemia",
    "מחלת כליות":   "gi_disorder",
}
_HE_INTOLERANCE_MAP = {
    "גלוטן":   "gluten",
    "לקטוז":   "lactose",
    "בוטנים":  "peanuts",
    "אגוזים":  "nuts",
    "ביצים":   "eggs",
    "דגים":    "fish",
    "סויה":    "soy",
    "שומשום":  "sesame",
}
_HE_SPORT_MAP = {
    "gym":          "gym",
    "running":      "running",
    "team_sport":   "team_sport",
    "bodybuilding": "bodybuilding",
    "martial_arts": "martial_arts",
    "cycling":      "cycling",
}
_HE_DIET_MAP = {
    "mediterranean": "mediterranean",
    "keto":          "keto",
    "if":            "if",
    "vegetarian":    "vegetarian",
    "vegan":         "vegan",
}


def _build_knowledge_context(user_id: str) -> str:
    """Return a compact nutrition hint based on user profile.
    Maps Hebrew profile values → router English keys → loads correct modules."""
    try:
        from nutrition_app.repositories.profile_repository import ProfileRepository as _PR
        _profile_data = _PR().load(user_id)
        _prefs = _profile_data.get("meal_preferences", {})

        # Map Hebrew conditions → router keys
        _conditions = []
        for c in _prefs.get("medical_conditions", []):
            key = _HE_CONDITION_MAP.get(c.lower(), _HE_CONDITION_MAP.get(c, c))
            _conditions.append(key)

        # Map Hebrew intolerances → router keys
        _intolerances = []
        for a in _prefs.get("allergies", []):
            key = _HE_INTOLERANCE_MAP.get(a, a.lower())
            _intolerances.append(key)

        _kashrut = _prefs.get("kashrut", "none")
        _diet    = _prefs.get("diet_type", "")
        _sport   = _prefs.get("sport_type", "")

        hints = []
        raw_conditions = _prefs.get("medical_conditions", [])
        raw_allergies  = _prefs.get("allergies", [])
        if raw_conditions:
            hints.append(f"מצבים רפואיים: {', '.join(raw_conditions)}")
        if raw_allergies:
            hints.append(f"אלרגיות/אי-סבילות: {', '.join(raw_allergies)} — אל תציע מזונות אלה")
        if _kashrut and _kashrut != "none":
            hints.append(f"כשרות: {_kashrut} — שמור על הפרדת בשר/חלב")
        if _diet:
            hints.append(f"סגנון תזונה: {_diet}")
        if _sport:
            hints.append(f"ספורט: {_sport}")

        return ("=== הגבלות תזונתיות למשתמש זה ===\n" + "\n".join(hints)) if hints else ""
    except Exception:
        return ""


def _ask_groq(history: list, user_msg: str, pending: list = None):
    """Send to Groq, return (reply_text, food_data_or_None)."""
    profile_ctx   = _build_profile_context(USER_ID)
    knowledge_ctx = _build_knowledge_context(USER_ID)
    # Combine: food-log system prompt + knowledge router context
    base_prompt   = _build_system_prompt(FOOD_LIST, profile_ctx)
    if knowledge_ctx:
        full_prompt = base_prompt + "\n\n" + knowledge_ctx
    else:
        full_prompt = base_prompt
    messages = [{"role": "system", "content": full_prompt}]
    messages += history

    # If there are pending entries, inject them as context so the AI can correct them
    if pending:
        pending_summary = ", ".join(
            f'{e["food_name"]} {int(e["grams"])}גרם' for e in pending
        )
        context_msg = (
            f"[SYSTEM CONTEXT - not said by user] "
            f"Currently pending (waiting for user approval): {pending_summary}. "
            f"If the user asks to change quantity/food — return FULL updated JSON with ALL items corrected."
        )
        messages.append({"role": "user", "content": context_msg})
        messages.append({"role": "assistant", "content": "הבנתי, אני זוכר מה בכרטיסייה."})

    messages.append({"role": "user", "content": user_msg})

    import time as _time
    for _attempt in range(3):
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=700,
                temperature=0.2,
            )
            break
        except Exception as _ex:
            if "429" in str(_ex) and _attempt < 2:
                _time.sleep(15 * (_attempt + 1))   # wait 15s, then 30s
                continue
            raise
    raw = resp.choices[0].message.content.strip()

    # 1. Try ```json ... ``` block
    json_str = None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if m:
        json_str = m.group(1)
    else:
        # 2. Try raw JSON object anywhere in the response
        m2 = re.search(r'(\{[\s\S]*"meal_type"[\s\S]*"foods"[\s\S]*\})', raw)
        if m2:
            json_str = m2.group(1)

    if json_str:
        try:
            data = json.loads(json_str)
            reply = data.get("reply", "")
            return reply, data
        except Exception:
            pass

    # No JSON — plain conversational reply
    return raw, None


#  Session state 
if "chat_messages"    not in st.session_state: st.session_state.chat_messages    = []
if "groq_history"     not in st.session_state: st.session_state.groq_history     = []
if "pending_entries"  not in st.session_state: st.session_state.pending_entries  = []
if "detected_meal"    not in st.session_state: st.session_state.detected_meal    = "lunch"
if "_ai_processing"   not in st.session_state: st.session_state._ai_processing   = False
if "_pending_user_msg" not in st.session_state: st.session_state._pending_user_msg = None

#  Get user first name 
def _get_user_name() -> str:
    try:
        import json as _json
        from nutrition_app.storage_paths import legacy_users_file
        _path = str(legacy_users_file())
        _data = _json.load(open(_path, encoding="utf-8"))
        for _u in _data.values():
            if _u.get("name"):
                return _u["name"]
    except Exception:
        pass
    return "חבר"

_USER_NAME = _get_user_name()

#  AI processing — runs BEFORE any render to avoid double-render 
# Pattern: form submit → add user msg + "_thinking" msg → set flag → rerun
#          next run  → this block fires, calls API, replaces thinking → rerun
#          final run → clean render, no spinner, no duplicate
if st.session_state._ai_processing and st.session_state._pending_user_msg:
    _user_msg = st.session_state._pending_user_msg
    try:
        _reply_text, _food_data = _ask_groq(
            st.session_state.groq_history,
            _user_msg,
            pending=st.session_state.pending_entries or None,
        )
    except Exception as _e:
        import traceback as _tb
        st.session_state["_last_chat_error"] = _tb.format_exc()
        if "429" in str(_e) or "rate_limit" in str(_e).lower():
            _reply_text = "יש עומס על השרת כרגע — נסה שוב בעוד כמה שניות"
        elif "timeout" in str(_e).lower() or "connection" in str(_e).lower():
            _reply_text = " בעיית חיבור — בדוק אינטרנט ונסה שוב"
        else:
            _reply_text = " תקלה זמנית — נסה שוב"
        _food_data = None

    # Remove temporary "thinking" bubble
    if st.session_state.chat_messages and st.session_state.chat_messages[-1].get("_thinking"):
        st.session_state.chat_messages.pop()

    st.session_state.groq_history.append({"role": "user", "content": _user_msg})
    if _reply_text:
        st.session_state.groq_history.append({"role": "assistant", "content": _reply_text})

    if _food_data:
        try:
            _meal_type = _food_data.get("meal_type", "lunch")
            st.session_state.detected_meal = _meal_type
            _matched, _not_found = [], []
            for _f in _food_data.get("foods", []):
                _entry = _match_food(_f["name"], float(_f.get("quantity", 1)), _f.get("unit", "יחידה"))
                if _entry:
                    _matched.append(_entry)
                else:
                    _not_found.append(_f["name"])
            if _matched:
                st.session_state.pending_entries = _matched
                if _not_found:
                    _reply_text += f"\n\n לא מצאתי במאגר: *{', '.join(_not_found)}*"
            else:
                _reply_text = "לא מצאתי את המזונות במאגר. נסה לנסח אחרת."
        except Exception as _e2:
            import traceback as _tb2
            st.session_state["_last_chat_error"] = _tb2.format_exc()
            _reply_text += f"\n\n שגיאה בעיבוד: `{type(_e2).__name__}: {_e2}`"

    if _reply_text:
        st.session_state.chat_messages.append({"role": "assistant", "text": _reply_text})

    st.session_state._ai_processing    = False
    st.session_state._pending_user_msg = None
    st.rerun()

#  Build all chat HTML as one block + scroll JS 
def _render_chat():
    msgs = st.session_state.chat_messages

    # Build message bubbles HTML
    bubbles = ""
    if not msgs:
        bubbles = (
            f'<div dir="rtl" style="display:flex;margin-bottom:10px;align-items:flex-start">'
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
            f'border-radius:4px 16px 16px 16px;padding:10px 14px;max-width:88%;'
            f'font-size:0.86rem;color:#f4f6fb;line-height:1.55;direction:rtl">'
            f'שלום {_USER_NAME}, איך אוכל לעזור?</div></div>'
        )
    else:
        for msg in msgs:
            txt = msg["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            if msg["role"] == "assistant":
                # "thinking" bubble gets a pulsing dots style
                if msg.get("_thinking"):
                    bubble_content = (
                        '<span class="biti-thinking">'
                        '<span></span><span></span><span></span>'
                        '</span>'
                    )
                else:
                    bubble_content = txt
                bubbles += (
                    f'<div dir="rtl" style="display:flex;margin-bottom:10px;align-items:flex-start">'
                    f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                    f'border-radius:4px 16px 16px 16px;padding:10px 14px;max-width:88%;'
                    f'font-size:0.86rem;color:#f4f6fb;line-height:1.55;direction:rtl">'
                    f'{bubble_content}</div></div>'
                )
            else:
                bubbles += (
                    f'<div dir="rtl" style="display:flex;margin-bottom:10px;'
                    f'align-items:flex-start;justify-content:flex-end">'
                    f'<div dir="rtl" style="background:#1a3a6b;border:1px solid #2d5096;'
                    f'border-radius:16px 4px 16px 16px;padding:10px 14px;max-width:80%;'
                    f'font-size:0.86rem;color:#e8f0ff;line-height:1.55;direction:rtl">'
                    f'{txt}</div></div>'
                )

    st.markdown(
        f'<div id="chat-scroll-box" style="'
        f'max-height:58vh;overflow-y:auto;padding:4px 2px 8px;'
        f'display:flex;flex-direction:column;">'
        f'{bubbles}'
        f'<div id="chat-end"></div>'
        f'</div>'
        f'<script>'
        f'(function(){{'
        f'  var b=document.getElementById("chat-scroll-box");'
        f'  if(b) b.scrollTop=b.scrollHeight;'
        f'  setTimeout(function(){{'
        f'    var b2=document.getElementById("chat-scroll-box");'
        f'    if(b2) b2.scrollTop=b2.scrollHeight;'
        f'  }},200);'
        f'}})();'
        f'</script>',
        unsafe_allow_html=True
    )

_render_chat()

#  Input — immediately after chat, ABOVE the food card 
with st.form("chat_form", clear_on_submit=True):
    col_in, col_btn = st.columns([5, 1])
    user_text = col_in.text_input("כתוב כאן", placeholder="מה אכלת?",
                                   label_visibility="collapsed", key="chat_input")
    submitted = col_btn.form_submit_button("שלח ", use_container_width=True, type="primary")

if submitted and user_text.strip():
    # Add user message immediately
    st.session_state.chat_messages.append({"role": "user", "text": user_text})
    # Add a temporary "thinking" bubble — will be replaced by the AI response
    st.session_state.chat_messages.append({"role": "assistant", "text": "", "_thinking": True})
    # Store what to process and trigger processing on next run
    st.session_state._pending_user_msg = user_text
    st.session_state._ai_processing    = True
    st.rerun()

#  Pending confirmation card — BELOW input 
if st.session_state.pending_entries:
    st.markdown(
        '<div dir="rtl" style="background:#0d1f0d;border:1px solid #1a4d1a;'
        'border-radius:16px;padding:14px 16px;margin:8px 0 4px">',
        unsafe_allow_html=True)

    st.markdown(
        '<div dir="rtl" style="font-size:0.72rem;color:#8892a4;margin-bottom:6px">'
        'ערוך כמויות ישירות או כתוב לביטי לתקן</div>',
        unsafe_allow_html=True)

    meal_type_sel = st.selectbox(
        "ארוחה", options=list(MEAL_HEB.keys()),
        format_func=lambda k: MEAL_HEB[k],
        index=list(MEAL_HEB.keys()).index(st.session_state.detected_meal)
              if st.session_state.detected_meal in MEAL_HEB else 2,
        key="confirm_meal_type")

    confirmed, any_removed = [], False
    for i, entry in enumerate(st.session_state.pending_entries):
        c_name, c_gram, c_del = st.columns([4, 2, 1])
        c_name.markdown(
            f'<div dir="rtl" style="font-size:0.84rem;font-weight:700;color:#f4f6fb;padding-top:6px">'
            f'{entry["food_name"]}</div>'
            f'<div dir="rtl" style="font-size:0.68rem;color:#4ade80">'
            f'{entry["calories"]:.0f} קק״ל · {entry["protein"]:.0f}g חלבון</div>',
            unsafe_allow_html=True)
        new_g = c_gram.number_input("ג", min_value=1, max_value=2000,
                                     value=max(1, int(entry["grams"])),
                                     step=10, key=f"gram_{i}",
                                     label_visibility="collapsed")
        entry["grams"] = float(new_g)
        ratio = new_g / 100.0
        n = entry["nutrition_per_100g"]
        entry["calories"] = round(n["calories_kcal"] * ratio, 1)
        entry["protein"]  = round(n["protein_g"]     * ratio, 1)
        entry["carbs"]    = round(n["carbs_g"]        * ratio, 1)
        entry["fat"]      = round(n["fat_g"]          * ratio, 1)
        if c_del.button("", key=f"del_{i}"):
            any_removed = True
        else:
            confirmed.append(entry)

    if any_removed:
        st.session_state.pending_entries = confirmed
        st.rerun()

    total_cal = int(sum(e["calories"] for e in st.session_state.pending_entries))
    st.markdown(
        f'<div dir="rtl" style="margin:6px 0 6px;display:flex;justify-content:space-between;align-items:center">'
        f'<div dir="rtl" style="font-size:0.72rem;color:#8892a4">סה״כ</div>'
        f'<div dir="rtl" style="font-size:1rem;font-weight:800;color:#4ade80">{total_cal} קק״ל</div></div>',
        unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    if c1.button("הוסף לרשומות", type="primary", use_container_width=True):
        today = date.today()
        added_cal = 0
        for entry in st.session_state.pending_entries:
            food_log_repo.add_entry(USER_ID, today, FoodLogEntry(
                food_id=entry["food_id"], food_name=entry["food_name"],
                grams=entry["grams"], calories=entry["calories"],
                protein=entry["protein"], carbs=entry["carbs"], fat=entry["fat"],
                meal_type=meal_type_sel, timestamp=datetime.now().isoformat()))
            added_cal += entry["calories"]
        n_added = len(st.session_state.pending_entries)
        st.session_state.pending_entries = []
        txt = f"נרשמו {n_added} פריטים — {int(added_cal)} קק״ל ל{MEAL_HEB.get(meal_type_sel,'')}. רוצה להוסיף עוד?"
        st.session_state.chat_messages.append({"role":"assistant","text":txt})
        st.session_state.groq_history.append({"role":"assistant","content":txt})
        st.rerun()

    if c2.button("ביטול", use_container_width=True):
        st.session_state.pending_entries = []
        txt = "בסדר, ביטלתי. תגיד לי מחדש מה אכלת."
        st.session_state.chat_messages.append({"role":"assistant","text":txt})
        st.session_state.groq_history.append({"role":"assistant","content":txt})
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

#  Debug info (only shown when there is an error) 
if st.session_state.get("_last_chat_error"):
    with st.expander(" פרטי שגיאה אחרונה (למפתח)"):
        st.code(st.session_state["_last_chat_error"], language="python")
        if st.button("נקה שגיאה"):
            del st.session_state["_last_chat_error"]
            st.rerun()

bottom_nav("chat")
