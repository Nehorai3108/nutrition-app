#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, urllib.request, urllib.parse, subprocess
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
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ── Image fetching ──────────────────────────────────────────────────────────
def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))

def _fetch_images(query: str, offset: int = 0) -> list:
    """Search DuckDuckGo images — most relevant results."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.images(
                f"{query} food recipe",
                max_results=offset + 6,
                safesearch="on",
            ))
        urls = [r["image"] for r in results[offset:offset+3] if r.get("image")]
        return urls
    except Exception:
        pass

    # Fallback: TheMealDB
    urls = []
    try:
        q = urllib.parse.urlencode({"s": query.split()[0]})
        data = _get(f"https://www.themealdb.com/api/json/v1/1/search.php?{q}")
        for m in (data.get("meals") or [])[:3]:
            urls.append(m["strMealThumb"])
    except: pass
    return urls

# ── Data helpers ────────────────────────────────────────────────────────────
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

def _push_to_git():
    try:
        subprocess.Popen(
            ["git", "add", "data/recipe_images.json"],
            cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).wait()
        subprocess.Popen(
            ["git", "commit", "-m", "img: recipe image update"],
            cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).wait()
        subprocess.Popen(
            ["git", "push", "origin", "main"],
            cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except: pass

# ── Session state ───────────────────────────────────────────────────────────
if "img_opts"   not in st.session_state: st.session_state.img_opts   = {}
if "img_offset" not in st.session_state: st.session_state.img_offset = {}
if "done_rids"  not in st.session_state: st.session_state.done_rids  = set()

recipes = _load_recipes()
saved   = _load_images()

# ── UI ──────────────────────────────────────────────────────────────────────
st.markdown("## תמונות מתכונים")

show_filter = st.radio("הצג:", ["הכל", "רק ללא תמונה"], index=1, horizontal=True)
filtered    = [r for r in recipes
               if r.get("recipe_id","") not in st.session_state.done_rids
               and (show_filter == "הכל" or not saved.get(r.get("recipe_id","")))]

PAGE_SIZE = 8
n_pages   = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
page      = st.number_input("עמוד", min_value=1, max_value=n_pages, value=1, step=1) - 1
page_recs = filtered[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
st.caption(f"{len(filtered)} מתכונים | עמוד {page+1}/{n_pages}")
st.divider()

for recipe in page_recs:
    rid     = recipe.get("recipe_id", "")
    name_he = recipe.get("name_he", "")
    name_en = recipe.get("name_en", "")
    current = saved.get(rid, "")
    status_color = "#4ade80" if current else "#f87171"
    status_text  = "יש תמונה" if current else "חסרה"

    st.markdown(
        f'<div style="font-size:1.2rem;font-weight:800;margin-bottom:4px">'
        f'{name_he} &nbsp;'
        f'<span style="font-size:0.75rem;color:{status_color};font-weight:600">{status_text}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Auto-load images on first view
    if rid not in st.session_state.img_opts:
        offset = st.session_state.img_offset.get(rid, 0)
        with st.spinner("מביא תמונות..."):
            st.session_state.img_opts[rid] = _fetch_images(name_en or name_he, offset)

    opts = st.session_state.img_opts.get(rid, [])

    if opts:
        cols = st.columns(3)
        for i, (col, url) in enumerate(zip(cols, opts)):
            col.image(url, use_container_width=True)
            if col.button("בחר", key=f"pick_{rid}_{i}", use_container_width=True, type="primary"):
                _save_image(rid, url)
                _push_to_git()
                st.session_state.img_opts.pop(rid, None)
                st.session_state.img_offset.pop(rid, None)
                st.session_state.done_rids.add(rid)
                st.rerun()

        if st.button("3 תמונות אחרות", key=f"more_{rid}"):
            st.session_state.img_offset[rid] = st.session_state.img_offset.get(rid, 0) + 3
            st.session_state.img_opts.pop(rid, None)
            st.rerun()
    else:
        st.warning("לא נמצאו תמונות — נסה בעמוד הבא")

    if current:
        with st.expander("תמונה נוכחית"):
            st.image(current, width=200)

    st.divider()
