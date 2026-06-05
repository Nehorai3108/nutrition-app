#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""9_history.py — היסטוריה ותכנון שבועי"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta, datetime
from pathlib import Path
import streamlit as st

from ui.components import inject_global_css, bottom_nav
from ui.persistent_auth import setup_persistent_auth
from ui.user_auth import require_auth, logout_button
from nutrition_app.repositories.workout_repository import WorkoutRepository
from nutrition_app.repositories.water_repository import WaterRepository
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog

st.set_page_config(page_title="BiteFit · היסטוריה", page_icon=None, layout="wide",
                   initial_sidebar_state="collapsed")
inject_global_css()

with st.sidebar:
    st.markdown(f'<div style="font-size:0.75rem;color:#8892a4;padding:4px"> {st.session_state.get("bitefit_user", {}).get("email", "")}</div>', unsafe_allow_html=True)
    logout_button()

#  CSS: transform 7-col grid buttons into calendar cells 
st.markdown("""<style>
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
>[data-testid="column"] { padding-left:2px !important; padding-right:2px !important; }

[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
.stButton button {
    min-height:90px !important; height:90px !important;
    padding:4px 1px !important; border-radius:12px !important;
    width:100% !important; cursor:pointer !important;
}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
.stButton button p {
    white-space:pre-line !important; margin:0 !important;
    text-align:center !important; font-size:0.72rem !important;
    line-height:1.45 !important;
}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
button[kind="primary"] {
    background:#172440 !important; border:2px solid #4f8ef7 !important;
    color:#e8f0ff !important;
}
[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(7))
button[kind="secondary"] {
    background:#161b26 !important; border:1px solid #252d3d !important;
    color:#c0cce0 !important;
}
</style>""", unsafe_allow_html=True)

USER_ID      = require_auth()
workout_repo = WorkoutRepository()
water_repo   = WaterRepository()
food_repo    = FoodLogRepository()
today        = date.today()

@st.cache_resource
def _get_catalog():
    return FoodCatalog()

HEB_WD       = {0:"שני",1:"שלישי",2:"רביעי",3:"חמישי",4:"שישי",5:"שבת",6:"ראשון"}
HEB_WD_SHORT = {6:"א׳",0:"ב׳",1:"ג׳",2:"ד׳",3:"ה׳",4:"ו׳",5:"ש׳"}
CALORIE_TARGET = 2000

from nutrition_app.storage_paths import user_weekly_plan_file
PLAN_FILE = user_weekly_plan_file(USER_ID)


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


def _heat(cal: int) -> str:
    if cal == 0:                        return "—"
    if cal >= CALORIE_TARGET * 0.85:    return "יעד"
    if cal >= CALORIE_TARGET * 0.45:    return "חלקי"
    return "נמוך"


#  Session state (no URL params → no browser navigation) 
if "mode"    not in st.session_state: st.session_state["mode"]    = "history"
if "woff"    not in st.session_state: st.session_state["woff"]    = 0
if "sel_day" not in st.session_state: st.session_state["sel_day"] = today.isoformat()

mode    = st.session_state["mode"]
woff    = st.session_state["woff"]
sel_day = st.session_state["sel_day"]

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
    st.session_state["sel_day"] = sel_date.isoformat()
    sel_day = sel_date.isoformat()

#  Fetch week data 
workout_data_all = workout_repo.get_workout_data(USER_ID)
week_data = {}
for d in week_days:
    cal = int(food_repo.get_totals(USER_ID, d)["calories"])
    wtr = int(sum(w.amount_ml for w in water_repo.get_water_intakes_for_date(USER_ID, d)))
    wos = len(workout_data_all.daily_log.get(d.isoformat(), []))
    week_data[d.isoformat()] = {"cal": cal, "wtr": wtr, "wos": wos}

plan = _load_plan()

#  Header
st.markdown(
    f'<div dir="rtl" style="display:flex;align-items:center;justify-content:space-between;padding:4px 2px 10px">'
    f'<div dir="rtl" style="font-size:1.1rem;font-weight:800;color:#f4f6fb">יומן תזונה</div>'
    f'<div dir="rtl" style="font-size:0.75rem;color:#545e70">{today.strftime("%d/%m/%Y")}</div>'
    f'</div>', unsafe_allow_html=True,
)

