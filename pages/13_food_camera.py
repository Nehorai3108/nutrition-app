#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
13_food_camera.py — זיהוי מזון מתמונה עם Gemini Vision
"""
import sys, os, json, base64, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import streamlit.components.v1 as components
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

# מצלמה אחורית — override getUserMedia דרך window.parent (same-origin iframe)
components.html("""
<script>
try {
  var p = window.parent;
  var orig = p.navigator.mediaDevices.getUserMedia.bind(p.navigator.mediaDevices);
  p.navigator.mediaDevices.getUserMedia = function(c) {
    if (c && c.video) {
      c.video = (typeof c.video === 'object')
        ? Object.assign({}, c.video, {facingMode:{ideal:'environment'}})
        : {facingMode:{ideal:'environment'}};
    }
    return orig(c);
  };
} catch(e) { console.log('rear camera override:', e); }
</script>
""", height=0)

# ── aliases: Gemini name → חיפוש ב-DB ────────────────────────────────────────
FOOD_ALIASES: dict[str, list[str]] = {
    # פרות
    "apple": ["apple","תפוח"], "green apple": ["apple","תפוח"],
    "banana": ["banana","בננה"], "orange": ["orange","תפוז"],
    "mango": ["mango","מנגו"], "watermelon": ["watermelon","אבטיח"],
    "strawberry": ["strawberry","תות"], "pear": ["pear","אגס"],
    "peach": ["peach","אפרסק"], "nectarine": ["peach","אפרסק"],
    "plum": ["plum","שזיף"], "cherry": ["cherry","דובדבן"],
    "grape": ["grape","ענב"], "grapes": ["grape","ענב"],
    "fig": ["fig","תאנה"], "pomegranate": ["pomegranate","רימון"],
    "kiwi": ["kiwi","קיווי"], "pineapple": ["pineapple","אננס"],
    "grapefruit": ["grapefruit","אשכולית"], "lemon": ["lemon","לימון"],
    "blueberry": ["blueberry","אוכמנית"], "blueberries": ["blueberry","אוכמנית"],
    "raspberry": ["raspberry","פטל"], "melon": ["melon","מלון"],
    "cantaloupe": ["melon","מלון"], "papaya": ["papaya","פפאיה"],
    "persimmon": ["persimmon","אפרסמון"], "lychee": ["lychee","ליצ׳י"],
    # ירקות
    "tomato": ["tomato","עגבנייה"], "cucumber": ["cucumber","מלפפון"],
    "carrot": ["carrot","גזר"], "onion": ["onion","בצל"],
    "garlic": ["garlic","שום"], "potato": ["potato","תפוח אדמה"],
    "sweet potato": ["sweet potato","בטטה"], "beet": ["beet","סלק"],
    "beetroot": ["beet","סלק"], "corn": ["corn","תירס"],
    "avocado": ["avocado","אבוקדו"], "mushroom": ["mushroom","פטריות"],
    "mushrooms": ["mushroom","פטריות"], "eggplant": ["eggplant","חציל"],
    "zucchini": ["zucchini","קישוא"], "pumpkin": ["pumpkin","דלעת"],
    "broccoli": ["broccoli","ברוקולי"], "cauliflower": ["cauliflower","כרובית"],
    "spinach": ["spinach","תרד"], "lettuce": ["lettuce","חסה"],
    "cabbage": ["cabbage","כרוב"], "pepper": ["pepper","פלפל"],
    "bell pepper": ["pepper","פלפל"], "celery": ["celery","סלרי"],
    "asparagus": ["asparagus","אספרגוס"], "leek": ["leek","כרישה"],
    "green onion": ["green onion","בצל ירוק"],
    # חלבונים
    "chicken": ["chicken","עוף","חזה עוף"],
    "chicken breast": ["chicken breast","חזה עוף"],
    "chicken thigh": ["chicken","עוף"],
    "beef": ["beef","בשר בקר"],
    "ground beef": ["ground beef","בשר טחון"],
    "steak": ["steak","סטייק"],
    "turkey": ["turkey","הודו"],
    "tuna": ["tuna","טונה"],
    "salmon": ["salmon","סלמון"],
    "egg": ["egg","ביצה"], "eggs": ["egg","ביצה"],
    "shrimp": ["shrimp","שרימפס"],
    "fish": ["fish","דג"],
    "tofu": ["tofu","טופו"],
    # פחמימות
    "rice": ["rice","אורז"],
    "white rice": ["rice","אורז"],
    "brown rice": ["brown rice","אורז מלא"],
    "pasta": ["pasta","פסטה"],
    "spaghetti": ["pasta","פסטה"],
    "bread": ["bread","לחם"],
    "pita": ["pita","פיתה"],
    "oats": ["oats","שיבולת שועל"],
    "oatmeal": ["oats","שיבולת שועל"],
    "quinoa": ["quinoa","קינואה"],
    "bulgur": ["bulgur","בורגול"],
    "couscous": ["couscous","קוסקוס"],
    "potato chips": ["potato","תפוח אדמה"],
    "corn": ["corn","תירס"],
    # מוצרי חלב
    "milk": ["milk","חלב"],
    "yogurt": ["yogurt","יוגורט"],
    "cheese": ["cheese","גבינה"],
    "cottage cheese": ["cottage cheese","קוטג׳"],
    "butter": ["butter","חמאה"],
    "cream": ["cream","שמנת"],
    # שמנים / ממרחים
    "olive oil": ["olive oil","שמן זית"],
    "hummus": ["hummus","חומוס"],
    "tahini": ["tahini","טחינה"],
    "peanut butter": ["peanut butter","חמאת בוטנים"],
    # קטניות
    "lentils": ["lentils","עדשים"],
    "chickpeas": ["chickpeas","חומוס"],
    "beans": ["beans","שעועית"],
    # אגוזים / זרעים
    "almonds": ["almonds","שקדים"],
    "walnuts": ["walnuts","אגוזי מלך"],
    "peanuts": ["peanuts","בוטנים"],
    "sunflower seeds": ["sunflower seeds","גרעיני חמנייה"],
    # מנות מוכנות
    "salad": ["salad","סלט"],
    "soup": ["soup","מרק"],
    "sandwich": ["bread","לחם"],
    "pizza": ["pizza","פיצה"],
    "shakshuka": ["egg","ביצה"],
    "schnitzel": ["chicken breast","שניצל"],
}

@st.cache_resource
def _get_catalog():
    return FoodCatalog()

def _identify_with_groq(image_bytes: bytes) -> list[dict]:
    """
    שולח תמונה ל-Groq Vision, מחזיר רשימת:
    [{"name": "grilled chicken breast", "grams": 150, "name_he": "חזה עוף על הגריל"}, ...]
    """
    api_key = st.secrets.get("groq_api_key", os.environ.get("GROQ_API_KEY", ""))
    if not api_key:
        st.error("groq_api_key לא מוגדר ב-Secrets")
        return []
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # שפר רזולוציה לזיהוי טוב יותר
        img = img.convert("RGB")
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        prompt_text = """You are an expert food recognition and nutrition AI.
Analyze this food image with maximum precision.

