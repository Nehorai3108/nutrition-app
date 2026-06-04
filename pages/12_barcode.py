#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12_barcode.py — סריקת ברקוד + מאגר קהילתי
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import date, datetime

from ui.components import inject_global_css, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry
from nutrition_app.repositories.barcode_repository import BarcodeRepository, BarcodeEntry
from nutrition_app.components.barcode_comp import barcode_scanner

st.set_page_config(page_title="BiteFit · ברקוד", page_icon="",
                   layout="wide", initial_sidebar_state="collapsed")
inject_global_css()
setup_persistent_auth()
USER_ID       = require_auth()
food_log_repo = FoodLogRepository()
barcode_repo  = BarcodeRepository()

st.markdown("""
<style>
.product-name { font-size:1.2rem; font-weight:700; color:#fff; }
.product-brand{ font-size:0.85rem; color:#8892a4; margin-top:2px; }
.badge        { border-radius:20px; padding:3px 10px; font-size:0.72rem;
                display:inline-block; margin-bottom:8px; }
.badge-comm   { background:#1a3a2a; color:#68d391; border:1px solid #2f855a; }
.badge-off    { background:#1a2a3a; color:#63b3ed; border:1px solid #2b6cb0; }
.not-found    { background:#2d1b1b; border:1px solid #744141; border-radius:14px;
                padding:20px; text-align:center; direction:rtl; margin-top:12px; }
/* hide default camera_input label */
[data-testid="stCameraInput"] > label { display:none !important; }
</style>
""", unsafe_allow_html=True)


#  barcode decode (server-side, OpenCV) 
def decode_barcode(img_bytes: bytes) -> str | None:
    """Decode barcode from image bytes using OpenCV BarcodeDetector.
    Tries multiple pre-processing strategies to maximise detection rate."""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        import io

        # Convert to numpy array via PIL (handles JPEG/PNG/WEBP)
        pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        arr = np.array(pil)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        detector = cv2.barcode.BarcodeDetector()

        # Strategy 1 — original image
        ok, vals, _, _ = detector.detectAndDecodeMulti(bgr)
        if ok:
            for v in vals:
                if v and v.strip():
                    return v.strip()

        # Strategy 2 — grayscale sharpened
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        sharp = cv2.filter2D(gray, -1,
                             np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]]))
        ok2, vals2, _, _ = detector.detectAndDecodeMulti(
            cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR))
        if ok2:
            for v in vals2:
                if v and v.strip():
                    return v.strip()

        # Strategy 3 — scaled up (helps with small/distant barcodes)
        h, w = bgr.shape[:2]
        if max(h, w) < 1200:
            scale = 1200 / max(h, w)
            big = cv2.resize(bgr, (int(w*scale), int(h*scale)),
                             interpolation=cv2.INTER_CUBIC)
            ok3, vals3, _, _ = detector.detectAndDecodeMulti(big)
            if ok3:
                for v in vals3:
                    if v and v.strip():
                        return v.strip()
    except Exception:
        pass
    return None


#  Open Food Facts lookup 
@st.cache_data(ttl=3600)
def lookup_off(barcode: str) -> dict | None:
    import requests
    for url in [
        f"https://il.openfoodfacts.org/api/v0/product/{barcode}.json",
        f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json",
    ]:
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "BiteFit/1.0"})
            d = r.json()
            if d.get("status") != 1:
                continue
            p = d["product"]
            n = p.get("nutriments", {})
            cal = float(n.get("energy-kcal_100g") or 0)
            if cal == 0:
                continue
            categories = (p.get("categories_tags") or p.get("categories", "")).lower()
            return {
                "name_he":    p.get("product_name_he") or p.get("product_name_en") or p.get("product_name", ""),
                "name_en":    p.get("product_name_en", ""),
                "brand":      p.get("brands", ""),
                "image_url":  p.get("image_front_small_url", ""),
                "serving_g":  float(p.get("serving_quantity") or 100),
                "categories": categories,
                "per100": {
                    "calories": round(cal, 1),
                    "protein":  round(float(n.get("proteins_100g", 0)), 1),
                    "carbs":    round(float(n.get("carbohydrates_100g", 0)), 1),
                    "fat":      round(float(n.get("fat_100g", 0)), 1),
                    "fiber":    round(float(n.get("fiber_100g", 0)), 1),
                },
                "source": "off",
            }
        except Exception:
            continue
    return None


