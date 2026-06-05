#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
13_food_camera.py — זיהוי מזון מתמונה עם Gemini Vision
"""
import sys, os, json, base64, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import date, datetime
from PIL import Image
import requests

from ui.components import inject_global_css, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog

st.set_page_config(page_title="BiteFit · זיהוי מזון", page_icon=None,
                   layout="wide", initial_sidebar_state="collapsed")
inject_global_css()
setup_persistent_auth()
USER_ID       = require_auth()
food_log_repo = FoodLogRepository()

st.markdown(
    "<style>[data-testid='stCameraInput']>label{display:none!important}</style>",
    unsafe_allow_html=True,
)

# ── מיפוי ידני: שמות אנגליים נפוצים שאולי חסרים ב-DB ────────────────────────
FOOD_ALIASES: dict[str, list[str]] = {
    "peach":        ["peach", "אפרסק", "nectarine"],
    "nectarine":    ["nectarine", "peach", "אפרסק"],
    "plum":         ["plum", "שזיף"],
    "cherry":       ["cherry", "דובדבן"],
    "grape":        ["grape", "ענב", "grapes"],
    "fig":          ["fig", "תאנה"],
    "pomegranate":  ["pomegranate", "רימון"],
    "kiwi":         ["kiwi", "קיווי"],
    "pineapple":    ["pineapple", "אננס"],
    "grapefruit":   ["grapefruit", "אשכולית"],
    "lemon":        ["lemon", "לימון"],
    "lime":         ["lime", "ליים"],
    "blueberry":    ["blueberry", "אוכמנית", "blueberries"],
    "raspberry":    ["raspberry", "פטל"],
    "blackberry":   ["blackberry", "פטל שחור"],
    "melon":        ["melon", "מלון", "cantaloupe"],
    "cantaloupe":   ["cantaloupe", "מלון"],
    "papaya":       ["papaya", "פפאיה"],
    "guava":        ["guava", "גויאבה"],
    "lychee":       ["lychee", "ליצ'י"],
    "persimmon":    ["persimmon", "אפרסמון"],
    "broccoli":     ["broccoli", "ברוקולי"],
    "cauliflower":  ["cauliflower", "כרובית"],
    "spinach":      ["spinach", "תרד"],
    "kale":         ["kale", "קייל"],
    "lettuce":      ["lettuce", "חסה"],
    "cabbage":      ["cabbage", "כרוב"],
    "eggplant":     ["eggplant", "חציל"],
    "zucchini":     ["zucchini", "קישוא"],
    "pumpkin":      ["pumpkin", "דלעת"],
    "sweet potato": ["sweet potato", "בטטה"],
    "potato":       ["potato", "תפוח אדמה"],
    "carrot":       ["carrot", "גזר"],
    "beetroot":     ["beetroot", "סלק", "beet"],
    "beet":         ["beet", "סלק", "beetroot"],
    "celery":       ["celery", "סלרי"],
    "onion":        ["onion", "בצל"],
    "garlic":       ["garlic", "שום"],
    "tomato":       ["tomato", "עגבנייה"],
    "cucumber":     ["cucumber", "מלפפון"],
    "pepper":       ["pepper", "פלפל", "bell pepper"],
    "bell pepper":  ["bell pepper", "פלפל"],
    "mushroom":     ["mushroom", "פטריות", "mushrooms"],
    "corn":         ["corn", "תירס"],
    "avocado":      ["avocado", "אבוקדו"],
    "asparagus":    ["asparagus", "אספרגוס"],
    "artichoke":    ["artichoke", "ארטישוק"],
    "leek":         ["leek", "כרישה"],
    "green onion":  ["green onion", "בצל ירוק", "scallion"],
    "radish":       ["radish", "צנון"],
    "turnip":       ["turnip", "לפת"],
    "kohlrabi":     ["kohlrabi", "קולרבי"],
    "fennel":       ["fennel", "שומר"],
}

@st.cache_resource
def _get_catalog():
    return FoodCatalog()

def _identify_with_gemini(image_bytes: bytes) -> list[str]:
    """שולח תמונה ל-Gemini REST API, מקבל רשימת שמות מזון באנגלית."""
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    if not api_key:
        st.error("GEMINI_API_KEY לא מוגדר ב-Secrets")
        return []
    try:
        img  = Image.open(io.BytesIO(image_bytes))
        buf  = io.BytesIO()
        fmt  = img.format or "JPEG"
        img.save(buf, format=fmt)
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        mime    = f"image/{fmt.lower()}"

        prompt_text = (
            "You are a food identification expert. Look carefully at this image.\n"
            "Identify ALL food items, fruits, vegetables, and ingredients visible.\n"
            "Be very specific — for example:\n"
            "- A green round fruit = 'apple' or 'green apple'\n"
            "- A yellow curved fruit = 'banana'\n"
            "- A fuzzy round fruit = 'peach' or 'nectarine'\n"
            "- A round red/orange fruit = 'orange' or 'tomato'\n"
            "Return ONLY a JSON array of English food names in lowercase, nothing else.\n"
            "Examples: [\"peach\"], [\"apple\", \"banana\"], [\"cucumber\", \"tomato\"]\n"
            "If absolutely no food is visible, return [].\n"
            "IMPORTANT: Always try to identify even if unsure — make your best guess."
        )
        payload = {
            "contents": [{"parts": [
                {"text": prompt_text},
                {"inline_data": {"mime_type": mime, "data": img_b64}},
            ]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200},
        }
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        models  = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
        resp    = None
        for model_name in models:
            url  = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code != 404:
                break
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        st.error(f"שגיאה בזיהוי: {e}")
        return []

def _search_food(name: str) -> list:
    """חיפוש ב-DB המקומי עם fallback לאליאסים."""
    catalog = _get_catalog()
    # חיפוש ישיר
    results = catalog.search_foods(name, limit=3)
    if results:
        return results
    # חפש עם aliases
    for alias in FOOD_ALIASES.get(name.lower(), []):
        results = catalog.search_foods(alias, limit=3)
        if results:
            return results
    return []

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb;'
    'padding:4px 2px 6px">📷 זיהוי מזון מתמונה</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div dir="rtl" style="font-size:0.82rem;color:#8892a4;margin-bottom:12px">'
    'צלם מזון — האפליקציה תזהה ותציג ערכים מהמאגר שלנו</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div dir="rtl" style="font-size:0.78rem;color:#8892a4;margin-bottom:6px">'
    '📱 במובייל: לחץ ← בחר "צלם תמונה" ← המצלמה האחורית תיפתח</div>',
    unsafe_allow_html=True,
)
img_file = st.file_uploader(
    "העלה תמונה או צלם",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed",
    key="food_img_upload",
)

if img_file:
    img_bytes = img_file.getvalue()
    st.image(img_bytes, width=300)

    with st.spinner("מזהה מזון..."):
        food_names = _identify_with_gemini(img_bytes)

    if not food_names:
        st.markdown(
            '<div dir="rtl" style="background:#2d1b1b;border:1px solid #744141;'
            'border-radius:14px;padding:16px;text-align:center;color:#f87171">'
            'לא זוהה מזון בתמונה. נסה צילום קרוב יותר עם תאורה טובה.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div dir="rtl" style="font-size:0.78rem;color:#4ade80;margin:6px 0 10px">'
            f'✅ זוהה: {", ".join(food_names)}</div>',
            unsafe_allow_html=True,
        )

        # חפש כל פריט ב-DB (ללא כפילויות)
        seen_ids = set()
        all_matches = []
        for name in food_names:
            for h in _search_food(name):
                if h.food_id not in seen_ids:
                    seen_ids.add(h.food_id)
                    all_matches.append(h)

        if not all_matches:
            st.markdown(
                '<div dir="rtl" style="background:#2d1b1b;border:1px solid #744141;'
                'border-radius:14px;padding:16px;text-align:center;color:#f87171">'
                'המזון זוהה אך לא נמצא במאגר. נסה לחפש ידנית בתפריט היומי.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div dir="rtl" style="font-size:0.85rem;font-weight:700;color:#f4f6fb;'
                'margin:4px 0 8px">בחר את המוצר הנכון:</div>',
                unsafe_allow_html=True,
            )

            for food in all_matches[:6]:
                n100 = food.nutrition_per_100g
                st.markdown(
                    f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                    f'border-radius:14px;padding:12px 14px;margin-bottom:6px">'
                    f'<div style="font-size:0.9rem;font-weight:800;color:#f4f6fb">{food.name_he}</div>'
                    f'<div style="font-size:0.72rem;color:#545e70;margin-bottom:6px">{food.name_en}</div>'
                    f'<div style="display:flex;gap:12px;font-size:0.78rem">'
                    f'<span style="color:#f4f6fb;font-weight:700">{round(n100.calories_kcal)} קק"ל/100ג</span>'
                    f'<span style="color:#4f8ef7">{n100.protein_g}ג חלבון</span>'
                    f'<span style="color:#f59e0b">{n100.carbs_g}ג פחמ׳</span>'
                    f'<span style="color:#f472b6">{n100.fat_g}ג שומן</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"בחר — {food.name_he}", key=f"sel_{food.food_id}",
                             use_container_width=True):
                    st.session_state["cam_selected"] = food
                    st.session_state["cam_grams"]    = 100

    # ── אם נבחר מוצר ──────────────────────────────────────────────────────────
    if "cam_selected" in st.session_state:
        sel  = st.session_state["cam_selected"]
        n100 = sel.nutrition_per_100g

        st.markdown(
            f'<div dir="rtl" style="background:#0d2240;border:1px solid #1e4080;'
            f'border-radius:14px;padding:14px;margin:10px 0 8px">'
            f'<div style="font-size:0.9rem;font-weight:800;color:#f4f6fb">✅ {sel.name_he}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        grams = st.number_input("כמות (גרמים)", min_value=1, max_value=2000,
                                value=st.session_state.get("cam_grams", 100),
                                step=10, key="cam_grams_input")
        st.session_state["cam_grams"] = grams

        meal_map = {
            "breakfast": "ארוחת בוקר", "morning_snack": "חטיף בוקר",
            "lunch": "ארוחת צהריים", "afternoon_snack": "חטיף אחה״צ",
            "dinner": "ארוחת ערב", "evening_snack": "חטיף ערב",
        }
        meal = st.selectbox("ארוחה", list(meal_map.keys()),
                            format_func=lambda k: meal_map[k], key="cam_meal")

        r     = grams / 100.0
        pcal  = round(n100.calories_kcal * r)
        pprot = round(n100.protein_g * r, 1)
        pcarb = round(n100.carbs_g   * r, 1)
        pfat  = round(n100.fat_g     * r, 1)

        st.markdown(
            f'<div style="background:#0d1117;border-radius:10px;padding:10px 14px;'
            f'display:flex;gap:16px;font-size:0.85rem;direction:rtl;margin:6px 0">'
            f'<span style="color:#f4f6fb;font-weight:800">{pcal} קק"ל</span>'
            f'<span style="color:#4f8ef7">{pprot}ג חלבון</span>'
            f'<span style="color:#f59e0b">{pcarb}ג פחמ׳</span>'
            f'<span style="color:#f472b6">{pfat}ג שומן</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("➕ הוסף ליומן", type="primary",
                     use_container_width=True, key="cam_add"):
            food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                food_id=sel.food_id, food_name=sel.name_he,
                grams=float(grams), calories=float(pcal),
                protein=float(pprot), carbs=float(pcarb), fat=float(pfat),
                meal_type=meal, timestamp=datetime.now().isoformat(),
            ))
            st.success(f"✅ נוסף: {sel.name_he} · {pcal} קק\"ל")
            del st.session_state["cam_selected"]
            st.rerun()

bottom_nav("barcode")
