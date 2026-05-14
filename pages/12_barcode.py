#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12_barcode.py — סריקת ברקוד + מאגר קהילתי
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime

from ui.components import inject_global_css, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry
from nutrition_app.repositories.barcode_repository import BarcodeRepository, BarcodeEntry

st.set_page_config(page_title="BiteFit · ברקוד", page_icon="📲",
                   layout="wide", initial_sidebar_state="collapsed")
inject_global_css()
setup_persistent_auth()
USER_ID       = require_auth()
food_log_repo = FoodLogRepository()
barcode_repo  = BarcodeRepository()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.product-card { background:#1e2535; border:1px solid #2d3748; border-radius:14px; padding:20px; margin:12px 0; }
.product-name { font-size:1.25rem; font-weight:700; color:#fff; }
.product-brand{ font-size:0.85rem; color:#8892a4; margin-top:2px; }
.badge        { border-radius:20px; padding:3px 10px; font-size:0.72rem; display:inline-block; margin-bottom:10px; }
.badge-comm   { background:#1a3a2a; color:#68d391; border:1px solid #2f855a; }
.badge-off    { background:#1a2a3a; color:#63b3ed; border:1px solid #2b6cb0; }
.not-found    { background:#2d1b1b; border:1px solid #744141; border-radius:14px;
                padding:20px; text-align:center; direction:rtl; margin-top:12px; }
</style>
""", unsafe_allow_html=True)

# ── Scanner HTML — uses native file/camera input (works on iOS) ───────────────
SCANNER_HTML = """
<style>
body { margin:0; background:#0d0f14; font-family:sans-serif; direction:rtl; }

#btn-wrap {
  display:flex; flex-direction:column; align-items:center;
  justify-content:center; padding:20px 16px; gap:14px;
}

label#cam-label {
  display:flex; align-items:center; justify-content:center; gap:10px;
  background:#4f8ef7; color:#fff; font-size:1.1rem; font-weight:700;
  border-radius:14px; padding:18px 32px; cursor:pointer;
  width:100%; max-width:360px; box-sizing:border-box;
  box-shadow:0 4px 20px rgba(79,142,247,0.4);
  transition: background 0.15s;
}
label#cam-label:active { background:#3a7ee0; }

#cam-input { display:none; }

#preview-wrap {
  display:none; width:100%; max-width:360px;
  border-radius:14px; overflow:hidden; position:relative;
}
#preview { width:100%; display:block; border-radius:14px; }

#result {
  display:none; background:#1a3a2a; border:1px solid #2f855a;
  border-radius:12px; padding:16px; text-align:center;
  max-width:360px; width:100%;
}
#result .lbl { color:#a0aec0; font-size:0.8rem; margin-bottom:4px; }
#result .val { color:#68d391; font-size:1.2rem; font-weight:700; direction:ltr; }

#scanning {
  display:none; color:#8892a4; font-size:0.9rem;
  text-align:center; padding:8px;
}

#err {
  display:none; background:#2d1b1b; border:1px solid #744141;
  border-radius:12px; padding:14px; text-align:center;
  color:#fc8181; font-size:0.85rem; max-width:360px; width:100%;
}

#again-btn {
  display:none; background:#2d3748; color:#e2e8f0;
  border:none; border-radius:10px; padding:10px 24px;
  font-size:0.9rem; cursor:pointer; margin-top:4px;
}
</style>

<div id="btn-wrap">
  <label id="cam-label" for="cam-input">
    📷 צלם ברקוד
  </label>
  <input id="cam-input" type="file" accept="image/*" capture="environment">

  <div id="scanning">⏳ מפענח ברקוד…</div>

  <div id="preview-wrap">
    <img id="preview" src="" alt="">
  </div>

  <div id="result">
    <div class="lbl">ברקוד זוהה ✅</div>
    <div class="val" id="result-val"></div>
  </div>

  <div id="err" id="err-box">
    <div id="err-txt">לא זוהה ברקוד — נסה שוב, ודא שהברקוד ממולא ומוארת</div>
    <button id="again-btn" onclick="reset()">נסה שוב</button>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js"></script>
<script>
var input = document.getElementById('cam-input');

function reset() {
  document.getElementById('result').style.display = 'none';
  document.getElementById('err').style.display = 'none';
  document.getElementById('again-btn').style.display = 'none';
  document.getElementById('preview-wrap').style.display = 'none';
  document.getElementById('cam-label').style.display = 'flex';
  input.value = '';
}

