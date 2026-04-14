#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף מעקב אימונים — תיעוד אימונים יומיים לכל לקוח
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
import streamlit as st
from nutrition_app.user_manager import (
    get_all_users, create_user,
    load_workouts, save_workout, delete_workout,
)

st.set_page_config(page_title="מעקב אימונים", page_icon="🏋️", layout="wide")

st.markdown("""
<style>
    .main .block-container { direction: rtl; }
    section[data-testid="stSidebar"] > div { direction: rtl; }
    h1,h2,h3 { text-align: right; }
</style>
""", unsafe_allow_html=True)

# ── קבועים ───────────────────────────────────────────────────────────────────

WORKOUT_TYPES = {
    "כוח": {"icon": "🏋️", "color": "#ef5350"},
    "אירובי": {"icon": "🏃", "color": "#42a5f5"},
    "HIIT": {"icon": "⚡", "color": "#ffa726"},
    "גמישות / יוגה": {"icon": "🧘", "color": "#66bb6a"},
    "שחייה": {"icon": "🏊", "color": "#26c6da"},
    "רכיבה על אופניים": {"icon": "🚴", "color": "#ab47bc"},
    "הליכה": {"icon": "🚶", "color": "#8d6e63"},
    "אחר": {"icon": "🏅", "color": "#78909c"},
}

INTENSITY_LABELS = {
    1: "קל מאוד",
    2: "קל",
    3: "בינוני",
    4: "קשה",
    5: "מאוד קשה",
}

# ── Sidebar — בחירת משתמש ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👥 לקוחות")
    users = get_all_users()

    if users:
        user_names = {u["user_id"]: u["name"] for u in users}
        selected_id = st.selectbox(
            "בחר לקוח",
            options=[u["user_id"] for u in users],
            format_func=lambda uid: user_names[uid],
            key="workout_user_id",
        )
    else:
        selected_id = None
        st.info("אין לקוחות עדיין.")

    st.divider()
    st.markdown("### ➕ לקוח חדש")
    new_name = st.text_input("שם הלקוח", key="new_user_name")
    if st.button("צור לקוח", use_container_width=True):
        if new_name.strip():
            u = create_user(new_name.strip())
            st.success(f"נוצר: {u['name']}")
            st.rerun()
        else:
            st.error("הכנס שם")

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("# 🏋️ מעקב אימונים")

if not selected_id:
    st.info("בחר לקוח מהתפריט השמאלי.")
    st.stop()

user = next((u for u in users if u["user_id"] == selected_id), None)
if not user:
    st.stop()

st.markdown(f"### 👤 {user['name']}")
st.divider()

today_str = date.today().isoformat()
all_workouts = load_workouts(selected_id)
today_workouts = [w for w in all_workouts if w.get("date", "") == today_str]

# ── סטטיסטיקות יום ──────────────────────────────────────────────────────────
col_stat1, col_stat2, col_stat3 = st.columns(3)
total_duration = sum(w.get("duration_min", 0) for w in today_workouts)
total_cal_burned = sum(w.get("calories_burned", 0) for w in today_workouts)

col_stat1.metric("אימונים היום", len(today_workouts))
col_stat2.metric("סה\"כ זמן", f"{total_duration} דק׳")
col_stat3.metric("קלוריות נשרפו (הערכה)", f"{total_cal_burned:.0f} קק\"ל")

st.divider()

# ── רישום אימון חדש ──────────────────────────────────────────────────────────
with st.expander("➕ רשום אימון חדש", expanded=len(today_workouts) == 0):
    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        workout_type = st.selectbox(
            "סוג אימון",
            options=list(WORKOUT_TYPES.keys()),
            key="wt_type",
        )
    with c2:
        duration = st.number_input("משך (דקות)", min_value=1, max_value=600, value=45, key="wt_dur")
    with c3:
        workout_date = st.date_input("תאריך", value=date.today(), key="wt_date")

    c4, c5 = st.columns([2, 2])
    with c4:
        intensity = st.select_slider(
            "עצימות",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: f"{x} — {INTENSITY_LABELS[x]}",
            key="wt_intensity",
        )
    with c5:
        notes = st.text_input("הערות (אופציונלי)", placeholder="לדוג׳: ריצה בפארק, 5 ק״מ...", key="wt_notes")

    # הערכת קלוריות שנשרפו (נוסחה פשוטה לפי עצימות וזמן)
    MET_BY_TYPE = {
        "כוח": 5, "אירובי": 8, "HIIT": 10, "גמישות / יוגה": 3,
        "שחייה": 7, "רכיבה על אופניים": 7, "הליכה": 4, "אחר": 5,
    }
    met = MET_BY_TYPE.get(workout_type, 5)
    est_calories = round(met * intensity * duration * 0.0175 * 70)  # ~70 ק״ג ממוצע
    st.caption(f"הערכת קלוריות שיישרפו: ~{est_calories} קק\"ל (לפי עצימות {intensity}/5)")

    if st.button("✔ שמור אימון", type="primary", use_container_width=True):
        entry = {
            "date": workout_date.isoformat(),
            "type": workout_type,
            "duration_min": int(duration),
            "intensity": int(intensity),
            "calories_burned": est_calories,
            "notes": notes.strip(),
        }
        save_workout(selected_id, entry)
        st.success(f"✅ נרשם: {WORKOUT_TYPES[workout_type]['icon']} {workout_type} — {duration} דק׳")
        st.rerun()

