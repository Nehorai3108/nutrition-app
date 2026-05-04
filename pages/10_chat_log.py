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

catalog       = _get_catalog()
groq_client   = _get_groq()
food_log_repo = FoodLogRepository()
USER_ID       = "ui_user_001"

MEAL_HEB = {
    "breakfast":       "🌅 ארוחת בוקר",
    "morning_snack":   "☕ חטיף בוקר",
    "lunch":           "🍽️ ארוחת צהריים",
    "afternoon_snack": "🍎 חטיף אחה״צ",
    "dinner":          "🌙 ארוחת ערב",
    "evening_snack":   "🌜 חטיף ערב",
    "snack":           "🍫 נשנוש",
}

SYSTEM_PROMPT = """You are "Biti", a warm Israeli nutrition assistant in the BiteFit app.
Your job: help users log their meals accurately and in a friendly way.

Rules:
1. Always reply in Hebrew, short and human (1-3 sentences max)
2. When the user mentions food — return JSON. Otherwise reply conversationally.
3. Remember context: "ומה עם הלחם?" after a meal = the bread from that same meal
4. If critical info is missing — ask ONE specific question
5. Never invent nutrition values — the system handles that
6. Food names in the JSON must be in Hebrew

When there is food to log, return EXACTLY this format (JSON inside ```json):
```json
{
  "meal_type": "breakfast|morning_snack|lunch|afternoon_snack|dinner|evening_snack",
  "foods": [
    {"name": "Hebrew food name", "quantity": 1, "unit": "יחידה|גרם|כוס|פרוסה|כף|קציצה|פחית|גביע|לחמנייה"}
  ],
  "reply": "Short friendly Hebrew reply"
}
```

If no food — plain Hebrew text only (NO json block).

Examples:
- "שתי ביצים עם גבינה" → json with foods:[{name:"ביצה",quantity:2,unit:"יחידה"},{name:"גבינה לבנה",quantity:1,unit:"יחידה"}], reply:"רשמתי! שתי ביצים עם גבינה 🍳"
- "חזה עוף 200 גרם" → json with foods:[{name:"חזה עוף",quantity:200,unit:"גרם"}], reply:"מעולה! חזה עוף 200 גרם נרשם ✅"
- "ומה עם הלחם?" → json with foods:[{name:"לחם",quantity:1,unit:"פרוסה"}], reply:"הלחם נרשם! כמה פרוסות בדיוק?"
- "מה אפשר לאכול אחרי אימון?" → plain Hebrew advice, no json"""


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

_STOPWORDS = {"עם","של","ה","ו","ל","מ","ב","את","לבן","שחור","טרי","מבושל","מטוגן"}

def _match_food(name: str, quantity: float, unit: str):
    words = [w for w in name.split() if len(w) > 1]
    candidates = [name]
    if len(words) >= 2:
        candidates.append(" ".join(words[-2:]))
        candidates.append(" ".join(words[:-1]))
        candidates.append(words[0])
    for w in reversed(words):
        if w not in _STOPWORDS:
            candidates.append(w)

    food = None
    for cand in candidates:
        results = catalog.search_foods(cand.strip(), limit=1)
        if results:
            food = results[0]
            break
    if not food:
        return None

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


