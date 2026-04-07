#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף סריקת קבלה / רשימת סופר
"""
import sys, os, json, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from nutrition_app.user_manager import (
    get_all_users, add_inventory_item,
)

st.set_page_config(page_title="סריקת קבלה", page_icon="📷", layout="wide")

st.markdown("""
<style>
    .main .block-container { direction: rtl; }
    section[data-testid="stSidebar"] > div { direction: rtl; }
    h1,h2,h3 { text-align: right; }
</style>
""", unsafe_allow_html=True)

# ── טעינת קטלוג ──────────────────────────────────────────────────────────────
@st.cache_data
def load_catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "nutrition_app", "data", "foods_extended.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

CATALOG = load_catalog()

def match_to_catalog(names: list[str]) -> tuple[list[dict], list[str]]:
    """מתאים שמות מה-OCR למוצרים מהקטלוג."""
    matched, unmatched = [], []
    for name in names:
        name_lower = name.strip().lower()
        found = None
        for food in CATALOG:
            if (name_lower in food["name_he"].lower()
                    or name_lower in food["name_en"].lower()
                    or any(name_lower in a.lower() for a in food.get("aliases_he", []))
                    or any(name_lower in a.lower() for a in food.get("aliases_en", []))):
                found = food
                break
        if found:
            matched.append(found)
        else:
            unmatched.append(name)
    return matched, unmatched


def scan_with_claude(image_bytes: bytes, api_key: str) -> list[str]:
    """שולח תמונה ל-Claude Vision ומחזיר רשימת מוצרים."""
    import anthropic
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                },
                {
                    "type": "text",
                    "text": (
                        "זוהי תמונה של קבלת סופרמרקט או רשימת קניות. "
                        "זהה את כל שמות המוצרים הנמצאים בתמונה. "
                        "החזר רשימה של שמות מוצרים בעברית בלבד, כל מוצר בשורה נפרדת. "
                        "כתוב רק את שמות המוצרים — ללא מחירים, כמויות, קודים או טקסט נוסף."
                    ),
                },
            ],
        }],
    )
    text = msg.content[0].text.strip()
    return [line.strip("•-– ").strip() for line in text.splitlines() if line.strip()]


def parse_text_list(text: str) -> list[str]:
    """מפרסר רשימת טקסט ידנית."""
    return [line.strip("•-– ,").strip() for line in text.splitlines() if line.strip()]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👥 לקוח")
    users = get_all_users()

    if users:
        user_names = {u["user_id"]: u["name"] for u in users}
        selected_id = st.selectbox(
            "בחר לקוח",
            options=[u["user_id"] for u in users],
            format_func=lambda uid: user_names[uid],
        )
    else:
        selected_id = None
        st.warning("אין לקוחות. צור לקוח בדף המלאי.")

    st.divider()
    st.markdown("## 🔑 הגדרות")

    # קודם מנסה מהסביבה
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key and "claude_api_key" not in st.session_state:
        st.session_state["claude_api_key"] = env_key

    api_key = st.text_input(
        "Claude API Key",
        type="password",
        value=st.session_state.get("claude_api_key", ""),
        help="נדרש לסריקת תמונות. קבל מ-console.anthropic.com",
    )
    if api_key:
        st.session_state["claude_api_key"] = api_key

    if st.session_state.get("claude_api_key"):
        st.success("✅ מפתח מוכן")
    else:
        st.warning("הכנס API Key לסריקת תמונות")

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("# 📷 סריקת קבלה / רשימת סופר")
st.caption("צלם קבלה, העלה תמונה, או הדבק רשימה — המערכת תזהה את המוצרים ותוסיף למלאי")

if not selected_id:
    st.error("יש לבחור לקוח מהתפריט השמאלי.")
    st.stop()

user = next((u for u in users if u["user_id"] == selected_id), None)
st.info(f"מוסיף מוצרים למלאי של: **{user['name']}**")

st.divider()

# ── בחירת שיטת קלט ────────────────────────────────────────────────────────────
tab_image, tab_text = st.tabs(["📷 תמונת קבלה / צילום", "📝 הדבקת רשימה ידנית"])

detected_names: list[str] = []

with tab_image:
    st.markdown("#### העלה תמונת קבלה או רשימת סופר")

    uploaded = st.file_uploader(
        "בחר תמונה (JPG / PNG / WEBP)",
        type=["jpg", "jpeg", "png", "webp"],
        key="receipt_image",
    )

    if uploaded:
        st.image(uploaded, caption="התמונה שהועלתה", width=400)

        if not st.session_state.get("claude_api_key"):
            st.warning("הכנס Claude API Key בסרגל השמאלי כדי לסרוק.")
        else:
            if st.button("🔍 סרוק ותזהה מוצרים", type="primary", use_container_width=True):
                with st.spinner("מנתח תמונה עם Claude Vision..."):
                    try:
                        names = scan_with_claude(
                            uploaded.read(),
                            st.session_state["claude_api_key"],
                        )
                        st.session_state["scan_results"] = names
                        st.success(f"זוהו {len(names)} פריטים!")
                    except Exception as e:
                        st.error(f"שגיאה בסריקה: {e}")

    if "scan_results" in st.session_state:
        detected_names = st.session_state["scan_results"]

with tab_text:
    st.markdown("#### הדבק רשימת מוצרים")
    st.caption("כל מוצר בשורה נפרדת, למשל: חזה עוף, אורז, ביצים...")

    text_input = st.text_area(
        "רשימת מוצרים",
        height=200,
        placeholder="חזה עוף\nאורז לבן\nביצים\nבננות\n...",
        key="manual_list",
    )

    if st.button("🔍 זהה מוצרים מהרשימה", use_container_width=True):
        if text_input.strip():
            detected_names = parse_text_list(text_input)
            st.session_state["scan_results"] = detected_names
        else:
            st.warning("הכנס רשימה תחילה.")

    if "scan_results" in st.session_state and not detected_names:
        detected_names = st.session_state.get("scan_results", [])

# ── תוצאות ────────────────────────────────────────────────────────────────────
if detected_names:
    st.divider()
    st.markdown("### ✅ תוצאות זיהוי")

    matched, unmatched = match_to_catalog(detected_names)

    if matched:
        st.markdown(f"**{len(matched)} מוצרים זוהו בקטלוג:**")

        selected_foods = []
        for food in matched:
            col_check, col_name, col_qty = st.columns([1, 4, 2])
            checked = col_check.checkbox("בחר", value=True, key=f"chk_{food['food_id']}", label_visibility="collapsed")
            col_name.write(f"✅ {food['name_he']} ({food['name_en']})")
            qty = col_qty.number_input(
                "גרם",
                min_value=1, max_value=9999, value=300,
                key=f"qty_scan_{food['food_id']}",
                label_visibility="collapsed",
            )
            if checked:
                selected_foods.append((food, qty))

        st.write("")
        if st.button("➕ הוסף לקוח למלאי", type="primary", use_container_width=True):
            for food, qty in selected_foods:
                add_inventory_item(selected_id, food["food_id"], food["name_he"], float(qty))
            st.success(f"נוספו {len(selected_foods)} מוצרים למלאי של {user['name']}!")
            del st.session_state["scan_results"]
            st.balloons()

    if unmatched:
        st.divider()
        st.markdown(f"**{len(unmatched)} פריטים לא זוהו בקטלוג:**")
        for name in unmatched:
            col_n, col_q, col_b = st.columns([4, 2, 2])
            col_n.write(f"❓ {name}")
            custom_qty = col_q.number_input(
                "גרם", min_value=1, value=300,
                key=f"uq_{name}", label_visibility="collapsed",
            )
            if col_b.button("הוסף בכ״ז", key=f"ub_{name}"):
                custom_id = f"custom_{name.replace(' ', '_')}"
                add_inventory_item(selected_id, custom_id, name, float(custom_qty))
                st.success(f"נוסף: {name}")
                st.rerun()

st.divider()
st.page_link("pages/4_inventory.py", label="← חזור למלאי", use_container_width=False)
