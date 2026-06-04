#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5_food_images.py — בחירת תמונות למאכלים ומתכונים
מביא 3 אפשרויות מ-Pexels לכל מאכל — אתה בוחר, זה נשמר.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css
from ui.auth import require_admin, admin_logout_button

st.set_page_config(page_title="תמונות מזון", layout="wide")
inject_global_css()
require_admin(page_title="תמונות מזון", icon_name="images")
admin_logout_button()

# ── Paths ──────────────────────────────────────────────────────────────────
_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MANUAL_IMG = os.path.join(_ROOT, "data", "food_images_manual.json")
_FOODS_FILE = os.path.join(_ROOT, "nutrition_app", "data", "foods_extended.json")
_RECIPES_FILE = os.path.join(_ROOT, "storage_agents", "recipes", "recipes.json")
_API_KEY_FILE = os.path.join(_ROOT, "storage_agents", "recipe_images", ".pexels_api_key")

PEXELS_URL = "https://api.pexels.com/v1/search"
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# ── Helpers ────────────────────────────────────────────────────────────────
def _get_api_key():
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if key:
        return key
    try:
        return open(_API_KEY_FILE, encoding="utf-8").read().strip() or None
    except Exception:
        return None

def _pexels_search(query: str, n: int = 3) -> list[str]:
    import urllib.request, urllib.parse, urllib.error
    key = _get_api_key()
    if not key:
        return []
    params = urllib.parse.urlencode({"query": query, "per_page": n, "orientation": "landscape"})
    req = urllib.request.Request(
        f"{PEXELS_URL}?{params}",
        headers={"Authorization": key, "User-Agent": _BROWSER_UA, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [p["src"]["medium"] for p in data.get("photos", [])]
    except Exception:
        return []

@st.cache_data(ttl=60)
def _load_manual() -> dict:
    try:
        d = json.load(open(_MANUAL_IMG, encoding="utf-8"))
        return {**d.get("recipes", {}), **d.get("ingredients", {})}
    except Exception:
        return {}

def _save_manual(flat: dict):
    """Save flat dict back into the structured JSON file."""
    try:
        d = json.load(open(_MANUAL_IMG, encoding="utf-8"))
    except Exception:
        d = {"recipes": {}, "ingredients": {}}
    # Split back: recipes keys contain meal/dish names, ingredients the rest
    # We just merge everything into ingredients for simplicity
    d["ingredients"].update(flat)
    with open(_MANUAL_IMG, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

@st.cache_data(ttl=300)
def _load_foods():
    try:
        return json.load(open(_FOODS_FILE, encoding="utf-8"))
    except Exception:
        return []

@st.cache_data(ttl=300)
def _load_recipes():
    try:
        return json.load(open(_RECIPES_FILE, encoding="utf-8"))
    except Exception:
        return []

# ── UI ─────────────────────────────────────────────────────────────────────
st.markdown("## בחירת תמונות למזון")
st.markdown("בחר מאכל — קבל 3 אפשרויות מ-Pexels — לחץ על אחת לאישור.")

_manual = _load_manual()
_foods   = _load_foods()
_recipes = _load_recipes()

# Build item list
_all_items = []
for r in _recipes:
    _all_items.append({
        "id": r.get("recipe_id", ""),
        "name_he": r.get("name_he", ""),
        "name_en": r.get("name_en", ""),
        "type": "מתכון",
        "query": r.get("name_en", r.get("name_he", "")),
        "key": r.get("name_en", "").lower(),
    })
for f in _foods:
    _all_items.append({
        "id": f.get("food_id", ""),
        "name_he": f.get("name_he", ""),
        "name_en": f.get("name_en", ""),
        "type": "רכיב",
        "query": f.get("name_en", f.get("name_he", "")),
        "key": f.get("name_en", "").lower(),
    })

# Filter
col_search, col_type = st.columns([3, 1])
_search = col_search.text_input("חיפוש מאכל", placeholder="הקלד שם בעברית או אנגלית...")
_type_filter = col_type.selectbox("סוג", ["הכל", "מתכון", "רכיב"])

_filtered = [
    i for i in _all_items
    if (_search.lower() in i["name_he"].lower() or _search.lower() in i["name_en"].lower())
    and (_type_filter == "הכל" or i["type"] == _type_filter)
][:30]

if not _search:
    st.info("הקלד שם מאכל לחיפוש")
    st.stop()

if not _filtered:
    st.warning("לא נמצאו תוצאות")
    st.stop()

for item in _filtered:
    with st.expander(f"{item['name_he']} ({item['name_en']}) — {item['type']}", expanded=False):
        _current = _manual.get(item["key"], "")
        if _current:
            st.markdown(f"**תמונה נוכחית:**")
            st.image(_current, width=300)

        if st.button(f"הבא 3 אפשרויות מ-Pexels", key=f"fetch_{item['id']}"):
            st.session_state[f"opts_{item['id']}"] = _pexels_search(item["query"], 3)

        _opts = st.session_state.get(f"opts_{item['id']}", [])
        if _opts:
            st.markdown("**בחר תמונה:**")
            cols = st.columns(len(_opts))
            for idx, (col, url) in enumerate(zip(cols, _opts)):
                with col:
                    st.image(url, use_container_width=True)
                    if st.button("בחר", key=f"pick_{item['id']}_{idx}"):
                        _manual_updated = dict(_manual)
                        _manual_updated[item["key"]] = url
                        _save_manual(_manual_updated)
                        _load_manual.clear()
                        st.success("נשמר!")
                        st.session_state.pop(f"opts_{item['id']}", None)
                        st.rerun()

        # Manual URL input
        with st.form(key=f"manual_url_{item['id']}"):
            _url_input = st.text_input("או הדבק URL ישירות:", value=_current)
            if st.form_submit_button("שמור URL"):
                _manual_updated = dict(_manual)
                _manual_updated[item["key"]] = _url_input
                _save_manual(_manual_updated)
                _load_manual.clear()
                st.success("נשמר!")
                st.rerun()