def _ask_groq(history: list, user_msg: str):
    """Send to Groq, return (reply_text, food_data_or_None)."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history
    messages.append({"role": "user", "content": user_msg})

    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600,
        temperature=0.4,
    )
    raw = resp.choices[0].message.content.strip()

    # Try to extract JSON block
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
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

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;padding:4px 2px 4px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#4f8ef7">BiteFit</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{date.today().strftime("%d/%m/%Y")}</div>'
    f'</div>', unsafe_allow_html=True)
st.markdown(
    '<div dir="rtl" style="font-size:0.78rem;color:#8892a4;margin-bottom:12px">'
    'ספר לביטי מה אכלת — בעברית טבעית</div>', unsafe_allow_html=True)

# ── Chat history ───────────────────────────────────────────────────────────────
for msg in st.session_state.chat_messages:
    if msg["role"] == "assistant":
        st.markdown(
            f'<div dir="rtl" style="display:flex;gap:10px;margin-bottom:10px;align-items:flex-start">'
            f'<div dir="rtl" style="width:30px;height:30px;border-radius:50%;background:#1a2540;'
            f'display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0;'
            f'border:1px solid #252d3d">🥗</div>'
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
            f'border-radius:4px 16px 16px 16px;padding:10px 14px;max-width:88%;'
            f'font-size:0.86rem;color:#f4f6fb;line-height:1.55;direction:rtl">'
            f'{msg["text"].replace(chr(10),"<br>")}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div dir="rtl" style="display:flex;gap:10px;margin-bottom:10px;align-items:flex-start;flex-direction:row-reverse">'
            f'<div dir="rtl" style="width:30px;height:30px;border-radius:50%;background:#4f8ef7;'
            f'display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0">👤</div>'
            f'<div dir="rtl" style="background:#1a3a6b;border:1px solid #2d5096;'
            f'border-radius:16px 4px 16px 16px;padding:10px 14px;max-width:88%;'
            f'font-size:0.86rem;color:#e8f0ff;line-height:1.55;direction:rtl">'
            f'{msg["text"]}</div></div>', unsafe_allow_html=True)

# ── Pending confirmation card ──────────────────────────────────────────────────
if st.session_state.pending_entries:
    st.markdown(
        '<div dir="rtl" style="background:#0d1f0d;border:1px solid #1a4d1a;border-radius:16px;'
        'padding:14px 16px;margin:8px 0 4px">', unsafe_allow_html=True)

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
            f'<div dir="rtl" style="font-size:0.86rem;font-weight:700;color:#f4f6fb;padding-top:6px">'
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
        f'<div dir="rtl" style="margin:10px 0 4px;display:flex;justify-content:space-between;align-items:center">'
        f'<div dir="rtl" style="font-size:0.72rem;color:#8892a4">סה״כ לאישור</div>'
        f'<div dir="rtl" style="font-size:1rem;font-weight:800;color:#4ade80">{total_cal} קק״ל</div></div>',
        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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

# ── Spacer + fixed input ───────────────────────────────────────────────────────
st.markdown('<div style="height:120px"></div>', unsafe_allow_html=True)
st.markdown("""
<style>
.chat-input-wrap{position:fixed;bottom:64px;left:0;right:0;z-index:9998;
background:linear-gradient(to top,#0d0f14 80%,transparent);padding:12px 16px 8px}
</style>
<div class="chat-input-wrap"></div>""", unsafe_allow_html=True)

with st.form("chat_form", clear_on_submit=True):
    col_in, col_btn = st.columns([5, 1])
    user_text = col_in.text_input("", placeholder='מה אכלת? למשל: "שתי ביצים עם גבינה לבוקר"',
                                   label_visibility="collapsed", key="chat_input")
    submitted = col_btn.form_submit_button("שלח ➤", use_container_width=True, type="primary")

if submitted and user_text.strip():
    st.session_state.chat_messages.append({"role":"user","text":user_text})

    with st.spinner("ביטי חושב..."):
        try:
            reply_text, food_data = _ask_groq(st.session_state.groq_history, user_text)
        except Exception as e:
            reply_text = "אופס, תקלה טכנית. נסה שוב 🙏"
            food_data = None

    st.session_state.groq_history.append({"role":"user","content":user_text})
    if reply_text:
        st.session_state.groq_history.append({"role":"assistant","content":reply_text})

    if food_data:
        meal_type = food_data.get("meal_type","lunch")
        st.session_state.detected_meal = meal_type
        matched, not_found = [], []
        for f in food_data.get("foods", []):
            entry = _match_food(f["name"], float(f.get("quantity",1)), f.get("unit","יחידה"))
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
        st.session_state.chat_messages.append({"role":"assistant","text":reply_text})

    st.rerun()

bottom_nav("chat")
