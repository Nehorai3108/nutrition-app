#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף סריקת קבלה / רשימת סופר — OCR.space (חינמי, 500 סריקות/חודש, עברית מלאה)
"""
import sys, os, json, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from nutrition_app.user_manager import get_all_users, add_inventory_item

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu, icon_button,
)
from chatbot.sidebar_widget import render_chatbot_sidebar

st.set_page_config(page_title="BiteFit · סריקה", page_icon="📷", layout="wide", initial_sidebar_state="collapsed")

inject_global_css()

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
    seen_ids = set()
    for name in names:
        name_lower = name.strip().lower()
        if not name_lower:
            continue
        found = None
        for food in CATALOG:
            if (name_lower in food["name_he"].lower()
                    or food["name_he"].lower() in name_lower
                    or name_lower in food["name_en"].lower()
                    or food["name_en"].lower() in name_lower
                    or any(name_lower in a.lower() for a in food.get("aliases_he", []))
                    or any(name_lower in a.lower() for a in food.get("aliases_en", []))):
                found = food
                break
        if found and found["food_id"] not in seen_ids:
            seen_ids.add(found["food_id"])
            matched.append(found)
        elif not found:
            unmatched.append(name)
    return matched, unmatched


def scan_with_ocrspace(image_bytes: bytes, api_key: str, mime_type: str = "image/jpeg") -> list[str]:
    """שולח תמונה ל-OCR.space ומחזיר שורות טקסט — עברית + אנגלית."""
    import requests

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{mime_type};base64,{b64}"

    payload = {
        "base64Image": data_uri,
        "language": "heb",
        "isOverlayRequired": False,
        "OCREngine": 2,
        "scale": True,
    }

    resp = requests.post(
        "https://api.ocr.space/parse/image",
        data=payload,
        headers={"apikey": api_key},
        timeout=30,
    )

    if resp.status_code == 403:
        raise Exception(
            "מפתח API לא תקף (403). "
            "השתמש במפתח האישי שלך מ-ocr.space — ראה הוראות בסרגל השמאלי."
        )
    if resp.status_code != 200:
        raise Exception(f"שגיאת API {resp.status_code}: {resp.text[:200]}")

    result = resp.json()
    if result.get("IsErroredOnProcessing"):
        err = result.get("ErrorMessage", ["שגיאה לא ידועה"])
        raise Exception(f"OCR נכשל: {err[0] if isinstance(err, list) else err}")

    lines = []
    for page in result.get("ParsedResults", []):
        text = page.get("ParsedText", "")
        for line in text.splitlines():
            line = line.strip("•-– \t\r")
            if line and len(line) > 1:
                lines.append(line)
    return lines


def parse_text_list(text: str) -> list[str]:
    """מפרסר רשימת טקסט ידנית."""
    return [line.strip("•-– ,").strip() for line in text.splitlines() if line.strip()]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    section_header("לקוח", "user")
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
    section_header("מפתח OCR", "lock")

    env_key = os.environ.get("OCR_SPACE_KEY", "")
    if env_key and "ocr_space_key" not in st.session_state:
        st.session_state["ocr_space_key"] = env_key

    api_key_input = st.text_input(
        "הכנס מפתח API",
        type="password",
        value=st.session_state.get("ocr_space_key", ""),
        key="ocr_key_input",
    )
    if api_key_input:
        st.session_state["ocr_space_key"] = api_key_input

    if st.session_state.get("ocr_space_key"):
        st.success("✅ מפתח מוכן")
    else:
        st.markdown("""
        <div style="background:#1a2a1a;border-radius:8px;padding:12px;font-size:0.85em;direction:rtl;line-height:1.7">
        <b>🆓 קבלת מפתח חינמי (500 סריקות/חודש):</b><br><br>
        1. פתח: <b>ocr.space/ocrapi</b><br>
        2. גלול למטה לטופס <b>"Free OCR API"</b><br>
        3. הכנס אימייל ולחץ <b>Send</b><br>
        4. תקבל מפתח ישירות לאימייל<br>
        5. הדבק אותו כאן<br><br>
        ⚡ <b>לבדיקה מהירה</b> (3/שעה בלבד):<br>
        הכנס: <code>helloworld</code>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    render_chatbot_sidebar()

# ── Main ──────────────────────────────────────────────────────────────────────
nav_menu(active="סריקת קבלה")
page_header(
    "סריקת קבלה / רשימת סופר",
    icon_name="scan",
    subtitle="העלה תמונה של קבלה — המערכת תזהה מוצרים עבריים ותוסיף למלאי",
)

if not selected_id:
    st.error("יש לבחור לקוח מהתפריט השמאלי.")
    st.stop()

user = next((u for u in users if u["user_id"] == selected_id), None)
st.info(f"מוסיף מוצרים למלאי של: **{user['name']}**")
st.divider()

# ── טאבים ────────────────────────────────────────────────────────────────────
tab_image, tab_text = st.tabs(["📷 תמונת קבלה", "📝 הדבקת רשימה ידנית"])

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
        mime = "image/png" if uploaded.name.lower().endswith(".png") else "image/jpeg"

        ocr_key = st.session_state.get("ocr_space_key", "")

        if not ocr_key:
            st.warning("הכנס מפתח API בסרגל השמאלי — ראה הוראות לקבלת מפתח חינמי.")
        else:
            if icon_button("סרוק ותזהה מוצרים", "scan",
                           key="scan_image_btn", type="primary"):
                with st.spinner("מנתח תמונה בעברית..."):
                    try:
                        names = scan_with_ocrspace(uploaded.read(), ocr_key, mime_type=mime)
                        st.session_state["scan_results"] = names
                        st.success(f"זוהו {len(names)} שורות טקסט!")
                    except Exception as e:
                        st.error(f"שגיאה בסריקה: {e}")

    if "scan_results" in st.session_state:
        detected_names = st.session_state["scan_results"]

with tab_text:
    st.markdown("#### הדבק רשימת מוצרים")
    st.caption("כל מוצר בשורה נפרדת — עובד תמיד, ללא API")

    text_input = st.text_area(
        "רשימת מוצרים",
        height=200,
        placeholder="חזה עוף\nאורז לבן\nביצים\nבננות\n...",
        key="manual_list",
    )

    if icon_button("זהה מוצרים מהרשימה", "scan", key="parse_text_btn"):
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
            checked = col_check.checkbox("", value=True, key=f"chk_{food['food_id']}")
            col_name.write(f"✅ {food['name_he']} ({food['name_en']})")
            qty = col_qty.number_input(
                "גרם", min_value=1, max_value=9999, value=300,
                key=f"qty_scan_{food['food_id']}", label_visibility="collapsed",
            )
            if checked:
                selected_foods.append((food, qty))

        st.write("")
        if icon_button("הוסף למלאי", "add",
                       key="add_matched_btn", type="primary"):
            for food, qty in selected_foods:
                add_inventory_item(selected_id, food["food_id"], food["name_he"], float(qty))
            st.success(f"✅ נוספו {len(selected_foods)} מוצרים למלאי של {user['name']}!")
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
            with col_b:
                _add_unmatched = icon_button("הוסף בכ״ז", "add", key=f"ub_{name}")
            if _add_unmatched:
                custom_id = f"custom_{name.replace(' ', '_')}"
                add_inventory_item(selected_id, custom_id, name, float(custom_qty))
                st.success(f"נוסף: {name}")
                st.rerun()

st.divider()
st.page_link("pages/4_inventory.py", label="← חזור למלאי", use_container_width=False)
