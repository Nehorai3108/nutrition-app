"""Receipt / document scanner — upload a receipt image and add foods to inventory."""
import base64
import json
import os
import sys

import streamlit as st

# ── path fix ──────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from anthropic import Anthropic
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.models.food_item import FoodItem

from ui.components import (
    inject_global_css, page_header, nav_menu, icon_button,
)
from auth.login_ui import require_auth, logout_button
from chatbot.sidebar_widget import render_chatbot_sidebar

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="NutriSmart · סריקה", page_icon="🧾", layout="wide", initial_sidebar_state="collapsed")

inject_global_css()

USER_ID = require_auth()

with st.sidebar:
    st.markdown(
        f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">👤 {st.session_state.get("user_email", "")}</div>',
        unsafe_allow_html=True,
    )
    logout_button(key="_receipt_scanner_logout_btn")
    st.divider()
    render_chatbot_sidebar()

# ── catalog (cached) ──────────────────────────────────────────────────────────
_DB_PATH = os.path.join(_ROOT, "storage", "nutrition.db")

@st.cache_resource
def _get_catalog() -> FoodCatalog:
    return FoodCatalog(db_path=_DB_PATH)

catalog = _get_catalog()

# ── helpers ───────────────────────────────────────────────────────────────────

def _encode_image(data: bytes, mime: str) -> str:
    return base64.standard_b64encode(data).decode("utf-8")


def _scan_receipt(image_data: bytes, mime_type: str) -> list[dict]:
    """Call Claude Vision and return list of {name, quantity_g}."""
    client = Anthropic()
    b64 = _encode_image(image_data, mime_type)

    prompt = """אתה מומחה לניתוח קבלות סופרמרקט.
תפקידך: לחלץ את כל המוצרי מזון מהתמונה ולהחזיר JSON בלבד.

כללים:
1. החזר מערך JSON בלבד — ללא טקסט נוסף, ללא markdown.
2. כל פריט: {"name_he": "שם בעברית", "name_en": "name in english", "quantity_g": <גרם כמספר>}
3. המר יחידות לגרם: ק"ג → ×1000, ליטר → ×1000, יחידה בודדת → 150, 6 יחידות → 900
4. אם כמות לא ידועה — השתמש ב-200
5. כלול רק מוצרי מזון (לא ניקיון, לא טיפוח)

דוגמה:
[{"name_he":"חזה עוף","name_en":"chicken breast","quantity_g":500},{"name_he":"אורז","name_en":"rice","quantity_g":1000}]
"""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )

    raw = resp.content[0].text.strip()
    # strip markdown fences if model added them
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def _scan_pdf(pdf_data: bytes) -> list[dict]:
    """Call Claude with a PDF document."""
    client = Anthropic()
    b64 = base64.standard_b64encode(pdf_data).decode("utf-8")

    prompt = """אתה מומחה לניתוח קבלות סופרמרקט.
תפקידך: לחלץ את כל המוצרי מזון מהמסמך ולהחזיר JSON בלבד.

כללים:
1. החזר מערך JSON בלבד — ללא טקסט נוסף, ללא markdown.
2. כל פריט: {"name_he": "שם בעברית", "name_en": "name in english", "quantity_g": <גרם כמספר>}
3. המר יחידות לגרם: ק"ג → ×1000, ליטר → ×1000, יחידה בודדת → 150
4. אם כמות לא ידועה — השתמש ב-200
5. כלול רק מוצרי מזון
"""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )

    raw = resp.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def _find_best_match(name_he: str, name_en: str) -> list[tuple[FoodItem, float]]:
    """Return top-5 catalog matches sorted by score descending."""
    q_he = name_he.lower().strip()
    q_en = name_en.lower().strip()
    results: list[tuple[FoodItem, float]] = []

    for food in catalog.get_all_foods():
        score = 0.0
        f_he = food.name_he.lower()
        f_en = food.name_en.lower()

        # Exact match
        if q_he and (q_he == f_he or q_he in f_he or f_he in q_he):
            score = max(score, 0.95 if q_he == f_he else 0.8)
        if q_en and (q_en == f_en or q_en in f_en or f_en in q_en):
            score = max(score, 0.95 if q_en == f_en else 0.8)

        # Word-level overlap
        he_words = set(q_he.split())
        en_words = set(q_en.split())
        f_he_words = set(f_he.split())
        f_en_words = set(f_en.split())
        if he_words & f_he_words:
            overlap = len(he_words & f_he_words) / max(len(he_words | f_he_words), 1)
            score = max(score, overlap * 0.7)
        if en_words & f_en_words:
            overlap = len(en_words & f_en_words) / max(len(en_words | f_en_words), 1)
            score = max(score, overlap * 0.7)

        # Alias match
        for alias in (food.aliases_he or []) + (food.aliases_en or []):
            a = alias.lower()
            if q_he and (q_he in a or a in q_he):
                score = max(score, 0.6)
            if q_en and (q_en in a or a in q_en):
                score = max(score, 0.6)

        if score > 0:
            results.append((food, score))

    return sorted(results, key=lambda x: -x[1])[:5]