# ── גרף קלוריות 7 ימים ──────────────────────────────────────────────────────
_target_cal = int(
    (lambda p: p.get("tdee") or p.get("calorie_target") or 2000)(
        __import__("nutrition_app.repositories.profile_repository",
                   fromlist=["ProfileRepository"]).ProfileRepository().load(USER_ID) or {}
    )
)

_graph_days  = [today - timedelta(days=i) for i in range(6, -1, -1)]
_graph_cals  = [int(food_repo.get_totals(USER_ID, d)["calories"]) for d in _graph_days]
_graph_labels = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","ש׳"]
_wd_to_heb   = {6:"א׳",0:"ב׳",1:"ג׳",2:"ד׳",3:"ה׳",4:"ו׳",5:"ש׳"}
_graph_labels = [_wd_to_heb[d.weekday()] for d in _graph_days]

_max_val = max(max(_graph_cals), _target_cal, 1)
_bars_html = ""
for i, (lbl, cal) in enumerate(zip(_graph_labels, _graph_cals)):
    _is_today = _graph_days[i] == today
    _pct      = min(cal / _max_val * 100, 100)
    _target_pct = min(_target_cal / _max_val * 100, 100)
    _color    = "#4f8ef7" if _is_today else ("#4ade80" if cal >= _target_cal * 0.85 else "#545e70")
    _border   = "2px solid #4f8ef7" if _is_today else "none"
    _bars_html += (
        f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">'
        f'<div style="font-size:0.6rem;color:{_color};font-weight:{"800" if _is_today else "500"}">'
        f'{"" if cal == 0 else str(cal)}</div>'
        f'<div style="width:100%;height:80px;background:#1a2235;border-radius:6px;'
        f'display:flex;align-items:flex-end;overflow:hidden;border:{_border}">'
        f'<div style="width:100%;height:{_pct:.0f}%;background:{_color};border-radius:4px;'
        f'transition:height 0.3s"></div></div>'
        f'<div style="font-size:0.62rem;color:{"#f4f6fb" if _is_today else "#545e70"}">{lbl}</div>'
        f'</div>'
    )

