#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4_settings.py — הגדרות יישום וניהול מערכת
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, page_header, section_header

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="הגדרות",
    page_icon="⚙️",
    layout="wide",
)

# ── Design system ─────────────────────────────────────────────────────────
inject_global_css()

# ── Page header ───────────────────────────────────────────────────────────
page_header(
    "הגדרות יישום",
    icon_name="settings",
    subtitle="ניהול תצורה וביצועי המערכת",
)

# ── Constants ─────────────────────────────────────────────────────────────
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage_agents")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "config.toml")
SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "secrets.toml")

# ── Tab navigation ────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["⚙️ הגדרות כלליות", "🔐 אבטחה", "💾 אחסון", "🔧 דיאגנוסטיקה"])

# ── Tab 1: General Settings ───────────────────────────────────────────────

with tab1:
    section_header("הגדרות כלליות", icon_name="sliders")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### שפה")
        language = st.radio(
            "בחר שפה",
            options=["עברית", "English"],
            index=0,
            key="language_select",
            horizontal=True
        )
        st.caption(f"שפה נבחרת: {language}")

    with col2:
        st.markdown("#### ערכת צבעים")
        theme = st.radio(
            "בחר ערכת צבעים",
            options=["כהה (Dark)", "בהיר (Light)"],
            index=0,
            key="theme_select",
            horizontal=True
        )
        st.caption(f"ערכת צבעים נבחרת: {theme}")

    st.divider()

    st.markdown("#### הודעות כלליות")
    app_version = st.text_input(
        "גרסת יישום",
        value="1.0.0",
        help="גרסת היישום הנוכחית"
    )
    st.caption("⚠️ שינוי גרסה עשוי להשפיע על תאימות נתונים")

# ── Tab 2: Security ───────────────────────────────────────────────────────

with tab2:
    section_header("הגדרות אבטחה", icon_name="shield")

    st.markdown("### סיסמת ניהול")
    st.info("""
    סיסמת הניהול מאוחסנת בקובץ `.streamlit/secrets.toml` ובמשתנה `NUTRITION_ADMIN_PASSWORD`.
    **אל תפרסם את הסיסמה בקוד או בהגדרות ציבוריות.**
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### הצג מידע ביטחוני")
        if st.checkbox("הצג פרטי סיסמה (רק לאישור שהוגדרה)", key="show_security"):
            # Check if secrets file exists
            if os.path.exists(SECRETS_FILE):
                st.success("✓ קובץ secrets קיים")
            else:
                st.warning("⚠️ קובץ secrets לא קיים")

    with col2:
        st.markdown("#### ניהול הרשאות")
        st.markdown("""
        הרשאות הניהול מוגדרות ב-`ui/auth.py`:
        - `is_admin()` — בדוק אם משתמש הוא ניהל
        - `require_admin()` — דרוש אימות ניהול
        """)

    st.divider()

    st.markdown("### מדיניות אבטחה")
    security_enabled = st.toggle("הפעל בדיקות אבטחה מתקדמות", value=True)
    if security_enabled:
        st.success("בדיקות אבטחה מופעלות")

# ── Tab 3: Storage ────────────────────────────────────────────────────────

with tab3:
    section_header("ניהול אחסון", icon_name="database")

    st.markdown("### מידע אחסון")

    # Display storage locations
    storage_locations = {
        "תיקיית אחסון עיקרית": STORAGE_DIR,
        "קובץ תצורה": CONFIG_FILE,
        "קובץ סודות": SECRETS_FILE,
    }

    for name, path in storage_locations.items():
        exists = os.path.exists(path)
        status = "✓ קיים" if exists else "✗ לא קיים"
        st.markdown(f"**{name}:** `{path}` {status}")

    st.divider()

    st.markdown("### ניקוי נתונים")
    st.warning("""
    ⚠️ **זהירות!** פעולות אלו לא ניתן לבטל. הכן גיבוי לפני ביצוע.
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ מחק דוחות ישנים", help="מחק דוחות שישנן ביותר מ-30 ימים"):
            st.info("תכונה זו לא מיושמת עדיין")

    with col2:
        if st.button("🗑️ מחק לוגים", help="מחק קבצי לוג ישנים"):
            st.info("תכונה זו לא מיושמת עדיין")

    st.divider()

    st.markdown("### חלל אחסון")
    if os.path.exists(STORAGE_DIR):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(STORAGE_DIR):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except:
                    pass

        used_mb = total_size / (1024 * 1024)
        st.metric("חלל בשימוש", f"{used_mb:.1f} MB")
    else:
        st.info("תיקיית אחסון לא קיימת")

# ── Tab 4: Diagnostics ────────────────────────────────────────────────────

with tab4:
    section_header("דיאגנוסטיקה", icon_name="wrench")

    st.markdown("### בדיקות מערכת")

    checks = []

    # Check 1: Storage directories
    check1 = os.path.exists(STORAGE_DIR)
    checks.append(("תיקיית אחסון קיימת", check1))

    # Check 2: Database exists
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "nutrition.db")
    check2 = os.path.exists(db_path)
    checks.append(("מסד נתונים קיים", check2))

    # Check 3: Config file
    check3 = os.path.exists(CONFIG_FILE)
    checks.append(("קובץ תצורה קיים", check3))

    # Display results
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        color = "green" if passed else "red"
        st.markdown(f"{status} {check_name}")

    st.divider()

    st.markdown("### מידע סביבה")
    env_info = {
        "Python Version": sys.version.split()[0],
        "Streamlit": st.__version__ if hasattr(st, "__version__") else "Unknown",
        "Operating System": sys.platform,
    }

    for key, value in env_info.items():
        st.markdown(f"**{key}:** `{value}`")

    st.divider()

    st.markdown("### רישומים אחרונים")
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents", "logs")

    if os.path.exists(logs_dir):
        log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith(".json")], reverse=True)
        if log_files:
            st.success(f"נמצאו {len(log_files)} קבצי רישום")
            with st.expander("הצג רישומים"):
                for log_file in log_files[:5]:  # Show only last 5
                    st.markdown(f"- `{log_file}`")
        else:
            st.info("אין קבצי רישום עדיין")
    else:
        st.warning("תיקיית רישומים לא קיימת")

# ── Footer ────────────────────────────────────────────────────────────────

st.divider()
st.markdown("""
### עזרה ותמיכה
- 📧 דוגלות בעיות: כתוב דוח באפליקציה
- 📚 תיעוד: קרא את CLAUDE.md להבנת הארכיטקטורה
- 🔗 אתר: [בדוק את הפרוייקט]
""")
