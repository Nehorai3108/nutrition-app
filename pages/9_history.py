#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""9_history.py — היסטוריה ותכנון שבועי"""

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

HEB_WD       = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}
HEB_WD_SHORT = {6:"א׳",0:"ב׳",1:"ג׳",2:"ד׳",3:"ה׳",4:"ו׳",5:"ש׳"}
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


# ── State entirely from query params (survives HTML link navigation) ───────────
_qp  = st.query_params
mode = _qp.get("mode", "history")          # "history" | "plan"
woff = int(_qp.get("woff", "0"))
sel_day = _qp.get("day", today.isoformat())

week_sunday = _week_sunday(woff)
week_days   = [week_sunday + timedelta(days=i) for i in range(7)]
week_end    = week_sunday + timedelta(days=6)

# Clamp selected day to current week
try:
    sel_date = date.fromisoformat(sel_day)
except Exception:
    sel_date = today
if not (week_sunday <= sel_date <= week_end):
    sel_date = today if (week_sunday <= today <= week_end) else week_sunday
    sel_day  = sel_date.isoformat()

# ── Fetch week data ────────────────────────────────────────────────────────────
workout_data_all = workout_repo.get_workout_data(USER_ID)
week_data = {}
for d in week_days:
    cal = int(food_repo.get_totals(USER_ID, d)["calories"])
    wtr = int(sum(w.amount_ml for w in water_repo.get_water_intakes_for_date(USER_ID, d)))
    wos = len(workout_data_all.daily_log.get(d.isoformat(), []))
    week_data[d.isoformat()] = {"cal": cal, "wtr": wtr, "wos": wos}

plan = _load_plan()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;'
    f'padding:4px 2px 10px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb">היסטוריה ותכנון</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{today.strftime("%d/%m/%Y")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Mode toggle (buttons update query params) ──────────────────────────────────
m1, m2 = st.columns(2)
if m1.button("היסטוריה",
             type="primary" if mode == "history" else "secondary",
             use_container_width=True, key="btn_mode_hist"):
    st.query_params.update({"mode": "history", "woff": str(woff), "day": sel_day})
    st.rerun()
if m2.button("תכנון שבועי",
             type="primary" if mode == "plan" else "secondary",
             use_container_width=True, key="btn_mode_plan"):
    st.query_params.update({"mode": "plan", "woff": str(woff), "day": sel_day})
    st.rerun()

# ── Week navigation ────────────────────────────────────────────────────────────
n1, n2, n3 = st.columns([1, 4, 1])
with n1:
    if st.button("< קדימה", key="nav_prev", use_container_width=True):
        nw = woff + 1
        nd = (sel_date + timedelta(weeks=1)).isoformat()
        st.query_params.update({"mode": mode, "woff": str(nw), "day": nd})
        st.rerun()
with n3:
    if st.button("אחורה >", key="nav_next", use_container_width=True,
                 disabled=(mode == "history" and woff >= 0)):
        nw = woff - 1
        nd = (sel_date - timedelta(weeks=1)).isoformat()
        st.query_params.update({"mode": mode, "woff": str(nw), "day": nd})
        st.rerun()
with n2:
    if woff == 0:    wl = "השבוע"
    elif woff == -1: wl = "שבוע שעבר"
    elif woff == 1:  wl = "שבוע הבא"
    elif woff < 0:   wl = f"לפני {abs(woff)} שבועות"
    else:            wl = f"שבוע +{woff}"
    wl += f' · {week_sunday.strftime("%d/%m")} – {week_end.strftime("%d/%m")}'
    st.markdown(
        f'<div dir="rtl" style="text-align:center;font-size:0.78rem;color:#a0aec0;padding:5px 0">'
        f'{wl}</div>',
        unsafe_allow_html=True,
    )

# ── Calendar HTML grid (pure HTML — looks like a real calendar) ────────────────
def _bar_color(cal: int) -> str:
    if cal == 0:                        return "#2d3748"
    if cal >= CALORIE_TARGET * 0.85:    return "#22c55e"
    if cal >= CALORIE_TARGET * 0.45:    return "#f59e0b"
    return "#ef4444"