# ── session state init ────────────────────────────────────────────────────────
if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = []   # list of {name_he, name_en, quantity_g, matches, selected_food_id, confirmed_qty}
if "scanned_inventory" not in st.session_state:
    st.session_state["scanned_inventory"] = {}  # food_id -> quantity_g

# ── UI ────────────────────────────────────────────────────────────────────────
nav_menu(active="סריקת קבלה")
page_header(
    "סורק קבלה / מסמך",
    icon_name="scan",
    subtitle="העלה תמונה של קבלת סופרמרקט או רשימת קניות — המערכת תזהה את המוצרים ותוסיף אותם למלאי",
)

# ── upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "📎 בחר קובץ (תמונה או PDF)",
    type=["jpg", "jpeg", "png", "webp", "pdf"],
    help="תמונה של קבלה, רשימת קניות ידנית, או מסמך PDF",
)

if uploaded:
    mime_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "pdf": "application/pdf",
    }
    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    mime = mime_map.get(ext, "image/jpeg")

    col_img, col_btn = st.columns([3, 1])
    with col_img:
        if mime != "application/pdf":
            st.image(uploaded, caption="קובץ שהועלה", use_container_width=True)
        else:
            st.info(f"📄 PDF: {uploaded.name}")

    with col_btn:
        st.write("")
        st.write("")
        scan_btn = icon_button("סרוק מוצרים", "scan",
                               key="scan_receipt_btn", type="primary")

    if scan_btn:
        with st.spinner("מנתח את הקבלה עם Claude Vision..."):
            try:
                file_bytes = uploaded.read()
                if mime == "application/pdf":
                    raw_items = _scan_pdf(file_bytes)
                else:
                    raw_items = _scan_receipt(file_bytes, mime)

                # Match each item to catalog
                enriched = []
                for item in raw_items:
                    matches = _find_best_match(
                        item.get("name_he", ""),
                        item.get("name_en", ""),
                    )
                    enriched.append({
                        "name_he": item.get("name_he", ""),
                        "name_en": item.get("name_en", ""),
                        "quantity_g": float(item.get("quantity_g", 200)),
                        "matches": matches,
                        "selected_food_id": matches[0][0].food_id if matches else None,
                        "confirmed_qty": float(item.get("quantity_g", 200)),
                    })

                st.session_state["scan_results"] = enriched
                st.success(f"זוהו **{len(enriched)}** מוצרים!")
            except json.JSONDecodeError as e:
                st.error(f"שגיאה בפענוח תשובת Claude: {e}")
            except Exception as e:
                st.error(f"שגיאה בסריקה: {e}")

# ── results table ─────────────────────────────────────────────────────────────
results = st.session_state.get("scan_results", [])