function showBarcode(bc) {
  document.getElementById('result-val').textContent = bc;
  document.getElementById('result').style.display = 'block';
  document.getElementById('scanning').style.display = 'none';
  document.getElementById('cam-label').style.display = 'none';

  // שלח לparent
  try { window.parent.postMessage({type:'bitefit_barcode', value: bc}, '*'); } catch(e){}
  try { window.localStorage.setItem('bitefit_last_barcode', bc + '|' + Date.now()); } catch(e){}
}

input.addEventListener('change', function() {
  var file = input.files[0];
  if (!file) return;

  document.getElementById('scanning').style.display = 'block';
  document.getElementById('cam-label').style.display = 'none';
  document.getElementById('err').style.display = 'none';

  var url = URL.createObjectURL(file);

  // הצג תצוגה מקדימה
  var prev = document.getElementById('preview');
  prev.src = url;
  document.getElementById('preview-wrap').style.display = 'block';

  var img = new Image();
  img.onload = function() {
    var hints = new Map();
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
      ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8,
      ZXing.BarcodeFormat.CODE_128, ZXing.BarcodeFormat.UPC_A,
      ZXing.BarcodeFormat.UPC_E, ZXing.BarcodeFormat.QR_CODE,
    ]);
    hints.set(ZXing.DecodeHintType.TRY_HARDER, true);

    var reader = new ZXing.BrowserMultiFormatReader(hints);
    reader.decodeFromImageElement(img)
      .then(function(result) {
        showBarcode(result.getText());
      })
      .catch(function() {
        document.getElementById('scanning').style.display = 'none';
        document.getElementById('err').style.display = 'block';
        document.getElementById('again-btn').style.display = 'inline-block';
      });
    URL.revokeObjectURL(url);
  };
  img.src = url;
});
</script>
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
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
            return {
                "name_he":   p.get("product_name_he") or p.get("product_name_en") or p.get("product_name",""),
                "name_en":   p.get("product_name_en",""),
                "brand":     p.get("brands",""),
                "image_url": p.get("image_front_small_url",""),
                "serving_g": float(p.get("serving_quantity") or 100),
                "per100": {
                    "calories": round(cal,1),
                    "protein":  round(float(n.get("proteins_100g",0)),1),
                    "carbs":    round(float(n.get("carbohydrates_100g",0)),1),
                    "fat":      round(float(n.get("fat_100g",0)),1),
                    "fiber":    round(float(n.get("fiber_100g",0)),1),
                },
                "source": "off",
            }
        except Exception:
            continue
    return None


def macros(per100: dict, grams: float) -> dict:
    return {k: round(v * grams / 100, 1) for k, v in per100.items()}


def show_product(product: dict, barcode: str):
    source    = product.get("source", "community")
    badge_cls = "badge-comm" if source == "community" else "badge-off"
    badge_txt = "✅ מאגר קהילתי" if source == "community" else "🌍 Open Food Facts"

    col_img, col_info = st.columns([1, 4])
    with col_img:
        if product.get("image_url"):
            st.image(product["image_url"], width=90)
        else:
            st.markdown('<div style="font-size:2.5rem;text-align:center">🛒</div>',
                        unsafe_allow_html=True)
    with col_info:
        st.markdown(f"""
        <span class="badge {badge_cls}">{badge_txt}</span>
        <div class="product-name">{product['name_he']}</div>
        <div class="product-brand">{product.get('brand','')}</div>
        """, unsafe_allow_html=True)

    p = product["per100"]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🔥 קלוריות", p['calories'])
    c2.metric("💪 חלבון",   f"{p['protein']}g")
    c3.metric("🌾 פחמימות", f"{p['carbs']}g")
    c4.metric("🥑 שומן",    f"{p['fat']}g")

    st.markdown("---")
    cg, cm, cd = st.columns(3)
    grams    = cg.number_input("גרם", 1, 2000, int(product.get("serving_g",100)), 5)
    meal_map = {"breakfast":"🌅 בוקר","morning_snack":"☕ חטיף בוקר",
                "lunch":"🍽️ צהריים","afternoon_snack":"🍎 חטיף אחה\"צ",
                "dinner":"🌙 ערב","evening_snack":"🌜 לילה"}
    meal     = cm.selectbox("ארוחה", list(meal_map.keys()),
                            format_func=lambda k: meal_map[k], index=3)
    log_date = cd.date_input("תאריך", value=date.today())

    m = macros(p, grams)
    st.caption(f"🔥 {m['calories']} קק\"ל · 💪 {m['protein']}g · 🌾 {m['carbs']}g · 🥑 {m['fat']}g")

    if st.button("➕ הוסף לתיעוד", type="primary", use_container_width=True):
        food_log_repo.add_entry(FoodLogEntry(
            user_id=USER_ID, date=str(log_date),
            food_id=f"barcode_{barcode}", food_name=product["name_he"],
            grams=float(grams), calories=m["calories"],
            protein=m["protein"], carbs=m["carbs"], fat=m["fat"],
            meal_type=meal, timestamp=datetime.now().isoformat(),
            entry_id=f"{USER_ID}_{log_date}_{barcode}_{datetime.now().timestamp():.0f}",
        ))
        st.success(f"✅ {product['name_he']} נוסף!")
        st.balloons()