CRITICAL: You MUST provide nutrition values for EVERY food you identify — even if it's packaged, branded, or unusual.

For EACH food item visible, return:
- "name": exact English food name (specific: "canned tuna in oil", not just "tuna")
- "name_he": Hebrew name
- "grams": estimated weight in grams (realistic portion)
- "calories": estimated total calories for this portion
- "protein": estimated protein in grams
- "carbs": estimated carbohydrates in grams
- "fat": estimated fat in grams

Visual estimation rules:
- Packaged product = use standard serving size from the package type
- Canned tuna (100g can) = ~120 cal, 26g protein, 0g carbs, 3g fat
- Tuna salad with mayo = ~180 cal, 16g protein, 2g carbs, 12g fat
- Plate of food = estimate by visual proportion
- Whole fruit = 100-200g depending on size
- Restaurant portion = 150-250g protein, 100-200g carbs

ALWAYS return nutrition values. If unsure, use typical values for that food type.

Return ONLY a JSON array:
[{"name": "canned tuna in brine", "name_he": "טונה בציר", "grams": 100, "calories": 90, "protein": 20, "carbs": 0, "fat": 1}]
[{"name": "grilled chicken breast", "name_he": "חזה עוף על הגריל", "grams": 150, "calories": 165, "protein": 31, "carbs": 0, "fat": 4}]

