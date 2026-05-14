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

# ── Scanner HTML — runs directly in page, not inside restricted iframe ────────
SCANNER_HTML = """
<div id="scan-wrap" style="position:relative;width:100%;max-width:480px;margin:0 auto;border-radius:14px;overflow:hidden;background:#000;">
  <video id="vid" autoplay muted playsinline
    style="width:100%;height:300px;object-fit:cover;display:block;"></video>

  <!-- מסגרת -->
  <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    width:68%;height:54%;border:2px solid rgba(79,142,247,0.9);border-radius:10px;pointer-events:none;">
    <div style="position:absolute;top:-3px;left:-3px;width:20px;height:20px;
      border:3px solid #4f8ef7;border-right:none;border-bottom:none;border-radius:5px 0 0 0;"></div>
    <div style="position:absolute;top:-3px;right:-3px;width:20px;height:20px;
      border:3px solid #4f8ef7;border-left:none;border-bottom:none;border-radius:0 5px 0 0;"></div>
    <div style="position:absolute;bottom:-3px;left:-3px;width:20px;height:20px;
      border:3px solid #4f8ef7;border-right:none;border-top:none;border-radius:0 0 0 5px;"></div>
    <div style="position:absolute;bottom:-3px;right:-3px;width:20px;height:20px;
      border:3px solid #4f8ef7;border-left:none;border-top:none;border-radius:0 0 5px 0;"></div>
  </div>

  <!-- קו סריקה -->
  <div id="scan-line" style="position:absolute;left:16%;width:68%;height:2px;
    background:linear-gradient(90deg,transparent,#4f8ef7,transparent);
    animation:sweep 2s ease-in-out infinite;top:22%;"></div>

  <!-- תוצאה -->
  <div id="scan-ok" style="display:none;position:absolute;inset:0;background:rgba(26,58,42,0.95);
    border-radius:14px;justify-content:center;align-items:center;flex-direction:column;gap:6px;">
    <div style="font-size:2.2rem;">✅</div>
    <div id="scan-val" style="font-size:1.15rem;font-weight:700;color:#68d391;direction:ltr;"></div>
    <div style="font-size:0.8rem;color:#a0aec0;">ברקוד זוהה — מחפש מוצר…</div>
  </div>

  <!-- שגיאה -->
  <div id="scan-err" style="display:none;position:absolute;inset:0;background:rgba(45,27,27,0.95);
    border-radius:14px;justify-content:center;align-items:center;flex-direction:column;gap:8px;padding:20px;text-align:center;">
    <div style="font-size:2rem;">📷</div>
    <div id="scan-err-txt" style="color:#fc8181;font-size:0.9rem;direction:rtl;"></div>
  </div>

  <div id="scan-hint" style="position:absolute;bottom:10px;left:0;right:0;text-align:center;
    color:rgba(255,255,255,0.7);font-size:12px;direction:rtl;">כוון את הברקוד למסגרת</div>
</div>

<!-- תיבת ברקוד לקריאה ע"י Streamlit -->
<input id="bc-out" type="text" value=""
  style="opacity:0;position:absolute;pointer-events:none;width:1px;height:1px;" />

<style>
@keyframes sweep { 0%{top:22%} 50%{top:76%} 100%{top:22%} }
</style>

<script src="https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js"
  onload="startScanner()" onerror="showErr('נכשל לטעון ספריית סריקה')">
</script>

<script>
var lastBarcode = null;

function showErr(msg) {
  var el = document.getElementById('scan-err');
  document.getElementById('scan-err-txt').textContent = msg;
  el.style.display = 'flex';
  document.getElementById('scan-hint').style.display = 'none';
}

function onBarcode(bc) {
  if (bc === lastBarcode) return;
  lastBarcode = bc;

  // הצג הצלחה
  document.getElementById('scan-val').textContent = bc;
  document.getElementById('scan-ok').style.display = 'flex';
  document.getElementById('scan-line').style.display = 'none';
  document.getElementById('scan-hint').style.display = 'none';

  // שמור בinput נסתר ושלח event לדף
  var inp = document.getElementById('bc-out');
  inp.value = bc;

  // שלח לparent frame
  try { window.parent.postMessage({type:'barcode', value: bc}, '*'); } catch(e){}
  // גם localStorage
  try { localStorage.setItem('bitefit_barcode', bc); } catch(e){}
}

function startScanner() {
  var constraints = {
    video: {
      facingMode: { ideal: 'environment' },
      width:  { ideal: 1280 },
      height: { ideal: 720 }
    }
  };

  navigator.mediaDevices.getUserMedia(constraints)
    .then(function(stream) {
      var video = document.getElementById('vid');
      video.srcObject = stream;
      video.play();

      var hints = new Map();
      hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
        ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8,
        ZXing.BarcodeFormat.CODE_128, ZXing.BarcodeFormat.UPC_A,
        ZXing.BarcodeFormat.UPC_E,
      ]);
      hints.set(ZXing.DecodeHintType.TRY_HARDER, true);

      var reader = new ZXing.BrowserMultiFormatReader(hints);

      function tick() {
        if (!video.paused && video.readyState >= 2) {
          try {
            reader.decodeFromVideoElement(video)
              .then(function(r){ if(r) onBarcode(r.getText()); })
              .catch(function(){});
          } catch(e) {}
        }
        setTimeout(tick, 300);
      }
      setTimeout(tick, 500);
    })
    .catch(function(err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        showErr('נדרשת הרשאת מצלמה — אפשר גישה בהגדרות הדפדפן');
      } else if (err.name === 'NotFoundError') {
        showErr('לא נמצאה מצלמה במכשיר');
      } else {
        showErr('שגיאה: ' + err.message);
      }
    });
}
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
    # Render scanner with full camera permissions (not in restricted component iframe)
    components.html(SCANNER_HTML, height=320, scrolling=False)

    # Manual input for when user has scanned (JS can't directly trigger Streamlit rerun)
    st.markdown('<p style="color:#8892a4;font-size:0.8rem;text-align:center;direction:rtl;">ברקוד זוהה? הדבק כאן:</p>',
                unsafe_allow_html=True)
    col_in, col_btn = st.columns([5,1])
    scanned_input = col_in.text_input("barcode_from_scan", label_visibility="collapsed",
                                       placeholder="הברקוד יופיע כאן אחרי סריקה",
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
