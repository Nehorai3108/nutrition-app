#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5_food_images.py — בחירת תמונה לכל מתכון (3 אפשרויות מ-Pexels)
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.auth import require_admin, admin_logout_button
from ui.components import inject_global_css

st.set_page_config(page_title="תמונות מזון", layout="wide")
inject_global_css()
require_admin(page_title="תמונות מזון", icon_name="images")
admin_logout_button()

# ── Paths ──────────────────────────────────────────────────────────────────
_ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RECIPES_FILE = os.path.join(_ROOT, "storage_agents", "recipes", "recipes.json")
_IMAGES_FILE  = os.path.join(_ROOT, "data", "recipe_images.json")
_API_KEY_FILE = os.path.join(_ROOT, "storage_agents", "recipe_images", ".pexels_api_key")
PEXELS_URL    = "https://api.pexels.com/v1/search"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ── Helpers ────────────────────────────────────────────────────────────────
def _api_key():
    k = os.environ.get("PEXELS_API_KEY", "").strip()
    if k: return k
    try: return open(_API_KEY_FILE, encoding="utf-8").read().strip() or None
    except: return None

def _search(query: str) -> list:
    import urllib.request, urllib.parse
    key = _api_key()
    if not key: return []
    params = urllib.parse.urlencode({"query": query, "per_page": 3, "orientation": "landscape"})
    req = urllib.request.Request(
        f"{PEXELS_URL}?{params}",
        headers={"Authorization": key, "User-Agent": _UA, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return [p["src"]["large"] for p in json.loads(r.read())["photos"]]
    except: return []

def _load_recipes():
    try: return json.load(open(_RECIPES_FILE, encoding="utf-8"))
    except: return []

def _load_images() -> dict:
    try: return json.load(open(_IMAGES_FILE, encoding="utf-8"))
    except: return {}

def _save_image(recipe_id: str, url: str):
    imgs = _load_images()
    imgs[recipe_id] = url
    with open(_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(imgs, f, ensure_ascii=False, indent=2)

# ── State ──────────────────────────────────────────────────────────────────
if "img_cache" not in st.session_state:
    st.session_state.img_cache = {}   # recipe_id → [url1, url2, url3]

# ── Data ───────────────────────────────────────────────────────────────────
recipes = _load_recipes()
saved   = _load_images()

# ── UI ─────────────────────────────────────────────────────────────────────
st.markdown("## תמונות מתכונים")

# Pagination
PAGE_SIZE = 10
total     = len(recipes)
n_pages   = (total + PAGE_SIZE - 1) // PAGE_SIZE
page      = st.number_input("עמוד", min_value=1, max_value=n_pages, value=1, step=1) - 1
page_recipes = recipes[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

st.markdown(f"מציג {page*PAGE_SIZE+1}–{min((page+1)*PAGE_SIZE, total)} מתוך {total} מתכונים")
st.divider()

for recipe in page_recipes:
    rid      = recipe.get("recipe_id", "")
    name_he  = recipe.get("name_he", "")
    name_en  = recipe.get("name_en", "")
    current  = saved.get(rid, "")

    col_title, col_status = st.columns([4, 1])
    col_title.markdown(f"### {name_he}")
    if current:
        col_status.success("יש תמונה")
    else:
        col_status.warning("אין תמונה")

    # Show current image small
    if current:
        st.image(current, width=200)

    # Fetch button
    if st.button(f"הבא 3 תמונות", key=f"fetch_{rid}"):
        with st.spinner("מחפש..."):
            opts = _search(name_en or name_he)
        st.session_state.img_cache[rid] = opts

    # Show 3 options
    opts = st.session_state.img_cache.get(rid, [])
    if opts:
        cols = st.columns(3)
        for i, (col, url) in enumerate(zip(cols, opts)):
            col.image(url, use_container_width=True)
            if col.button("בחר תמונה זו", key=f"pick_{rid}_{i}", use_container_width=True, type="primary"):
                _save_image(rid, url)
                st.session_state.img_cache.pop(rid, None)
                st.success(f"נשמר עבור {name_he}")
                st.rerun()

    st.divider()