st.divider()

# ── אימוני היום ──────────────────────────────────────────────────────────────
st.markdown(f"### 📅 אימונים היום — {today_str}")

if not today_workouts:
    st.info("לא נרשמו אימונים היום.")
else:
    for w in reversed(today_workouts):
        wtype = w.get("type", "אחר")
        icon = WORKOUT_TYPES.get(wtype, {}).get("icon", "🏅")
        color = WORKOUT_TYPES.get(wtype, {}).get("color", "#888")
        dur = w.get("duration_min", 0)
        intens = w.get("intensity", 3)
        cal_b = w.get("calories_burned", 0)
        notes_txt = w.get("notes", "")
        wid = w.get("workout_id", "")
        logged = w.get("logged_at", "")[:16].replace("T", " ")

        col_w, col_del = st.columns([10, 1])
        with col_w:
            st.markdown(
                f'<div style="background:#1a1a2e;border:1px solid {color};border-radius:12px;'
                f'padding:12px 16px;margin:5px 0;direction:rtl">'
                f'<span style="font-size:1.2em">{icon}</span> '
                f'<strong style="color:#e8e8ff">{wtype}</strong>'
                f'<span style="color:#888;font-size:0.85em"> · {dur} דק׳ · עצימות {intens}/5 · ~{cal_b} קק״ל</span>'
                + (f'<br><span style="color:#aaa;font-size:0.82em">📝 {notes_txt}</span>' if notes_txt else '')
                + f'<br><span style="color:#555;font-size:0.75em">נרשם ב-{logged}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            st.write("")
            if st.button("🗑", key=f"del_w_{wid}"):
                delete_workout(selected_id, wid)
                st.rerun()

st.divider()

# ── היסטוריה ─────────────────────────────────────────────────────────────────
st.markdown("### 📊 היסטוריית אימונים")

past_workouts = [w for w in all_workouts if w.get("date", "") != today_str]

if not past_workouts:
    st.info("אין היסטוריה עדיין.")
else:
    # קיבוץ לפי תאריך
    by_date: dict = {}
    for w in past_workouts:
        d = w.get("date", "לא ידוע")
        by_date.setdefault(d, []).append(w)

    for d in sorted(by_date.keys(), reverse=True)[:7]:  # 7 ימים אחרונים
        day_list = by_date[d]
        day_dur = sum(w.get("duration_min", 0) for w in day_list)
        day_cal = sum(w.get("calories_burned", 0) for w in day_list)
        icons_str = " ".join(WORKOUT_TYPES.get(w.get("type", ""), {}).get("icon", "🏅") for w in day_list)

        with st.expander(f"{d}  —  {icons_str}  |  {day_dur} דק׳  |  ~{day_cal:.0f} קק\"ל"):
            for w in day_list:
                wtype = w.get("type", "אחר")
                icon = WORKOUT_TYPES.get(wtype, {}).get("icon", "🏅")
                dur = w.get("duration_min", 0)
                intens = w.get("intensity", 3)
                cal_b = w.get("calories_burned", 0)
                notes_txt = w.get("notes", "")
                wid = w.get("workout_id", "")

                del_col, info_col = st.columns([1, 10])
                with del_col:
                    if st.button("🗑", key=f"del_hist_{wid}"):
                        delete_workout(selected_id, wid)
                        st.rerun()
                with info_col:
                    txt = f"{icon} **{wtype}** — {dur} דק׳ · עצימות {intens}/5 · ~{cal_b} קק״ל"
                    if notes_txt:
                        txt += f" · _{notes_txt}_"
                    st.markdown(txt)
