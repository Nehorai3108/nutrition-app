#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12_barcode.py — סריקת ברקוד + מאגר קהילתי ישראלי
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

st.set_page_config(
    page_title="BiteFit · סריקת ברקוד",
    page_icon="📲",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()
setup_persistent_auth()
USER_ID       = require_auth()
food_log_repo = FoodLogRepository()
barcode_repo  = BarcodeRepository()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.barcode-hero {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 16px; padding: 24px; text-align: center; margin-bottom: 20px;
}
.barcode-hero h2 { color:#fff; margin:0 0 6px 0; font-size:1.4rem; }
.barcode-hero p  { color:#8892a4; margin:0; font-size:0.9rem; }

.product-card {
    background:#1e2535; border:1px solid #2d3748;
    border-radius:14px; padding:20px; margin:16px 0; direction:rtl;
}
.product-name  { font-size:1.3rem; font-weight:700; color:#fff; margin-bottom:4px; }
.product-brand { font-size:0.9rem; color:#8892a4; margin-bottom:16px; }
.macro-row     { display:flex; gap:12px; flex-wrap:wrap; margin-top:12px; }
.macro-chip {
    background:#2d3748; border-radius:20px; padding:6px 14px;
    font-size:0.85rem; color:#e2e8f0; white-space:nowrap;
}
.macro-chip span { color:#63b3ed; font-weight:700; }
.badge-community { background:#1a3a2a; color:#68d391; border:1px solid #2f855a;
    border-radius:20px; padding:3px 10px; font-size:0.75rem; display:inline-block; margin-bottom:8px; }
.badge-off  { background:#1a2a3a; color:#63b3ed; border:1px solid #2b6cb0;
    border-radius:20px; padding:3px 10px; font-size:0.75rem; display:inline-block; margin-bottom:8px; }
.not-found { background:#2d1b1b; border:1px solid #744141; border-radius:14px;
    padding:20px; text-align:center; }
.add-form { background:#1e2535; border:1px solid #2d3748; border-radius:14px; padding:20px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="barcode-hero">
  <h2>📲 סריקת ברקוד</h2>
  <p>צלם ברקוד · מחפש אוטומטית · אם לא נמצא — הוסף למאגר הקהילתי</p>
</div>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def decode_barcode(image_bytes: bytes) -> str | None:
    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        barcodes = decode(img)
        if barcodes:
            return barcodes[0].data.decode("utf-8")
    except ImportError:
        st.warning("ספריית pyzbar לא מותקנת — הזן ברקוד ידנית.")
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def lookup_off(barcode: str) -> dict | None:
    """Open Food Facts — עובד טוב למוצרים בינלאומיים."""
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
            cal = float(n.get("energy-kcal_100g") or n.get("energy_100g", 0) / 4.184 or 0)
            if cal == 0:
                continue
            return {
                "name_he":   p.get("product_name_he") or p.get("product_name_en") or p.get("product_name", ""),
                "name_en":   p.get("product_name_en") or "",
                "brand":     p.get("brands", ""),
                "image_url": p.get("image_front_small_url", ""),
                "serving_g": float(p.get("serving_quantity") or 100),
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


def macros_for_grams(per100: dict, grams: float) -> dict:
    return {k: round(v * grams / 100, 1) for k, v in per100.items()}


def show_product_and_log(product: dict, barcode: str, source_label: str):
    """מציג כרטיס מוצר + טופס הוספה לתיעוד."""
    badge_class = "badge-community" if source_label == "community" else "badge-off"
    badge_text  = "✅ מאגר קהילתי" if source_label == "community" else "🌍 Open Food Facts"

    col_img, col_info = st.columns([1, 3])
    with col_img:
        if product.get("image_url"):
            st.image(product["image_url"], width=110)
        else:
            st.markdown('<div style="font-size:3rem;text-align:center">🛒</div>', unsafe_allow_html=True)
    with col_info:
        brand_str = f" · {product['brand']}" if product.get("brand") else ""
        st.markdown(f"""
        <div>
          <span class="{badge_class}">{badge_text}</span>
          <div class="product-name">{product['name_he']}</div>
          <div class="product-brand">{brand_str}</div>
        </div>
        """, unsafe_allow_html=True)

    p = product["per100"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 קלוריות", f"{p['calories']}")
    c2.metric("💪 חלבון",   f"{p['protein']}g")
    c3.metric("🌾 פחמימות", f"{p['carbs']}g")
    c4.metric("🥑 שומן",    f"{p['fat']}g")

    st.markdown("---")
    st.markdown("#### הוסף לתיעוד")
    col_g, col_meal, col_date = st.columns(3)

    grams = col_g.number_input(
        "כמות (גרם)", min_value=1, max_value=2000,
        value=int(product.get("serving_g", 100)), step=5, key=f"grams_{barcode}"
    )
    meal_options = {
        "breakfast": "🌅 ארוחת בוקר", "morning_snack": "☕ חטיף בוקר",
        "lunch": "🍽️ צהריים", "afternoon_snack": "🍎 חטיף אחה\"צ",
        "dinner": "🌙 ארוחת ערב", "evening_snack": "🌜 חטיף לילה",
    }
    meal_type = col_meal.selectbox(
        "ארוחה", options=list(meal_options.keys()),
        format_func=lambda k: meal_options[k],
        index=list(meal_options.keys()).index("lunch"), key=f"meal_{barcode}"
    )
    log_date = col_date.date_input("תאריך", value=date.today(), key=f"date_{barcode}")

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

    if st.button("➕ הוסף לתיעוד", type="primary", use_container_width=True, key=f"log_{barcode}"):
        entry = FoodLogEntry(
            user_id=USER_ID,
            date=str(log_date),
            food_id=f"barcode_{barcode}",
            food_name=product["name_he"],
            grams=float(grams),
            calories=m["calories"],
            protein=m["protein"],
            carbs=m["carbs"],
            fat=m["fat"],
            meal_type=meal_type,
            timestamp=datetime.now().isoformat(),
            entry_id=f"{USER_ID}_{log_date}_{barcode}_{datetime.now().timestamp():.0f}",
        )
        food_log_repo.add_entry(entry)
        st.success(f"✅ {product['name_he']} ({grams}גר') נוסף!")
        st.balloons()


def show_add_form(barcode: str):
    """טופס הוספה ידנית למאגר הקהילתי."""
    st.markdown(f"""
    <div class="not-found">
      <div style="font-size:2rem">🔍</div>
      <div style="font-size:1.1rem;font-weight:700;color:#fc8181;margin:8px 0">
        ברקוד {barcode} לא נמצא
      </div>
      <div style="font-size:0.9rem;color:#fc8181">
        עזור לקהילה — הוסף את המוצר ויהיה זמין לכולם!
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### ➕ הוסף מוצר למאגר")

    with st.form(key=f"add_barcode_{barcode}"):
        col1, col2 = st.columns(2)
        name_he  = col1.text_input("שם המוצר בעברית *", placeholder="במבה אסם")
        name_en  = col2.text_input("שם באנגלית", placeholder="Bamba")
        brand    = col1.text_input("מותג", placeholder="אסם")
        serving  = col2.number_input("מנה רגילה (גרם)", min_value=1, max_value=1000, value=100)

        st.markdown("**ערכים תזונתיים ל-100 גרם:**")
        nc1, nc2, nc3, nc4, nc5 = st.columns(5)
        cal   = nc1.number_input("🔥 קלוריות", min_value=0.0, max_value=900.0, value=0.0, step=1.0)
        prot  = nc2.number_input("💪 חלבון",   min_value=0.0, max_value=100.0, value=0.0, step=0.1)
        carbs = nc3.number_input("🌾 פחמימות", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
        fat   = nc4.number_input("🥑 שומן",    min_value=0.0, max_value=100.0, value=0.0, step=0.1)
        fiber = nc5.number_input("🌿 סיבים",   min_value=0.0, max_value=100.0, value=0.0, step=0.1)

        submitted = st.form_submit_button("💾 שמור למאגר הקהילתי", type="primary", use_container_width=True)

    if submitted:
        if not name_he.strip():
            st.error("שם המוצר בעברית הוא שדה חובה.")
        elif cal == 0:
            st.error("הכנס קלוריות.")
        else:
            entry = BarcodeEntry(
                barcode=barcode,
                name_he=name_he.strip(),
                name_en=name_en.strip(),
                brand=brand.strip(),
                calories=cal,
                protein=prot,
                carbs=carbs,
                fat=fat,
                fiber=fiber,
                serving_g=float(serving),
                source="community",
                added_by=USER_ID,
            )
            ok = barcode_repo.save(entry)
            if ok:
                st.success(f"✅ {name_he} נשמר! כל המשתמשים יוכלו למצוא אותו מעכשיו.")
                # שמור ב-session כדי להציג מיד
                st.session_state[f"product_{barcode}"] = {
                    "name_he":   name_he.strip(),
                    "name_en":   name_en.strip(),
                    "brand":     brand.strip(),
                    "image_url": "",
                    "serving_g": float(serving),
                    "per100": {"calories": cal, "protein": prot, "carbs": carbs, "fat": fat, "fiber": fiber},
                    "source": "community",
                }
                st.rerun()
            else:
                st.error("שגיאה בשמירה — בדוק חיבור לרשת.")


# ── Main UI ───────────────────────────────────────────────────────────────────
tab_cam, tab_manual = st.tabs(["📷 מצלמה", "⌨️ ברקוד ידני"])

barcode_str: str | None = None

with tab_cam:
    st.markdown("##### צלם את הברקוד של המוצר")
    st.caption("טיפ: קרוב + תאורה טובה = זיהוי מהיר")
    img_file = st.camera_input("צלם", label_visibility="collapsed")
    if img_file:
        bc = decode_barcode(img_file.getvalue())
        if bc:
            st.success(f"✅ ברקוד זוהה: `{bc}`")
            barcode_str = bc
        else:
            st.warning("לא זוהה ברקוד — נסה צילום קרוב יותר או הזן ידנית.")

with tab_manual:
    st.markdown("##### הזן מספר ברקוד (EAN-13)")
    col_in, col_btn = st.columns([4, 1])
    manual_bc = col_in.text_input("ברקוד", placeholder="7290000066423",
                                   label_visibility="collapsed", key="manual_bc_input")
    if col_btn.button("חפש", type="primary", use_container_width=True):
        if manual_bc.strip():
            barcode_str = manual_bc.strip()

# ── Lookup logic ──────────────────────────────────────────────────────────────
if barcode_str:
    # קודם בדוק אם כבר נמצא ב-session (נוסף זה עתה)
    cached = st.session_state.get(f"product_{barcode_str}")
    if cached:
        st.markdown("---")
        show_product_and_log(cached, barcode_str, cached.get("source", "community"))
        st.stop()

    with st.spinner("מחפש מוצר..."):
        # 1️⃣ מאגר קהילתי (Supabase)
        community = barcode_repo.get(barcode_str)
        if community:
            product = {
                "name_he":   community.name_he,
                "name_en":   community.name_en,
                "brand":     community.brand,
                "image_url": community.image_url,
                "serving_g": community.serving_g,
                "per100": {
                    "calories": community.calories,
                    "protein":  community.protein,
                    "carbs":    community.carbs,
                    "fat":      community.fat,
                    "fiber":    community.fiber,
                },
                "source": "community",
            }
            st.markdown("---")
            show_product_and_log(product, barcode_str, "community")

        else:
            # 2️⃣ Open Food Facts
            off = lookup_off(barcode_str)
            if off:
                # שמור אוטומטית במאגר הקהילתי כדי שהפעם הבאה יהיה מהיר
                barcode_repo.save(BarcodeEntry(
                    barcode=barcode_str,
                    name_he=off["name_he"] or off["name_en"],
                    name_en=off["name_en"],
                    brand=off["brand"],
                    image_url=off["image_url"],
                    calories=off["per100"]["calories"],
                    protein=off["per100"]["protein"],
                    carbs=off["per100"]["carbs"],
                    fat=off["per100"]["fat"],
                    fiber=off["per100"]["fiber"],
                    serving_g=off["serving_g"],
                    source="off",
                    added_by="system",
                ))
                st.markdown("---")
                show_product_and_log(off, barcode_str, "off")

            else:
                # 3️⃣ לא נמצא בשום מקום — טופס קהילתי
                st.markdown("---")
                show_add_form(barcode_str)

# ── Bottom nav ────────────────────────────────────────────────────────────────
bottom_nav(active="barcode")