if results:
    st.divider()
    st.markdown("## ✅ מוצרים שזוהו — אשר ועדכן")
    st.caption("בחר את המוצר המתאים מהקטלוג ועדכן כמות לפי הצורך.")

    confirmed_items: list[dict] = []

    for i, item in enumerate(results):
        with st.container(border=True):
            col_orig, col_match, col_qty, col_del = st.columns([2, 3, 1.5, 0.5])

            with col_orig:
                st.markdown(f"**{item['name_he']}**")
                st.caption(item["name_en"])

            with col_match:
                matches = item["matches"]
                if matches:
                    options = [f"{f.name_he} ({f.name_en})" for f, _ in matches]
                    ids = [f.food_id for f, _ in matches]
                    default_idx = 0
                    chosen_label = st.selectbox(
                        "התאמה בקטלוג",
                        options=options,
                        index=default_idx,
                        key=f"match_{i}",
                        label_visibility="collapsed",
                    )
                    chosen_idx = options.index(chosen_label)
                    selected_food_id = ids[chosen_idx]
                    selected_food = matches[chosen_idx][0]
                    score = matches[chosen_idx][1]
                    badge = "🟢" if score >= 0.8 else "🟡" if score >= 0.5 else "🔴"
                    st.caption(f"{badge} התאמה: {int(score * 100)}%")
                else:
                    st.warning("לא נמצאה התאמה בקטלוג")
                    selected_food_id = None
                    selected_food = None

            with col_qty:
                qty = st.number_input(
                    "גרם",
                    min_value=0,
                    max_value=10000,
                    value=int(item["confirmed_qty"]),
                    step=50,
                    key=f"qty_{i}",
                    label_visibility="collapsed",
                )

            with col_del:
                st.write("")
                remove = st.checkbox("❌", key=f"remove_{i}", value=False)

            if not remove and selected_food_id and qty > 0:
                confirmed_items.append({
                    "food_id": selected_food_id,
                    "name_he": selected_food.name_he if selected_food else item["name_he"],
                    "quantity_g": float(qty),
                })

    st.divider()

    col_summary, col_add = st.columns([3, 1])
    with col_summary:
        st.markdown(f"**{len(confirmed_items)} מוצרים** מסומנים להוספה למלאי")
        if confirmed_items:
            names = ", ".join(x["name_he"] for x in confirmed_items[:6])
            if len(confirmed_items) > 6:
                names += f" ועוד {len(confirmed_items)-6}..."
            st.caption(names)

    with col_add:
        add_btn = icon_button(
            "הוסף למלאי", "add",
            key="add_scanned_btn", type="primary",
            disabled=len(confirmed_items) == 0,
        )

    if add_btn and confirmed_items:
        inventory = st.session_state.get("scanned_inventory", {})
        for item in confirmed_items:
            fid = item["food_id"]
            inventory[fid] = inventory.get(fid, 0) + item["quantity_g"]
        st.session_state["scanned_inventory"] = inventory
        st.session_state["scan_results"] = []
        st.success(f"✅ {len(confirmed_items)} מוצרים נוספו למלאי!")
        st.balloons()

# ── current scanned inventory summary ─────────────────────────────────────────
inv = st.session_state.get("scanned_inventory", {})
if inv:
    st.divider()
    st.markdown("## 📦 מלאי שנסרק עד כה")
    all_foods = {f.food_id: f for f in catalog.get_all_foods()}
    rows = []
    for fid, qty in inv.items():
        food = all_foods.get(fid)
        rows.append({
            "מוצר": food.name_he if food else fid,
            "כמות (גרם)": int(qty),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    col_clear, col_go = st.columns([1, 2])
    with col_clear:
        if icon_button("נקה מלאי", "clear", key="clear_scanned_btn"):
            st.session_state["scanned_inventory"] = {}
            st.rerun()
    with col_go:
        st.page_link(
            "app_user.py",
            label="🥗 עבור לתכנון תפריט עם המלאי שנסרק ←",
            use_container_width=True,
        )