If truly no food visible, return [].
Return ONLY the JSON array, no explanation."""

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        models = [
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ]
        resp = None
        for model in models:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]}],
                "temperature": 0.0,
                "max_tokens": 500,
            }
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                resp = r
                break
        if resp is None:
            st.warning("שירות הזיהוי עמוס — נסה שוב בעוד שנייה")
            return []
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
        result = []
        for item in parsed:
            if isinstance(item, dict) and "name" in item:
                result.append({
                    "name":     item.get("name", ""),
                    "name_he":  item.get("name_he", ""),
                    "grams":    int(item.get("grams", 100)),
                    "calories": float(item.get("calories", 0)),
                    "protein":  float(item.get("protein", 0)),
                    "carbs":    float(item.get("carbs", 0)),
                    "fat":      float(item.get("fat", 0)),
                })
            elif isinstance(item, str):
                result.append({"name": item, "name_he": "", "grams": 100,
                                "calories": 0, "protein": 0, "carbs": 0, "fat": 0})
        return result
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
st.markdown("""
<style>
[data-testid="stCameraInputButton"] {
    width: 72px !important;
    height: 72px !important;
    border-radius: 50% !important;
    background: white !important;
    border: 5px solid rgba(255,255,255,0.4) !important;
    box-shadow: 0 0 0 3px white !important;
    padding: 0 !important;
    font-size: 0 !important;
    color: transparent !important;
    cursor: pointer !important;
    display: block !important;
    margin: 8px auto !important;
}
[data-testid="stCameraInputButton"]:active {
    background: #d0d0d0 !important;
}
</style>
""", unsafe_allow_html=True)

img_file = st.camera_input("", label_visibility="collapsed")

if img_file:
    img_bytes = img_file.getvalue()

    with st.spinner("מזהה מזון..."):
        detected_items = _identify_with_groq(img_bytes)

    if not detected_items:
        st.markdown(
            '<div dir="rtl" style="background:#2d1b1b;border:1px solid #744141;'
            'border-radius:14px;padding:16px;text-align:center;color:#f87171">'
            'לא זוהה מזון בתמונה. נסה צילום קרוב יותר עם תאורה טובה.</div>',
            unsafe_allow_html=True,
        )
    else:
        # הצג מה זוהה
        detected_labels = ", ".join(
            item.get("name_he") or item.get("name", "") for item in detected_items
        )
        st.markdown(
            f'<div dir="rtl" style="font-size:0.82rem;color:#4ade80;margin:6px 0 12px;'
            f'font-weight:600">זוהה: {detected_labels}</div>',
            unsafe_allow_html=True,
        )

        # חפש כל פריט ב-DB
        seen_ids = set()
        all_matches = []  # list of (food_item, estimated_grams, ai_name_he)
        for item in detected_items:
            ai_grams   = item.get("grams", 100)
            ai_name_he = item.get("name_he", "")
            for h in _search_food(item["name"]):
                if h.food_id not in seen_ids:
                    seen_ids.add(h.food_id)
                    all_matches.append((h, ai_grams, ai_name_he))

        if not all_matches:
            # השתמש ישירות בנתוני ה-AI
            st.markdown(
                '<div dir="rtl" style="font-size:0.85rem;font-weight:700;color:#f4f6fb;'
                'margin:4px 0 8px">תוצאות זיהוי AI:</div>',
                unsafe_allow_html=True,
            )
            for item in detected_items:
                ai_name = item.get("name_he") or item.get("name", "")
                ai_g    = item.get("grams", 100)
                ai_cal  = item.get("calories", 0)
                ai_prot = item.get("protein", 0)
                ai_carb = item.get("carbs", 0)
                ai_fat  = item.get("fat", 0)
                st.markdown(
                    f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                    f'border-radius:14px;padding:12px 14px;margin-bottom:6px">'
                    f'<div style="font-size:0.9rem;font-weight:800;color:#f4f6fb">{ai_name}</div>'
                    f'<div style="font-size:0.72rem;color:#4ade80;margin-bottom:6px">~ {ai_g}ג (הערכת AI)</div>'
                    f'<div style="display:flex;gap:12px;font-size:0.82rem">'
                    f'<span style="color:#f4f6fb;font-weight:700">{round(ai_cal)} קק"ל</span>'
                    f'<span style="color:#4f8ef7">{ai_prot}ג חלבון</span>'
                    f'<span style="color:#f59e0b">{ai_carb}ג פחמ׳</span>'
                    f'<span style="color:#f472b6">{ai_fat}ג שומן</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                _ai_key = f"ai_{item['name'].replace(' ','_')}"
                if st.button(f"הוסף — {ai_name}", key=f"ai_sel_{_ai_key}",
                             use_container_width=True):
                    st.session_state["cam_selected_ai"] = item
                    st.session_state["cam_grams"] = ai_g
        else:
            st.markdown(
                '<div dir="rtl" style="font-size:0.85rem;font-weight:700;color:#f4f6fb;'
                'margin:4px 0 8px">בחר את המוצר הנכון:</div>',
                unsafe_allow_html=True,
            )

            for food, ai_grams, ai_name_he in all_matches[:6]:
                n100  = food.nutrition_per_100g
                ratio = ai_grams / 100.0
                est_cal  = round(n100.calories_kcal * ratio)
                est_prot = round(n100.protein_g * ratio, 1)
                est_carb = round(n100.carbs_g * ratio, 1)
                est_fat  = round(n100.fat_g * ratio, 1)
                display_name = food.name_he or ai_name_he
                st.markdown(
                    f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                    f'border-radius:14px;padding:12px 14px;margin-bottom:6px">'
                    f'<div style="font-size:0.9rem;font-weight:800;color:#f4f6fb">{display_name}</div>'
                    f'<div style="font-size:0.72rem;color:#4ade80;margin-bottom:6px">~ {ai_grams}ג (הערכת AI)</div>'
                    f'<div style="display:flex;gap:12px;font-size:0.82rem">'
                    f'<span style="color:#f4f6fb;font-weight:700">{est_cal} קק"ל</span>'
                    f'<span style="color:#4f8ef7">{est_prot}ג חלבון</span>'
                    f'<span style="color:#f59e0b">{est_carb}ג פחמ׳</span>'
                    f'<span style="color:#f472b6">{est_fat}ג שומן</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"בחר — {display_name}", key=f"sel_{food.food_id}",
                             use_container_width=True):
                    st.session_state["cam_selected"] = food
                    st.session_state["cam_grams"]    = ai_grams  # גרמים מה-AI

    # ── אם נבחר מוצר מ-AI ישירות ────────────────────────────────────────────
    if "cam_selected_ai" in st.session_state:
        ai_item = st.session_state["cam_selected_ai"]
        ai_name = ai_item.get("name_he") or ai_item.get("name", "")
        ai_g    = st.session_state.get("cam_grams", ai_item.get("grams", 100))
        ratio   = ai_g / (ai_item.get("grams", 100) or 100)

        st.markdown(
            f'<div dir="rtl" style="background:#0d2240;border:1px solid #1e4080;'
            f'border-radius:14px;padding:14px;margin:10px 0 8px">'
            f'<div style="font-size:0.9rem;font-weight:800;color:#f4f6fb">{ai_name}</div>'
            f'</div>', unsafe_allow_html=True,
        )
        grams_ai = st.number_input("כמות (גרמים)", min_value=1, max_value=2000,
                                   value=int(ai_g), step=10, key="cam_grams_ai")
        ratio2   = grams_ai / (ai_item.get("grams", 100) or 100)
        pcal  = round(ai_item.get("calories", 0) * ratio2)
        pprot = round(ai_item.get("protein", 0) * ratio2, 1)
        pcarb = round(ai_item.get("carbs", 0) * ratio2, 1)
        pfat  = round(ai_item.get("fat", 0) * ratio2, 1)

        meal_map = {"breakfast": "ארוחת בוקר", "morning_snack": "חטיף בוקר",
                    "lunch": "ארוחת צהריים", "afternoon_snack": "חטיף אחה״צ",
                    "dinner": "ארוחת ערב", "evening_snack": "חטיף ערב"}
        meal_ai = st.selectbox("ארוחה", list(meal_map.keys()),
                               format_func=lambda k: meal_map[k], key="cam_meal_ai")

        st.markdown(
            f'<div style="background:#0d1117;border-radius:10px;padding:10px 14px;'
            f'display:flex;gap:16px;font-size:0.85rem;direction:rtl;margin:6px 0">'
            f'<span style="color:#f4f6fb;font-weight:800">{pcal} קק"ל</span>'
            f'<span style="color:#4f8ef7">{pprot}ג חלבון</span>'
            f'<span style="color:#f59e0b">{pcarb}ג פחמ׳</span>'
            f'<span style="color:#f472b6">{pfat}ג שומן</span>'
            f'</div>', unsafe_allow_html=True,
        )
        if st.button("➕ הוסף ליומן", type="primary",
                     use_container_width=True, key="cam_add_ai"):
            food_log_repo.add_entry(USER_ID, date.today(), FoodLogEntry(
                food_id=f"ai_{ai_item['name'][:20]}",
                food_name=ai_name,
                grams=float(grams_ai), calories=float(pcal),
                protein=float(pprot), carbs=float(pcarb), fat=float(pfat),
                meal_type=meal_ai, timestamp=datetime.now().isoformat(),
            ))
            st.success(f"✅ נוסף: {ai_name} · {pcal} קק\"ל")
            del st.session_state["cam_selected_ai"]
            st.rerun()

    # ── אם נבחר מוצר מ-DB ────────────────────────────────────────────────────
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
