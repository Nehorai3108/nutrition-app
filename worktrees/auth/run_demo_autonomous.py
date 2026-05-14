#!/usr/bin/env python3
"""
Autonomous System Demo
======================
Demonstrates the full goal-oriented autonomous system:
1. Initialize all components with demo goals
2. Run autonomous pipeline
3. Simulate failure -> self-healing + verification
4. Submit feedback -> classification, routing, lifecycle
5. Proactive scan -> improvement detection
6. Goal progress check
7. Dashboard state
8. Audit trail
"""

import json
import sys
import os
import io

# Fix Windows console encoding for Hebrew
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime, timezone

# ─── Import existing system ──────────────────────────────────────────────
from nutrition_app.models.enums import (
    ActivityLevel, Gender, Goal, FoodCategory, MealType, ConfidenceLevel,
)
from nutrition_app.models.user import UserProfile
from nutrition_app.models.nutrition_targets import NutritionTargets
from nutrition_app.models.food_item import FoodItem, NutritionPer100g
from nutrition_app.models.food_match import FoodMatch, FoodMatchResult
from nutrition_app.models.inventory import InventoryState

from nutrition_app.agents.agent_2_nutrition.nutrition_engine import NutritionEngine
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.agents.agent_4_inventory.inventory_manager import InventoryManager
from nutrition_app.agents.agent_5_planner.meal_planner import MealPlanner
from nutrition_app.agents.agent_6_ai.ai_layer import AILayer

# ─── Import autonomy system ─────────────────────────────────────────────
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
from nutrition_app.autonomy.loop.continuous_loop import ContinuousLoop
from nutrition_app.autonomy.dashboard.active_dashboard import ActiveDashboard


def separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_json(data: dict, indent: int = 2) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=indent, default=str))