def show_add_form(barcode: str):
    st.markdown(f"""
    <div class="not-found">
      <div style="font-size:1.8rem">🔍</div>
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
        n1,n2,n3,n4 = st.columns(4)
        cal   = n1.number_input("🔥 קלוריות", 0.0, 900.0, 0.0, 1.0)
        prot  = n2.number_input("💪 חלבון g",  0.0, 100.0, 0.0, 0.1)
        carbs = n3.number_input("🌾 פחמימות g",0.0, 100.0, 0.0, 0.1)
        fat_v = n4.number_input("🥑 שומן g",   0.0, 100.0, 0.0, 0.1)
        ok = st.form_submit_button("💾 שמור למאגר", type="primary", use_container_width=True)

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
                st.success(f"✅ {name_he} נשמר!")
                st.session_state[f"prod_{barcode}"] = {
                    "name_he":name_he.strip(),"name_en":name_en.strip(),
                    "brand":brand.strip(),"image_url":"","serving_g":float(serving),
                    "per100":{"calories":cal,"protein":prot,"carbs":carbs,"fat":fat_v,"fiber":0},
                    "source":"community",
                }
                st.rerun()
            else:
                st.error("שגיאה בשמירה.")


# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("## 📲 סריקת ברקוד")

tab_scan, tab_manual = st.tabs(["📷 סריקה", "⌨️ הזנה ידנית"])

barcode_str: str | None = None

with tab_scan:
    components.html(SCANNER_HTML, height=280, scrolling=False)

    st.markdown('<p style="color:#8892a4;font-size:0.8rem;text-align:center;direction:rtl;margin-top:8px;">אחרי הצילום — הברקוד יופיע למעלה. העתק אותו לכאן:</p>',
                unsafe_allow_html=True)
    col_in, col_btn = st.columns([5,1])
    scanned_input = col_in.text_input("bc_scan", label_visibility="collapsed",
                                       placeholder="הדבק ברקוד כאן…",
                                       key="scan_result_input")
    if col_btn.button("✓", type="primary"):
        if scanned_input.strip():
            barcode_str = scanned_input.strip()

with tab_manual:
    c1, c2 = st.columns([4,1])
    manual  = c1.text_input("מספר ברקוד", placeholder="7290000066423",
                             label_visibility="collapsed")
    if c2.button("חפש", type="primary", use_container_width=True):
        if manual.strip():
            barcode_str = manual.strip()

# ── Lookup ────────────────────────────────────────────────────────────────────
if barcode_str:
    cached = st.session_state.get(f"prod_{barcode_str}")
    if cached:
        show_product(cached, barcode_str)
    else:
        with st.spinner("מחפש..."):
            comm = barcode_repo.get(barcode_str)
            if comm:
                show_product({
                    "name_he":comm.name_he,"name_en":comm.name_en,
                    "brand":comm.brand,"image_url":comm.image_url,
                    "serving_g":comm.serving_g,"source":"community",
                    "per100":{"calories":comm.calories,"protein":comm.protein,
                              "carbs":comm.carbs,"fat":comm.fat,"fiber":comm.fiber},
                }, barcode_str)
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
                    show_product(off, barcode_str)
                else:
                    show_add_form(barcode_str)

bottom_nav(active="barcode")
