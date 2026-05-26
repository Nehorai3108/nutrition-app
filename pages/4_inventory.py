#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף מלאי אישי — ניהול מוצרים של המשתמש המחובר
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import streamlit as st
from nutrition_app.user_manager import (
    load_inventory, add_inventory_item, update_inventory_item, remove_inventory_item,
)

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu, icon_button,
)
from auth.login_ui import require_auth, logout_button
from chatbot.sidebar_widget import render_chatbot_sidebar

st.set_page_config(page_title="BiteFit · מלאי", page_icon="🛒", layout="wide", initial_sidebar_state="collapsed")

inject_global_css()

USER_ID = require_auth()

# ── טעינת קטלוג מזון ─────────────────────────────────────────────────────────
@st.cache_data
def load_catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "nutrition_app", "data", "foods_extended.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

CATALOG = load_catalog()
CATALOG_BY_ID = {f["food_id"]: f for f in CATALOG}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="font-size:0.75rem;color:#8892a4;padding:4px">👤 {st.session_state.get("user_email", "")}</div>',
        unsafe_allow_html=True,
    )
    logout_button(key="_inv_logout_btn")
    st.divider()
    render_chatbot_sidebar()

# ── Main ──────────────────────────────────────────────────────────────────────
nav_menu(active="מלאי")
page_header("המלאי שלי", icon_name="inventory",
            subtitle="ניהול המוצרים בבית — נשמר בענן")

items = load_inventory(USER_ID)

# ── הוספת מוצר ──────────────────────────────────────────────────────────────
with st.expander("➕ הוסף מוצר ידנית", expanded=False):
    col_search, col_qty, col_btn = st.columns([3, 1, 1])

    with col_search:
        search_q = st.text_input("חפש מוצר", key="inv_search", placeholder="עוף, אורז, ביצה...")

    filtered = []
    if search_q:
        q = search_q.strip().lower()
        filtered = [
            f for f in CATALOG
            if q in f["name_he"].lower()
            or q in f["name_en"].lower()
            or any(q in a.lower() for a in f.get("aliases_he", []))
        ]

    if filtered:
        with col_search:
            chosen_id = st.selectbox(
                "תוצאות",
                options=[f["food_id"] for f in filtered],
                format_func=lambda fid: CATALOG_BY_ID[fid]["name_he"],
                key="inv_chosen",
            )
        with col_qty:
            qty = st.number_input("כמות (גרם)", min_value=1, max_value=9999, value=100, key="inv_qty")
        with col_btn:
            st.write("")
            st.write("")
            if icon_button("הוסף", "add", key="inv_add_btn", type="primary"):
                food = CATALOG_BY_ID[chosen_id]
                add_inventory_item(USER_ID, chosen_id, food["name_he"], float(qty))
                st.success(f"נוסף: {food['name_he']} — {qty}ג")
                st.rerun()
    elif search_q:
        st.warning("לא נמצאו תוצאות. נסה מילה אחרת.")

    # הוספה מותאמת (מחוץ לקטלוג)
    with st.expander("➕ מוצר שאינו ברשימה"):
        c1, c2, c3 = st.columns([3, 1, 1])
        custom_name = c1.text_input("שם המוצר", key="custom_name")
        custom_qty = c2.number_input("כמות (גרם)", min_value=1, value=100, key="custom_qty")
        c3.write("")
        c3.write("")
        with c3:
            _add_custom = icon_button("הוסף", "add", key="add_custom")
        if _add_custom:
            if custom_name.strip():
                custom_id = f"custom_{custom_name.strip().replace(' ', '_')}"
                add_inventory_item(USER_ID, custom_id, custom_name.strip(), float(custom_qty))
                st.success(f"נוסף: {custom_name}")
                st.rerun()

st.divider()

# ── רשימת מלאי ───────────────────────────────────────────────────────────────
if not items:
    st.info("המלאי ריק. הוסף מוצרים למעלה או סרוק קבלה.")
else:
    st.markdown(f"**{len(items)} פריטים במלאי**")

    # כותרת
    h1, h2, h3, h4 = st.columns([4, 2, 2, 1])
    h1.markdown("**מוצר**")
    h2.markdown("**כמות (גרם)**")
    h3.markdown("**עדכון**")
    h4.markdown("**מחיקה**")

    for item in sorted(items, key=lambda x: x["name_he"]):
        fid = item["food_id"]
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])

        food_info = CATALOG_BY_ID.get(fid)
        category_icon = {
            "protein": "🥩", "carbohydrate": "🍞", "vegetable": "🥦",
            "fruit": "🍎", "dairy": "🧀", "fat_oil": "🫒",
            "snack": "🥜", "condiment": "🫙",
        }.get(food_info["category"] if food_info else "", "📦")

        c1.write(f"{category_icon} {item['name_he']}")

        new_qty = c2.number_input(
            "כמות", min_value=0, max_value=9999,
            value=int(item["quantity_g"]),
            key=f"qty_{fid}",
            label_visibility="collapsed",
        )

        with c3:
            if icon_button("שמור", "save", key=f"save_{fid}",
                           help="עדכן כמות"):
                update_inventory_item(USER_ID, fid, float(new_qty))
                st.success("עודכן!")
                st.rerun()

        with c4:
            if icon_button("מחק", "delete", key=f"del_{fid}",
                           type="secondary", help="הסר מהמלאי"):
                remove_inventory_item(USER_ID, fid)
                st.rerun()

st.divider()
col_scan = st.columns(1)[0]
col_scan.page_link("pages/5_scanner.py", label="📷 סרוק קבלה / רשימת סופר", use_container_width=True)