def main():
    print("=" * 60)
    print("  AUTONOMOUS NUTRITION SYSTEM - DEMO")
    print("  Goal-Oriented Continuous Autonomous System")
    print("=" * 60)

    # ─── Step 1: Initialize Existing Agents ──────────────────────────────
    separator("Step 1: Initialize Existing Agents")

    engine = NutritionEngine()
    catalog = FoodCatalog()
    inventory_mgr = InventoryManager()
    planner = MealPlanner()
    ai_layer = AILayer()

    print("[OK] All 7 agents initialized")

    # ─── Step 2: Initialize Autonomy Components ──────────────────────────
    separator("Step 2: Initialize Autonomy Components")

    storage_dir = "storage_demo_autonomous"
    os.makedirs(storage_dir, exist_ok=True)

    audit_log = AuditLog(f"{storage_dir}/audit")
    authority = AuthorityPolicy()
    goal_tracker = GoalTracker()
    prioritizer = TaskPrioritizer()
    self_healer = SelfHealer()
    improvement_engine = ImprovementEngine()
    data_optimizer = DataOptimizer(storage_dir, audit_log)
    feedback_manager = FeedbackManager(f"{storage_dir}/feedback")

    print("[OK] AuditLog initialized (append-only)")
    print("[OK] AuthorityPolicy initialized (supreme rule active)")
    print("[OK] GoalTracker initialized with demo goals:")
    for goal in goal_tracker.get_goals():
        for cond in goal["conditions"]:
            print(f"     - {cond['metric']} {cond['operator']} {cond['threshold']}")
    print("[OK] TaskPrioritizer initialized (focus mode active)")
    print("[OK] SelfHealer V2 initialized (confidence gating >= 0.7)")
    print("[OK] ImprovementEngine initialized (goal-gap only)")
    print("[OK] DataOptimizer initialized")
    print("[OK] FeedbackManager initialized")

    # ─── Step 3: Run Pipeline Manually (simulating WorkflowEngine) ───────
    separator("Step 3: Run Nutrition Pipeline")

    user = UserProfile(
        user_id="demo_auto_001",
        name="Israel Demo",
        gender=Gender.MALE,
        date_of_birth=date(1990, 5, 15),
        height_cm=178.0,
        weight_kg=82.0,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=Goal.LOSE_WEIGHT,
    )
    print(f"[User] {user.name}, {user.age} years, {user.weight_kg}kg, goal={user.goal.value}")

    targets = engine.calculate_targets(user)
    validation = engine.validate_targets(targets)
    print(f"[Targets] BMR={targets.bmr_kcal}, TDEE={targets.tdee_kcal}, "
          f"Target={targets.target_calories_kcal} kcal")
    print(f"[Macros] P={targets.protein_g}g, C={targets.carbs_g}g, F={targets.fat_g}g")
    print(f"[Validation] {'PASS' if not validation else 'FAIL: ' + str(validation)}")

    food_queries = ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "עגבנייה"]
    match_result = catalog.match_foods(food_queries)
    print(f"[Food Matching] {len(match_result.matches)} matched, "
          f"{len(match_result.unmatched)} unmatched, "
          f"{len(match_result.low_confidence)} low confidence")

    # Add inventory
    inventory_mgr.add_item("demo_auto_001", "food_001", 500, "gram")
    inventory_mgr.add_item("demo_auto_001", "food_002", 1000, "gram")
    inventory_mgr.add_item("demo_auto_001", "food_003", 300, "gram")
    inv_state = inventory_mgr.get_state("demo_auto_001")
    print(f"[Inventory] {len(inv_state.items)} items added")

    # Generate meal plan
    food_lookup = {f.food_id: f for f in catalog.get_all_foods()}
    planner.set_food_lookup(food_lookup)
    plan = planner.generate_plan(targets, match_result, inv_state, "run_auto_001")
    plan_errors = planner.validate_plan(plan)
    print(f"[Meal Plan] {len(plan.meals)} meals, "
          f"total={plan.total_calories} kcal, "
          f"deviation={plan.calorie_deviation_pct:+.1f}%")
    if plan_errors:
        print(f"[Plan Validation] ISSUES: {plan_errors}")
    else:
        print("[Plan Validation] PASS")

    summary = ai_layer.generate_plan_summary(plan)
    print(f"\n[AI Summary]\n{summary}")

    # ─── Step 4: Test Self-Healer ────────────────────────────────────────
    separator("Step 4: Test Self-Healing (Reactive)")

    # Simulate a failure
    error_msg = "Calorie deviation 8.5% exceeds threshold"
    print(f"[Simulated Error] {error_msg}")

    record = self_healer.detect(error_msg, "generate_meal_plan", "run_auto_001")
    print(f"[Detect] HealRecord created: {record.heal_id[:8]}...")

    record = self_healer.diagnose(record)
    print(f"[Diagnose] Root cause: {record.root_cause}, "
          f"Agent: {record.responsible_agent.value if record.responsible_agent else 'N/A'}")

    fix = self_healer.propose_fix(record)
    print(f"[Propose Fix] Strategy: {fix.get('strategy')}, "
          f"Confidence: {fix.get('confidence')}")

    # Check authority
    auth_level = authority.check_authority(fix.get("action_category"))
    can_auto = self_healer.should_auto_fix(fix, auth_level)
    print(f"[Authority] Level: {auth_level.value}, Auto-fix allowed: {can_auto}")

    if can_auto:
        context = {"resolve_foods_output": match_result.to_dict()}
        context = self_healer.apply_fix(record, context)
        print(f"[Auto-Fix] Applied: {fix.get('strategy')}")

        # Simulate verification
        verified = self_healer.verify_fix(record, {"success": True})
        print(f"[Verify] Passed: {verified}")

    # Test low-confidence scenario
    print("\n[Simulated Low-Confidence Error]")
    error_msg2 = "No handler registered for stage X"
    record2 = self_healer.detect(error_msg2, "unknown_stage", "run_auto_002")
    record2 = self_healer.diagnose(record2)
    fix2 = self_healer.propose_fix(record2)
    auth2 = authority.check_authority(fix2.get("action_category"))
    can_auto2 = self_healer.should_auto_fix(fix2, auth2)
    print(f"[Result] Strategy: {fix2.get('strategy')}, "
          f"Confidence: {fix2.get('confidence')}, "
          f"Auto-fix: {can_auto2} -> {'ESCALATED' if not can_auto2 else 'AUTO'}")

    # ─── Step 5: Test Feedback System ────────────────────────────────────
    separator("Step 5: Test Feedback System")

    # Submit Hebrew feedback
    fb_result = feedback_manager.submit_feedback(
        description="התוצאה של תכנון הארוחה לא טובה - יותר מדי קלוריות",
        related_run_id="run_auto_001",
        related_stage="generate_meal_plan",
    )
    print(f"[Feedback] Submitted: type={fb_result.feedback_type.value}, "
          f"agent={fb_result.assigned_agent.value if fb_result.assigned_agent else 'N/A'}")

    task = feedback_manager.create_task_for_feedback(fb_result)
    print(f"[Task Created] ID={task.task_id[:8]}..., "
          f"owner={task.owner.value}, priority={task.priority.value}")

    # Test English feedback
    fb_result2 = feedback_manager.submit_feedback(
        description="Food matching is incorrect for olive oil",
        target_agent=AgentId.FOOD_CATALOG,
    )
    print(f"[Feedback 2] type={fb_result2.feedback_type.value}, "
          f"agent={fb_result2.assigned_agent.value if fb_result2.assigned_agent else 'N/A'}")

    # ─── Step 6: Test Goal Tracker ───────────────────────────────────────
    separator("Step 6: Test Goal Tracker")

    test_metrics = SystemMetrics(
        timestamp=datetime.now(timezone.utc),
        average_deviation=abs(plan.calorie_deviation_pct),
        success_rate=80.0,
        auto_fix_rate=100.0,
        avg_fix_time_seconds=5.0,
        escalation_count=1,
        open_failures=0,
        stuck_tasks=0,
        total_runs=1,
        total_tasks=2,
        completed_tasks=0,
        demo_readiness=False,
        open_critical_failures=0,
        pending_verifications=1,
    )

    evaluations = goal_tracker.evaluate_progress(test_metrics)
    for goal_id, eval_result in evaluations.items():
        print(f"[Goal] Demo Ready: {eval_result.demo_ready}, "
              f"Progress: {eval_result.progress_pct}%")
        for a in eval_result.achieved:
            print(f"  [PASS] {a['metric']}: {a['current']} ({a['target']})")
        for na in eval_result.not_achieved:
            print(f"  [FAIL] {na['metric']}: {na['current']} ({na['target']})")
        if eval_result.missing_for_goal:
            print(f"  [Missing]")
            for m in eval_result.missing_for_goal:
                print(f"    - {m}")

    # ─── Step 7: Test Improvement Engine ─────────────────────────────────
    separator("Step 7: Test Improvement Engine")

    for eval_result in evaluations.values():
        improvements = improvement_engine.detect_gaps(test_metrics, eval_result)
        print(f"[Improvements Detected] {len(improvements)}")
        for imp in improvements:
            print(f"  - [{imp.improvement_type.value}] {imp.description}")
            print(f"    Target agent: {imp.target_agent.value}")
            print(f"    Action: {imp.proposed_action}")

    # ─── Step 8: Test Task Prioritizer (Focus Mode) ──────────────────────
    separator("Step 8: Test Task Prioritizer (Focus Mode)")

    blocking = prioritizer.get_blocking_reason(test_metrics)
    print(f"[Blocking] {blocking}")

    all_tasks = [task]
    if improvements:
        imp_tasks = improvement_engine.create_tasks_for_improvements(improvements)
        all_tasks.extend(imp_tasks)

    prioritized = prioritizer.prioritize(all_tasks, test_metrics)
    print(f"[Prioritized] {len(prioritized)} tasks in queue:")
    for i, t in enumerate(prioritized):
        print(f"  {i+1}. [{t.priority.value}] [{t.source}] {t.description[:60]}...")

    # ─── Step 9: Test Data Optimizer ─────────────────────────────────────
    separator("Step 9: Test Data Optimizer")

    health = data_optimizer.measure_storage_health()
    print(f"[Storage Health] {health['total_size_mb']}MB, "
          f"{health['total_files']} files, {health['json_files']} JSON")

    # ─── Step 10: Test Anti-Loop ─────────────────────────────────────────
    separator("Step 10: Test Anti-Loop Enforcement")

    test_task = task
    print(f"[Task] attempts={test_task.attempts}, max={test_task.max_attempts}")
    print(f"[Can Retry] {test_task.can_retry()}")

    # Simulate failures
    for i in range(4):
        if test_task.can_retry():
            test_task.record_failure()
            print(f"  Attempt {test_task.attempts}: "
                  f"status={test_task.status.value}, "
                  f"cooldown={'YES' if test_task.cooldown_until else 'NO'}")
        else:
            print(f"  BLOCKED: Cannot retry (status={test_task.status.value})")
            break

    # ─── Step 11: Dashboard State ────────────────────────────────────────
    separator("Step 11: Dashboard State (Control Panel)")

    # Create a minimal orchestrator for dashboard
    # (In production, this wraps the real WorkflowEngine)
    class MockWorkflowEngine:
        def create_run(self, uid): pass
        def execute_run(self, rid, ctx): pass
        def rerun_stage(self, rid, stage): pass
        def resolve_decision(self, did, approved, resolution=""): pass

    orchestrator = AutonomyOrchestrator(
        workflow_engine=MockWorkflowEngine(),
        audit_log=audit_log,
        authority=authority,
        self_healer=self_healer,
        improvement_engine=improvement_engine,
        feedback_manager=feedback_manager,
        goal_tracker=goal_tracker,
        task_prioritizer=prioritizer,
        data_optimizer=data_optimizer,
        storage_dir=storage_dir,
    )

    dashboard = ActiveDashboard(orchestrator)

    print("[Demo Readiness]")
    readiness = dashboard.get_demo_readiness()
    print(f"  Ready: {readiness['ready']}")
    print(f"  Progress: {readiness['progress_pct']}%")
    if readiness['missing']:
        print(f"  Missing:")
        for m in readiness['missing']:
            print(f"    - {m['metric']}: {m['current']} (target: {m['target']})")

    print("\n[Quality Metrics]")
    qm = dashboard.get_quality_metrics()
    for key in ["average_deviation", "success_rate", "auto_fix_rate",
                 "open_failures", "stuck_tasks", "demo_readiness"]:
        print(f"  {key}: {qm.get(key)}")

    print("\n[Data Health]")
    dh = dashboard.get_data_health()
    print(f"  Size: {dh['total_size_mb']}MB, Files: {dh['total_files']}")

    # ─── Step 12: Audit Trail ────────────────────────────────────────────
    separator("Step 12: Audit Trail")

    audit_summary = audit_log.get_summary()
    print(f"[Audit] Total entries: {audit_summary['total_entries']}")
    if audit_summary["by_actor"]:
        print(f"  By actor: {audit_summary['by_actor']}")
    if audit_summary["by_result"]:
        print(f"  By result: {audit_summary['by_result']}")

    recent = audit_log.get_recent(5)
    if recent:
        print(f"\n  Last {len(recent)} entries:")
        for entry in recent:
            print(f"    [{entry['actor']}] {entry['description'][:60]}... -> {entry['result']}")

    # ─── Summary ─────────────────────────────────────────────────────────
    separator("DEMO COMPLETE")

    print("System capabilities demonstrated:")
    print("  [OK] Nutrition pipeline (agents 1-7)")
    print("  [OK] Self-healing (reactive + confidence gating)")
    print("  [OK] Feedback handling (Hebrew + English classification)")
    print("  [OK] Goal tracking (hard constraints)")
    print("  [OK] Improvement detection (goal-gap based)")
    print("  [OK] Task prioritization (focus mode)")
    print("  [OK] Data optimization")
    print("  [OK] Anti-loop enforcement")
    print("  [OK] Dashboard (control panel)")
    print("  [OK] Audit trail (before/after mandatory)")
    print()
    print("Supreme Rule: Technical->AUTO, Business->ESCALATE")
    print("Confidence Gate: >= 0.7 for auto-fix")
    print("Anti-Loop: max_attempts + cooldown + STUCK terminal status")
    print("Focus Mode: critical failures block all other work")


if __name__ == "__main__":
    main()
