#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דאשבורד סוכנים — לוח בקרה אוטונומי
"""

import json
import sys
import os
import time
from datetime import date, datetime, timezone
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from ui.components import (
    inject_global_css, page_header, section_header, nav_menu, icon_button,
)
from ui.auth import require_admin, admin_logout_button
from chatbot.sidebar_widget import render_chatbot_sidebar

# ── Autonomy imports ──────────────────────────────────────────────────────────
from nutrition_app.models.enums import ActivityLevel, Gender, Goal
from nutrition_app.models.user import UserProfile
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner

from nutrition_app.autonomy.models.autonomy_enums import (
    AgentId, FeedbackType, TaskPriority, TaskStatus,
)
from nutrition_app.autonomy.models.system_metrics import SystemMetrics
from nutrition_app.autonomy.audit.audit_log import AuditLog
from nutrition_app.autonomy.authority.authority_policy import AuthorityPolicy
from nutrition_app.autonomy.goals.goal_tracker import GoalTracker
from nutrition_app.autonomy.prioritizer.task_prioritizer import TaskPrioritizer
from nutrition_app.autonomy.healing.self_healer import SelfHealer
from nutrition_app.autonomy.improvement.improvement_engine import ImprovementEngine
from nutrition_app.autonomy.data_optimizer.data_optimizer import DataOptimizer
from nutrition_app.autonomy.feedback.feedback_manager import FeedbackManager
from nutrition_app.autonomy.orchestrator.autonomy_orchestrator import AutonomyOrchestrator
from nutrition_app.autonomy.dashboard.active_dashboard import ActiveDashboard

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="דאשבורד סוכנים",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system ─────────────────────────────────────────────────────────
# Admin authentication is handled at the app level (app_admin.py)
inject_global_css()

# ── Top nav + page header (admin only past this point) ───────────────────────
nav_menu(active="סוכנים")
page_header(
    "דאשבורד סוכנים",
    icon_name="agent",
    subtitle="לוח בקרה אוטונומי — גישת מנהל",
)
admin_logout_button()

# ── Storage dir ───────────────────────────────────────────────────────────────
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage_agents")
os.makedirs(STORAGE_DIR, exist_ok=True)

# ── Live-data helpers ─────────────────────────────────────────────────────────

def _load_json(path: str, fallback):
    """Load JSON from path; return fallback on any error."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return fallback

def _latest_file(directory: str, pattern: str) -> str:
    """Return path to the most-recently-modified file matching pattern, or ''."""
    import glob
    files = sorted(glob.glob(os.path.join(directory, pattern)), reverse=True)
    return files[0] if files else ""

_TASKS_DIR = os.path.join(STORAGE_DIR, "tasks")
_REPORTS_DIR = os.path.join(STORAGE_DIR, "audit", "director_reports")
_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents", "logs")

# ── Simple run_state mock (no WorkflowEngine needed) ─────────────────────────

class _RunResult:
    """Minimal object to satisfy orchestrator._record_run()"""
    def __init__(self, run_id, user_id, success, deviation):
        self.run_id = run_id
        self.user_id = user_id
        self.is_success = success
        self.stages = {}
        def pending_decisions(): return []
        self.pending_decisions = pending_decisions

# ── Initialize orchestrator (once, persisted in session) ─────────────────────

def _init_orchestrator() -> AutonomyOrchestrator:
    audit = AuditLog(f"{STORAGE_DIR}/audit")
    authority = AuthorityPolicy()
    goal_tracker = GoalTracker()
    prioritizer = TaskPrioritizer()
    healer = SelfHealer()
    improvement = ImprovementEngine()
    data_opt = DataOptimizer(STORAGE_DIR, audit)
    feedback = FeedbackManager(f"{STORAGE_DIR}/feedback")

    orc = AutonomyOrchestrator(
        workflow_engine=None,   # We run agents directly
        audit_log=audit,
        authority=authority,
        self_healer=healer,
        improvement_engine=improvement,
        feedback_manager=feedback,
        goal_tracker=goal_tracker,
        task_prioritizer=prioritizer,
        data_optimizer=data_opt,
        storage_dir=STORAGE_DIR,
    )
    return orc


if "orc" not in st.session_state:
    st.session_state["orc"] = _init_orchestrator()
    st.session_state["cycles"] = []
    st.session_state["run_count"] = 0

