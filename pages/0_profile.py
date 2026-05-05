#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0_profile.py — פרופיל משתמש מלא: פרטים אישיים, העדפות ויעדים
"""
import sys, os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, page_header, section_header
from nutrition_app.models.enums import Gender, ActivityLevel, Goal
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.models.user import UserProfile
from nutrition_app.repositories.profile_repository import ProfileRepository

st.set_page_config(page_title="BiteFit · פרופיל", page_icon="👤", layout="wide")
inject_global_css()

USER_ID = "ui_user_001"
repo    = ProfileRepository()
profile = repo.load(USER_ID)

page_header("פרופיל משתמש", icon_name="user", subtitle="עדכן פרטים, העדפות ויעדים")

saved_msg = st.empty()

GENDER_LABELS = {Gender.MALE: "זכר", Gender.FEMALE: "נקבה"}
ACTIVITY_LABELS = {
    ActivityLevel.SEDENTARY:         "יושבני (כמעט ללא פעילות)",
    ActivityLevel.LIGHTLY_ACTIVE:    "פעילות קלה (1–3 ימים/שבוע)",
    ActivityLevel.MODERATELY_ACTIVE: "פעילות בינונית (3–5 ימים/שבוע)",
    ActivityLevel.VERY_ACTIVE:       "פעילות גבוהה (6–7 ימים/שבוע)",
    ActivityLevel.EXTRA_ACTIVE:      "פעילות אינטנסיבית / עבודה פיזית",
}
GOAL_LABELS = {
    Goal.LOSE_WEIGHT: "ירידה במשקל",
    Goal.MAINTAIN:    "שמירה על משקל",
    Goal.GAIN_WEIGHT: "עלייה במשקל",
}
PACE_LABELS = {
    "slow":     "איטי",
    "moderate": "בינוני",
    "fast":     "מהיר",
}
PACE_DESCRIPTIONS = {
    "lose_weight": {
        "slow":     "~0.25 ק״ג/שבוע — בטוח מאוד, שימור שריר מקסימלי",
        "moderate": "~0.5 ק״ג/שבוע — מומלץ על ידי תזונאים",
        "fast":     "~1 ק״ג/שבוע — קשה לשמירה, סיכון לאיבוד שריר",
    },
    "maintain": {
        "slow": "", "moderate": "", "fast": "",
    },
    "gain_weight": {
        "slow":     "~0.2 ק״ג/שבוע — lean bulk, מינימום שומן",
        "moderate": "~0.35 ק״ג/שבוע — מאוזן",
        "fast":     "~0.5 ק״ג/שבוע — גידול מהיר, יותר שומן גוף",
    },
}

tab_personal, tab_prefs, tab_targets = st.tabs(["👤 פרטים אישיים", "🍽️ העדפות תזונה", "🎯 יעדים"])

# ── Tab 1: Personal details ───────────────────────────────────────────────────
with tab_personal:
    section_header("פרטים אישיים", icon_name="user")

    col1, col2 = st.columns(2)

    with col1:
        new_name = st.text_input("שם מלא", value=profile.get("name", ""))

        gender_opts = list(GENDER_LABELS.keys())
        cur_gender_val = profile.get("gender", "male")
        cur_gender = next((g for g in gender_opts if g.value == cur_gender_val), gender_opts[0])
        new_gender = st.radio("מגדר", options=gender_opts,
                              format_func=lambda g: GENDER_LABELS[g],
                              index=gender_opts.index(cur_gender), horizontal=True)

        try:
            dob_val = date.fromisoformat(profile.get("date_of_birth", "1990-05-15"))
        except ValueError:
            dob_val = date(1990, 5, 15)
        new_dob = st.date_input("תאריך לידה", value=dob_val,
                                min_value=date(1930, 1, 1),
                                max_value=date(date.today().year - 10, 1, 1))

    with col2:
        c_h, c_w = st.columns(2)
        with c_h:
            new_height = st.number_input("גובה (ס״מ)", 130.0, 220.0,
                                         value=float(profile.get("height_cm", 178.0)), step=0.5)
        with c_w:
            new_weight = st.number_input("משקל נוכחי (ק״ג)", 35.0, 200.0,
                                         value=float(profile.get("weight_kg", 82.0)), step=0.1)

        activity_opts = list(ACTIVITY_LABELS.keys())
        cur_act_val = profile.get("activity_level", "moderately_active")
        cur_act = next((a for a in activity_opts if a.value == cur_act_val), activity_opts[2])
        new_activity = st.selectbox("רמת פעילות", options=activity_opts,
                                    format_func=lambda a: ACTIVITY_LABELS[a],
                                    index=activity_opts.index(cur_act))

        goal_opts = list(GOAL_LABELS.keys())
        cur_goal_val = profile.get("goal", "lose_weight")
        cur_goal = next((g for g in goal_opts if g.value == cur_goal_val), goal_opts[0])
        new_goal = st.selectbox("מטרה", options=goal_opts,
                                format_func=lambda g: GOAL_LABELS[g],
                                index=goal_opts.index(cur_goal))

    # ── Target weight + weeks slider ─────────────────────────────────────────
    if new_goal != Goal.MAINTAIN:
        st.divider()
        tw_default = float(profile.get("target_weight_kg") or new_weight)
        # Guard: target weight must be on the correct side of current weight
        if new_goal == Goal.LOSE_WEIGHT:
            tw_default = min(tw_default, new_weight - 0.5)
            tw_max = new_weight - 0.5
            tw_min = 35.0
        else:
            tw_default = max(tw_default, new_weight + 0.5)
            tw_max = 200.0
            tw_min = new_weight + 0.5

        tw_default = max(tw_min, min(tw_max, tw_default))
        new_target_weight = st.number_input(
            "משקל יעד (ק״ג)",
            min_value=float(tw_min), max_value=float(tw_max),
            value=float(tw_default), step=0.5,
        )

        # Weeks slider → derive kg/week
        delta_kg = abs(new_target_weight - new_weight)
        # Safe range: fastest = 1 kg/week, slowest = 0.15 kg/week
        min_weeks = max(1, round(delta_kg / 1.0))
        max_weeks = round(delta_kg / 0.15)
        max_weeks = max(max_weeks, min_weeks + 1)

        saved_weeks = int(profile.get("weeks_to_goal", max(min_weeks, round((min_weeks + max_weeks) / 2))))
        saved_weeks = max(min_weeks, min(max_weeks, saved_weeks))

        new_weeks = st.slider(
            "כמה שבועות עד היעד?",
            min_value=min_weeks,
            max_value=max_weeks,
            value=saved_weeks,
            step=1,
        )
        new_weekly_kg = round(delta_kg / max(new_weeks, 1), 3)
        kcal_adj = round(new_weekly_kg * 7700 / 7)
        direction = "גירעון" if new_goal == Goal.LOSE_WEIGHT else "עודף"
        st.caption(
            f"קצב: **{new_weekly_kg:.2f} ק״ג/שבוע** · "
            f"{direction}: **{kcal_adj} קק״ל/יום**"
        )
        new_pace = "moderate"  # fallback for engine calls that use pace
    else:
        new_target_weight = new_weight
        new_weekly_kg     = 0.0
        new_weeks         = 0
        new_pace          = "moderate"

    # ── Live calculation card ─────────────────────────────────────────────────
    st.divider()

    try:
        _prev_user = UserProfile(
            user_id=USER_ID, name=new_name or "user",
            gender=new_gender, date_of_birth=new_dob,
            height_cm=new_height, weight_kg=new_weight,
            activity_level=new_activity, goal=new_goal,
        )
        _engine = NutritionEngine()
        _t = _engine.calculate_targets(
            _prev_user,
            weekly_change_kg=new_weekly_kg if new_goal != Goal.MAINTAIN else None,
            target_weight_kg=new_target_weight if new_goal != Goal.MAINTAIN else None,
        )

        _diff     = int(_t.target_calories_kcal - _t.tdee_kcal)
        _diff_str = f"{_diff:+d}"
        _goal_color = "#4ade80" if new_goal == Goal.GAIN_WEIGHT else ("#f87171" if new_goal == Goal.LOSE_WEIGHT else "#4f8ef7")
        _total_macro_kcal = _t.protein_g * 4 + _t.carbs_g * 4 + _t.fat_g * 9
        _p_pct = round(_t.protein_g * 4 / max(_total_macro_kcal, 1) * 100)
        _c_pct = round(_t.carbs_g   * 4 / max(_total_macro_kcal, 1) * 100)
        _f_pct = round(_t.fat_g     * 9 / max(_total_macro_kcal, 1) * 100)

        def _bar(pct, color):
            return (
                f'<div style="background:#252d3d;border-radius:99px;height:8px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{color};border-radius:99px"></div>'
                f'</div>'
            )

        st.markdown(
            f'<div dir="rtl" style="background:#161b26;border:1px solid #252d3d;border-radius:20px;padding:20px 18px">'

            # Top row: big calorie number + BMR/TDEE chips
            f'<div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:18px">'
            f'<div>'
            f'<div style="font-size:0.72rem;color:#8892a4;margin-bottom:4px;direction:rtl">יעד קלורי יומי</div>'
            f'<div style="font-size:2.6rem;font-weight:900;color:{_goal_color};line-height:1;letter-spacing:-0.04em">'
            f'{int(_t.target_calories_kcal)}</div>'
            f'<div style="font-size:0.72rem;color:#8892a4;margin-top:4px">קק״ל</div>'
            f'</div>'
            f'<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">'
            f'<div style="background:#1e2433;border-radius:10px;padding:6px 12px;text-align:center">'
            f'<div style="font-size:0.58rem;color:#545e70">BMR</div>'
            f'<div style="font-size:0.88rem;font-weight:700;color:#f4f6fb">{int(_t.bmr_kcal)}</div>'
            f'</div>'
            f'<div style="background:#1e2433;border-radius:10px;padding:6px 12px;text-align:center">'
            f'<div style="font-size:0.58rem;color:#545e70">TDEE</div>'
            f'<div style="font-size:0.88rem;font-weight:700;color:#f4f6fb">{int(_t.tdee_kcal)}</div>'
            f'</div>'
            f'<div style="background:#1e2433;border-radius:10px;padding:6px 12px;text-align:center">'
            f'<div style="font-size:0.58rem;color:#545e70">{"גירעון" if _diff < 0 else "עודף"}</div>'
            f'<div style="font-size:0.88rem;font-weight:700;color:{_goal_color}">{_diff_str}</div>'
            f'</div>'
            f'</div>'
            f'</div>'

            # Macro bars
            f'<div style="display:flex;flex-direction:column;gap:10px">'

            f'<div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
            f'<span style="font-size:0.75rem;color:#f4f6fb;font-weight:600">🥩 חלבון</span>'
            f'<span style="font-size:0.75rem;color:#4f8ef7;font-weight:700">{int(_t.protein_g)}g &nbsp;·&nbsp; {_p_pct}%</span>'
            f'</div>'
            f'{_bar(_p_pct, "#4f8ef7")}'
            f'</div>'

            f'<div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
            f'<span style="font-size:0.75rem;color:#f4f6fb;font-weight:600">🍞 פחמימות</span>'
            f'<span style="font-size:0.75rem;color:#f59e0b;font-weight:700">{int(_t.carbs_g)}g &nbsp;·&nbsp; {_c_pct}%</span>'
            f'</div>'
            f'{_bar(_c_pct, "#f59e0b")}'
            f'</div>'

            f'<div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
            f'<span style="font-size:0.75rem;color:#f4f6fb;font-weight:600">🥑 שומן</span>'
            f'<span style="font-size:0.75rem;color:#f472b6;font-weight:700">{int(_t.fat_g)}g &nbsp;·&nbsp; {_f_pct}%</span>'
            f'</div>'
            f'{_bar(_f_pct, "#f472b6")}'
            f'</div>'

            f'</div>'

            # Footer insight
            f'<div style="margin-top:16px;padding-top:14px;border-top:1px solid #252d3d;'
            f'font-size:0.72rem;color:#8892a4;line-height:1.6;direction:rtl">'
            + (
                f'גירעון של {abs(_diff)} קק״ל/יום = ירידה של <b style="color:{_goal_color}">'
                f'{new_weekly_kg:.2f} ק״ג/שבוע</b>. '
                f'חלבון {int(_t.protein_g)}g ({_t.protein_g/new_weight:.1f}g/ק״ג) לשמירה על שריר.'
                if new_goal == Goal.LOSE_WEIGHT else
                f'עודף של {_diff} קק״ל/יום = עלייה של <b style="color:{_goal_color}">'
                f'{new_weekly_kg:.2f} ק״ג/שבוע</b>. '
                f'חלבון {int(_t.protein_g)}g לבניית שריר. דגש על פחמימות סביב אימון.'
                if new_goal == Goal.GAIN_WEIGHT else
                f'TDEE שלך: {int(_t.tdee_kcal)} קק״ל. אכול {int(_t.target_calories_kcal)} קק״ל כדי לשמור על משקלך.'
            )
            + f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.warning(f"מלא פרטים כדי לראות חישוב ({e})")

    # ── Save ─────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("💾 שמור פרטים אישיים", type="primary", use_container_width=True):
        profile.update({
            "name":             new_name,
            "gender":           new_gender.value,
            "date_of_birth":    new_dob.isoformat(),
            "height_cm":        new_height,
            "weight_kg":        new_weight,
            "activity_level":   new_activity.value,
            "goal":             new_goal.value,
            "pace":             new_pace,
            "weekly_change_kg": new_weekly_kg,
            "weeks_to_goal":    new_weeks,
            "target_weight_kg": new_target_weight,
            "notes":            profile.get("notes") or None,
        })
        repo.save(profile)
        st.success("✅ פרטים אישיים נשמרו!")
        st.rerun()

# ── Tab 2: Meal preferences ───────────────────────────────────────────────────
with tab_prefs:
    section_header("העדפות תזונה", icon_name="plate")
    prefs = profile.get("meal_preferences", {})

    col1, col2 = st.columns(2)

    with col1:
        kashrut_map = {"parve": "פרווה (הכל)", "dairy": "חלבי בלבד", "meat": "בשרי בלבד"}
        kashrut_opts = list(kashrut_map.keys())
        cur_k = prefs.get("kashrut", "parve")
        new_kashrut = st.radio("כשרות", options=kashrut_opts,
                               format_func=lambda x: kashrut_map[x],
                               index=kashrut_opts.index(cur_k) if cur_k in kashrut_opts else 0,
                               horizontal=True)

        new_meals_per_day = st.slider("ארוחות ביום", min_value=3, max_value=6,
                                       value=int(prefs.get("meals_per_day", 5)))

        st.markdown("**אלרגיות / רגישויות מזון:**")
        common_allergies = ["גלוטן", "לקטוז", "בוטנים", "אגוזים", "ביצים", "דגים", "סויה", "שומשום"]
        cur_allergies = prefs.get("allergies", [])
        new_allergies = st.multiselect("בחר אלרגיות", options=common_allergies,
                                        default=[a for a in cur_allergies if a in common_allergies])
        custom_allergy = st.text_input("הוסף אלרגיה מותאמת", key="custom_allergy")
        if custom_allergy and custom_allergy not in new_allergies:
            new_allergies = new_allergies + [custom_allergy]

    with col2:
        st.markdown("**מזונות מועדפים:**")
        preferred_raw = "\n".join(prefs.get("preferred_foods", []))
        new_preferred_raw = st.text_area("מזון אחד בכל שורה", value=preferred_raw,
                                          height=120, key="preferred_foods_input")
        new_preferred = [f.strip() for f in new_preferred_raw.splitlines() if f.strip()]

        st.markdown("**מזונות להימנע:**")
        disliked_raw = "\n".join(prefs.get("disliked_foods", []))
        new_disliked_raw = st.text_area("מזון אחד בכל שורה", value=disliked_raw,
                                         height=120, key="disliked_foods_input")
        new_disliked = [f.strip() for f in new_disliked_raw.splitlines() if f.strip()]

    if st.button("💾 שמור העדפות תזונה", type="primary", use_container_width=True):
        profile["meal_preferences"] = {
            "kashrut":        new_kashrut,
            "allergies":      new_allergies,
            "preferred_foods": new_preferred,
            "disliked_foods": new_disliked,
            "meals_per_day":  new_meals_per_day,
        }
        repo.save(profile)
        st.success("✅ העדפות נשמרו!")
        st.rerun()

# ── Tab 3: Saved targets breakdown ────────────────────────────────────────────
with tab_targets:
    section_header("יעדים תזונתיים שמורים", icon_name="chart")

    try:
        _user = UserProfile(
            user_id=USER_ID,
            name=profile.get("name", ""),
            gender=Gender(profile.get("gender", "male")),
            date_of_birth=date.fromisoformat(profile.get("date_of_birth", "1990-05-15")),
            height_cm=float(profile.get("height_cm", 178)),
            weight_kg=float(profile.get("weight_kg", 82)),
            activity_level=ActivityLevel(profile.get("activity_level", "moderately_active")),
            goal=Goal(profile.get("goal", "lose_weight")),
        )
        _saved_pace = profile.get("pace", "moderate")
        _saved_target_w = profile.get("target_weight_kg")
        _engine = NutritionEngine()
        _targets = _engine.calculate_targets(_user, pace=_saved_pace,
                                             target_weight_kg=_saved_target_w)

        # Header metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("BMR (מנוחה)", f"{_targets.bmr_kcal:.0f} קק״ל",
                  help="קלוריות שהגוף שורף ללא כל פעילות")
        c2.metric("TDEE (פעיל)", f"{_targets.tdee_kcal:.0f} קק״ל",
                  help="סך קלוריות שגופך שורף ביום כולל פעילות")
        c3.metric("🎯 יעד יומי", f"{_targets.target_calories_kcal:.0f} קק״ל",
                  delta=f"{_targets.target_calories_kcal - _targets.tdee_kcal:+.0f}")

        st.divider()

        # Macros with percentage
        mc1, mc2, mc3 = st.columns(3)
        total_macro_kcal = _targets.protein_g * 4 + _targets.carbs_g * 4 + _targets.fat_g * 9
        with mc1:
            pct_p = _targets.protein_g * 4 / total_macro_kcal * 100 if total_macro_kcal else 0
            st.markdown("#### 🥩 חלבון")
            st.metric("", f"{_targets.protein_g:.0f}g",
                      help=f"{_user.weight_kg:.1f}kg × {_targets.protein_g/_user.weight_kg:.1f}g/kg")
            st.caption(f"{pct_p:.0f}% מהקלוריות")
        with mc2:
            pct_c = _targets.carbs_g * 4 / total_macro_kcal * 100 if total_macro_kcal else 0
            st.markdown("#### 🍞 פחמימות")
            st.metric("", f"{_targets.carbs_g:.0f}g")
            st.caption(f"{pct_c:.0f}% מהקלוריות")
        with mc3:
            pct_f = _targets.fat_g * 9 / total_macro_kcal * 100 if total_macro_kcal else 0
            st.markdown("#### 🥑 שומן")
            st.metric("", f"{_targets.fat_g:.0f}g")
            st.caption(f"{pct_f:.0f}% מהקלוריות")

        if _targets.notes:
            st.caption(f"⚙️ {_targets.notes} | שיטה: {_targets.calculation_method}")

    except Exception as e:
        st.warning(f"לא ניתן לחשב יעדים — וודא שהפרטים האישיים נשמרו. ({e})")

    st.divider()
    st.info("💡 שנה משקל / פעילות / מטרה / קצב בלשונית **פרטים אישיים** — החישוב מתעדכן מיידית")
