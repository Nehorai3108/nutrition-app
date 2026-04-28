#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10_chat_log.py — הזנת ארוחה שיחתית בעברית
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
import streamlit as st

from ui.components import inject_global_css, bottom_nav
from ui import theme as t

from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_chat_parser import parse_hebrew_meal
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry

st.set_page_config(page_title="הזנה שיחתית", page_icon="💬", layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

@st.cache_resource
def _get_catalog():
    return FoodCatalog(db_path=_DB_PATH)

catalog = _get_catalog()
food_log_repo = FoodLogRepository()
USER_ID = "ui_user_001"

MEAL_HEB = {
    "breakfast":       "🌅 ארוחת בוקר",
    "morning_snack":   "☕ חטיף בוקר",
    "lunch":           "🍽️ ארוחת צהריים",
    "afternoon_snack": "🍎 חטיף אחה״צ",
    "dinner":          "🌙 ארוחת ערב",
    "evening_snack":   "🌜 חטיף ערב",
}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;'
    f'padding:4px 2px 16px">'
    f'<div style="font-size:1.1rem;font-weight:800;color:#f4f6fb">💬 הזנה שיחתית</div>'
    f'<div style="font-size:0.75rem;color:#545e70">{date.today().strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Chat history ──────────────────────────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "text": "שלום! תגיד לי מה אכלת — בדיוק כמו שהיית מספר לחבר. למשל: \"אכלתי שתי ביצים, גבינה לבנה 150 גרם וכוס קפה לארוחת בוקר\""}
    ]
if "pending_entries" not in st.session_state:
    st.session_state.pending_entries = []

# Render messages
for msg in st.session_state.chat_messages:
    if msg["role"] == "assistant":
        st.markdown(
            f'<div style="display:flex;gap:10px;margin-bottom:12px;align-items:flex-start">'
            f'<div style="width:32px;height:32px;border-radius:50%;background:#1e2433;'
            f'display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0">🤖</div>'
            f'<div style="background:#1e2433;border:1px solid #252d3d;border-radius:4px 16px 16px 16px;'
            f'padding:10px 14px;max-width:85%;font-size:0.88rem;color:#f4f6fb;line-height:1.5">'
            f'{msg["text"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="display:flex;gap:10px;margin-bottom:12px;align-items:flex-start;'
            f'flex-direction:row-reverse">'
            f'<div style="width:32px;height:32px;border-radius:50%;background:#4f8ef7;'
            f'display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0">👤</div>'
            f'<div style="background:#4f8ef7;border-radius:16px 4px 16px 16px;'
            f'padding:10px 14px;max-width:85%;font-size:0.88rem;color:#fff;line-height:1.5">'
            f'{msg["text"]}</div></div>',
            unsafe_allow_html=True,
        )

