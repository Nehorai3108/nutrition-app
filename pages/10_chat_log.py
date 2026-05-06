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
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry

st.set_page_config(page_title="BiteFit · הזנה", page_icon="💬", layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

@st.cache_resource
def _get_catalog():
    return FoodCatalog(db_path=_DB_PATH)

@st.cache_resource
def _get_groq():
    return Groq(api_key=st.secrets["groq_api_key"])

@st.cache_resource
def _get_recipe_mgr():
    return RecipeManager()

@st.cache_resource
def _build_food_list() -> str:
    """Build food + recipe catalog string for the AI system prompt."""
    cat = FoodCatalog(db_path=_DB_PATH)
    foods = cat.search_foods("", limit=500)
    lines = []
    for f in foods:
        lines.append(f"{f.name_he} ({int(f.default_serving_g)}g)")

    # Add recipes so AI knows complex dishes by name
    try:
        mgr = RecipeManager()
        recipes = mgr.search_recipes(RecipeFilter(max_results=200))
        for r in recipes:
            name_he = r.get("name_he", "")
            portions = max(r.get("portions", 1), 1)
            nut = r.get("total_nutrition", {})
            cal = round(nut.get("calories", 0) / portions)
            if name_he and cal:
                lines.append(f"{name_he} [מתכון, {cal}קק״ל/מנה]")
    except Exception:
        pass

    return ", ".join(lines)

catalog       = _get_catalog()
recipe_mgr    = _get_recipe_mgr()
groq_client   = _get_groq()
food_log_repo = FoodLogRepository()
USER_ID       = "ui_user_001"
FOOD_LIST     = _build_food_list()

MEAL_HEB = {
    "breakfast":       "🌅 ארוחת בוקר",
    "morning_snack":   "☕ חטיף בוקר",
    "lunch":           "🍽️ ארוחת צהריים",
    "afternoon_snack": "🍎 חטיף אחה״צ",
    "dinner":          "🌙 ארוחת ערב",
    "evening_snack":   "🌜 חטיף ערב",
    "snack":           "🍫 נשנוש",
}

def _build_system_prompt(food_list: str) -> str:
    return f"""You are "Biti" — an intelligent, warm Israeli nutrition AI assistant inside the BiteFit app.
You speak like a knowledgeable friend who happens to be a nutritionist: direct, caring, and smart.

YOUR PERSONALITY:
- Warm but not cheesy. Helpful but not robotic.
- Give real nutritional insight when relevant
- Remember everything said in the conversation

YOUR JOB:
1. Log food accurately when the user describes what they ate
2. Answer nutrition questions with real knowledge
3. Handle clarifications: if user says "זה היה 200 גרם" → update the pending entry and return full corrected JSON
4. ALWAYS estimate grams even when not specified — use Israeli typical portion sizes

AVAILABLE FOODS IN DATABASE (use these names exactly in JSON):
{food_list}

SERVING SIZE GUIDE — use these when quantity is not specified:
- שניצל/קציצה/המבורגר = 130g each
- חזה עוף = 150g, ירך עוף = 120g, כנפיים = 80g each
- ביצה = 55g each
- פרוסת לחם = 30g each, לחמנייה = 50g each, פיתה = 60g each
- כוס אורז מבושל = 180g, כוס פסטה מבושלת = 180g, כוס קינואה = 185g
- כוס קטניות מבושלות = 170g
- כוס חלב = 240g, גביע יוגורט = 125g, קוטג' קטן = 150g
- כף שמן/חמאה/טחינה = 15g, כפית = 5g
- כוס ירקות = 100g, כוס פירות = 150g
- תפוח/אגס = 150g, בננה = 120g, תפוז = 130g
- כוס מיץ = 200g
- פחית שתייה = 330g, בקבוק מים = 500g

UNIT RULES:
- "3 שניצלים" → quantity:3, unit:"יחידה" (system converts to 390g)
- "4 כוסות אורז" → quantity:4, unit:"כוס"
- "2 פרוסות לחם" → quantity:2, unit:"פרוסה"
- "חצי כוס שמן" → quantity:0.5, unit:"כוס"
- If no unit given → use "יחידה" for countable foods, "גרם" with estimated weight for others

STRICT RULES:
- Always reply in Hebrew only
- Food names in JSON must match the database list above as closely as possible
- Never invent calorie counts
- When user corrects → return FULL updated JSON with ALL foods

COMPLEX DISHES — when the user says a dish name (שקשוקה, פסטה בולונז, סלט ירקות, אורז עם עוף etc.):
- First check if it appears in the food list above as [מתכון] → use that name exactly
- If not a known recipe, decompose it into individual DB ingredients:
  e.g. "אורז עם עוף ובצל" → [{name:"אורז לבן",qty:3,unit:"כף"},{name:"חזה עוף",qty:1,unit:"יחידה"},{name:"בצל",qty:0.5,unit:"יחידה"}]
- Always use names from the DB food list above

WHEN THERE IS FOOD TO LOG — return EXACTLY this format (ALWAYS wrap in ```json code block):
```json
{{
  "meal_type": "breakfast|morning_snack|lunch|afternoon_snack|dinner|evening_snack",
  "foods": [
    {{"name": "שם מהמאגר", "quantity": 1, "unit": "יחידה|גרם|פרוסה|כוס|כף|כפית|פחית|גביע"}}
  ],
  "reply": "תגובה חכמה וקצרה בעברית"
}}
```

IF NO FOOD TO LOG — reply in plain Hebrew only (no json block).

CRITICAL FOOD MAPPINGS — never confuse these:
- חביתה / ביצת עין / מקושקשת / שקשוקה → name:"ביצה" (NOT חלה, NOT לחם)
- חלה → name:"חלה" (only if user explicitly says חלה)
- לחם לבן / טוסט / כריך → name:"לחם לבן"
- חזה / חזה עוף → name:"חזה עוף"
- שניצל → name:"שניצל עוף"

EXAMPLES:
- "חביתה עם 2 ביצים" → foods:[{{name:"ביצה",qty:3,unit:"יחידה"}}]
- "3 שניצלים עם אורז" → foods:[{{name:"שניצל עוף",qty:3,unit:"יחידה"}},{{name:"אורז לבן",qty:1,unit:"כוס"}}]
- "2 ביצים עם גבינה לבנה" → foods:[{{name:"ביצה",qty:2,unit:"יחידה"}},{{name:"גבינה לבנה",qty:1,unit:"יחידה"}}]
- "חזה עוף 200 גרם" → foods:[{{name:"חזה עוף",qty:200,unit:"גרם"}}]
- "מה כדאי לאכול אחרי אימון?" → plain Hebrew advice, no json"""


# ── Food aliases: common Israeli names → searchable DB terms ──────────────────
FOOD_ALIASES = {
    "טוסט":          "toast",
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
    "חזה":           "חזה עוף",
    "שניצל":         "שניצל עוף",
    "כנפיים":        "כנפי עוף",
    "ירך":           "ירך עוף",
    "פרגית":         "עוף",
    "קבב":           "בשר בקר",
    "המבורגר":       "בשר בקר טחון",
    "סטייק":         "סטייק בקר",
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
    "לאטה":          "קפה עם חלב",
    "קפוצינו":       "קפה עם חלב",
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
    "בקבוק": 500,
    "גביע": 125, "גביעים": 125,
    "לחמנייה": 50,
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

    # ── Ingredient found in catalog ──────────────────────────────────────
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

    # ── Fallback: search recipes (complex dishes) ────────────────────────
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


def _ask_groq(history: list, user_msg: str, pending: list = None):
    """Send to Groq, return (reply_text, food_data_or_None)."""
    messages = [{"role": "system", "content": _build_system_prompt(FOOD_LIST)}]
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

    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600,
        temperature=0.4,
    )
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


# ── Session state ──────────────────────────────────────────────────────────────
if "chat_messages"    not in st.session_state: st.session_state.chat_messages    = []
if "groq_history"     not in st.session_state: st.session_state.groq_history     = []
if "pending_entries"  not in st.session_state: st.session_state.pending_entries  = []
if "detected_meal"    not in st.session_state: st.session_state.detected_meal    = "lunch"

# ── Get user first name ────────────────────────────────────────────────────────
def _get_user_name() -> str:
    try:
        import json as _json
        _path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "storage_agents", "users.json")
        _data = _json.load(open(_path, encoding="utf-8"))
        for _u in _data.values():
            if _u.get("name"):
                return _u["name"]
    except Exception:
        pass
    return "חבר"