def _build_calendar() -> str:
    cells = ""
    for d in week_days:
        dk      = d.isoformat()
        row     = week_data[dk]
        is_sel  = (dk == sel_day)
        is_tod  = (d == today)

        # Cell border & background
        if is_sel:
            cell_bg  = "#172440"
            cell_bdr = "2px solid #4f8ef7"
        elif is_tod:
            cell_bg  = "#161f2e"
            cell_bdr = "1px solid #2a3f5f"
        else:
            cell_bg  = "#161b26"
            cell_bdr = "1px solid #252d3d"

        # Date circle
        if is_sel:
            circ_bg    = "#4f8ef7"
            circ_color = "#ffffff"
            circ_bdr   = "none"
        elif is_tod:
            circ_bg    = "#0d0f14"
            circ_color = "#4f8ef7"
            circ_bdr   = "2px solid #4f8ef7"
        else:
            circ_bg    = "#1e2535"
            circ_color = "#e0e6f0"
            circ_bdr   = "none"

        # Bottom content
        if mode == "history":
            cal_val = row["cal"]
            bar_pct = min(cal_val / CALORIE_TARGET, 1.0) * 100 if cal_val > 0 else 0
            bar_col = _bar_color(cal_val)
            cal_txt = str(cal_val) if cal_val > 0 else "—"
            act     = ("מ " if row["wtr"] > 0 else "") + ("כ" if row["wos"] > 0 else "")
            bottom  = f"""
              <div style="font-size:0.58rem;color:#a0aec0;line-height:1">{cal_txt}</div>
              <div style="width:75%;height:3px;background:#1e2535;border-radius:2px;overflow:hidden;margin:1px 0">
                <div style="width:{bar_pct:.0f}%;height:100%;background:{bar_col}"></div>
              </div>
              <div style="font-size:0.52rem;color:#545e70;min-height:9px">{act}</div>
            """
        else:
            dp      = plan.get(dk, {})
            n_m     = len(dp.get("meals", []))
            n_w     = len(dp.get("workouts", []))
            if n_m == 0 and n_w == 0:
                ptxt = "—"; pcol = "#3a4255"
            else:
                parts = []
                if n_m: parts.append(f"א{n_m}")
                if n_w: parts.append(f"כ{n_w}")
                ptxt = " ".join(parts); pcol = "#a3e635"
            bottom  = f"""
              <div style="font-size:0.6rem;color:{pcol};font-weight:700;margin-top:4px">{ptxt}</div>
            """

        link = f"?mode={mode}&woff={woff}&day={dk}"
        cells += f"""
        <a href="{link}" style="text-decoration:none;display:block">
          <div style="background:{cell_bg};border:{cell_bdr};border-radius:12px;
                      padding:7px 2px 5px;text-align:center;
                      display:flex;flex-direction:column;align-items:center;
                      justify-content:flex-start;gap:3px;min-height:92px;
                      transition:border-color .15s">
            <div style="font-size:0.6rem;color:#6b7a94;font-weight:700;letter-spacing:.3px">
              {HEB_WD_SHORT[d.weekday()]}
            </div>
            <div style="width:30px;height:30px;border-radius:50%;
                        background:{circ_bg};border:{circ_bdr};
                        display:flex;align-items:center;justify-content:center;
                        font-size:0.9rem;font-weight:900;color:{circ_color}">
              {d.day}
            </div>
            {bottom}
          </div>
        </a>
        """

    return (
        '<div style="display:grid;grid-template-columns:repeat(7,minmax(0,1fr));'
        'gap:5px;direction:rtl;margin:4px 0 6px">'
        + cells + "</div>"
    )


st.markdown(_build_calendar(), unsafe_allow_html=True)

# ── Legend ─────────────────────────────────────────────────────────────────────
if mode == "history":
    st.markdown(
        '<div dir="rtl" style="display:flex;gap:14px;justify-content:center;'
        'font-size:0.6rem;color:#545e70;margin-bottom:12px">'
        '<span><span style="color:#22c55e">■</span> יעד</span>'
        '<span><span style="color:#f59e0b">■</span> חלקי</span>'
        '<span><span style="color:#ef4444">■</span> נמוך</span>'
        '<span>מ = מים &nbsp; כ = כושר</span>'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div dir="rtl" style="font-size:0.6rem;color:#545e70;'
        'text-align:center;margin-bottom:12px">א = ארוחות &nbsp; כ = כושר</div>',
        unsafe_allow_html=True,
    )

# ── Day title ──────────────────────────────────────────────────────────────────
day_label = "היום" if sel_date == today else \
            f'{HEB_WD.get(sel_date.weekday(), "")} {sel_date.strftime("%d/%m/%Y")}'