def macros(per100: dict, grams: float) -> dict:
    return {k: round(v * grams / 100, 1) for k, v in per100.items()}


#  Detect if product is a drink 
_DRINK_KEYWORDS_HE = ["מיץ", "שתייה", "קולה", "בירה", "יין", "וודקה", "ויסקי",
                      "ספרייט", "פנטה", "מים", "תה", "קפה", "שייק", "סודה",
                      "אנרגיה", "איזוטוני", "לימונדה", "חלב", "מחלב", "פרימור"]
_DRINK_KEYWORDS_EN = ["beverage", "drink", "juice", "cola", "beer", "wine", "water",
                      "tea", "coffee", "milk", "shake", "soda", "energy drink",
                      "sport", "smoothie", "lemonade", "dairy drink"]

def _is_drink(product: dict) -> bool:
    name = (product.get("name_he") or product.get("name_en") or "").lower()
    cats = str(product.get("categories") or "").lower()
    for kw in _DRINK_KEYWORDS_HE:
        if kw in name: return True
    for kw in _DRINK_KEYWORDS_EN:
        if kw in name or kw in cats: return True
    if "beverage" in cats or "drinks" in cats or "en:beverages" in cats:
        return True
    return False


#  Serving options per product type 
def _serving_options(product: dict) -> list[tuple[str, int]]:
    """Returns list of (label, grams/ml) options."""
    serving = int(product.get("serving_g") or 100)
    if _is_drink(product):
        return [
            ("כוס קטנה  (150 מ\"ל)",  150),
            ("כוס          (200 מ\"ל)",  200),
            ("כוס גדולה  (250 מ\"ל)",  250),
            ("פחית            (330 מ\"ל)",  330),
            ("בקבוק קטן (500 מ\"ל)",  500),
            ("בקבוק גדול (1.5 ל׳)", 1500),
            (f"מנה מהאריזה ({serving} מ\"ל)", serving),
        ]
    else:
        return [
            (f"מנה מהאריזה ({serving}g)",   serving),
            ("100 גרם",                      100),
            ("מנה קטנה   (50g)",              50),
            ("מנה בינונית (150g)",           150),
            ("מנה גדולה  (200g)",            200),
        ]


