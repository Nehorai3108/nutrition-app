#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, urllib.request, urllib.parse
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

def _save_image(recipe_id: str, url: str):
    imgs = _load_images()
    imgs[recipe_id] = url
    with open(_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(imgs, f, ensure_ascii=False, indent=2)

def _search_images(query: str) -> list:
    """Search TheMealDB for meals matching query, return up to 3 image URLs."""
    urls = []
    try:
        q = urllib.parse.urlencode({"s": query})
        req = urllib.request.Request(
            f"https://www.themealdb.com/api/json/v1/1/search.php?{q}",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            meals = json.loads(r.read()).get("meals") or []
            urls = [m["strMealThumb"] for m in meals[:3]]
    except: pass

    # If less than 3 results, try first word only
    if len(urls) < 3:
        try:
            first_word = query.split()[0]
            q2 = urllib.parse.urlencode({"s": first_word})
            req2 = urllib.request.Request(
                f"https://www.themealdb.com/api/json/v1/1/search.php?{q2}",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req2, timeout=8) as r2:
                meals2 = json.loads(r2.read()).get("meals") or []
                for m in meals2:
                    if m["strMealThumb"] not in urls:
                        urls.append(m["strMealThumb"])
                    if len(urls) >= 3:
                        break
        except: pass

    return urls[:3]

# ── State ──────────────────────────────────────────────────────────────────
if "img_cache" not in st.session_state:
    st.session_state.img_cache = {}

recipes = _load_recipes()
saved   = _load_images()

# ── UI ─────────────────────────────────────────────────────────────────────
st.markdown("## תמונות מתכונים")

PAGE_SIZE = 10
total     = len(recipes)
n_pages   = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
page      = st.number_input("עמוד", min_value=1, max_value=n_pages, value=1, step=1) - 1

# Filter: show only without image or all
show_filter = st.radio("הצג:", ["הכל", "רק ללא תמונה"], horizontal=True)
filtered = [r for r in recipes if show_filter == "הכל" or not saved.get(r.get("recipe_id",""))]
page_recipes = filtered[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

st.caption(f"{len(filtered)} מתכונים | עמוד {page+1} מתוך {max(1,(len(filtered)+PAGE_SIZE-1)//PAGE_SIZE)}")
st.divider()

for recipe in page_recipes:
    rid     = recipe.get("recipe_id", "")
    name_he = recipe.get("name_he", "")
    name_en = recipe.get("name_en", "")
    current = saved.get(rid, "")

    # Title row
    c1, c2 = st.columns([5, 1])
    c1.markdown(f"### {name_he}")
    if current:
        c2.success("נבחרה")
    else:
        c2.warning("חסרה")

    # Search row
    s_col1, s_col2 = st.columns([3, 1])
    search_term = s_col1.text_input("חיפוש (אנגלית)", value=name_en, key=f"term_{rid}", label_visibility="collapsed")
    if s_col2.button("הבא 3 תמונות", key=f"fetch_{rid}", use_container_width=True):
        with st.spinner("מחפש..."):
            st.session_state.img_cache[rid] = _search_images(search_term)

    opts = st.session_state.img_cache.get(rid, [])

    # Show current + options
    if current or opts:
        cols = st.columns(3)

        all_imgs = []
        if current:
            all_imgs.append(("תמונה נוכחית", current))
        for i, url in enumerate(opts):
            if url != current:
                all_imgs.append((f"אפשרות {i+1}", url))
        all_imgs = all_imgs[:3]

        for col, (label, url) in zip(cols, all_imgs):
            col.image(url, use_container_width=True)
            col.caption(label)
            if col.button("בחר", key=f"pick_{rid}_{url[-20:]}", use_container_width=True, type="primary"):
                _save_image(rid, url)
                st.session_state.img_cache.pop(rid, None)
                st.success(f"נשמר!")
                st.rerun()

    st.divider()