orc: AutonomyOrchestrator = st.session_state["orc"]
dashboard = ActiveDashboard(orchestrator=orc)

# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_pipeline_cycle(user_cfg: Dict, inventory_cfg: Dict) -> Dict:
    """Run one full pipeline cycle using agents directly, feed results into orchestrator."""
    cycle_start = time.time()
    run_id = f"cycle_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{st.session_state['run_count']}"
    st.session_state["run_count"] += 1

    log = []
    success = True
    deviation = 0.0
    auto_fixes = []
    escalations = []

    try:
        # Agent 1: User Profile
        user = UserProfile(**user_cfg)
        log.append({"step": "פרופיל משתמש", "status": "✓", "detail": f"{user.name}, {user.age} שנים"})

        # Agent 2: Nutrition targets
        engine = NutritionEngine()
        targets = engine.calculate_targets(user)
        errs = engine.validate_targets(targets)
        if errs:
            success = False
            escalations.append({"what_happened": f"שגיאת ולידציה: {errs}", "what_we_tried": [], "why_it_failed": str(errs), "options": ["בדוק נתוני משתמש"], "impact_on_goal": "חישוב יעדים נכשל"})
            log.append({"step": "חישוב יעדים", "status": "✗", "detail": str(errs)})
        else:
            log.append({"step": "חישוב יעדים", "status": "✓", "detail": f"יעד: {targets.target_calories_kcal:.0f} קק\"ל"})

        # Agent 3: Food matching
        catalog = FoodCatalog()
        food_queries = list(inventory_cfg.get("queries", ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית"]))
        match_result = catalog.match_foods(food_queries)
        food_lookup = {f.food_id: f for f in catalog.get_all_foods()}

        if match_result.unmatched:
            # Self-healer: detect low-confidence food
            error_msg = f"food_id not found: {match_result.unmatched}"
            record = orc.self_healer.detect(error_msg, "resolve_foods", run_id)
            record = orc.self_healer.diagnose(record)
            fix = orc.self_healer.propose_fix(record)
            auth = orc._authority.check_authority(fix.get("action_category"))
            if orc.self_healer.should_auto_fix(fix, auth):
                auto_fixes.append({"stage": "resolve_foods", "fix": fix.get("strategy"), "confidence": fix.get("confidence")})
                log.append({"step": "זיהוי מזונות", "status": "⚡", "detail": f"תוקן אוטומטית: {fix.get('strategy')}"})
            else:
                escalations.append({"what_happened": f"מזונות לא זוהו: {match_result.unmatched}", "what_we_tried": [{"attempt": 1, "action": "auto_fix", "result": "confidence_too_low"}], "why_it_failed": "ביטחון נמוך", "options": ["הוסף מזון ידנית", "בחר מחליף"], "impact_on_goal": "תפריט חלקי"})
                log.append({"step": "זיהוי מזונות", "status": "⚠", "detail": f"לא זוהה: {match_result.unmatched}"})
        else:
            log.append({"step": "זיהוי מזונות", "status": "✓", "detail": f"{len(match_result.matches)} מזונות זוהו"})

        # Agent 4: Inventory
        inv_mgr = InventoryManager()
        for food_id, qty in inventory_cfg.get("items", {}).items():
            if qty > 0:
                inv_mgr.add_item(user_cfg["user_id"], food_id, qty, "gram")
        inv_state = inv_mgr.get_state(user_cfg["user_id"])
        log.append({"step": "מלאי", "status": "✓", "detail": f"{len(inv_state.items)} פריטים"})

        # Agent 5: Meal planner
        planner = MealPlanner()
        planner.set_food_lookup(food_lookup)
        plan = planner.generate_plan(targets, match_result, inv_state, run_id)
        plan_errors = planner.validate_plan(plan)
        deviation = plan.calorie_deviation_pct

        if plan_errors:
            success = False
            log.append({"step": "תפריט יומי", "status": "✗", "detail": str(plan_errors)})
            # Self-healer attempt
            record = orc.self_healer.detect(str(plan_errors), "generate_meal_plan", run_id)
            record = orc.self_healer.diagnose(record)
            fix = orc.self_healer.propose_fix(record)
            auth = orc._authority.check_authority(fix.get("action_category"))
            if orc.self_healer.should_auto_fix(fix, auth):
                auto_fixes.append({"stage": "generate_meal_plan", "fix": fix.get("strategy"), "confidence": fix.get("confidence")})
                success = True
                log.append({"step": "תפריט יומי (תיקון)", "status": "⚡", "detail": f"תוקן: {fix.get('strategy')}"})
        else:
            if abs(deviation) > 10:
                # Calorie deviation — healer kicks in
                error_msg = f"Calorie deviation {abs(deviation):.1f}% exceeds threshold"
                record = orc.self_healer.detect(error_msg, "generate_meal_plan", run_id)
                record = orc.self_healer.diagnose(record)
                fix = orc.self_healer.propose_fix(record)
                auth = orc._authority.check_authority(fix.get("action_category"))
                if orc.self_healer.should_auto_fix(fix, auth):
                    auto_fixes.append({"stage": "generate_meal_plan", "fix": fix.get("strategy"), "confidence": fix.get("confidence")})
                    log.append({"step": "תפריט יומי", "status": "⚡", "detail": f"{plan.total_calories:.0f} קק\"ל | סטייה {deviation:+.1f}% | תוקן: {fix.get('strategy')}"})
                else:
                    log.append({"step": "תפריט יומי", "status": "⚠", "detail": f"{plan.total_calories:.0f} קק\"ל | סטייה {deviation:+.1f}%"})
            else:
                log.append({"step": "תפריט יומי", "status": "✓", "detail": f"{plan.total_calories:.0f} קק\"ל | סטייה {deviation:+.1f}%"})

        # Inventory deduction
        inv_mgr.deduct_for_plan(user_cfg["user_id"], plan, plan.run_id)
        log.append({"step": "ניכוי מלאי", "status": "✓", "detail": "עודכן"})

    except Exception as e:
        success = False
        log.append({"step": "שגיאה בלתי צפויה", "status": "✗", "detail": str(e)})
        escalations.append({"what_happened": f"Exception: {e}", "what_we_tried": [], "why_it_failed": str(e), "options": ["בדוק לוגים", "צור קשר עם מפתח"], "impact_on_goal": "מחזור נכשל"})

    elapsed = time.time() - cycle_start

    # Record into orchestrator
    run_mock = _RunResult(run_id, user_cfg["user_id"], success, deviation)
    orc._record_run(run_mock, {
        "success": success,
        "calorie_deviation_pct": deviation,
        "auto_fixes": auto_fixes,
        "escalations": escalations,
    })

    # Add escalations to orchestrator
    for esc in escalations:
        orc._escalations.append(esc)

    # Detect improvements after run
    metrics = orc.collect_metrics()
    evaluations = orc._goals.evaluate_progress(metrics)
    for eval_result in evaluations.values():
        new_imps = orc._improvement.detect_gaps(metrics, eval_result)
        new_tasks = orc._improvement.create_tasks_for_improvements(new_imps)
        orc._tasks.extend(new_tasks)

    # Data optimizer
    orc._data_optimizer.deduplicate_artifacts()

    cycle_result = {
        "run_id": run_id,
        "success": success,
        "deviation": deviation,
        "auto_fixes": auto_fixes,
        "escalations_count": len(escalations),
        "log": log,
        "elapsed_sec": round(elapsed, 2),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    st.session_state["cycles"].append(cycle_result)
    return cycle_result


# ── Sidebar — Control panel ───────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🤖 לוח בקרה — סוכנים")
    st.divider()

    st.markdown("### ⚙️ הגדרות ריצה")
    user_id = st.text_input("מזהה משתמש", value="agent_user_001")
    goal_sel = st.selectbox("מטרה", options=[g.value for g in Goal],
                             format_func=lambda v: {"lose_weight": "ירידה במשקל", "maintain": "שמירה", "gain_weight": "עלייה"}.get(v, v))
    activity_sel = st.selectbox("פעילות", options=[a.value for a in ActivityLevel],
                                  format_func=lambda v: {"sedentary": "יושבני", "lightly_active": "קלה", "moderately_active": "בינונית", "very_active": "גבוהה", "extra_active": "אינטנסיבית"}.get(v, v),
                                  index=2)
    weight_s = st.slider("משקל (ק\"ג)", 40, 150, 82)
    height_s = st.slider("גובה (ס\"מ)", 140, 210, 178)

    st.divider()
    st.markdown("### 🛒 מלאי לריצה")
    inv_chicken = st.number_input("חזה עוף (ג)", 0, 2000, 600, step=100)
    inv_rice    = st.number_input("אורז (ג)", 0, 2000, 1000, step=100)
    inv_egg     = st.number_input("ביצה (ג)", 0, 2000, 400, step=50)
    inv_banana  = st.number_input("בננה (ג)", 0, 1000, 360, step=50)

    st.divider()
    run_cycle_btn = icon_button("הרץ מחזור", "play",
                                key="run_cycle_btn", type="primary")
    auto_refresh = st.toggle("רענון אוטומטי (5 שנ')", value=False)

    if icon_button("אפס מערכת", "delete", key="reset_orc_btn"):
        for key in ["orc", "cycles", "run_count"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ── Build user/inventory config ───────────────────────────────────────────────

user_cfg = dict(
    user_id=user_id,
    name="סוכן-משתמש",
    gender=Gender.MALE,
    date_of_birth=date(1990, 5, 15),
    height_cm=float(height_s),
    weight_kg=float(weight_s),
    activity_level=ActivityLevel(activity_sel),
    goal=Goal(goal_sel),
)
inventory_cfg = {
    "queries": ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "לחם", "עגבנייה"],
    "items": {
        "food_001": float(inv_chicken),
        "food_002": float(inv_rice),
        "food_003": float(inv_egg),
        "food_004": float(inv_banana),
    }
}

# ── Run cycle if requested ────────────────────────────────────────────────────

if run_cycle_btn:
    with st.spinner("מריץ מחזור אוטונומי..."):
        result = run_pipeline_cycle(user_cfg, inventory_cfg)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("---")

metrics = orc.collect_metrics()
dash_state = dashboard.get_demo_readiness()
goal_pct = dash_state.get("progress_pct", 0)

# Demo readiness bar
ready = dash_state.get("ready", False)
col_status, col_bar = st.columns([1, 3])
with col_status:
    if ready:
        st.success("✅ מוכן להדגמה")
    else:
        st.warning(f"⏳ בתהליך — {goal_pct:.0f}%")
with col_bar:
    st.progress(int(goal_pct) if goal_pct else 0, text=f"התקדמות לעמידה ביעדים: {goal_pct:.0f}%")

st.divider()

# ── Top metrics ───────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("🔄 מחזורים", metrics.total_runs)
c2.metric("✅ שיעור הצלחה", f"{metrics.success_rate:.0f}%")
c3.metric("📊 סטייה ממוצעת", f"{metrics.average_deviation:.1f}%")
c4.metric("⚡ תיקונים אוטו", f"{metrics.auto_fix_rate:.0f}%")
c5.metric("🚨 הסלמות", metrics.escalation_count)
c6.metric("📋 משימות פתוחות", metrics.open_failures + metrics.stuck_tasks)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_cycles, tab_tasks, tab_healer, tab_escalations, tab_recipe_images, tab_feedback, tab_improvements, tab_audit, tab_live_state = st.tabs([
    "🔄 מחזורים",
    "📋 משימות",
    "🩺 ריפוי עצמי",
    "🚨 הסלמות",
    "🖼️ תמונות מתכונים",
    "💬 משוב",
    "📈 שיפורים",
    "📝 ביקורת",
    "🗂️ מצב מערכת חי",
])

# ── Tab: Cycles ───────────────────────────────────────────────────────────────

with tab_cycles:
    st.markdown("### היסטוריית מחזורים")
    cycles = st.session_state.get("cycles", [])

    if not cycles:
        st.info("לא הורצו מחזורים עדיין. לחץ **הרץ מחזור** בסרגל השמאלי.")
    else:
        # Last cycle expanded
        last = cycles[-1]
        status_icon = "✅" if last["success"] else "❌"
        with st.expander(f"{status_icon} מחזור אחרון — {last['timestamp']} ({last['elapsed_sec']}שנ')", expanded=True):
            for step in last["log"]:
                icon = step["status"]
                color = "green" if icon == "✓" else ("orange" if icon in ("⚠", "⚡") else "red")
                st.markdown(f"**{icon} {step['step']}** — {step['detail']}")
            if last["auto_fixes"]:
                st.markdown("**⚡ תיקונים אוטומטיים:**")
                for fix in last["auto_fixes"]:
                    st.markdown(f"&nbsp;&nbsp;• {fix['stage']}: `{fix['fix']}` (ביטחון: {fix['confidence']})")

        # Previous cycles table
        if len(cycles) > 1:
            st.markdown("**מחזורים קודמים:**")
            for c in reversed(cycles[:-1]):
                icon = "✅" if c["success"] else "❌"
                fixes = len(c.get("auto_fixes", []))
                st.markdown(
                    f"{icon} `{c['run_id'][-12:]}` — {c['timestamp']} | "
                    f"סטייה: {c['deviation']:+.1f}% | תיקונים: {fixes} | "
                    f"הסלמות: {c['escalations_count']}"
                )

# ── Tab: Tasks ────────────────────────────────────────────────────────────────

with tab_tasks:
    st.markdown("### תור משימות")
    tasks = orc.tasks

    if not tasks:
        st.info("אין משימות בתור.")
    else:
        STATUS_ICON = {
            "created": "🔵",
            "in_progress": "🟡",
            "fixed": "🟣",
            "verified": "🟢",
            "closed": "✅",
            "failed": "🔴",
            "stuck": "⛔",
            "escalated": "🚨",
            "needs_info": "❓",
        }
        STATUS_HE = {
            "created": "ממתין", "in_progress": "בביצוע", "fixed": "תוקן",
            "verified": "אומת", "closed": "סגור", "failed": "נכשל",
            "stuck": "תקוע", "escalated": "הוסלם", "needs_info": "דרוש מידע",
        }

        open_tasks = [t for t in tasks if t.status.value not in ("closed",)]
        closed_tasks = [t for t in tasks if t.status.value == "closed"]

        st.markdown(f"**פתוחות: {len(open_tasks)} | סגורות: {len(closed_tasks)}**")

        for task in sorted(open_tasks, key=lambda t: t.priority.value):
            icon = STATUS_ICON.get(task.status.value, "⬜")
            status_he = STATUS_HE.get(task.status.value, task.status.value)
            with st.expander(f"{icon} [{task.priority.value.upper()}] {task.description[:70]}", expanded=False):
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("סטטוס", status_he)
                col_b.metric("ניסיונות", f"{task.attempts}/{task.max_attempts}")
                col_c.metric("בעלים", task.owner.value)
                st.caption(f"מקור: {task.source} | עדכון: {task.updated_at.strftime('%H:%M:%S')}")

# ── Tab: Self-Healer ──────────────────────────────────────────────────────────

with tab_healer:
    st.markdown("### ריפוי עצמי — היסטוריה")

    auto_fixes = dashboard.get_auto_fixes(limit=20)
    heal_history = orc.self_healer.get_history()

    col_h1, col_h2 = st.columns(2)
    col_h1.metric("סה\"כ בדיקות", len(heal_history))
    col_h2.metric("תיקונים אוטומטיים", len(auto_fixes))

    if not heal_history:
        st.info("אין היסטוריית ריפוי עדיין.")
    else:
        for rec in reversed(heal_history[-10:]):
            status = rec.get("status", "")
            icon = "✅" if status == "verified" else ("⚡" if status in ("auto_fixed", "applied") else "🔍")
            with st.expander(f"{icon} {rec.get('issue_type', 'לא ידוע')} — {rec.get('detected_in_stage', '')}", expanded=False):
                st.markdown(f"**שגיאה:** {rec.get('issue_description', '')}")
                st.markdown(f"**סיבת שורש:** {rec.get('root_cause', 'לא זוהתה')}")
                if rec.get("fix_description"):
                    st.markdown(f"**אסטרטגיית תיקון:** `{rec.get('fix_description')}`")
                    conf = rec.get("fix_confidence") or 0
                    st.markdown(f"**ביטחון:** {conf:.0%}")
                st.caption(f"סטטוס: {status}")

# ── Tab: Escalations ──────────────────────────────────────────────────────────

with tab_escalations:
    st.markdown("### הסלמות ממתינות")
    escalations = dashboard.get_pending_escalations()

    if not escalations:
        st.success("✅ אין הסלמות ממתינות.")
    else:
        for i, esc in enumerate(escalations):
            with st.expander(f"🚨 הסלמה #{i+1} — {esc.get('what_happened', '')[:60]}", expanded=True):
                st.markdown(f"**מה קרה:** {esc.get('what_happened', '')}")
                tried = esc.get("what_we_tried", [])
                if tried:
                    st.markdown("**מה ניסינו:**")
                    for attempt in tried:
                        st.markdown(f"&nbsp;&nbsp;• ניסיון {attempt.get('attempt', '')}: `{attempt.get('action', '')}` → {attempt.get('result', '')}")
                st.markdown(f"**למה נכשל:** {esc.get('why_it_failed', '')}")
                options = esc.get("options", [])
                if options:
                    st.markdown(f"**אפשרויות:** {' | '.join(options)}")
                st.markdown(f"**השפעה על יעד:** {esc.get('impact_on_goal', '')}")

                col_approve, col_reject, col_notes = st.columns([1, 1, 3])
                notes_val = col_notes.text_input("הערות", key=f"esc_notes_{i}")
                if col_approve.button("✅ אשר", key=f"esc_approve_{i}"):
                    orc.resolve_escalation(i, approved=True, notes=notes_val)
                    st.success("אושר")
                    st.rerun()
                if col_reject.button("❌ דחה", key=f"esc_reject_{i}"):
                    orc.resolve_escalation(i, approved=False, notes=notes_val)
                    st.warning("נדחה")
                    st.rerun()

# ── Tab: Recipe Images ────────────────────────────────────────────────────────

with tab_recipe_images:
    st.markdown("### 🖼️ תמונות מתכונים")
    st.info("ניהול אישור / דחיית תמונות הועבר לדף **מנהל תמונות** הייעודי.")
    if st.button("🔗 עבור למנהל תמונות", type="primary"):
        st.switch_page("pages_admin/2_photo_manager.py")

# ── Tab: Feedback ─────────────────────────────────────────────────────────────

with tab_feedback:
    st.markdown("### הגשת משוב")

    with st.form("feedback_form"):
        fb_text = st.text_area("תוכן המשוב (עברית / אנגלית)", height=100,
                                placeholder="למשל: תכנון הארוחה לא מתאים — יותר מדי פחמימות")
        col_f1, col_f2 = st.columns(2)
        fb_type = col_f1.selectbox("סוג (אופציונלי)",
                                    options=["אוטומטי"] + [f.value for f in FeedbackType],
                                    format_func=lambda v: {"auto": "אוטומטי", "bug": "באג", "quality": "איכות",
                                                           "feature_request": "בקשת פיצ'ר", "data": "נתונים",
                                                           "performance": "ביצועים", "other": "אחר", "אוטומטי": "אוטומטי"}.get(v, v))
        fb_agent = col_f2.selectbox("סוכן יעד (אופציונלי)",
                                     options=["אוטומטי"] + [a.value for a in AgentId])
        fb_submit = st.form_submit_button("📤 שלח משוב", type="primary")

    if fb_submit and fb_text.strip():
        kwargs = dict(description=fb_text.strip())
        if fb_type != "אוטומטי":
            kwargs["feedback_type"] = FeedbackType(fb_type)
        if fb_agent != "אוטומטי":
            kwargs["target_agent"] = AgentId(fb_agent)
        result = orc.submit_feedback(**kwargs)
        st.success(f"✅ משוב התקבל | סוג: {result.get('type')} | מוקצה ל: {result.get('assigned_to', 'אוטומטי')} | משימה: {result.get('task_id', '')[:8]}")

    st.divider()
    st.markdown("### היסטוריית משוב")
    fb_status = dashboard.get_feedback_status()
    all_fb = fb_status.get("items", [])
    st.caption(f"סה\"כ: {fb_status.get('total', 0)} | ממתין: {fb_status.get('pending', 0)}")

    if all_fb:
        for fb in reversed(all_fb[-10:]):
            st.markdown(f"• [{fb.get('feedback_type', '?')}] {fb.get('description', '')[:80]}")

# ── Tab: Improvements ─────────────────────────────────────────────────────────

with tab_improvements:
    st.markdown("### בקלוג שיפורים")
    improvements = dashboard.get_improvement_backlog()

    if not improvements:
        st.info("אין שיפורים ממתינים.")
    else:
        for imp in improvements:
            priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(imp.get("priority", ""), "⬜")
            with st.expander(f"{priority_icon} [{imp.get('improvement_type', '')}] {imp.get('description', '')[:70]}"):
                st.markdown(f"**פעולה:** {imp.get('proposed_action', '')}")
                st.markdown(f"**סוכן יעד:** {imp.get('target_agent', '')}")
                gap_info = imp.get("expected_vs_actual", {})
                if gap_info:
                    st.markdown(f"**פער:** צפוי {gap_info.get('expected', '')} | בפועל {gap_info.get('actual', '')}")
                st.caption(f"מזהה: {imp.get('improvement_id', '')[:8]}")

# ── Tab: Audit ────────────────────────────────────────────────────────────────

with tab_audit:
    st.markdown("### יומן ביקורת")
    audit_summary = dashboard.get_audit_summary()

    c_a1, c_a2 = st.columns(2)
    c_a1.metric("סה\"כ רשומות", audit_summary.get("total_entries", 0))
    c_a2.metric("קבצי יומן", audit_summary.get("log_files", 0))

    audit_entries = orc.audit_log.get_recent(limit=20)
    if not audit_entries:
        st.info("אין רשומות ביקורת עדיין.")
    else:
        for entry in reversed(audit_entries):
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            actor = entry.get("actor", "")
            desc = entry.get("description", "")
            result = entry.get("result", "")
            icon = "✅" if result == "success" else ("🚨" if result == "escalated" else "❌")
            st.markdown(f"{icon} `{ts}` **{actor}** — {desc[:80]}")

# ── Goal gap (sidebar bottom) ─────────────────────────────────────────────────

with st.sidebar:
    st.divider()
    st.markdown("### 🎯 מצב יעדים")
    gap = dashboard.get_goal_progress()
    achieved = gap.get("achieved", [])
    not_achieved = gap.get("not_achieved", [])
    for a in achieved:
        st.markdown(f"✅ {a.get('metric', '')} — {a.get('current', '')}")
    for na in not_achieved:
        st.markdown(f"❌ {na.get('metric', '')} — {na.get('current', '')} (יעד: {na.get('target', '')})")
    st.divider()
    render_chatbot_sidebar()

# ── Section: Director & Critic ────────────────────────────────────────────────

st.divider()
st.markdown("## 🤖 אוטונומי — Director & Critic")

from nutrition_app.agents.agent_8_director.director_agent import DirectorAgent, DirectorReport
from nutrition_app.agents.agent_9_critic.critic_agent import CriticAgent

col_dir, col_crit = st.columns(2)

# ── Director Panel ────────────────────────────────────────────────────────────
with col_dir:
    st.markdown("### 🎯 Director Agent")
    if st.button("הרץ ניתוח", key="btn_director", type="primary", use_container_width=True):
        with st.spinner("מנתח מערכת..."):
            director = DirectorAgent()
            dir_report = director.run_analysis()
            st.session_state["director_report"] = dir_report.to_dict()

    dir_data = st.session_state.get("director_report")
    if dir_data:
        score = dir_data.get("system_health_score", 0)
        if score >= 80:
            score_color = "green"
        elif score >= 50:
            score_color = "orange"
        else:
            score_color = "red"

        st.markdown(
            f"<h2 style='color: {score_color}; text-align: center;'>"
            f"ציון בריאות: {score}/100</h2>",
            unsafe_allow_html=True,
        )

        tasks_list = dir_data.get("tasks_created", [])
        if tasks_list:
            st.markdown(f"**משימות ממתינות ({len(tasks_list)}):**")
            for t in tasks_list:
                pri = t.get("priority", "medium")
                badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(pri, "⬜")
                st.markdown(f"{badge} **[{pri.upper()}]** {t.get('details', '')[:80]}")
        else:
            st.success("אין משימות ממתינות.")

        summary = dir_data.get("summary", "")
        if summary:
            st.info(summary)
    else:
        st.caption("לחץ 'הרץ ניתוח' לסריקת המערכת.")

# ── Critic Panel ──────────────────────────────────────────────────────────────
with col_crit:
    st.markdown("### 🔍 Critic Agent")
    if st.button("בקר תוצאות", key="btn_critic", type="primary", use_container_width=True):
        with st.spinner("בודק משימות שהושלמו..."):
            critic = CriticAgent()
            verdicts = critic.review_completed_tasks()
            st.session_state["critic_verdicts"] = verdicts

    verdicts_data = st.session_state.get("critic_verdicts")
    if verdicts_data is not None:
        if not verdicts_data:
            st.info("אין משימות שהושלמו לבדיקה.")
        else:
            approved = [v for v in verdicts_data if v.get("verdict") == "APPROVED"]
            rejected = [v for v in verdicts_data if v.get("verdict") == "REJECTED"]

            c_a, c_r = st.columns(2)
            c_a.metric("✅ אושרו", len(approved))
            c_r.metric("❌ נדחו (הוחזרו לתור)", len(rejected))

            for v in verdicts_data:
                is_ok = v.get("verdict") == "APPROVED"
                icon = "✅" if is_ok else "❌"
                st.markdown(
                    f"{icon} `{v.get('task_id', '')[:8]}` — "
                    f"{v.get('reason', '')[:80]}"
                )
    else:
        st.caption("לחץ 'בקר תוצאות' לביקורת משימות שהושלמו.")

# ── Tab: Live System State ────────────────────────────────────────────────────

with tab_live_state:
    st.markdown("### מצב מערכת חי — נתונים מ-storage_agents/")

    # Load all live files
    pending   = _load_json(os.path.join(_TASKS_DIR, "pending_tasks.json"),   [])
    completed = _load_json(os.path.join(_TASKS_DIR, "completed_tasks.json"), [])
    verdicts  = _load_json(os.path.join(_TASKS_DIR, "verdicts.json"),        [])

    col_ls1, col_ls2, col_ls3 = st.columns(3)
    col_ls1.metric("📋 משימות ממתינות", len(pending))
    col_ls2.metric("✅ משימות שהושלמו", len(completed))
    col_ls3.metric("🔍 פסיקות Critic", len(verdicts))

    st.divider()

    # Director report
    latest_report_path = _latest_file(_REPORTS_DIR, "*.json")
    if latest_report_path:
        report_data = _load_json(latest_report_path, {})
        st.markdown("#### דוח Director אחרון")
        score = report_data.get("system_health_score", "—")
        summary = report_data.get("summary", "")
        ts = report_data.get("timestamp", "")[:19].replace("T", " ")
        score_color = "green" if isinstance(score, int) and score >= 80 else ("orange" if isinstance(score, int) and score >= 50 else "red")
        st.markdown(
            f"<b>ציון בריאות:</b> <span style='color:{score_color};font-weight:bold;'>{score}/100</span> &nbsp;|&nbsp; "
            f"<b>זמן:</b> {ts}",
            unsafe_allow_html=True,
        )
        if summary:
            st.info(summary)
        report_tasks = report_data.get("tasks_created", [])
        if report_tasks:
            st.markdown(f"**משימות בדוח ({len(report_tasks)}):**")
            for t in report_tasks:
                badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", ""), "⬜")
                st.markdown(f"{badge} {t.get('details', '')[:90]}")
    else:
        st.info("אין דוח Director — לחץ 'הרץ ניתוח' בחלק Director & Critic.")

    st.divider()

    # Pending tasks list
    if pending:
        with st.expander(f"📋 משימות ממתינות ({len(pending)})", expanded=False):
            for t in pending:
                badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", ""), "⬜")
                st.markdown(
                    f"{badge} **[{t.get('type','')}]** {t.get('details','')[:80]} "
                    f"<span style='color:gray;font-size:11px;'>→ {t.get('agent','')}</span>",
                    unsafe_allow_html=True,
                )

    # Verdicts list
    if verdicts:
        approved_v = sum(1 for v in verdicts if v.get("verdict") == "APPROVED")
        rejected_v = len(verdicts) - approved_v
        with st.expander(f"🔍 פסיקות Critic — ✅ {approved_v} אושרו | ❌ {rejected_v} נדחו", expanded=False):
            for v in verdicts:
                is_ok = v.get("verdict") == "APPROVED"
                icon = "✅" if is_ok else "❌"
                st.markdown(f"{icon} `{v.get('task_id','')[:8]}` — {v.get('reason','')[:80]}")

    # Food coverage (agents/logs/daily_*.json)
    latest_log_path = _latest_file(_LOGS_DIR, "daily_*.json")
    if latest_log_path:
        st.divider()
        log_data = _load_json(latest_log_path, {})
        st.markdown("#### כיסוי מזונות — דוח יומי אחרון")
        coverage = log_data.get("coverage_rate", log_data.get("coverage_pct", "—"))
        cache_size = log_data.get("cache_size", log_data.get("cached_count", "—"))
        log_date = os.path.basename(latest_log_path).replace("daily_", "").replace(".json", "")
        col_c1, col_c2, col_c3 = st.columns(3)
        col_c1.metric("📅 תאריך דוח", log_date)
        col_c2.metric("📊 כיסוי", f"{coverage}%" if isinstance(coverage, (int, float)) else str(coverage))
        col_c3.metric("🗄️ מטמון", str(cache_size))


# ── Auto-refresh ──────────────────────────────────────────────────────────────

if auto_refresh:
    time.sleep(5)
    st.rerun()
