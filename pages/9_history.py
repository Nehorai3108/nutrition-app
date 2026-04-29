#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""9_history.py — היסטוריה עם לוח שנה + תכנון שבועי"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from pathlib import Path
import streamlit as st

from ui.components import inject_global_css, bottom_nav
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.repositories.water_repository import WaterRepository
from nutrition_app.repositories.food_log_repository import FoodLogRepository

st.set_page_config(page_title="היסטוריה", page_icon=None, layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

USER_ID      = "ui_user_001"
workout_repo = WorkoutRepository()
water_repo   = WaterRepository()
food_repo    = FoodLogRepository()
today        = date.today()

HEB_WD = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי",
           4: "שישי", 5: "שבת", 6: "ראשון"}
HEB_WD_SHORT = {0: "ב'", 1: "ג'", 2: "ד'", 3: "ה'", 4: "ו'", 5: "ש'", 6: "א'"}

CALORIE_TARGET = 2000  # fallback

# ── Weekly plan storage ────────────────────────────────────────────────────────
PLANS_DIR = Path(__file__).parent.parent / "storage_agents" / "weekly_plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)
PLAN_FILE = PLANS_DIR / f"{USER_ID}.json"


def _load_plan() -> dict:
    if PLAN_FILE.exists():
        try:
            return json.loads(PLAN_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_plan(plan: dict):
    PLAN_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def _week_start(offset: int = 0) -> date:
    """Return Monday of the week at `offset` weeks from today."""
    wd = today.weekday()  # Monday=0
    monday = today - timedelta(days=wd) + timedelta(weeks=offset)
    return monday


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;'
    f'padding:4px 2px 16px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb">היסטוריה ותכנון</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{today.strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

tab_hist, tab_plan = st.tabs(["📅 היסטוריה", "📋 תכנון שבועי"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HISTORY CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_hist:

    # Week navigation
    if "hist_woff" not in st.session_state:
        st.session_state["hist_woff"] = 0

    hw_col1, hw_col2, hw_col3 = st.columns([1, 3, 1])
    with hw_col1:
        if st.button("‹ קדימה", key="hist_prev", use_container_width=True):
            st.session_state["hist_woff"] += 1
    with hw_col3:
        if st.button("אחורה ›", key="hist_next", use_container_width=True,
                     disabled=st.session_state["hist_woff"] >= 0):
            st.session_state["hist_woff"] -= 1

    woff = st.session_state["hist_woff"]
    week_monday = _week_start(woff)
    week_sunday = week_monday + timedelta(days=6)

    with hw_col2:
        label = f'{week_monday.strftime("%d/%m")} – {week_sunday.strftime("%d/%m/%Y")}'
        if woff == 0:
            label = f"השבוע הנוכחי · {label}"
        elif woff == -1:
            label = f"שבוע שעבר · {label}"
        else:
            label = f"לפני {abs(woff)} שבועות · {label}"
        st.markdown(
            f'<div dir="rtl" style="text-align:center;font-size:0.82rem;'
            f'color:#a0aec0;padding:6px 0">{label}</div>',
            unsafe_allow_html=True,
        )

    # Build week data
    week_days = [week_monday + timedelta(days=i) for i in range(7)]
    week_data = []
    for d in week_days:
        cal  = int(food_repo.get_totals(USER_ID, d)["calories"])
        wtr  = int(sum(w.amount_ml for w in water_repo.get_water_intakes_for_date(USER_ID, d)))
        wos  = workout_repo.get_workout_data(USER_ID).daily_log.get(d.isoformat(), [])
        week_data.append({"date": d, "cal": cal, "wtr": wtr, "wos": len(wos)})

    max_cal = max((r["cal"] for r in week_data), default=1) or 1

    # 7-column calendar grid header
    day_cols = st.columns(7)
    for i, col in enumerate(day_cols):
        d = week_days[i]
        is_today = (d == today)
        header_bg = "#1e3a5f" if is_today else "transparent"
        header_color = "#4f8ef7" if is_today else "#a0aec0"
        col.markdown(
            f'<div dir="rtl" style="text-align:center;font-size:0.72rem;font-weight:700;'
            f'color:{header_color};background:{header_bg};border-radius:8px;padding:4px 2px">'
            f'{HEB_WD_SHORT[d.weekday()]}<br>'
            f'<span style="font-size:0.9rem;font-weight:900">{d.day}</span></div>',
            unsafe_allow_html=True,
        )

    # Calendar cells
    if "hist_sel" not in st.session_state:
        st.session_state["hist_sel"] = today.isoformat()

    cell_cols = st.columns(7)
    for i, col in enumerate(cell_cols):
        row = week_data[i]
        d = row["date"]
        cal_pct = min(row["cal"] / max_cal, 1.0) if max_cal > 0 else 0
        bar_h   = max(int(cal_pct * 48), 2)
        is_sel  = (d.isoformat() == st.session_state["hist_sel"])
        border  = "2px solid #4f8ef7" if is_sel else "1px solid #252d3d"
        cell_bg = "#1a2540" if is_sel else "#161b26"

        dots_html = ""
        if row["wtr"] > 0:
            dots_html += '<span style="color:#38bdf8;font-size:0.65rem">💧</span>'
        if row["wos"] > 0:
            dots_html += f'<span style="color:#f59e0b;font-size:0.65rem">🏋️</span>'
        cal_text = str(row["cal"]) if row["cal"] > 0 else "—"

        col.markdown(
            f'<div dir="rtl" style="background:{cell_bg};border:{border};border-radius:12px;'
            f'padding:6px 4px;text-align:center;min-height:90px;'
            f'display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:2px">'
            f'<div style="width:14px;background:#253356;border-radius:4px;height:52px;'
            f'display:flex;align-items:flex-end;overflow:hidden">'
            f'<div style="width:100%;height:{bar_h}px;background:#4f8ef7;border-radius:3px"></div></div>'
            f'<div dir="rtl" style="font-size:0.6rem;font-weight:700;color:#f4f6fb;margin-top:2px">'
            f'{cal_text}</div>'
            f'<div dir="rtl" style="font-size:0.65rem;line-height:1.1">{dots_html}&nbsp;</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if col.button("בחר", key=f"hsel_{d.isoformat()}", use_container_width=True):
            st.session_state["hist_sel"] = d.isoformat()
            st.rerun()

    # Selected day detail
    sel_date_str = st.session_state.get("hist_sel", today.isoformat())
    try:
        sel_date = date.fromisoformat(sel_date_str)
    except Exception:
        sel_date = today

    if sel_date < week_monday or sel_date > week_sunday:
        sel_date = today if (week_monday <= today <= week_sunday) else week_monday
        st.session_state["hist_sel"] = sel_date.isoformat()

    day_label = "היום" if sel_date == today else \
                f'{HEB_WD.get(sel_date.weekday(),"")} {sel_date.strftime("%d/%m/%Y")}'

    st.markdown(
        f'<div dir="rtl" style="margin-top:20px;margin-bottom:8px;font-size:0.95rem;'
        f'font-weight:800;color:#f4f6fb;border-right:3px solid #4f8ef7;padding-right:10px">'
        f'פירוט יום — {day_label}</div>',
        unsafe_allow_html=True,
    )

    # Food entries
    food_entries = food_repo.get_log(USER_ID, sel_date) or []
    totals = food_repo.get_totals(USER_ID, sel_date)
    MEAL_LABELS = {
        "BREAKFAST": "ארוחת בוקר", "MORNING_SNACK": "ביניים בוקר",
        "LUNCH": "ארוחת צהריים", "AFTERNOON_SNACK": "ביניים אחה״צ",
        "DINNER": "ארוחת ערב", "EVENING_SNACK": "ביניים ערב",
    }

    if food_entries:
        st.markdown(
            f'<div dir="rtl" style="font-size:0.78rem;color:#a0aec0;margin-bottom:4px">🍽️ תזונה</div>',
            unsafe_allow_html=True,
        )
        for fe in food_entries:
            meal_label = MEAL_LABELS.get(fe.meal_type, fe.meal_type)
            cal_v = round(fe.calories_consumed)
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:10px;'
                f'padding:8px 12px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center">'
                f'<div dir="rtl">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{fe.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70">{meal_label}</div>'
                f'</div>'
                f'<div dir="rtl" style="font-size:0.85rem;font-weight:800;color:#4f8ef7">{cal_v} קק״ל</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div dir="rtl" style="text-align:left;font-size:0.75rem;color:#a0aec0;margin-bottom:12px">'
            f'סה״כ: <b style="color:#4f8ef7">{int(totals["calories"])} קק״ל</b> · '
            f'<b style="color:#a3e635">{round(totals["protein"],1)}ג׳ חלבון</b> · '
            f'<b style="color:#f59e0b">{round(totals["carbs"],1)}ג׳ פחמימות</b> · '
            f'<b style="color:#fb923c">{round(totals["fat"],1)}ג׳ שומן</b>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין רישומי תזונה ליום זה</div>',
            unsafe_allow_html=True,
        )

    # Water
    water_entries = water_repo.get_water_intakes_for_date(USER_ID, sel_date)
    total_water = int(sum(w.amount_ml for w in water_entries))
    st.markdown(
        f'<div dir="rtl" style="font-size:0.78rem;color:#a0aec0;margin-bottom:4px">💧 מים</div>',
        unsafe_allow_html=True,
    )
    if total_water > 0:
        st.markdown(
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:10px;'
            f'padding:8px 12px;margin-bottom:12px">'
            f'<span style="font-size:0.88rem;font-weight:800;color:#38bdf8">{total_water} מ״ל</span>'
            f'<span style="font-size:0.7rem;color:#545e70"> ({len(water_entries)} כוסות)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין רישומי מים ליום זה</div>',
            unsafe_allow_html=True,
        )

    # Workouts
    workout_data = workout_repo.get_workout_data(USER_ID)
    day_wos = workout_data.daily_log.get(sel_date.isoformat(), [])
    st.markdown(
        f'<div dir="rtl" style="font-size:0.78rem;color:#a0aec0;margin-bottom:4px">🏋️ אימונים</div>',
        unsafe_allow_html=True,
    )
    if day_wos:
        for wo in day_wos:
            wo_type = wo.get("type", "")
            wo_dur  = wo.get("duration_minutes", 0)
            wo_int  = wo.get("intensity", "")
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:10px;'
                f'padding:8px 12px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{wo_type}</div>'
                f'<div dir="rtl" style="font-size:0.75rem;color:#f59e0b">{wo_dur} דקות · {wo_int}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין רישומי אימונים ליום זה</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — WEEKLY PLANNER
# ══════════════════════════════════════════════════════════════════════════════
with tab_plan:

    plan = _load_plan()

    # Week navigation
    if "plan_woff" not in st.session_state:
        st.session_state["plan_woff"] = 0

    pw_col1, pw_col2, pw_col3 = st.columns([1, 3, 1])
    with pw_col1:
        if st.button("‹ קדימה", key="plan_prev", use_container_width=True):
            st.session_state["plan_woff"] += 1
    with pw_col3:
        if st.button("אחורה ›", key="plan_next", use_container_width=True):
            st.session_state["plan_woff"] -= 1

    pwoff = st.session_state["plan_woff"]
    plan_monday = _week_start(pwoff)
    plan_sunday = plan_monday + timedelta(days=6)

    with pw_col2:
        wlabel = f'{plan_monday.strftime("%d/%m")} – {plan_sunday.strftime("%d/%m/%Y")}'
        if pwoff == 0:
            wlabel = f"השבוע הנוכחי · {wlabel}"
        elif pwoff == 1:
            wlabel = f"שבוע הבא · {wlabel}"
        elif pwoff == -1:
            wlabel = f"שבוע שעבר · {wlabel}"
        else:
            wlabel = f"שבוע {pwoff:+d} · {wlabel}"
        st.markdown(
            f'<div dir="rtl" style="text-align:center;font-size:0.82rem;'
            f'color:#a0aec0;padding:6px 0">{wlabel}</div>',
            unsafe_allow_html=True,
        )

    plan_days = [plan_monday + timedelta(days=i) for i in range(7)]

    # Grid header
    ph_cols = st.columns(7)
    for i, col in enumerate(ph_cols):
        d = plan_days[i]
        is_today = (d == today)
        hdr_color = "#4f8ef7" if is_today else "#a0aec0"
        hdr_bg    = "#1e3a5f" if is_today else "transparent"
        col.markdown(
            f'<div dir="rtl" style="text-align:center;font-size:0.72rem;font-weight:700;'
            f'color:{hdr_color};background:{hdr_bg};border-radius:8px;padding:4px 2px">'
            f'{HEB_WD_SHORT[d.weekday()]}<br>'
            f'<span style="font-size:0.9rem;font-weight:900">{d.day}</span></div>',
            unsafe_allow_html=True,
        )

    # Grid cells with planned meals/workouts dots
    if "plan_sel" not in st.session_state:
        st.session_state["plan_sel"] = today.isoformat()

    pc_cols = st.columns(7)
    for i, col in enumerate(pc_cols):
        d = plan_days[i]
        day_plan = plan.get(d.isoformat(), {})
        meals    = day_plan.get("meals", [])
        workouts = day_plan.get("workouts", [])
        is_sel   = (d.isoformat() == st.session_state["plan_sel"])
        border   = "2px solid #4f8ef7" if is_sel else "1px solid #252d3d"
        cell_bg  = "#1a2540" if is_sel else "#161b26"

        meal_dots = "".join(
            ['<span style="color:#a3e635;font-size:0.65rem">🍽️</span>'] * min(len(meals), 3)
        )
        wo_dots = "".join(
            ['<span style="color:#f59e0b;font-size:0.65rem">🏋️</span>'] * min(len(workouts), 2)
        )
        count_txt = ""
        if meals or workouts:
            parts = []
            if meals:
                parts.append(f"{len(meals)} א׳")
            if workouts:
                parts.append(f"{len(workouts)} א\"מ")
            count_txt = " · ".join(parts)

        col.markdown(
            f'<div dir="rtl" style="background:{cell_bg};border:{border};border-radius:12px;'
            f'padding:6px 4px;text-align:center;min-height:80px;'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px">'
            f'<div>{meal_dots}{wo_dots}</div>'
            f'<div dir="rtl" style="font-size:0.55rem;color:#545e70">{count_txt if count_txt else "ריק"}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if col.button("בחר", key=f"psel_{d.isoformat()}", use_container_width=True):
            st.session_state["plan_sel"] = d.isoformat()
            st.rerun()

    # Ensure selected day is in current plan week
    psel_str = st.session_state.get("plan_sel", today.isoformat())
    try:
        psel_date = date.fromisoformat(psel_str)
    except Exception:
        psel_date = today

    if not (plan_monday <= psel_date <= plan_sunday):
        psel_date = today if (plan_monday <= today <= plan_sunday) else plan_monday
        st.session_state["plan_sel"] = psel_date.isoformat()

    pday_label = "היום" if psel_date == today else \
                 f'{HEB_WD.get(psel_date.weekday(),"")} {psel_date.strftime("%d/%m/%Y")}'

    st.markdown(
        f'<div dir="rtl" style="margin-top:20px;margin-bottom:8px;font-size:0.95rem;'
        f'font-weight:800;color:#f4f6fb;border-right:3px solid #a3e635;padding-right:10px">'
        f'תכנון יום — {pday_label}</div>',
        unsafe_allow_html=True,
    )

    pday_key = psel_date.isoformat()
    if pday_key not in plan:
        plan[pday_key] = {"meals": [], "workouts": []}
    day_plan = plan[pday_key]

    # ── Planned meals ──────────────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="font-size:0.78rem;color:#a3e635;margin-bottom:6px;font-weight:700">🍽️ ארוחות מתוכננות</div>',
        unsafe_allow_html=True,
    )

    MEAL_TYPE_OPTIONS = {
        "BREAKFAST": "ארוחת בוקר", "MORNING_SNACK": "ביניים בוקר",
        "LUNCH": "ארוחת צהריים", "AFTERNOON_SNACK": "ביניים אחה״צ",
        "DINNER": "ארוחת ערב", "EVENING_SNACK": "ביניים ערב",
    }

    meals = day_plan.get("meals", [])
    if meals:
        for mi, meal in enumerate(meals):
            mtype = MEAL_TYPE_OPTIONS.get(meal.get("type", ""), meal.get("type", ""))
            mname = meal.get("name", "")
            mcal  = meal.get("calories", 0)
            m_col1, m_col2 = st.columns([5, 1])
            m_col1.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #1e3a1e;border-radius:10px;'
                f'padding:8px 12px">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{mname}</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70">{mtype}'
                f'{" · " + str(mcal) + " קק״ל" if mcal else ""}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if m_col2.button("🗑", key=f"del_meal_{pday_key}_{mi}"):
                plan[pday_key]["meals"].pop(mi)
                _save_plan(plan)
                st.rerun()
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין ארוחות מתוכננות</div>',
            unsafe_allow_html=True,
        )

    # Add meal expander
    with st.expander("➕ הוסף ארוחה"):
        with st.form(f"add_meal_form_{pday_key}", clear_on_submit=True):
            new_meal_name = st.text_input("שם המנה / מאכל", key=f"mn_{pday_key}")
            new_meal_type = st.selectbox(
                "סוג ארוחה",
                options=list(MEAL_TYPE_OPTIONS.keys()),
                format_func=lambda x: MEAL_TYPE_OPTIONS[x],
                key=f"mt_{pday_key}",
            )
            new_meal_cal = st.number_input("קלוריות משוערות", min_value=0, max_value=3000,
                                           step=50, value=0, key=f"mc_{pday_key}")
            if st.form_submit_button("הוסף ארוחה ✓"):
                if new_meal_name.strip():
                    if pday_key not in plan:
                        plan[pday_key] = {"meals": [], "workouts": []}
                    plan[pday_key]["meals"].append({
                        "name": new_meal_name.strip(),
                        "type": new_meal_type,
                        "calories": int(new_meal_cal),
                    })
                    _save_plan(plan)
                    st.success("הארוחה נוספה!")
                    st.rerun()

    # ── Planned workouts ───────────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="font-size:0.78rem;color:#f59e0b;margin-top:16px;margin-bottom:6px;font-weight:700">🏋️ אימונים מתוכננים</div>',
        unsafe_allow_html=True,
    )

    WORKOUT_TYPES = ["ריצה", "הליכה", "אופניים", "שחייה", "כוח", "יוגה", "פילאטיס", "HIIT", "אחר"]
    INTENSITY_OPTIONS = {"LOW": "נמוכה", "MODERATE": "בינונית", "HIGH": "גבוהה"}

    workouts = day_plan.get("workouts", [])
    if workouts:
        for wi, wo in enumerate(workouts):
            wtype = wo.get("type", "")
            wdur  = wo.get("duration_minutes", 0)
            wint  = INTENSITY_OPTIONS.get(wo.get("intensity", ""), wo.get("intensity", ""))
            w_col1, w_col2 = st.columns([5, 1])
            w_col1.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #3a2e10;border-radius:10px;'
                f'padding:8px 12px">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{wtype}</div>'
                f'<div dir="rtl" style="font-size:0.68rem;color:#545e70">{wdur} דקות · {wint}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if w_col2.button("🗑", key=f"del_wo_{pday_key}_{wi}"):
                plan[pday_key]["workouts"].pop(wi)
                _save_plan(plan)
                st.rerun()
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין אימונים מתוכננים</div>',
            unsafe_allow_html=True,
        )

    # Add workout expander
    with st.expander("➕ הוסף אימון"):
        with st.form(f"add_wo_form_{pday_key}", clear_on_submit=True):
            new_wo_type = st.selectbox("סוג אימון", WORKOUT_TYPES, key=f"wt_{pday_key}")
            wf1, wf2 = st.columns(2)
            new_wo_dur = wf1.number_input("משך (דקות)", min_value=5, max_value=300,
                                          step=5, value=45, key=f"wd_{pday_key}")
            new_wo_int = wf2.selectbox("עצימות",
                                       options=list(INTENSITY_OPTIONS.keys()),
                                       format_func=lambda x: INTENSITY_OPTIONS[x],
                                       key=f"wi_{pday_key}")
            if st.form_submit_button("הוסף אימון ✓"):
                if pday_key not in plan:
                    plan[pday_key] = {"meals": [], "workouts": []}
                plan[pday_key]["workouts"].append({
                    "type": new_wo_type,
                    "duration_minutes": int(new_wo_dur),
                    "intensity": new_wo_int,
                })
                _save_plan(plan)
                st.success("האימון נוסף!")
                st.rerun()

    # ── Weekly summary strip ───────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="margin-top:24px;margin-bottom:6px;font-size:0.78rem;'
        'color:#a0aec0;font-weight:700">סיכום שבועי מתוכנן</div>',
        unsafe_allow_html=True,
    )

    total_planned_cal  = 0
    total_planned_wos  = 0
    total_planned_meals = 0
    for d in plan_days:
        dp = plan.get(d.isoformat(), {})
        total_planned_meals += len(dp.get("meals", []))
        total_planned_wos   += len(dp.get("workouts", []))
        for m in dp.get("meals", []):
            total_planned_cal += m.get("calories", 0)

    st.markdown(
        f'<div dir="rtl" style="display:flex;gap:8px;margin-bottom:24px">'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#a3e635">{total_planned_meals}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">ארוחות מתוכננות</div></div>'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#f59e0b">{total_planned_wos}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">אימונים מתוכננים</div></div>'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#4f8ef7">{total_planned_cal}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">קק״ל מתוכנן</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("history")
