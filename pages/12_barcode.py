#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12_barcode.py — סריקת ברקוד מוצר + חיפוש ב-Open Food Facts
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import date, datetime

from ui.components import inject_global_css, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry

st.set_page_config(
    page_title="BiteFit · סריקת ברקוד",
    page_icon="📲",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()
setup_persistent_auth()
USER_ID = require_auth()
food_log_repo = FoodLogRepository()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.barcode-hero {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    margin-bottom: 20px;
}
.barcode-hero h2 { color: #fff; margin: 0 0 6px 0; font-size: 1.4rem; }
.barcode-hero p  { color: #8892a4; margin: 0; font-size: 0.9rem; }

.product-card {
    background: #1e2535;
    border: 1px solid #2d3748;
    border-radius: 14px;
    padding: 20px;
    margin: 16px 0;
    direction: rtl;
}
.product-name { font-size: 1.3rem; font-weight: 700; color: #fff; margin-bottom: 4px; }
.product-brand { font-size: 0.9rem; color: #8892a4; margin-bottom: 16px; }
.macro-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }
.macro-chip {
    background: #2d3748;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.85rem;
    color: #e2e8f0;
    white-space: nowrap;
}
.macro-chip span { color: #63b3ed; font-weight: 700; }
.not-found-card {
    background: #2d1b1b;
    border: 1px solid #744141;
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    color: #fc8181;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="barcode-hero">
  <h2>📲 סריקת ברקוד</h2>
  <p>צלם את ברקוד המוצר — נמצא את הערכים התזונתיים אוטומטית</p>
</div>
""", unsafe_allow_html=True)

# ── Helper functions ──────────────────────────────────────────────────────────

def decode_barcode(image_bytes: bytes) -> str | None:
    """מפענח ברקוד מתמונה. מחזיר מחרוזת EAN או None."""
    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        barcodes = decode(img)
        if barcodes:
            return barcodes[0].data.decode("utf-8")
    except ImportError:
        st.warning("⚠️ ספריית pyzbar לא מותקנת — נסה להזין ברקוד ידנית.")
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def lookup_barcode(barcode: str) -> dict | None:
    """מחפש מוצר ב-Open Food Facts. מחזיר dict עם ערכים תזונתיים או None."""
    import requests

    # נסה קודם את ישראל, אחר-כך עולמי
    for base in [
        f"https://il.openfoodfacts.org/api/v0/product/{barcode}.json",
        f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json",
    ]:
        try:
            resp = requests.get(base, timeout=8,
                                headers={"User-Agent": "BiteFit-App/1.0"})
            if resp.status_code != 200:
                continue
            data = resp.json()
            if data.get("status") != 1:
                continue

            p = data["product"]
            n = p.get("nutriments", {})

            # שם בעברית → אנגלית → כינוי כללי
            name = (p.get("product_name_he")
                    or p.get("product_name_en")
                    or p.get("product_name")
                    or "מוצר לא ידוע")
            brand = p.get("brands", "")
            serving_g = float(p.get("serving_quantity") or 100)

            return {
                "barcode": barcode,
                "name": name,
                "brand": brand,
                "serving_g": serving_g,
                "per100": {
                    "calories": round(float(n.get("energy-kcal_100g") or n.get("energy_100g", 0) / 4.184 or 0), 1),
                    "protein":  round(float(n.get("proteins_100g", 0)), 1),
                    "carbs":    round(float(n.get("carbohydrates_100g", 0)), 1),
                    "fat":      round(float(n.get("fat_100g", 0)), 1),
                    "fiber":    round(float(n.get("fiber_100g", 0)), 1),
                },
                "image_url": p.get("image_front_small_url", ""),
            }
        except Exception:
            continue
    return None


def macros_for_grams(per100: dict, grams: float) -> dict:
    f = grams / 100
    return {k: round(v * f, 1) for k, v in per100.items()}


# ── UI ────────────────────────────────────────────────────────────────────────
tab_cam, tab_manual = st.tabs(["📷 מצלמה", "⌨️ הזנת ברקוד ידנית"])

barcode_str: str | None = None
product: dict | None = None

# ── Tab 1: Camera ─────────────────────────────────────────────────────────────
with tab_cam:
    st.markdown("##### צלם את הברקוד של המוצר")
    st.caption("טיפ: החזק את המוצר יציב, וודא תאורה טובה")

    img_file = st.camera_input("📸 צלם ברקוד", label_visibility="collapsed")

    if img_file:
        barcode_str = decode_barcode(img_file.getvalue())
        if barcode_str:
            st.success(f"✅ ברקוד זוהה: `{barcode_str}`")
        else:
            st.warning("לא הצלחתי לזהות ברקוד — נסה צילום קרוב יותר, או הזן ידנית.")

# ── Tab 2: Manual ─────────────────────────────────────────────────────────────
with tab_manual:
    st.markdown("##### הזן את מספר הברקוד (EAN-13)")
    col_in, col_btn = st.columns([4, 1])
    manual_barcode = col_in.text_input(
        "ברקוד", placeholder="לדוגמה: 7290000066423",
        label_visibility="collapsed", key="manual_bc"
    )
    go = col_btn.button("חפש", type="primary", use_container_width=True)
    if go and manual_barcode.strip():
        barcode_str = manual_barcode.strip()

# ── Lookup ────────────────────────────────────────────────────────────────────
if barcode_str:
    with st.spinner("מחפש מוצר..."):
        product = lookup_barcode(barcode_str)

# ── Product card ──────────────────────────────────────────────────────────────
if product:
    st.markdown("---")
    col_img, col_info = st.columns([1, 3])

    with col_img:
        if product["image_url"]:
            st.image(product["image_url"], width=120)
        else:
            st.markdown("### 🛒")

    with col_info:
        brand_line = f" · {product['brand']}" if product["brand"] else ""
        st.markdown(f"""
        <div>
          <div class="product-name">{product['name']}</div>
          <div class="product-brand">{brand_line}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### ערכים לכל 100 גרם")
    p = product["per100"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 קלוריות", f"{p['calories']} קק\"ל")
    c2.metric("💪 חלבון",   f"{p['protein']} גר'")
    c3.metric("🌾 פחמימות", f"{p['carbs']} גר'")
    c4.metric("🥑 שומן",    f"{p['fat']} גר'")

    # ── Add to log ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### הוסף לתיעוד")

    col_g, col_meal, col_date = st.columns(3)

    grams = col_g.number_input(
        "כמות (גרם)",
        min_value=1, max_value=2000,
        value=int(product["serving_g"]),
        step=5,
    )

    meal_options = {
        "breakfast":       "🌅 ארוחת בוקר",
        "morning_snack":   "☕ חטיף בוקר",
        "lunch":           "🍽️ צהריים",
        "afternoon_snack": "🍎 חטיף אחה\"צ",
        "dinner":          "🌙 ארוחת ערב",
        "evening_snack":   "🌜 חטיף לילה",
    }
    meal_type = col_meal.selectbox(
        "ארוחה",
        options=list(meal_options.keys()),
        format_func=lambda k: meal_options[k],
        index=list(meal_options.keys()).index("lunch"),
    )

    log_date = col_date.date_input("תאריך", value=date.today())

    # תצוגה מקדימה של ערכים לכמות שנבחרה
    m = macros_for_grams(p, grams)
    st.markdown(f"""
    <div class="product-card">
      <div style="color:#8892a4;font-size:0.85rem;margin-bottom:8px">ערכים ל-{grams}גר':</div>
      <div class="macro-row">
        <div class="macro-chip">🔥 <span>{m['calories']}</span> קק"ל</div>
        <div class="macro-chip">💪 <span>{m['protein']}גר'</span> חלבון</div>
        <div class="macro-chip">🌾 <span>{m['carbs']}גר'</span> פחמימות</div>
        <div class="macro-chip">🥑 <span>{m['fat']}גר'</span> שומן</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("➕ הוסף לתיעוד", type="primary", use_container_width=True):
        entry = FoodLogEntry(
            user_id=USER_ID,
            date=str(log_date),
            food_id=f"barcode_{barcode_str}",
            food_name=product["name"],
            grams=float(grams),
            calories=m["calories"],
            protein=m["protein"],
            carbs=m["carbs"],
            fat=m["fat"],
            meal_type=meal_type,
            timestamp=datetime.now().isoformat(),
            entry_id=f"{USER_ID}_{log_date}_{barcode_str}_{datetime.now().timestamp():.0f}",
        )
        food_log_repo.add_entry(entry)
        st.success(f"✅ {product['name']} ({grams}גר') נוסף לתיעוד!")
        st.balloons()

elif barcode_str and product is None:
    st.markdown(f"""
    <div class="not-found-card">
      <div style="font-size:2rem">😕</div>
      <div style="font-size:1.1rem;font-weight:700;margin:8px 0">מוצר לא נמצא</div>
      <div style="font-size:0.9rem">ברקוד {barcode_str} לא קיים ב-Open Food Facts</div>
      <div style="font-size:0.85rem;color:#fc8181;margin-top:8px">
        נסה להוסיף מהצ'אט ← כתוב "אכלתי {barcode_str}"
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Bottom nav ────────────────────────────────────────────────────────────────
bottom_nav(active="ברקוד")