# ══════════════════════════════════════════════════════════════════════════════
# HISTORY DETAIL
# ══════════════════════════════════════════════════════════════════════════════
if mode == "history":
    st.markdown(
        f'<div dir="rtl" style="margin-bottom:10px;font-size:0.95rem;font-weight:800;'
        f'color:#f4f6fb;border-right:3px solid #4f8ef7;padding-right:10px">'
        f'פירוט יום — {day_label}</div>',
        unsafe_allow_html=True,
    )

    MEAL_LABELS = {
        "BREAKFAST": "ארוחת בוקר", "MORNING_SNACK": "ביניים בוקר",
        "LUNCH": "ארוחת צהריים",   "AFTERNOON_SNACK": "ביניים אחה״צ",
        "DINNER": "ארוחת ערב",     "EVENING_SNACK": "ביניים ערב",
    }

    # Food
    food_entries = food_repo.get_log(USER_ID, sel_date) or []
    totals       = food_repo.get_totals(USER_ID, sel_date)
    st.markdown(
        '<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;'
        'margin-bottom:4px;font-weight:700">תזונה</div>',
        unsafe_allow_html=True,
    )
    if food_entries:
        for fe in food_entries:
            ml = MEAL_LABELS.get(fe.meal_type, fe.meal_type)
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
                f'border-radius:10px;padding:8px 12px;margin-bottom:4px;'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<div dir="rtl">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">'
                f'{fe.food_name}</div>'
                f'<div dir="rtl" style="font-size:0.67rem;color:#545e70">{ml}</div>'
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
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">'
            'אין רישומי תזונה ליום זה</div>',
            unsafe_allow_html=True,
        )

    # Water
    st.markdown(
        '<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;'
        'margin-bottom:4px;font-weight:700">מים</div>',
        unsafe_allow_html=True,
    )
    water_entries = water_repo.get_water_intakes_for_date(USER_ID, sel_date)
    total_water   = int(sum(w.amount_ml for w in water_entries))
    if total_water > 0:
        st.markdown(
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;'
            f'border-radius:10px;padding:8px 12px;margin-bottom:8px">'
            f'<span style="font-size:0.88rem;font-weight:800;color:#38bdf8">'
            f'{total_water} מ״ל</span>'
            f'<span style="font-size:0.7rem;color:#545e70"> ({len(water_entries)} כוסות)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">'
            'אין רישומי מים ליום זה</div>',
            unsafe_allow_html=True,
        )

    # Workouts
    st.markdown(
        '<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;'
        'margin-bottom:4px;font-weight:700">אימונים</div>',
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
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">'
            'אין רישומי אימונים ליום זה</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# PLANNER DETAIL
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.markdown(
        f'<div dir="rtl" style="margin-bottom:10px;font-size:0.95rem;font-weight:800;'
        f'color:#f4f6fb;border-right:3px solid #a3e635;padding-right:10px">'
        f'תכנון יום — {day_label}</div>',
        unsafe_allow_html=True,
    )

    pday_key = sel_date.isoformat()
    if pday_key not in plan:
        plan[pday_key] = {"meals": [], "workouts": []}
    day_plan = plan[pday_key]

    MEAL_TYPE_OPTIONS = {
        "BREAKFAST": "ארוחת בוקר", "MORNING_SNACK": "ביניים בוקר",
        "LUNCH": "ארוחת צהריים",   "AFTERNOON_SNACK": "ביניים אחה״צ",
        "DINNER": "ארוחת ערב",     "EVENING_SNACK": "ביניים ערב",
    }
    WORKOUT_TYPES     = ["ריצה","הליכה","אופניים","שחייה","כוח","יוגה","פילאטיס","HIIT","אחר"]
    INTENSITY_OPTIONS = {"LOW": "נמוכה", "MODERATE": "בינונית", "HIGH": "גבוהה"}

    # Planned meals
    st.markdown(
        '<div dir="rtl" style="font-size:0.78rem;color:#a3e635;'
        'margin-bottom:6px;font-weight:700">ארוחות מתוכננות</div>',
        unsafe_allow_html=True,
    )
    meals = day_plan.get("meals", [])
    if meals:
        for mi, meal in enumerate(meals):
            mtype = MEAL_TYPE_OPTIONS.get(meal.get("type",""), meal.get("type",""))
            mname = meal.get("name","")
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
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:6px">'
            'אין ארוחות מתוכננות</div>',
            unsafe_allow_html=True,
        )

    with st.expander("+ הוסף ארוחה"):
        with st.form(f"add_meal_{pday_key}", clear_on_submit=True):
            nm_name = st.text_input("שם המנה", key=f"mn_{pday_key}")
            nm_type = st.selectbox("סוג ארוחה",
                                   options=list(MEAL_TYPE_OPTIONS.keys()),
                                   format_func=lambda x: MEAL_TYPE_OPTIONS[x],
                                   key=f"mt_{pday_key}")
            nm_cal  = st.number_input("קלוריות", 0, 3000, 0, 50, key=f"mc_{pday_key}")
            if st.form_submit_button("הוסף"):
                if nm_name.strip():
                    plan[pday_key]["meals"].append({
                        "name": nm_name.strip(), "type": nm_type, "calories": int(nm_cal)
                    })
                    _save_plan(plan)
                    st.success("נוסף!")
                    st.rerun()

    # Planned workouts
    st.markdown(
        '<div dir="rtl" style="font-size:0.78rem;color:#f59e0b;margin-top:14px;'
        'margin-bottom:6px;font-weight:700">אימונים מתוכננים</div>',
        unsafe_allow_html=True,
    )
    workouts = day_plan.get("workouts", [])
    if workouts:
        for wi, wo in enumerate(workouts):
            wtype = wo.get("type","")
            wdur  = wo.get("duration_minutes", 0)
            wint  = INTENSITY_OPTIONS.get(wo.get("intensity",""), wo.get("intensity",""))
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
            '<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:6px">'
            'אין אימונים מתוכננים</div>',
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
                st.success("נוסף!")
                st.rerun()

    # Weekly summary
    plan = _load_plan()
    total_pm = total_pw = total_pc = 0
    for d in week_days:
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
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">קק״ל</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("history")
