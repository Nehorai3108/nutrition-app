#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף מלאי אישי — ניהול מוצרים לכל לקוח
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import streamlit as st
from nutrition_app.user_manager import (
    get_all_users, create_user, delete_user,
    load_inventory, add_inventory_item, update_inventory_item, remove_inventory_item,
)

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu, icon_button,
)
from chatbot.sidebar_widget import render_chatbot_sidebar

st.set_page_config(page_title="מלאי אישי", page_icon="🛒", layout="wide", initial_sidebar_state="collapsed")

inject_global_css()

# ── טעינת קטלוג מזון ─────────────────────────────────────────────────────────
@st.cache_data
def load_catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "nutrition_app", "data", "foods_extended.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

CATALOG = load_catalog()
CATALOG_BY_ID = {f["food_id"]: f for f in CATALOG}

# ── Sidebar — בחירת משתמש ────────────────────────────────────────────────────
with st.sidebar:
    section_header("לקוחות", "user")

    users = get_all_users()

    if users:
        user_names = {u["user_id"]: u["name"] for u in users}
        selected_id = st.selectbox(
            "בחר לקוח",
            options=[u["user_id"] for u in users],
            format_func=lambda uid: user_names[uid],
            key="selected_user_id",
        )
    else:
        selected_id = None
        st.info("אין לקוחות עדיין. צור לקוח חדש.")

    st.divider()
    section_header("לקוח חדש", "add")
    new_name = st.text_input("שם הלקוח", key="new_user_name")
    if icon_button("צור לקוח", "add", key="create_user_btn"):
        if new_name.strip():
            u = create_user(new_name.strip())
            st.success(f"נוצר: {u['name']}")
            st.rerun()
        else:
            st.error("הכנס שם")

    if selected_id:
        st.divider()
        if icon_button("מחק לקוח זה", "delete",
                       key="delete_user_btn", type="secondary"):
            delete_user(selected_id)
            st.rerun()

    st.divider()
    render_chatbot_sidebar()

# ── Main ──────────────────────────────────────────────────────────────────────
nav_menu(active="מלאי")
page_header("מלאי אישי", icon_name="inventory",
            subtitle="ניהול מוצרים לכל לקוח")

if not selected_id:
    st.info("בחר לקוח מהתפריט השמאלי או צור לקוח חדש.")
    st.stop()

user = next((u for u in users if u["user_id"] == selected_id), None)
if not user:
    st.stop()

st.markdown(f"### 👤 {user['name']}")
st.divider()

items = load_inventory(selected_id)

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
                add_inventory_item(selected_id, chosen_id, food["name_he"], float(qty))
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
                add_inventory_item(selected_id, custom_id, custom_name.strip(), float(custom_qty))
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
                update_inventory_item(selected_id, fid, float(new_qty))
                st.success("עודכן!")
                st.rerun()

        with c4:
            if icon_button("מחק", "delete", key=f"del_{fid}",
                           type="secondary", help="הסר מהמלאי"):
                remove_inventory_item(selected_id, fid)
                st.rerun()

st.divider()
col_scan = st.columns(1)[0]
col_scan.page_link("pages/5_scanner.py", label="📷 סרוק קבלה / רשימת סופר", use_container_width=True)
