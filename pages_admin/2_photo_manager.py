#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2_photo_manager.py — אישור / דחייה של תמונות מתכונים מהצינור האוטומטי
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, page_header, section_header
from ui.auth import require_admin, admin_logout_button

inject_global_css()
require_admin(page_title="מנהל תמונות", icon_name="images")

page_header(
    "תמונות מתכונים",
    icon_name="images",
    subtitle="אשר או דחה תמונות שנאספו אוטומטית מ-Pexels עבור כל מתכון",
)
admin_logout_button()

#  Load pipeline modules 

try:
    from nutrition_app.agents.agent_recipe_images import image_fetcher as _fetcher
    from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager as _RecipeManager
    _pipeline_ok = True
except Exception as exc:
    st.error(f"שגיאה בטעינת מודול תמונות: {exc}")
    st.stop()
    _pipeline_ok = False

#  Stats + actions row 

stats = _fetcher.get_stats()

c1, c2, c3, c4 = st.columns(4)
c1.metric("סך מתכונים",        stats["total_recipes"])
c2.metric("עם תמונה מאושרת",  stats["with_image"])
c3.metric("ממתינים לאישור",    stats["pending"])
c4.metric("ללא תוצאות",        stats["no_results"])

col_fetch, col_retry = st.columns(2)

if col_fetch.button(" אסוף batch חדש מ-Pexels", use_container_width=True, type="primary"):
    with st.spinner("מחפש תמונות ב-Pexels..."):
        result = _fetcher.run_batch(limit=10)
    msg = []
    if result["fetched"]:
        msg.append(f"נאספו {result['fetched']} מתכונים חדשים")
    if result["no_results"]:
        msg.append(f"{result['no_results']} ללא תוצאות")
    if result["skipped"]:
        msg.append(f"{result['skipped']} דולגו")
    st.success(" | ".join(msg) if msg else "לא נמצאו מתכונים חדשים לאיסוף")
    st.rerun()

if col_retry.button(" נסה שוב לפריטים ללא תוצאות / נדחו", use_container_width=True):
    pending_all = _fetcher.load_pending()
    cleaned = {k: v for k, v in pending_all.items()
               if v.get("status") not in ("no_results", "rejected")}
    _fetcher.save_pending(cleaned)
    st.info("הוסרו רשומות ה-no_results וה-rejected. לחץ 'אסוף batch חדש' להתחיל מחדש.")
    st.rerun()

st.divider()

#  Pending approvals 

pending = _fetcher.load_pending()
pending_items = [
    (rid, entry) for rid, entry in pending.items()
    if entry.get("status") == "pending" and entry.get("candidates")
]

section_header(f"ממתינים לאישור ({len(pending_items)})", icon_name="image")

if not pending_items:
    st.info("אין הצעות ממתינות. לחץ 'אסוף batch חדש' כדי לאסוף תמונות ממתכונים שטרם צולמו.")
else:
    for rid, entry in pending_items:
        name_he = entry.get("name_he", rid)
        name_en = entry.get("name_en", "")

        with st.expander(f" {name_he}  ({name_en})", expanded=True):
            candidates = entry.get("candidates", [])
            cols = st.columns(max(len(candidates), 1))

            for idx, (col, cand) in enumerate(zip(cols, candidates)):
                abs_path = os.path.join(_fetcher.PROJECT_ROOT, cand["local_path"])
                if os.path.isfile(abs_path):
                    try:
                        col.image(abs_path, use_container_width=True)
                    except Exception:
                        col.caption("(שגיאה בטעינת תמונה)")
                else:
                    col.caption("(תמונה חסרה בדיסק)")

                photographer = cand.get("photographer", "")
                if photographer:
                    col.caption(f" {photographer}")

                if col.button(" אשר", key=f"approve_{rid}_{idx}", use_container_width=True, type="primary"):
                    result = _fetcher.approve(rid, idx)
                    if result:
                        rm = _RecipeManager()
                        ok = rm.set_recipe_image(
                            rid,
                            result["image_path"],
                            result.get("image_credit"),
                        )
                        if ok:
                            st.success(f"תמונה שויכה ל-{name_he}")
                        else:
                            st.error("שגיאה בעדכון recipes.json")
                    else:
                        st.error("שגיאה באישור התמונה")
                    st.rerun()

            st.markdown("")
            if st.button(" דחה הכל למתכון זה", key=f"reject_{rid}",
                         use_container_width=False):
                _fetcher.reject(rid)
                st.warning(f"נדחה: {name_he}")
                st.rerun()

#  Approved gallery 

st.divider()
section_header("תמונות מאושרות", icon_name="grid")

approved_dir = os.path.join(_fetcher.PROJECT_ROOT, "storage_agents", "recipe_images", "approved")
approved_files = sorted([
    f for f in os.listdir(approved_dir)
    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
]) if os.path.isdir(approved_dir) else []

if not approved_files:
    st.info("אין תמונות מאושרות עדיין.")
else:
    st.caption(f"סה\"כ {len(approved_files)} תמונות מאושרות")
    grid_cols = st.columns(4)
    for i, fname in enumerate(approved_files):
        col = grid_cols[i % 4]
        fpath = os.path.join(approved_dir, fname)
        recipe_id = fname.rsplit(".", 1)[0]
        try:
            col.image(fpath, caption=recipe_id, use_container_width=True)
        except Exception:
            col.caption(f"(שגיאה: {fname})")
