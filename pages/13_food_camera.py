#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
13_food_camera.py — זיהוי מזון מתמונה עם Gemini Vision
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import date, datetime
from PIL import Image
import io

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

@st.cache_resource
def _get_catalog():
    return FoodCatalog()

def _identify_with_gemini(image_bytes: bytes) -> list[str]:
    """שולח תמונה ל-Gemini REST API, מקבל רשימת שמות מזון באנגלית."""
    import requests, base64
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    if not api_key:
        st.error("GEMINI_API_KEY לא מוגדר ב-Secrets")
        return []
    try:
        # זיהוי סוג התמונה
        img      = Image.open(io.BytesIO(image_bytes))
        buf      = io.BytesIO()
        fmt      = img.format or "JPEG"
        img.save(buf, format=fmt)
        img_b64  = base64.b64encode(buf.getvalue()).decode()
        mime     = f"image/{fmt.lower()}"

        prompt_text = (
            "Look at this image and identify all food items visible. "
            "Return ONLY a JSON array of English food names, nothing else. "
            "Example: [\"cucumber\", \"tomato\", \"olive oil\"] "
            "If no food is visible, return []."
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {"inline_data": {"mime_type": mime, "data": img_b64}},
                ]
            }],
            "generationConfig": {"temperature": 0.1},
        }
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        # נסה מודלים בסדר עדיפות
        models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
        ]
        resp = None
        for model_name in models:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent"
            )
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            if resp.status_code != 404:
                break
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # נקה markdown
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        st.error(f"שגיאה בזיהוי: {e}")
        return []

def _search_db(name_en: str) -> list:
    """חיפוש במסד הנתונים המקומי לפי שם אנגלי."""
    catalog = _get_catalog()
    results = catalog.search_foods(name_en, limit=3)
    return results

# ── UI ───────────────────────────────────────────────────────────────────────

st.markdown(
    '<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb;'
    'padding:4px 2px 14px">📷 זיהוי מזון מתמונה</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div dir="rtl" style="font-size:0.82rem;color:#8892a4;margin-bottom:16px">'
    'צלם מזון — האפליקציה תזהה ותציג את הערכים מהמאגר שלנו</div>',
    unsafe_allow_html=True,
)

# ── צילום ────────────────────────────────────────────────────────────────────
img_file = st.camera_input("", label_visibility="collapsed")

if img_file:
    img_bytes = img_file.getvalue()

    with st.spinner("מזהה מזון..."):
        food_names = _identify_with_gemini(img_bytes)

    if not food_names:
        st.markdown(
            '<div dir="rtl" style="background:#2d1b1b;border:1px solid #744141;'
            'border-radius:14px;padding:16px;text-align:center;color:#f87171">'
            'לא זוהה מזון בתמונה. נסה צילום קרוב יותר.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div dir="rtl" style="font-size:0.78rem;color:#8892a4;margin:8px 0 4px">'
            f'זוהה: {", ".join(food_names)}</div>',
            unsafe_allow_html=True,
        )

        # חפש כל פריט ב-DB
        all_matches = []
        for name in food_names:
            hits = _search_db(name)
            for h in hits:
                if h not in all_matches:
                    all_matches.append(h)

        if not all_matches:
            st.markdown(
                '<div dir="rtl" style="background:#2d1b1b;border:1px solid #744141;'
                'border-radius:14px;padding:16px;text-align:center;color:#f87171">'
                'המזון זוהה אך לא נמצא במאגר. נסה חיפוש ידני בתפריט היומי.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div dir="rtl" style="font-size:0.85rem;font-weight:700;color:#f4f6fb;'
                'margin:12px 0 8px">בחר את המוצר הנכון:</div>',
                unsafe_allow_html=True,
            )

            for food in all_matches[:6]:
                n100 = food.nutrition_per_100g
                _fid = food.food_id
                _key = f"sel_{_fid}"

                # כרטיס מוצר
                st.markdown(
                    f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                    f'border-radius:14px;padding:12px 14px;margin-bottom:8px">'
                    f'<div style="font-size:0.9rem;font-weight:800;color:#f4f6fb">{food.name_he}</div>'
                    f'<div style="font-size:0.72rem;color:#545e70;margin-bottom:8px">{food.name_en}</div>'
                    f'<div style="display:flex;gap:12px;font-size:0.78rem">'
                    f'<span style="color:#f4f6fb;font-weight:700">{round(n100.calories_kcal)} קק"ל/100ג</span>'
                    f'<span style="color:#4f8ef7">{n100.protein_g}ג חלבון</span>'
                    f'<span style="color:#f59e0b">{n100.carbs_g}ג פחמ׳</span>'
                    f'<span style="color:#f472b6">{n100.fat_g}ג שומן</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

                if st.button(f"בחר — {food.name_he}", key=_key, use_container_width=True):
                    st.session_state["cam_selected"] = food
                    st.session_state["cam_grams"]    = 100

            # ── אם נבחר מוצר ────────────────────────────────────────────────
            if "cam_selected" in st.session_state:
                sel  = st.session_state["cam_selected"]
                n100 = sel.nutrition_per_100g

                st.markdown(
                    f'<div dir="rtl" style="background:#0d2240;border:1px solid #1e4080;'
                    f'border-radius:14px;padding:14px;margin:12px 0 8px">'
                    f'<div style="font-size:0.9rem;font-weight:800;color:#f4f6fb;margin-bottom:4px">'
                    f'✅ {sel.name_he}</div></div>',
                    unsafe_allow_html=True,
                )

                grams = st.number_input(
                    "כמות (גרמים)",
                    min_value=1, max_value=2000,
                    value=st.session_state.get("cam_grams", 100),
                    step=10, key="cam_grams_input",
                )
                st.session_state["cam_grams"] = grams

                meal_map = {
                    "breakfast":       "ארוחת בוקר",
                    "morning_snack":   "חטיף בוקר",
                    "lunch":           "ארוחת צהריים",
                    "afternoon_snack": "חטיף אחה״צ",
                    "dinner":          "ארוחת ערב",
                    "evening_snack":   "חטיף ערב",
                }
                meal = st.selectbox(
                    "ארוחה",
                    options=list(meal_map.keys()),
                    format_func=lambda k: meal_map[k],
                    key="cam_meal",
                )

                ratio = grams / 100.0
                pcal  = round(n100.calories_kcal * ratio)
                pprot = round(n100.protein_g     * ratio, 1)
                pcarb = round(n100.carbs_g       * ratio, 1)
                pfat  = round(n100.fat_g         * ratio, 1)

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
                        food_id=sel.food_id,
                        food_name=sel.name_he,
                        grams=float(grams),
                        calories=float(pcal),
                        protein=float(pprot),
                        carbs=float(pcarb),
                        fat=float(pfat),
                        meal_type=meal,
                        timestamp=datetime.now().isoformat(),
                    ))
                    st.success(f"✅ נוסף: {sel.name_he} · {pcal} קק\"ל")
                    del st.session_state["cam_selected"]
                    st.rerun()

bottom_nav("barcode")