#  Product card 
def show_product(product: dict, barcode: str):
    source    = product.get("source", "community")
    badge_cls = "badge-comm" if source == "community" else "badge-off"
    badge_txt = "מאגר קהילתי" if source == "community" else "Open Food Facts"
    drink     = _is_drink(product)

    #  Header: image + name 
    col_img, col_info = st.columns([1, 4])
    with col_img:
        if product.get("image_url"):
            st.image(product["image_url"], width=80)
        else:
            icon = "" if drink else ""
            st.markdown(f'<div style="font-size:2.2rem;text-align:center">{icon}</div>',
                        unsafe_allow_html=True)
    with col_info:
        st.markdown(f"""
        <span class="badge {badge_cls}">{badge_txt}</span>
        <div class="product-name">{product['name_he']}</div>
        <div class="product-brand">{product.get('brand','')}</div>
        """, unsafe_allow_html=True)

    #  Nutrition per 100g/ml 
    p = product["per100"]
    unit_lbl = "100 מ\"ל" if drink else "100 גרם"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"קלוריות / {unit_lbl}", f"{p['calories']}")
    c2.metric("חלבון",    f"{p['protein']}g")
    c3.metric("פחמימות",  f"{p['carbs']}g")
    c4.metric("שומן",     f"{p['fat']}g")

    st.markdown("---")

    #  Serving selector 
    options      = _serving_options(product)
    option_lbls  = [o[0] for o in options] + ["כמות אחרת (גרם/מ\"ל)"]
    sel_idx      = st.selectbox(
        "כמות שצרכת" if drink else "כמות שאכלת",
        range(len(option_lbls)),
        format_func=lambda i: option_lbls[i],
        key=f"srv_{barcode}",
    )

    if sel_idx == len(options):
        # Custom amount
        grams = st.number_input(
            "מ\"ל" if drink else "גרם",
            min_value=1, max_value=5000,
            value=int(product.get("serving_g") or 100),
            step=10, key=f"cust_{barcode}",
        )
    else:
        grams = options[sel_idx][1]

    #  Meal + date 
    cm, cd = st.columns(2)
    meal_map = {
        "breakfast":       "ארוחת בוקר",
        "morning_snack":   "חטיף בוקר",
        "lunch":           "ארוחת צהריים",
        "afternoon_snack": "חטיף אחה\"צ",
        "dinner":          "ארוחת ערב",
        "evening_snack":   "חטיף ערב",
    }
    meal     = cm.selectbox("ארוחה", list(meal_map.keys()),
                            format_func=lambda k: meal_map[k], index=3,
                            key=f"meal_{barcode}")
    log_date = cd.date_input("תאריך", value=date.today(), key=f"date_{barcode}")

    #  Calories summary 
    m = macros(p, grams)
    vol_unit = "מ\"ל" if drink else "גרם"
    st.markdown(
        f'<div dir="rtl" style="background:#0d1a0d;border:1px solid #1a4d1a;border-radius:12px;'
        f'padding:10px 16px;margin:8px 0;text-align:center">'
        f'<span style="font-size:1.3rem;font-weight:800;color:#4ade80">{m["calories"]:.0f} קק"ל</span>'
        f'<span style="color:#8892a4;font-size:0.8rem;margin-right:8px"> · {grams} {vol_unit}</span>'
        f'<span style="color:#8892a4;font-size:0.75rem"> · חלבון {m["protein"]}g · '
        f'פחמימות {m["carbs"]}g · שומן {m["fat"]}g</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("הוסף לתיעוד", type="primary", use_container_width=True,
                 key=f"log_{barcode}"):
        food_log_repo.add_entry(USER_ID, log_date, FoodLogEntry(
            food_id=f"barcode_{barcode}", food_name=product["name_he"],
            grams=float(grams), calories=m["calories"],
            protein=m["protein"], carbs=m["carbs"], fat=m["fat"],
            meal_type=meal, timestamp=datetime.now().isoformat(),
            entry_id=f"{USER_ID}_{log_date}_{barcode}_{datetime.now().timestamp():.0f}",
        ))
        st.success(f"{product['name_he']} נוסף — {m['calories']:.0f} קק\"ל")
        st.balloons()