# ── Pending entries confirmation ──────────────────────────────────────────────
if st.session_state.pending_entries:
    st.markdown(
        f'<div style="background:#161b26;border:1px solid #252d3d;border-radius:16px;'
        f'padding:14px 16px;margin-bottom:12px">',
        unsafe_allow_html=True,
    )
    st.markdown(f"**✅ זיהיתי את הפריטים הבאים — אשר להוספה:**")

    meal_type_sel = st.selectbox(
        "סוג ארוחה",
        options=list(MEAL_HEB.keys()),
        format_func=lambda k: MEAL_HEB[k],
        index=list(MEAL_HEB.keys()).index(
            st.session_state.get("detected_meal_type", "lunch")
        ),
        key="confirm_meal_type",
    )

    confirmed = []
    any_removed = False
    for i, entry in enumerate(st.session_state.pending_entries):
        col_info, col_gram, col_del = st.columns([4, 2, 1])
        col_info.markdown(f"**{entry['food_name']}**")
        new_grams = col_gram.number_input(
            "גרם", min_value=1, max_value=2000,
            value=int(entry["grams"]),
            step=10, key=f"gram_{i}",
            label_visibility="collapsed",
        )
        entry["grams"] = float(new_grams)
        # Recalculate nutrition on gram change
        ratio = new_grams / 100.0
        n = entry["nutrition_per_100g"]
        entry["calories"] = round(n["calories_kcal"] * ratio, 1)
        entry["protein"]  = round(n["protein_g"]  * ratio, 1)
        entry["carbs"]    = round(n["carbs_g"]    * ratio, 1)
        entry["fat"]      = round(n["fat_g"]      * ratio, 1)
        col_info.caption(f"🔥 {entry['calories']:.0f} קק״ל · {entry['protein']:.0f}g חלבון")
        if col_del.button("🗑️", key=f"del_pend_{i}"):
            any_removed = True
        else:
            confirmed.append(entry)

    if any_removed:
        st.session_state.pending_entries = confirmed
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    col_confirm, col_cancel = st.columns(2)
    if col_confirm.button("✅ הוסף לרשומות", type="primary", use_container_width=True):
        today = date.today()
        added = 0
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
            added += 1
        st.session_state.pending_entries = []
        total_cal = sum(e["calories"] for e in st.session_state.pending_entries) if st.session_state.pending_entries else sum(e["calories"] for e in confirmed)
        st.session_state.chat_messages.append({
            "role": "assistant",
            "text": f"✅ נרשמו {added} פריטים לרשומות שלך! רוצה להוסיף עוד?",
        })
        st.rerun()

    if col_cancel.button("ביטול", use_container_width=True):
        st.session_state.pending_entries = []
        st.session_state.chat_messages.append({
            "role": "assistant",
            "text": "בסדר, בוטל. תגיד לי מחדש מה אכלת.",
        })
        st.rerun()

# ── Input ─────────────────────────────────────────────────────────────────────
st.markdown('<div style="height:80px"></div>', unsafe_allow_html=True)

with st.form("chat_form", clear_on_submit=True):
    col_input, col_send = st.columns([5, 1])
    user_text = col_input.text_input(
        "מה אכלת?",
        placeholder='למשל: "שתי ביצים, גבינה 100 גרם וכוס קפה"',
        label_visibility="collapsed",
        key="chat_input",
    )
    submitted = col_send.form_submit_button("➤", use_container_width=True, type="primary")

if submitted and user_text.strip():
    st.session_state.chat_messages.append({"role": "user", "text": user_text})

    result = parse_hebrew_meal(user_text)

    matched = []
    not_found = []
    for item in result.items:
        foods = catalog.search_foods(item.food_query, limit=1)
        if not foods:
            # Try shorter query (first word)
            short = item.food_query.split()[0] if item.food_query.split() else item.food_query
            foods = catalog.search_foods(short, limit=1)
        if foods:
            food = foods[0]
            n = food.nutrition_per_100g
            grams = item.grams if item.grams else food.default_serving_g * item.quantity
            matched.append({
                "food_id": food.food_id,
                "food_name": food.name_he,
                "grams": round(grams, 0),
                "calories": round(n.calories_kcal * grams / 100, 1),
                "protein":  round(n.protein_g  * grams / 100, 1),
                "carbs":    round(n.carbs_g    * grams / 100, 1),
                "fat":      round(n.fat_g      * grams / 100, 1),
                "nutrition_per_100g": {
                    "calories_kcal": n.calories_kcal,
                    "protein_g": n.protein_g,
                    "carbs_g": n.carbs_g,
                    "fat_g": n.fat_g,
                },
            })
        else:
            not_found.append(item.food_query)

    if matched:
        st.session_state.pending_entries = matched
        st.session_state.detected_meal_type = result.meal_type
        names = ", ".join(e["food_name"] for e in matched)
        reply = f"מצאתי: **{names}**. בדוק את הכמויות למטה ואשר:"
        if not_found:
            reply += f"\n\nלא זיהיתי: *{', '.join(not_found)}* — תוכל לחפש אותם ידנית."
    else:
        reply = f"לא הצלחתי לזהות אוכל בטקסט הזה. נסה לנסח אחרת, למשל: \"אכלתי חזה עוף 150 גרם\"."

    st.session_state.chat_messages.append({"role": "assistant", "text": reply})
    st.rerun()

bottom_nav("food")
