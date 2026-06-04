#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, subprocess, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.auth import require_admin, admin_logout_button
from ui.components import inject_global_css

st.set_page_config(page_title="תמונות מתכונים", layout="wide")
inject_global_css()
require_admin(page_title="תמונות מתכונים", icon_name="images")
admin_logout_button()

_ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RECIPES_FILE = os.path.join(_ROOT, "storage_agents", "recipes", "recipes.json")
_IMAGES_FILE  = os.path.join(_ROOT, "data", "recipe_images.json")

def _load_recipes():
    try: return json.load(open(_RECIPES_FILE, encoding="utf-8"))
    except: return []

def _load_images():
    try: return json.load(open(_IMAGES_FILE, encoding="utf-8"))
    except: return {}

def _save_and_push(recipe_id: str, url: str):
    imgs = _load_images()
    imgs[recipe_id] = url
    with open(_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(imgs, f, ensure_ascii=False, indent=2)
    try:
        subprocess.run(["git", "add", "data/recipe_images.json"], cwd=_ROOT, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"img: {recipe_id}"], cwd=_ROOT, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=_ROOT, capture_output=True)
    except: pass

recipes = _load_recipes()
saved   = _load_images()

st.markdown("## תמונות מתכונים")
st.caption("חפש תמונה ב-Google Images, העתק את כתובת התמונה, והדבק כאן.")

PAGE_SIZE = 10
show_filter = st.radio("הצג:", ["הכל", "רק ללא תמונה"], horizontal=True)
filtered = [r for r in recipes if show_filter == "הכל" or not saved.get(r.get("recipe_id",""))]

n_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
page = st.number_input("עמוד", min_value=1, max_value=n_pages, value=1, step=1) - 1
page_recipes = filtered[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
st.caption(f"{len(filtered)} מתכונים")
st.divider()

for recipe in page_recipes:
    rid     = recipe.get("recipe_id", "")
    name_he = recipe.get("name_he", "")
    name_en = recipe.get("name_en", "")
    current = saved.get(rid, "")

    status = "✔ יש תמונה" if current else "✖ חסר"
    st.markdown(f"### {name_he} &nbsp; <small style='color:{'#4ade80' if current else '#f87171'}'>{status}</small>", unsafe_allow_html=True)

    # Google Images link
    g_query = urllib.parse.quote(f"{name_he} {name_en} food")
    st.markdown(
        f'<a href="https://www.google.com/search?q={g_query}&tbm=isch" target="_blank">'
        f'פתח Google Images עבור "{name_he}"</a>',
        unsafe_allow_html=True
    )

    # Current image preview
    if current:
        st.image(current, width=250)

    # URL paste + save
    with st.form(key=f"form_{rid}"):
        url_input = st.text_input(
            "הדבק כאן URL של תמונה:",
            value=current,
            placeholder="https://...",
            key=f"url_{rid}"
        )
        # Preview before saving
        if url_input and url_input != current:
            st.image(url_input, width=250, caption="תצוגה מקדימה")

        if st.form_submit_button("שמור ופרסם", type="primary", use_container_width=True):
            if url_input.startswith("http"):
                _save_and_push(rid, url_input)
                st.success(f"נשמר ועלה לאוויר!")
                st.rerun()
            else:
                st.error("URL לא תקין")

    st.divider()