_USER_NAME = _get_user_name()

# ── Build all chat HTML as one block + scroll JS ───────────────────────────────
def _render_chat():
    msgs = st.session_state.chat_messages

    # Build message bubbles HTML
    bubbles = ""
    if not msgs:
        bubbles = (
            f'<div dir="rtl" style="display:flex;gap:10px;margin-bottom:10px;align-items:flex-start">'
            f'<div style="width:30px;height:30px;border-radius:50%;background:#1a2540;'
            f'display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0;'
            f'border:1px solid #252d3d">&#x1F957;</div>'
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
            f'border-radius:4px 16px 16px 16px;padding:10px 14px;max-width:88%;'
            f'font-size:0.86rem;color:#f4f6fb;line-height:1.55;direction:rtl">'
            f'שלום {_USER_NAME}, איך אוכל לעזור?</div></div>'
        )
    else:
        for msg in msgs:
            txt = msg["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            if msg["role"] == "assistant":
                bubbles += (
                    f'<div dir="rtl" style="display:flex;gap:10px;margin-bottom:10px;align-items:flex-start">'
                    f'<div style="width:30px;height:30px;border-radius:50%;background:#1a2540;'
                    f'display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0;'
                    f'border:1px solid #252d3d">&#x1F957;</div>'
                    f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                    f'border-radius:4px 16px 16px 16px;padding:10px 14px;max-width:88%;'
                    f'font-size:0.86rem;color:#f4f6fb;line-height:1.55;direction:rtl">'
                    f'{txt}</div></div>'
                )
            else:
                bubbles += (
                    f'<div dir="rtl" style="display:flex;gap:10px;margin-bottom:10px;'
                    f'align-items:flex-start;flex-direction:row-reverse">'
                    f'<div style="width:30px;height:30px;border-radius:50%;background:#4f8ef7;'
                    f'display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0">&#x1F464;</div>'
                    f'<div dir="rtl" style="background:#1a3a6b;border:1px solid #2d5096;'
                    f'border-radius:16px 4px 16px 16px;padding:10px 14px;max-width:88%;'
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

# ── Input — immediately after chat, ABOVE the food card ───────────────────────
with st.form("chat_form", clear_on_submit=True):
    col_in, col_btn = st.columns([5, 1])
    user_text = col_in.text_input("כתוב כאן", placeholder="מה אכלת?",
                                   label_visibility="collapsed", key="chat_input")
    submitted = col_btn.form_submit_button("שלח ➤", use_container_width=True, type="primary")

if submitted and user_text.strip():
    st.session_state.chat_messages.append({"role": "user", "text": user_text})

    with st.spinner("ביטי חושב..."):
        try:
            reply_text, food_data = _ask_groq(
                st.session_state.groq_history, user_text,
                pending=st.session_state.pending_entries or None
            )
        except Exception as e:
            reply_text = "אופס, תקלה טכנית. נסה שוב 🙏"
            food_data = None

    st.session_state.groq_history.append({"role": "user", "content": user_text})
    if reply_text:
        st.session_state.groq_history.append({"role": "assistant", "content": reply_text})

    if food_data:
        meal_type = food_data.get("meal_type", "lunch")
        st.session_state.detected_meal = meal_type
        matched, not_found = [], []
        for f in food_data.get("foods", []):
            entry = _match_food(f["name"], float(f.get("quantity", 1)), f.get("unit", "יחידה"))
            if entry:
                matched.append(entry)
            else:
                not_found.append(f["name"])
        if matched:
            st.session_state.pending_entries = matched
            if not_found:
                reply_text += f"\n\n⚠️ לא מצאתי במאגר: *{', '.join(not_found)}*"
        else:
            reply_text = "לא מצאתי את המזונות במאגר. נסה לנסח אחרת."

    if reply_text:
        st.session_state.chat_messages.append({"role": "assistant", "text": reply_text})

    st.rerun()

# ── Pending confirmation card — BELOW input ───────────────────────────────────
if st.session_state.pending_entries:
    st.markdown(
        '<div dir="rtl" style="background:#0d1f0d;border:1px solid #1a4d1a;'
        'border-radius:16px;padding:14px 16px;margin:8px 0 4px">',
        unsafe_allow_html=True)

    st.markdown(
        '<div dir="rtl" style="font-size:0.72rem;color:#8892a4;margin-bottom:6px">'
        '💡 ערוך כמויות ישירות או כתוב לביטי לתקן</div>',
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
            f'🔥 {entry["calories"]:.0f} קק״ל · {entry["protein"]:.0f}g חלבון</div>',
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
        if c_del.button("✕", key=f"del_{i}"):
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
    if c1.button("✅ הוסף לרשומות", type="primary", use_container_width=True):
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
        txt = f"✅ נרשמו {n_added} פריטים — **{int(added_cal)} קק״ל** ל{MEAL_HEB.get(meal_type_sel,'')}\n\nרוצה להוסיף עוד?"
        st.session_state.chat_messages.append({"role":"assistant","text":txt})
        st.session_state.groq_history.append({"role":"assistant","content":txt})
        st.rerun()

    if c2.button("ביטול", use_container_width=True):
        st.session_state.pending_entries = []
        txt = "בסדר, ביטלתי 😊 תגיד לי מחדש מה אכלת."
        st.session_state.chat_messages.append({"role":"assistant","text":txt})
        st.session_state.groq_history.append({"role":"assistant","content":txt})
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

bottom_nav("chat")
