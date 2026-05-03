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
repo = ProfileRepository()
profile = repo.load(USER_ID)

page_header("פרופיל משתמש", icon_name="user", subtitle="עדכן פרטים, העדפות ויעדים")

saved_msg = st.empty()

tab_personal, tab_prefs, tab_targets = st.tabs(["👤 פרטים אישיים", "🍽️ העדפות תזונה", "🎯 יעדים"])

# ── Tab 1: Personal details ───────────────────────────────────────────────────
with tab_personal:
    section_header("פרטים אישיים", icon_name="user")

    GENDER_LABELS  = {Gender.MALE: "זכר", Gender.FEMALE: "נקבה"}
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

    # notes
    new_notes = st.text_area("הערות אישיות (אופציונלי)",
                              value=profile.get("notes", "") or "", height=80)

    if st.button("💾 שמור פרטים אישיים", type="primary", use_container_width=True):
        profile.update({
            "name": new_name,
            "gender": new_gender.value,
            "date_of_birth": new_dob.isoformat(),
            "height_cm": new_height,
            "weight_kg": new_weight,
            "activity_level": new_activity.value,
            "goal": new_goal.value,
            "notes": new_notes or None,
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
        custom_allergy = st.text_input("הוסף אלרגיה מותאמת (Enter לאישור)", key="custom_allergy")
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
            "kashrut": new_kashrut,
            "allergies": new_allergies,
            "preferred_foods": new_preferred,
            "disliked_foods": new_disliked,
            "meals_per_day": new_meals_per_day,
        }
        repo.save(profile)
        st.success("✅ העדפות נשמרו!")
        st.rerun()

# ── Tab 3: Calculated targets ─────────────────────────────────────────────────
with tab_targets:
    section_header("יעדים תזונתיים מחושבים", icon_name="chart")

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
        _engine = NutritionEngine()
        _targets = _engine.calculate_targets(_user)

        c1, c2, c3 = st.columns(3)
        c1.metric("BMR (מנוחה)", f"{_targets.bmr_kcal:.0f} קק״ל")
        c2.metric("TDEE (פעיל)", f"{_targets.tdee_kcal:.0f} קק״ל")
        c3.metric("יעד יומי", f"{_targets.target_calories_kcal:.0f} קק״ל")

        st.divider()
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.markdown("#### 🥩 חלבון")
            st.metric("", f"{_targets.protein_g:.0f}g ({_targets.protein_pct:.0f}%)")
        with mc2:
            st.markdown("#### 🍞 פחמימות")
            st.metric("", f"{_targets.carbs_g:.0f}g ({_targets.carbs_pct:.0f}%)")
        with mc3:
            st.markdown("#### 🥑 שומן")
            st.metric("", f"{_targets.fat_g:.0f}g ({_targets.fat_pct:.0f}%)")

        st.caption(f"שיטת חישוב: {_targets.calculation_method}")

    except Exception as e:
        st.warning(f"לא ניתן לחשב יעדים — וודא שהפרטים האישיים נשמרו. ({e})")

    st.divider()
    st.info("💡 לעדכון היעדים — עדכן משקל / רמת פעילות / מטרה בלשונית **פרטים אישיים**")
