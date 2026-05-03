#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10_chat_log.py — הזנת ארוחה שיחתית בעברית
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
from typing import Optional
import streamlit as st

from ui.components import inject_global_css, bottom_nav
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_chat_parser import parse_hebrew_meal
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry

st.set_page_config(page_title="BiteFit · הזנה", page_icon="💬", layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

@st.cache_resource
def _get_catalog():
    return FoodCatalog(db_path=_DB_PATH)

catalog       = _get_catalog()
food_log_repo = FoodLogRepository()

# ── Smart food matcher ────────────────────────────────────────────────────────
_HEB_STOPWORDS = {"עם", "של", "ה", "ו", "ל", "מ", "ב", "את", "לבן", "שחור", "טרי", "מבושל"}

def _smart_match(query: str, grams_hint: Optional[float], quantity: float):
    """
    Try multiple search strategies to find the best food match.
    Returns a dict ready for pending_entries, or None.
    """
    import re as _re
    words = [w for w in query.split() if len(w) > 1]

    # Build search candidates: full → last-2-words → each-word → first-word
    candidates = []
    candidates.append(query)                              # full
    if len(words) >= 2:
        candidates.append(" ".join(words[-2:]))           # last 2 words
        candidates.append(" ".join(words[:-1]))           # all but last
    for w in reversed(words):                             # each word, longest first
        if w not in _HEB_STOPWORDS:
            candidates.append(w)

    food = None
    for cand in candidates:
        results = catalog.search_foods(cand.strip(), limit=1)
        if results:
            food = results[0]
            break

    if not food:
        return None

    n = food.nutrition_per_100g
    # Determine grams: explicit > unit-based > default_serving * quantity
    if grams_hint and grams_hint > 0:
        g = grams_hint
    else:
        g = food.default_serving_g * quantity

    g = max(1.0, round(g, 0))
    ratio = g / 100.0
    return {
        "food_id":   food.food_id,
        "food_name": food.name_he,
        "grams":     g,
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


def _process_text(text: str):
    """Parse Hebrew text and return (matched_list, not_found_list, meal_type)."""
    from typing import List, Tuple
    result  = parse_hebrew_meal(text)
    matched, not_found = [], []
    for item in result.items:
        entry = _smart_match(item.food_query, item.grams, item.quantity)
        if entry:
            matched.append(entry)
        else:
            not_found.append(item.food_query)
    return matched, not_found, result.meal_type
USER_ID      = "ui_user_001"

MEAL_HEB = {
    "breakfast":       "🌅 ארוחת בוקר",
    "morning_snack":   "☕ חטיף בוקר",
    "lunch":           "🍽️ ארוחת צהריים",
    "afternoon_snack": "🍎 חטיף אחה״צ",
    "dinner":          "🌙 ארוחת ערב",
    "evening_snack":   "🌜 חטיף ערב",
    "snack":           "🍫 נשנוש",
}

EXAMPLES = [
    "אכלתי שתי ביצים עם גבינה לבנה וכוס קפה",
    "חזה עוף 150 גרם עם אורז ושעועית לצהריים",
    "יוגורט, בננה וכף דבש לארוחת בוקר",
    "סלט עם טונה, עגבנייה ומלפפון",
    "פיתה עם חומוס וסלט ערבי לצהריים",
]

# ── Session state ─────────────────────────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "pending_entries" not in st.session_state:
    st.session_state.pending_entries = []
if "show_examples" not in st.session_state:
    st.session_state.show_examples = True

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;'
    f'padding:4px 2px 4px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#4f8ef7;letter-spacing:-0.01em">BiteFit</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{date.today().strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div dir="rtl" style="font-size:0.78rem;color:#8892a4;margin-bottom:12px">'
    'פשוט תספר מה אכלת — בעברית טבעית, בלי טפסים</div>',
    unsafe_allow_html=True,
)

# ── Example chips (shown when chat is empty) ──────────────────────────────────
if st.session_state.show_examples and not st.session_state.chat_messages:
    st.markdown(
        '<div dir="rtl" style="font-size:0.72rem;color:#545e70;margin-bottom:8px;font-weight:600">'
        'לדוגמה:</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(EXAMPLES))
    for i, (col, ex) in enumerate(zip(cols, EXAMPLES)):
        if col.button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state.show_examples = False
            # Process the example
            st.session_state.chat_messages.append({"role": "user", "text": ex})
            _matched, _not_found, _meal_type = _process_text(ex)
            if _matched:
                st.session_state.pending_entries = _matched
                st.session_state.detected_meal_type = _meal_type
                _names = ", ".join(e["food_name"] for e in _matched)
                _reply = f"מצאתי: **{_names}**\n\nבדוק כמויות ואשר:"
                if _not_found:
                    _reply += f"\n\n⚠️ לא זיהיתי: *{', '.join(_not_found)}*"
            else:
                _reply = "לא הצלחתי לזהות מזון. נסה לנסח אחרת."
            st.session_state.chat_messages.append({"role": "assistant", "text": _reply})
            st.rerun()

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.chat_messages:
    if msg["role"] == "assistant":
        st.markdown(
            f'<div dir="rtl" style="display:flex;gap:10px;margin-bottom:10px;align-items:flex-start">'
            f'<div dir="rtl" style="width:30px;height:30px;border-radius:50%;background:#1a2540;'
            f'display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0;'
            f'border:1px solid #252d3d">🤖</div>'
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
            f'border-radius:4px 16px 16px 16px;padding:10px 14px;max-width:88%;'
            f'font-size:0.86rem;color:#f4f6fb;line-height:1.55;direction:rtl">'
            f'{msg["text"].replace(chr(10), "<br>")}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div dir="rtl" style="display:flex;gap:10px;margin-bottom:10px;align-items:flex-start;'
            f'flex-direction:row-reverse">'
            f'<div dir="rtl" style="width:30px;height:30px;border-radius:50%;background:#4f8ef7;'
            f'display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0">👤</div>'
            f'<div dir="rtl" style="background:#1a3a6b;border:1px solid #2d5096;'
            f'border-radius:16px 4px 16px 16px;padding:10px 14px;max-width:88%;'
            f'font-size:0.86rem;color:#e8f0ff;line-height:1.55;direction:rtl">'
            f'{msg["text"]}</div></div>',
            unsafe_allow_html=True,
        )

# ── Pending entries confirmation ──────────────────────────────────────────────
if st.session_state.pending_entries:
    total_cal = sum(e["calories"] for e in st.session_state.pending_entries)

    st.markdown(
        f'<div dir="rtl" style="background:#0d1f0d;border:1px solid #1a4d1a;border-radius:16px;'
        f'padding:14px 16px;margin:8px 0 4px">',
        unsafe_allow_html=True,
    )

    meal_type_sel = st.selectbox(
        "ארוחה",
        options=list(MEAL_HEB.keys()),
        format_func=lambda k: MEAL_HEB[k],
        index=list(MEAL_HEB.keys()).index(
            st.session_state.get("detected_meal_type", "lunch")
        ) if st.session_state.get("detected_meal_type", "lunch") in MEAL_HEB else 2,
        key="confirm_meal_type",
    )

    confirmed = []
    any_removed = False
    for i, entry in enumerate(st.session_state.pending_entries):
        c_name, c_gram, c_del = st.columns([4, 2, 1])
        c_name.markdown(
            f'<div dir="rtl" style="font-size:0.86rem;font-weight:700;color:#f4f6fb;padding-top:6px">'
            f'{entry["food_name"]}</div>'
            f'<div dir="rtl" style="font-size:0.68rem;color:#4ade80">'
            f'🔥 {entry["calories"]:.0f} קק״ל · {entry["protein"]:.0f}g חלבון</div>',
            unsafe_allow_html=True,
        )
        new_grams = c_gram.number_input(
            "גרם", min_value=1, max_value=2000,
            value=max(1, int(entry["grams"])),
            step=10, key=f"gram_{i}",
            label_visibility="collapsed",
        )
        entry["grams"] = float(new_grams)
        ratio = new_grams / 100.0
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

    # Total calories bar
    st.markdown(
        f'<div dir="rtl" style="margin:10px 0 4px;display:flex;justify-content:space-between;'
        f'align-items:center">'
        f'<div dir="rtl" style="font-size:0.72rem;color:#8892a4">סה״כ לאישור</div>'
        f'<div dir="rtl" style="font-size:1rem;font-weight:800;color:#4ade80">'
        f'{int(sum(e["calories"] for e in st.session_state.pending_entries))} קק״ל</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    if c1.button("✅ הוסף לרשומות", type="primary", use_container_width=True):
        today = date.today()
        added_cal = 0
        for entry in st.session_state.pending_entries:
            food_log_repo.add_entry(USER_ID, today, FoodLogEntry(
                food_id=entry["food_id"],
                food_name=entry["food_name"],
                grams=entry["grams"],
                calories=entry["calories"],
                protein=entry["protein"],
                carbs=entry["carbs"],
                fat=entry["fat"],
                meal_type=meal_type_sel,
                timestamp=datetime.now().isoformat(),
            ))
            added_cal += entry["calories"]
        n_added = len(st.session_state.pending_entries)
        st.session_state.pending_entries = []
        st.session_state.chat_messages.append({
            "role": "assistant",
            "text": f"✅ נרשמו {n_added} פריטים — **{int(added_cal)} קק״ל** ל{MEAL_HEB.get(meal_type_sel,'')}\n\nרוצה להוסיף עוד?",
        })
        st.rerun()

    if c2.button("ביטול", use_container_width=True):
        st.session_state.pending_entries = []
        st.session_state.chat_messages.append({
            "role": "assistant", "text": "בוטל. תגיד לי מחדש מה אכלת.",
        })
        st.rerun()

# ── Spacer before fixed input ─────────────────────────────────────────────────
st.markdown('<div style="height:120px"></div>', unsafe_allow_html=True)

# ── Fixed bottom input ────────────────────────────────────────────────────────
st.markdown("""
<style>
.chat-input-wrap {
    position: fixed; bottom: 64px; left: 0; right: 0; z-index: 9998;
    background: linear-gradient(to top, #0d0f14 80%, transparent);
    padding: 12px 16px 8px;
}
</style>
<div class="chat-input-wrap" id="chat-input-anchor"></div>
""", unsafe_allow_html=True)

with st.form("chat_form", clear_on_submit=True):
    col_in, col_btn = st.columns([5, 1])
    user_text = col_in.text_input(
        "",
        placeholder='מה אכלת? למשל: "שתי ביצים עם גבינה לבוקר"',
        label_visibility="collapsed",
        key="chat_input",
    )
    submitted = col_btn.form_submit_button("שלח ➤", use_container_width=True, type="primary")

if submitted and user_text.strip():
    st.session_state.show_examples = False
    st.session_state.chat_messages.append({"role": "user", "text": user_text})

    matched, not_found, detected_meal = _process_text(user_text)

    if matched:
        st.session_state.pending_entries = matched
        st.session_state.detected_meal_type = detected_meal
        names = ", ".join(e["food_name"] for e in matched)
        total = int(sum(e["calories"] for e in matched))
        reply = f"מצאתי **{len(matched)} פריטים** ({total} קק״ל):\n**{names}**\n\nבדוק כמויות ואשר:"
        if not_found:
            reply += f"\n\n⚠️ לא זיהיתי: *{', '.join(not_found)}* — ניתן להוסיף ידנית."
    else:
        reply = "לא הצלחתי לזהות מזון בטקסט. נסה לנסח אחרת, למשל:\n\"חזה עוף 150 גרם עם אורז לצהריים\""

    st.session_state.chat_messages.append({"role": "assistant", "text": reply})
    st.rerun()

bottom_nav("chat")
