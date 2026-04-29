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

# ── Calendar cell CSS (targets ONLY 7-column grids via :has selector) ──────────
st.markdown("""<style>
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
>[data-testid="column"] {
    padding-left: 2px !important;
    padding-right: 2px !important;
    min-width: 0 !important;
}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
.stButton button {
    padding: 4px 1px !important;
    min-height: 80px !important;
    height: 80px !important;
    border-radius: 14px !important;
    width: 100% !important;
    line-height: 1.5 !important;
    font-size: 0.78rem !important;
}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
.stButton button p {
    white-space: pre-line !important;
    margin: 0 !important;
    text-align: center !important;
    font-size: 0.78rem !important;
    line-height: 1.5 !important;
}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
.stButton button[kind="primary"] {
    background: linear-gradient(160deg,#1e3a5f,#1a2e52) !important;
    border: 2px solid #4f8ef7 !important;
    color: #e8f0ff !important;
}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
.stButton button[kind="secondary"] {
    background: #161b26 !important;
    border: 1px solid #252d3d !important;
    color: #c8d0e0 !important;
}
</style>""", unsafe_allow_html=True)

USER_ID      = "ui_user_001"
workout_repo = WorkoutRepository()
water_repo   = WaterRepository()
food_repo    = FoodLogRepository()
today        = date.today()

HEB_WD = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי",
           4: "שישי", 5: "שבת", 6: "ראשון"}
HEB_WD_SHORT = {6: "א׳", 0: "ב׳", 1: "ג׳", 2: "ד׳", 3: "ה׳", 4: "ו׳", 5: "ש׳"}

CALORIE_TARGET = 2000

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


def _week_sunday(offset: int = 0) -> date:
    wd = today.weekday()
    days_since_sunday = (wd + 1) % 7
    return today - timedelta(days=days_since_sunday) + timedelta(weeks=offset)


def _cal_label(cal: int) -> str:
    """Return short calorie status text (no emoji)."""
    if cal == 0:
        return "—"
    elif cal >= CALORIE_TARGET * 0.85:
        return f"{cal}"
    elif cal >= CALORIE_TARGET * 0.45:
        return f"{cal}"
    else:
        return f"{cal}"


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;'
    f'padding:4px 2px 14px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb">היסטוריה ותכנון</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{today.strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