st.markdown(
    f'<div style="background:#161b26;border:1px solid #252d3d;border-radius:16px;'
    f'padding:14px 16px;margin-bottom:16px">'
    f'<div style="font-size:0.72rem;color:#8892a4;margin-bottom:10px;direction:rtl">'
    f'7 ימים אחרונים · יעד {_target_cal} קק"ל</div>'
    f'<div style="display:flex;gap:4px;align-items:flex-end">{_bars_html}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── הוסף מזון ───────────────────────────────────────────────────────────────
with st.expander("➕  הוסף מזון ליומן", expanded=False):
    _catalog = _get_catalog()
    _add_date = st.date_input("תאריך", value=today, key="add_food_date", format="DD/MM/YYYY")
    _meal_options = {
        "breakfast": "ארוחת בוקר",
        "morning_snack": "חטיף בוקר",
        "lunch": "ארוחת צהריים",
        "afternoon_snack": "חטיף אחה״צ",
        "dinner": "ארוחת ערב",
        "evening_snack": "חטיף ערב",
    }
    _meal_key = st.selectbox(
        "ארוחה",
        options=list(_meal_options.keys()),
        format_func=lambda k: _meal_options[k],
        key="add_food_meal",
    )
    _query = st.text_input("חיפוש מזון", placeholder="עוף, אורז, בננה...", key="add_food_query")

    _selected_food = None
    if _query.strip():
        _hits = _catalog.search_foods(_query.strip(), limit=6)
        if _hits:
            _food_labels = [f"{h.name_he} ({h.name_en})" for h in _hits]
            _chosen_idx  = st.selectbox("בחר מוצר", range(len(_food_labels)),
                                        format_func=lambda i: _food_labels[i],
                                        key="add_food_select")
            _selected_food = _hits[_chosen_idx]

            _n100 = _selected_food.nutrition_per_100g
            _grams = st.number_input(
                "כמות (גרמים)",
                min_value=1, max_value=2000, value=100, step=10,
                key="add_food_grams",
            )
            _ratio = _grams / 100.0
            _pcal  = round(_n100.calories_kcal * _ratio)
            _pprot = round(_n100.protein_g * _ratio, 1)
            _pcarb = round(_n100.carbs_g   * _ratio, 1)
            _pfat  = round(_n100.fat_g     * _ratio, 1)

            st.markdown(
                f'<div style="background:#0d1117;border-radius:10px;padding:10px 14px;'
                f'display:flex;gap:16px;font-size:0.82rem;direction:rtl;margin:6px 0">'
                f'<span style="color:#f4f6fb;font-weight:800">{_pcal} קק"ל</span>'
                f'<span style="color:#4f8ef7">{_pprot}ג חלבון</span>'
                f'<span style="color:#f59e0b">{_pcarb}ג פחמ׳</span>'
                f'<span style="color:#f472b6">{_pfat}ג שומן</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if st.button("הוסף ליומן", type="primary", use_container_width=True, key="add_food_btn"):
                food_repo.add_entry(USER_ID, _add_date, FoodLogEntry(
                    food_id=_selected_food.food_id,
                    food_name=_selected_food.name_he,
                    grams=float(_grams),
                    calories=float(_pcal),
                    protein=float(_pprot),
                    carbs=float(_pcarb),
                    fat=float(_pfat),
                    meal_type=_meal_key,
                    timestamp=datetime.now().isoformat(),
                ))
                st.success(f"נוסף: {_selected_food.name_he} · {_pcal} קק\"ל")
                st.rerun()
        else:
            st.markdown(
                f'<div style="color:#545e70;font-size:0.8rem;padding:8px">לא נמצא מזון עבור "{_query}"</div>',
                unsafe_allow_html=True,
            )

#  Mode toggle 
m1, m2 = st.columns(2)
if m1.button("היסטוריה", type="primary" if mode=="history" else "secondary",
             use_container_width=True, key="btn_hist"):
    st.session_state["mode"] = "history"
    st.rerun()
if m2.button("תכנון שבועי", type="primary" if mode=="plan" else "secondary",
             use_container_width=True, key="btn_plan"):
    st.session_state["mode"] = "plan"
    st.rerun()

#  Week navigation 
n1, n2, n3 = st.columns([1, 4, 1])
with n1:
    if st.button("< קדימה", key="nav_prev", use_container_width=True):
        st.session_state["woff"] += 1
        st.rerun()
with n3:
    if st.button("אחורה >", key="nav_next", use_container_width=True,
                 disabled=(mode == "history" and woff >= 0)):
        st.session_state["woff"] -= 1
        st.rerun()
with n2:
    if woff == 0:    wl = "השבוע"
    elif woff == -1: wl = "שבוע שעבר"
    elif woff == 1:  wl = "שבוע הבא"
    elif woff < 0:   wl = f"לפני {abs(woff)} שבועות"
    else:            wl = f"שבוע +{woff}"
    wl += f' · {week_sunday.strftime("%d/%m")} – {week_end.strftime("%d/%m")}'
    st.markdown(
        f'<div dir="rtl" style="text-align:center;font-size:0.78rem;color:#a0aec0;padding:5px 0">{wl}</div>',
        unsafe_allow_html=True,
    )

#  Calendar grid (pure st.button — no <a href>, no new tabs) 
cal_cols = st.columns(7, gap="small")
for i, col in enumerate(cal_cols):
    d   = week_days[i]
    dk  = d.isoformat()
    row = week_data[dk]
    is_sel = (dk == sel_day)
    is_tod = (d == today)

    today_mark = " " if is_tod else ""

    if mode == "history":
        heat = _heat(row["cal"])
        act  = ("מ" if row["wtr"] > 0 else "") + (" כ" if row["wos"] > 0 else "")
        line3 = heat
        line4 = act if act.strip() else " "
        label = f"{HEB_WD_SHORT[d.weekday()]}{today_mark}\n{d.day}\n{line3}\n{line4}"
    else:
        dp  = plan.get(dk, {})
        n_m = len(dp.get("meals", []))
        n_w = len(dp.get("workouts", []))
        parts = []
        if n_m: parts.append(f"א{n_m}")
        if n_w: parts.append(f"כ{n_w}")
        line3 = " ".join(parts) if parts else "—"
        label = f"{HEB_WD_SHORT[d.weekday()]}{today_mark}\n{d.day}\n{line3}"

    btn_type = "primary" if is_sel else "secondary"
    if col.button(label, key=f"cal_{dk}", type=btn_type, use_container_width=True):
        st.session_state["sel_day"] = dk
        st.rerun()

#  Legend 
if mode == "history":
    st.markdown(
        '<div dir="rtl" style="display:flex;gap:14px;justify-content:center;'
        'font-size:0.6rem;color:#545e70;margin-bottom:12px">'
        '<span>יעד = 85%+</span><span>חלקי = 45-85%</span>'
        '<span>נמוך = מתחת ל-45%</span><span>מ=מים כ=כושר</span>'
        '</div>', unsafe_allow_html=True,
    )

#  Day label 
day_label = "היום" if sel_date == today else \
            f'{HEB_WD.get(sel_date.weekday(),"")} {sel_date.strftime("%d/%m/%Y")}'

# 
# HISTORY DETAIL
# 
if mode == "history":
    st.markdown(
        f'<div dir="rtl" style="margin-bottom:10px;font-size:0.95rem;font-weight:800;'
        f'color:#f4f6fb;border-right:3px solid #4f8ef7;padding-right:10px">'
        f'פירוט יום — {day_label}</div>', unsafe_allow_html=True,
    )

    MEAL_LABELS = {
        "breakfast":"ארוחת בוקר","morning_snack":"ביניים בוקר",
        "lunch":"ארוחת צהריים","afternoon_snack":"ביניים אחה״צ",
        "dinner":"ארוחת ערב","evening_snack":"ביניים ערב",
        "snack":"נשנוש",
        # uppercase variants (legacy)
        "BREAKFAST":"ארוחת בוקר","MORNING_SNACK":"ביניים בוקר",
        "LUNCH":"ארוחת צהריים","AFTERNOON_SNACK":"ביניים אחה״צ",
        "DINNER":"ארוחת ערב","EVENING_SNACK":"ביניים ערב",
    }
    MEAL_COLORS = {
        "breakfast":"#f59e0b","morning_snack":"#a78bfa","lunch":"#4f8ef7",
        "afternoon_snack":"#34d399","dinner":"#f87171","evening_snack":"#818cf8",
        "snack":"#fb923c",
    }

    food_entries = food_repo.get_log(USER_ID, sel_date) or []
    totals       = food_repo.get_totals(USER_ID, sel_date)
    st.markdown('<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;margin-bottom:4px;font-weight:700">תזונה</div>', unsafe_allow_html=True)
    if food_entries:
        for fe in food_entries:
            ml = MEAL_LABELS.get(fe.meal_type.upper(), fe.meal_type)
            _mc = MEAL_COLORS.get(fe.meal_type.lower(), "#4f8ef7")
            try:
                _ts_str = datetime.fromisoformat(fe.timestamp).strftime("%H:%M")
            except Exception:
                _ts_str = ""
            _sub = ml + (f" · {_ts_str}" if _ts_str else "")
            _col1, _col2 = st.columns([10, 1])
            with _col1:
                st.markdown(
                    f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:10px;'
                    f'padding:8px 12px;display:flex;justify-content:space-between;align-items:center">'
                    f'<div dir="rtl" style="display:flex;align-items:center;gap:8px">'
                    f'<div style="width:3px;height:28px;border-radius:99px;background:{_mc};flex-shrink:0"></div>'
                    f'<div dir="rtl"><div style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{fe.food_name}</div>'
                    f'<div style="font-size:0.67rem;color:#545e70">{_sub} · {round(fe.grams)}ג׳</div></div></div>'
                    f'<div style="font-size:0.85rem;font-weight:800;color:{_mc}">{round(fe.calories)} קק״ל</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with _col2:
                if st.button("🗑", key=f"del_{fe.entry_id}", help="מחק"):
                    food_repo.remove_entry(USER_ID, sel_date, fe.entry_id)
                    st.rerun()
            st.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div dir="rtl" style="font-size:0.72rem;color:#a0aec0;margin-bottom:12px">'
            f'סה״כ: <b style="color:#4f8ef7">{int(totals["calories"])} קק״ל</b> · '
            f'<b style="color:#a3e635">{round(totals["protein"],1)}ג׳ חלבון</b> · '
            f'<b style="color:#f59e0b">{round(totals["carbs"],1)}ג׳ פחמ׳</b> · '
            f'<b style="color:#fb923c">{round(totals["fat"],1)}ג׳ שומן</b></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין רישומי תזונה ליום זה</div>', unsafe_allow_html=True)

    water_entries = water_repo.get_water_intakes_for_date(USER_ID, sel_date)
    total_water   = int(sum(w.amount_ml for w in water_entries))
    st.markdown('<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;margin-bottom:4px;font-weight:700">מים</div>', unsafe_allow_html=True)
    if total_water > 0:
        st.markdown(
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:10px;padding:8px 12px;margin-bottom:8px">'
            f'<span style="font-size:0.88rem;font-weight:800;color:#38bdf8">{total_water} מ״ל</span>'
            f'<span style="font-size:0.7rem;color:#545e70"> ({len(water_entries)} כוסות)</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין רישומי מים ליום זה</div>', unsafe_allow_html=True)

    st.markdown('<div dir="rtl" style="font-size:0.75rem;color:#a0aec0;margin-bottom:4px;font-weight:700">אימונים</div>', unsafe_allow_html=True)
    day_wos = workout_data_all.daily_log.get(sel_date.isoformat(), [])
    if day_wos:
        for wo in day_wos:
            st.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:10px;'
                f'padding:8px 12px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{wo.get("type","")}</div>'
                f'<div dir="rtl" style="font-size:0.75rem;color:#f59e0b">{wo.get("duration_minutes",0)} דקות · {wo.get("intensity","")}</div>'
                f'</div>', unsafe_allow_html=True,
            )
    else:
        st.markdown('<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:8px">אין רישומי אימונים ליום זה</div>', unsafe_allow_html=True)

# 
# PLANNER DETAIL
# 
else:
    st.markdown(
        f'<div dir="rtl" style="margin-bottom:10px;font-size:0.95rem;font-weight:800;'
        f'color:#f4f6fb;border-right:3px solid #a3e635;padding-right:10px">'
        f'תכנון יום — {day_label}</div>', unsafe_allow_html=True,
    )

    pday_key = sel_date.isoformat()
    if pday_key not in plan:
        plan[pday_key] = {"meals": [], "workouts": []}
    day_plan = plan[pday_key]

    MEAL_TYPE_OPTIONS = {
        "BREAKFAST":"ארוחת בוקר","MORNING_SNACK":"ביניים בוקר",
        "LUNCH":"ארוחת צהריים","AFTERNOON_SNACK":"ביניים אחה״צ",
        "DINNER":"ארוחת ערב","EVENING_SNACK":"ביניים ערב",
    }
    WORKOUT_TYPES     = ["ריצה","הליכה","אופניים","שחייה","כוח","יוגה","פילאטיס","HIIT","אחר"]
    INTENSITY_OPTIONS = {"LOW":"נמוכה","MODERATE":"בינונית","HIGH":"גבוהה"}

    st.markdown('<div dir="rtl" style="font-size:0.78rem;color:#a3e635;margin-bottom:6px;font-weight:700">ארוחות מתוכננות</div>', unsafe_allow_html=True)
    meals = day_plan.get("meals", [])
    if meals:
        for mi, meal in enumerate(meals):
            mtype = MEAL_TYPE_OPTIONS.get(meal.get("type",""), meal.get("type",""))
            mname = meal.get("name","")
            mcal  = meal.get("calories", 0)
            mc1, mc2 = st.columns([5, 1])
            mc1.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #1e3a1e;border-radius:10px;padding:8px 12px">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{mname}</div>'
                f'<div dir="rtl" style="font-size:0.67rem;color:#545e70">{mtype}{" · "+str(mcal)+" קק״ל" if mcal else ""}</div>'
                f'</div>', unsafe_allow_html=True,
            )
            if mc2.button("×", key=f"del_meal_{pday_key}_{mi}"):
                plan[pday_key]["meals"].pop(mi)
                _save_plan(plan)
                st.rerun()
    else:
        st.markdown('<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:6px">אין ארוחות מתוכננות</div>', unsafe_allow_html=True)

    with st.expander("+ הוסף ארוחה"):
        with st.form(f"add_meal_{pday_key}", clear_on_submit=True):
            nm_name = st.text_input("שם המנה", key=f"mn_{pday_key}")
            nm_type = st.selectbox("סוג ארוחה", options=list(MEAL_TYPE_OPTIONS.keys()),
                                   format_func=lambda x: MEAL_TYPE_OPTIONS[x], key=f"mt_{pday_key}")
            nm_cal  = st.number_input("קלוריות", 0, 3000, 0, 50, key=f"mc_{pday_key}")
            if st.form_submit_button("הוסף"):
                if nm_name.strip():
                    plan[pday_key]["meals"].append({"name":nm_name.strip(),"type":nm_type,"calories":int(nm_cal)})
                    _save_plan(plan)
                    st.success("נוסף!")
                    st.rerun()

    st.markdown('<div dir="rtl" style="font-size:0.78rem;color:#f59e0b;margin-top:14px;margin-bottom:6px;font-weight:700">אימונים מתוכננים</div>', unsafe_allow_html=True)
    workouts = day_plan.get("workouts", [])
    if workouts:
        for wi, wo in enumerate(workouts):
            wtype = wo.get("type","")
            wdur  = wo.get("duration_minutes",0)
            wint  = INTENSITY_OPTIONS.get(wo.get("intensity",""), wo.get("intensity",""))
            wc1, wc2 = st.columns([5, 1])
            wc1.markdown(
                f'<div dir="rtl" style="background:#161b26;border:1px solid #3a2e10;border-radius:10px;padding:8px 12px">'
                f'<div dir="rtl" style="font-size:0.82rem;font-weight:700;color:#f4f6fb">{wtype}</div>'
                f'<div dir="rtl" style="font-size:0.67rem;color:#545e70">{wdur} דקות · {wint}</div>'
                f'</div>', unsafe_allow_html=True,
            )
            if wc2.button("×", key=f"del_wo_{pday_key}_{wi}"):
                plan[pday_key]["workouts"].pop(wi)
                _save_plan(plan)
                st.rerun()
    else:
        st.markdown('<div dir="rtl" style="color:#545e70;font-size:0.8rem;margin-bottom:6px">אין אימונים מתוכננים</div>', unsafe_allow_html=True)

    with st.expander("+ הוסף אימון"):
        with st.form(f"add_wo_{pday_key}", clear_on_submit=True):
            nw_type = st.selectbox("סוג אימון", WORKOUT_TYPES, key=f"wt_{pday_key}")
            wf1, wf2 = st.columns(2)
            nw_dur  = wf1.number_input("משך (דקות)", 5, 300, 45, 5, key=f"wd_{pday_key}")
            nw_int  = wf2.selectbox("עצימות", options=list(INTENSITY_OPTIONS.keys()),
                                    format_func=lambda x: INTENSITY_OPTIONS[x], key=f"wi_{pday_key}")
            if st.form_submit_button("הוסף"):
                plan[pday_key]["workouts"].append({"type":nw_type,"duration_minutes":int(nw_dur),"intensity":nw_int})
                _save_plan(plan)
                st.success("נוסף!")
                st.rerun()

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
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#a3e635">{total_pm}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">ארוחות</div></div>'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#f59e0b">{total_pw}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">אימונים</div></div>'
        f'<div dir="rtl" style="flex:1;background:#161b26;border:1px solid #252d3d;border-radius:14px;padding:12px 8px;text-align:center">'
        f'<div dir="rtl" style="font-size:1.1rem;font-weight:900;color:#4f8ef7">{total_pc}</div>'
        f'<div dir="rtl" style="font-size:0.6rem;color:#545e70;margin-top:2px">קק״ל</div></div>'
        f'</div>', unsafe_allow_html=True,
    )

st.markdown('<div dir="rtl" style="height:80px"></div>', unsafe_allow_html=True)
bottom_nav("diary")