def show_add_form(barcode: str):
    st.markdown(f"""
    <div class="not-found">
      <div style="font-size:1.8rem"></div>
      <div style="color:#fc8181;font-weight:700;margin:6px 0">ברקוד {barcode} לא נמצא</div>
      <div style="color:#fc8181;font-size:0.85rem">מלא את הפרטים — יישמר לכולם</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form(f"add_{barcode}"):
        c1, c2 = st.columns(2)
        name_he = c1.text_input("שם בעברית *", placeholder="במבה")
        brand   = c2.text_input("מותג", placeholder="אסם")
        serving = c1.number_input("מנה (גרם)", 1, 1000, 100)
        name_en = c2.text_input("שם באנגלית", placeholder="Bamba")
        st.markdown("**ל-100 גרם:**")
        n1, n2, n3, n4 = st.columns(4)
        cal   = n1.number_input(" קלוריות", 0.0, 900.0, 0.0, 1.0)
        prot  = n2.number_input(" חלבון g",  0.0, 100.0, 0.0, 0.1)
        carbs = n3.number_input(" פחמימות g", 0.0, 100.0, 0.0, 0.1)
        fat_v = n4.number_input(" שומן g",   0.0, 100.0, 0.0, 0.1)
        ok = st.form_submit_button(" שמור למאגר", type="primary", use_container_width=True)

    if ok:
        if not name_he.strip() or cal == 0:
            st.error("שם וקלוריות הם שדות חובה.")
        else:
            saved = barcode_repo.save(BarcodeEntry(
                barcode=barcode, name_he=name_he.strip(), name_en=name_en.strip(),
                brand=brand.strip(), calories=cal, protein=prot,
                carbs=carbs, fat=fat_v, serving_g=float(serving),
                source="community", added_by=USER_ID,
            ))
            if saved:
                st.success(f" {name_he} נשמר!")
                st.session_state[f"prod_{barcode}"] = {
                    "name_he": name_he.strip(), "name_en": name_en.strip(),
                    "brand": brand.strip(), "image_url": "", "serving_g": float(serving),
                    "per100": {"calories": cal, "protein": prot, "carbs": carbs,
                               "fat": fat_v, "fiber": 0},
                    "source": "community",
                }
                st.rerun()
            else:
                st.error("שגיאה בשמירה.")


#  Main 
st.markdown("## סריקת ברקוד")

tab_scan, tab_manual = st.tabs(["צלם ברקוד", "הזנה ידנית"])

barcode_str: str | None = None

with tab_scan:
    # barcode_scanner is a self-contained browser component:
    #  • " סרוק ברקוד" button  → file input (works over HTTP on mobile)
    #  • Strategy 1: BarcodeDetector native API  (Chrome Android, iOS 17.4+)
    #  • Strategy 2: ZXing via CDN (fallback)
    #  • " מצלמה חיה" link  → getUserMedia live scan (needs HTTPS / localhost)
    # The image never leaves the browser.  Only the barcode number is sent back.
    scanned = barcode_scanner(key="bc_main", height=150)

    if scanned == "":
        # User pressed "סרוק מוצר אחר" inside the component → clear state
        st.session_state.pop("_bc_last", None)
        st.rerun()
    elif scanned and scanned != st.session_state.get("_bc_last"):
        st.session_state["_bc_last"] = scanned

    if st.session_state.get("_bc_last"):
        barcode_str = st.session_state["_bc_last"]

with tab_manual:
    c1, c2 = st.columns([4, 1])
    manual = c1.text_input("מספר ברקוד", placeholder="7290000066423",
                           label_visibility="collapsed")
    if c2.button("חפש", type="primary", use_container_width=True):
        if manual.strip():
            barcode_str = manual.strip()

#  Lookup 
if barcode_str:
    cached = st.session_state.get(f"prod_{barcode_str}")
    if cached:
        show_product(cached, barcode_str)
    else:
        with st.spinner("מחפש מוצר…"):
            comm = barcode_repo.get(barcode_str)
            if comm:
                product_data = {
                    "name_he": comm.name_he, "name_en": comm.name_en,
                    "brand": comm.brand, "image_url": comm.image_url,
                    "serving_g": comm.serving_g, "source": "community",
                    "per100": {"calories": comm.calories, "protein": comm.protein,
                               "carbs": comm.carbs, "fat": comm.fat, "fiber": comm.fiber},
                }
                st.session_state[f"prod_{barcode_str}"] = product_data
                show_product(product_data, barcode_str)
            else:
                off = lookup_off(barcode_str)
                if off:
                    barcode_repo.save(BarcodeEntry(
                        barcode=barcode_str,
                        name_he=off["name_he"] or off["name_en"],
                        name_en=off["name_en"], brand=off["brand"],
                        image_url=off["image_url"],
                        calories=off["per100"]["calories"],
                        protein=off["per100"]["protein"],
                        carbs=off["per100"]["carbs"],
                        fat=off["per100"]["fat"],
                        fiber=off["per100"]["fiber"],
                        serving_g=off["serving_g"],
                        source="off", added_by="system",
                    ))
                    st.session_state[f"prod_{barcode_str}"] = off
                    show_product(off, barcode_str)
                else:
                    show_add_form(barcode_str)

bottom_nav(active="barcode")