tab_hist, tab_plan = st.tabs(["היסטוריה", "תכנון שבועי"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HISTORY CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_hist:

    if "hist_woff" not in st.session_state:
        st.session_state["hist_woff"] = 0
    if "hist_sel" not in st.session_state:
        st.session_state["hist_sel"] = today.isoformat()

    # ── Week navigation ────────────────────────────────────────────────────────
    nav1, nav2, nav3 = st.columns([1, 4, 1])
    with nav1:
        if st.button("< קדימה", key="hist_prev", use_container_width=True):
            st.session_state["hist_woff"] += 1
            st.rerun()
    with nav3:
        if st.button("אחורה >", key="hist_next", use_container_width=True,
                     disabled=(st.session_state["hist_woff"] >= 0)):
            st.session_state["hist_woff"] -= 1
            st.rerun()

    woff        = st.session_state["hist_woff"]
    week_sunday = _week_sunday(woff)
    week_days   = [week_sunday + timedelta(days=i) for i in range(7)]
    week_end    = week_sunday + timedelta(days=6)

    with nav2:
        wlabel = f'{week_sunday.strftime("%d/%m")} – {week_end.strftime("%d/%m/%Y")}'
        if woff == 0:
            wlabel = f"השבוע · {wlabel}"
        elif woff == -1:
            wlabel = f"שבוע שעבר · {wlabel}"
        else:
            wlabel = f"לפני {abs(woff)} שבועות · {wlabel}"
        st.markdown(
            f'<div dir="rtl" style="text-align:center;font-size:0.8rem;color:#a0aec0;padding:4px 0">'
            f'{wlabel}</div>',
            unsafe_allow_html=True,
        )

    # ── Build week data ────────────────────────────────────────────────────────
    week_data = []
    workout_data_all = workout_repo.get_workout_data(USER_ID)
    for d in week_days:
        cal = int(food_repo.get_totals(USER_ID, d)["calories"])
        wtr = int(sum(w.amount_ml for w in water_repo.get_water_intakes_for_date(USER_ID, d)))
        wos = len(workout_data_all.daily_log.get(d.isoformat(), []))
        week_data.append({"date": d, "cal": cal, "wtr": wtr, "wos": wos})

    # ── 7-column calendar grid ─────────────────────────────────────────────────
    day_cols = st.columns(7, gap="small")
    for i, col in enumerate(day_cols):
        row        = week_data[i]
        d          = row["date"]
        is_sel     = (d.isoformat() == st.session_state["hist_sel"])
        is_today_d = (d == today)

        day_name   = HEB_WD_SHORT[d.weekday()]
        today_mark = " *" if is_today_d else ""

        # Line 3: calorie count + activity abbreviations
        cal_txt  = str(row["cal"]) if row["cal"] > 0 else "—"
        activity = ""
        if row["wtr"] > 0: activity += " מ"
        if row["wos"] > 0: activity += " כ"
        line3 = cal_txt + activity

        label    = f"{day_name}{today_mark}\n{d.day}\n{line3}"
        btn_type = "primary" if is_sel else "secondary"
        if col.button(label, key=f"hsel_{d.isoformat()}",
                      type=btn_type, use_container_width=True):
            st.session_state["hist_sel"] = d.isoformat()
            st.rerun()

    # ── Legend ─────────────────────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="display:flex;gap:16px;justify-content:center;'
        'font-size:0.62rem;color:#545e70;margin:6px 0 16px">'
        '<span>* = היום</span>'
        '<span>מ = מים</span>'
        '<span>כ = כושר</span>'
        '<span>— = אין נתונים</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Ensure selected day is in the current week ─────────────────────────────
    sel_date_str = st.session_state.get("hist_sel", today.isoformat())
    try:
        sel_date = date.fromisoformat(sel_date_str)
    except Exception:
        sel_date = today
    if not (week_sunday <= sel_date <= week_end):
        sel_date = today if (week_sunday <= today <= week_end) else week_sunday
        st.session_state["hist_sel"] = sel_date.isoformat()

    # ── Selected day detail ────────────────────────────────────────────────────
    day_label = "היום" if sel_date == today else \
                f'{HEB_WD.get(sel_date.weekday(), "")} {sel_date.strftime("%d/%m/%Y")}'

    st.markdown(
        f'<div dir="rtl" style="margin-bottom:10px;font-size:0.95rem;font-weight:800;'
        f'color:#f4f6fb;border-right:3px solid #4f8ef7;padding-right:10px">'
        f'פירוט יום — {day_label}</div>',
        unsafe_allow_html=True,
    )

    MEAL_LABELS = {
        "BREAKFAST": "ארוחת בוקר", "MORNING_SNACK": "ביניים בוקר",
        "LUNCH": "ארוחת צהריים", "AFTERNOON_SNACK": "ביניים אחה״צ",
        "DINNER": "ארוחת ערב", "EVENING_SNACK": "ביניים ערב",
    }

    # Food
    food_entries = food_repo.get_log(USER_ID, sel_date) or []
    totals = food_repo.get_totals(USER_ID, sel_date)
    st.markdown(
        '<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;margin-bottom:4px;font-weight:700">תזונה</div>',
        unsafe_allow_html=True,
    )
    if food_entries:
        for fe in food_entries:
            meal_label = MEAL_LABELS.get(fe.meal_type, fe.meal_type)
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                f'border-radius:10px;padding:8px 12px;margin-bottom:4px;'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<div dir="rtl">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{fe.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.67rem;color:#545e70">{meal_label}</div>'
                f'</div>'
                f'<div dir="rtl" style="font-size:0.85rem;font-weight:800;color:#4f8ef7">'
                f'{round(fe.calories)} קק״ל</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div dir="rtl" style="font-size:0.72rem;color:#a0aec0;margin-bottom:12px">'
            f'סה״כ: <b style="color:#4f8ef7">{int(totals["calories"])} קק״ל</b> · '
            f'<b style="color:#a3e635">{round(totals["protein"],1)}ג׳ חלבון</b> · '
            f'<b style="color:#f59e0b">{round(totals["carbs"],1)}ג׳ פחמ׳</b> · '
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
    st.markdown(
        '<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;margin-bottom:4px;font-weight:700">מים</div>',
        unsafe_allow_html=True,
    )
    water_entries = water_repo.get_water_intakes_for_date(USER_ID, sel_date)
    total_water   = int(sum(w.amount_ml for w in water_entries))
    if total_water > 0:
        st.markdown(
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
            f'border-radius:10px;padding:8px 12px;margin-bottom:8px">'
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
    st.markdown(
        '<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;margin-bottom:4px;font-weight:700">אימונים</div>',
        unsafe_allow_html=True,
    )
    day_wos = workout_data_all.daily_log.get(sel_date.isoformat(), [])
    if day_wos:
        for wo in day_wos:
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                f'border-radius:10px;padding:8px 12px;margin-bottom:4px;'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">'
                f'{wo.get("type","")}</div>'
                f'<div dir="rtl" style="font-size:0.75rem;color:#f59e0b">'
                f'{wo.get("duration_minutes",0)} דקות · {wo.get("intensity","")}</div>'
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

    if "plan_woff" not in st.session_state:
        st.session_state["plan_woff"] = 0
    if "plan_sel" not in st.session_state:
        st.session_state["plan_sel"] = today.isoformat()

    # ── Week navigation ────────────────────────────────────────────────────────
    pn1, pn2, pn3 = st.columns([1, 4, 1])
    with pn1:
        if st.button("< קדימה", key="plan_prev", use_container_width=True):
            st.session_state["plan_woff"] += 1
            st.rerun()
    with pn3:
        if st.button("אחורה >", key="plan_next", use_container_width=True):
            st.session_state["plan_woff"] -= 1
            st.rerun()

    pwoff       = st.session_state["plan_woff"]
    plan_sunday = _week_sunday(pwoff)
    plan_days   = [plan_sunday + timedelta(days=i) for i in range(7)]
    plan_end    = plan_sunday + timedelta(days=6)

    with pn2:
        wlabel = f'{plan_sunday.strftime("%d/%m")} – {plan_end.strftime("%d/%m/%Y")}'
        if pwoff == 0:    wlabel = f"השבוע · {wlabel}"
        elif pwoff == 1:  wlabel = f"שבוע הבא · {wlabel}"
        elif pwoff == -1: wlabel = f"שבוע שעבר · {wlabel}"
        else:             wlabel = f"שבוע {pwoff:+d} · {wlabel}"
        st.markdown(
            f'<div dir="rtl" style="text-align:center;font-size:0.8rem;color:#a0aec0;padding:4px 0">'
            f'{wlabel}</div>',
            unsafe_allow_html=True,
        )

    # ── 7-column planner grid ──────────────────────────────────────────────────
    plan_cols = st.columns(7, gap="small")
    for i, col in enumerate(plan_cols):
        d          = plan_days[i]
        dp         = plan.get(d.isoformat(), {})
        n_meals    = len(dp.get("meals", []))
        n_wos      = len(dp.get("workouts", []))
        is_sel     = (d.isoformat() == st.session_state["plan_sel"])
        is_today_d = (d == today)

        day_name   = HEB_WD_SHORT[d.weekday()]
        today_mark = " *" if is_today_d else ""

        if n_meals == 0 and n_wos == 0:
            content_line = "ריק"
        else:
            parts = []
            if n_meals: parts.append(f"א{n_meals}")
            if n_wos:   parts.append(f"כ{n_wos}")
            content_line = " ".join(parts)

        label    = f"{day_name}{today_mark}\n{d.day}\n{content_line}"
        btn_type = "primary" if is_sel else "secondary"
        if col.button(label, key=f"psel_{d.isoformat()}",
                      type=btn_type, use_container_width=True):
            st.session_state["plan_sel"] = d.isoformat()
            st.rerun()

    # ── Ensure selected day is in current plan week ────────────────────────────
    psel_str = st.session_state.get("plan_sel", today.isoformat())
    try:
        psel_date = date.fromisoformat(psel_str)
    except Exception:
        psel_date = today
    if not (plan_sunday <= psel_date <= plan_end):
        psel_date = today if (plan_sunday <= today <= plan_end) else plan_sunday
        st.session_state["plan_sel"] = psel_date.isoformat()

    pday_key   = psel_date.isoformat()
    pday_label = "היום" if psel_date == today else \
                 f'{HEB_WD.get(psel_date.weekday(), "")} {psel_date.strftime("%d/%m/%Y")}'

    st.markdown(
        f'<div dir="rtl" style="margin-top:14px;margin-bottom:10px;font-size:0.95rem;'
        f'font-weight:800;color:#f4f6fb;border-right:3px solid #a3e635;padding-right:10px">'
        f'תכנון יום — {pday_label}</div>',
        unsafe_allow_html=True,
    )

    if pday_key not in plan:
        plan[pday_key] = {"meals": [], "workouts": []}
    day_plan = plan[pday_key]

    MEAL_TYPE_OPTIONS = {
        "BREAKFAST": "ארוחת בוקר", "MORNING_SNACK": "ביניים בוקר",
        "LUNCH": "ארוחת צהריים", "AFTERNOON_SNACK": "ביניים אחה״צ",
        "DINNER": "ארוחת ערב", "EVENING_SNACK": "ביניים ערב",
    }
    WORKOUT_TYPES     = ["ריצה", "הליכה", "אופניים", "שחייה", "כוח", "יוגה", "פילאטיס", "HIIT", "אחר"]
    INTENSITY_OPTIONS = {"LOW": "נמוכה", "MODERATE": "בינונית", "HIGH": "גבוהה"}

    # ── Planned meals ──────────────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="font-size:0.78rem;color:#a3e635;margin-bottom:6px;font-weight:700">'
        'ארוחות מתוכננות</div>',
        unsafe_allow_html=True,
    )
    meals = day_plan.get("meals", [])
    if meals:
        for mi, meal in enumerate(meals):
            mtype = MEAL_TYPE_OPTIONS.get(meal.get("type", ""), meal.get("type", ""))
            mname = meal.get("name", "")
            mcal  = meal.get("calories", 0)
            mc1, mc2 = st.columns([5, 1])
            mc1.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #1e3a1e;'
                f'border-radius:10px;padding:8px 12px">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{mname}</div>'
                f'<div dir="rtl" style="font-size:0.67rem;color:#545e70">{mtype}'
                f'{" · " + str(mcal) + " קק״ל" if mcal else ""}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if mc2.button("×", key=f"del_meal_{pday_key}_{mi}"):
                plan[pday_key]["meals"].pop(mi)
                _save_plan(plan)
                st.rerun()
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:6px">אין ארוחות מתוכננות</div>',
            unsafe_allow_html=True,
        )

    with st.expander("+ הוסף ארוחה"):
        with st.form(f"add_meal_{pday_key}", clear_on_submit=True):
            nm_name = st.text_input("שם המנה / מאכל", key=f"mn_{pday_key}")
            nm_type = st.selectbox("סוג ארוחה",
                                   options=list(MEAL_TYPE_OPTIONS.keys()),
                                   format_func=lambda x: MEAL_TYPE_OPTIONS[x],
                                   key=f"mt_{pday_key}")
            nm_cal  = st.number_input("קלוריות משוערות", 0, 3000, 0, 50, key=f"mc_{pday_key}")
            if st.form_submit_button("הוסף"):
                if nm_name.strip():
                    plan[pday_key]["meals"].append({
                        "name": nm_name.strip(), "type": nm_type, "calories": int(nm_cal)
                    })
                    _save_plan(plan)
                    st.success("הארוחה נוספה!")
                    st.rerun()

    # ── Planned workouts ───────────────────────────────────────────────────────
    st.markdown(
        '<div dir="rtl" style="font-size:0.78rem;color:#f59e0b;margin-top:14px;'
        'margin-bottom:6px;font-weight:700">אימונים מתוכננים</div>',
        unsafe_allow_html=True,
    )
    workouts = day_plan.get("workouts", [])
    if workouts:
        for wi, wo in enumerate(workouts):
            wtype = wo.get("type", "")
            wdur  = wo.get("duration_minutes", 0)
            wint  = INTENSITY_OPTIONS.get(wo.get("intensity", ""), wo.get("intensity", ""))
            wc1, wc2 = st.columns([5, 1])
            wc1.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #3a2e10;'
                f'border-radius:10px;padding:8px 12px">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{wtype}</div>'
                f'<div dir="rtl" style="font-size:0.67rem;color:#545e70">{wdur} דקות · {wint}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if wc2.button("×", key=f"del_wo_{pday_key}_{wi}"):
                plan[pday_key]["workouts"].pop(wi)
                _save_plan(plan)
                st.rerun()
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:6px">אין אימונים מתוכננים</div>',
            unsafe_allow_html=True,
        )

    with st.expander("+ הוסף אימון"):
        with st.form(f"add_wo_{pday_key}", clear_on_submit=True):
            nw_type = st.selectbox("סוג אימון", WORKOUT_TYPES, key=f"wt_{pday_key}")
            wf1, wf2 = st.columns(2)
            nw_dur  = wf1.number_input("משך (דקות)", 5, 300, 45, 5, key=f"wd_{pday_key}")
            nw_int  = wf2.selectbox("עצימות",
                                    options=list(INTENSITY_OPTIONS.keys()),
                                    format_func=lambda x: INTENSITY_OPTIONS[x],
                                    key=f"wi_{pday_key}")
            if st.form_submit_button("הוסף"):
                plan[pday_key]["workouts"].append({
                    "type": nw_type, "duration_minutes": int(nw_dur), "intensity": nw_int
                })
                _save_plan(plan)
                st.success("האימון נוסף!")
                st.rerun()

    # ── Weekly summary ─────────────────────────────────────────────────────────
    total_pm = total_pw = total_pc = 0
    for d in plan_days:
        dp = plan.get(d.isoformat(), {})
        total_pm += len(dp.get("meals", []))
        total_pw += len(dp.get("workouts", []))
        for m in dp.get("meals", []):
            total_pc += m.get("calories", 0)

    st.markdown(
        f'<div dir="rtl" style="display:flex;gap:8px;margin-top:20px;margin-bottom:24px">'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;'
        f'border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#a3e635">{total_pm}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">ארוחות</div></div>'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;'
        f'border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#f59e0b">{total_pw}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">אימונים</div></div>'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;'
        f'border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#4f8ef7">{total_pc}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">קק״ל מתוכנן</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("history")
