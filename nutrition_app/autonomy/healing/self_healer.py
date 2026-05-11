"""SelfHealer V2 - proactive + reactive, confidence-gated.

Reactive: responds to stage failures
Proactive: periodic scans for deviations, recurring failures, performance issues

Boundaries (enforced):
    ALLOWED: modify context dict, rerun stages, skip invalid items, adjust portions
    FORBIDDEN: change agent code, change business rules, change architecture
    Rule: if fix needs code change -> ESCALATE
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..models.autonomy_enums import (
    ActionCategory,
    AgentId,
    AuthorityLevel,
    HealStatus,
    ImprovementType,
    TaskPriority,
)
from ..models.heal_record import HealRecord
from ..models.improvement_item import ImprovementItem
from ..models.system_metrics import SystemMetrics


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Confidence threshold for auto-fix
CONFIDENCE_THRESHOLD = 0.7


class SelfHealer:
    """
    Proactive + reactive self-healing engine.
    Confidence-gated: only auto-fixes when confidence >= 0.7.
    """

    def __init__(self):
        self._heal_history: List[HealRecord] = []

    # ─── Issue Pattern Registry ───────────────────────────────────────────
    # Maps error substrings to (root_cause, fix_strategy, confidence, action_category)
    ISSUE_PATTERNS: Dict[str, Dict[str, Any]] = {
        "food_id not found": {
            "root_cause": "stale_food_reference",
            "fix_strategy": "refresh_catalog_and_retry",
            "confidence": 0.8,
            "action_category": ActionCategory.TECHNICAL_FIX,
            "responsible_agent": AgentId.FOOD_CATALOG,
        },
        "No match found": {
            "root_cause": "unrecognized_food_item",
            "fix_strategy": "skip_unmatched_and_retry",
            "confidence": 0.75,
            "action_category": ActionCategory.TECHNICAL_FIX,
            "responsible_agent": AgentId.FOOD_CATALOG,
        },
        "Calorie deviation": {
            "root_cause": "plan_deviation_too_high",
            "fix_strategy": "adjust_portions_and_retry",
            "confidence": 0.8,
            "action_category": ActionCategory.CALCULATION,
            "responsible_agent": AgentId.PLANNER,
        },
        "Negative nutrition": {
            "root_cause": "invalid_nutrition_data",
            "fix_strategy": "remove_invalid_item_and_retry",
            "confidence": 0.85,
            "action_category": ActionCategory.DATA_PROCESSING,
            "responsible_agent": AgentId.FOOD_CATALOG,
        },
        "insufficient": {
            "root_cause": "insufficient_inventory",
            "fix_strategy": "skip_unavailable_items",
            "confidence": 0.8,
            "action_category": ActionCategory.TECHNICAL_FIX,
            "responsible_agent": AgentId.INVENTORY,
        },
        "quantity": {
            "root_cause": "quantity_error",
            "fix_strategy": "skip_unavailable_items",
            "confidence": 0.75,
            "action_category": ActionCategory.TECHNICAL_FIX,
            "responsible_agent": AgentId.INVENTORY,
        },
        "No handler registered": {
            "root_cause": "missing_handler_registration",
            "fix_strategy": None,  # Cannot auto-fix - needs code change
            "confidence": 0.0,
            "action_category": ActionCategory.ARCHITECTURE_CHANGE,
            "responsible_agent": AgentId.ORCHESTRATOR,
        },
        "contract violation": {
            "root_cause": "contract_violation",
            "fix_strategy": None,
            "confidence": 0.0,
            "action_category": ActionCategory.BUSINESS_LOGIC_CHANGE,
            "responsible_agent": AgentId.CONTRACTS,
        },
    }

    # ─── Reactive Mode ────────────────────────────────────────────────────

    def detect(
        self,
        error_message: str,
        stage: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> HealRecord:
        """Detect and create a HealRecord for a failure."""
        record = HealRecord.create(
            issue_type="stage_failure",
            issue_description=error_message,
            detected_in_stage=stage,
            detected_in_run_id=run_id,
            proactive=False,
        )
        self._heal_history.append(record)
        return record

    def diagnose(self, record: HealRecord) -> HealRecord:
        """Match error against known patterns to identify root cause."""
        record.update_status(HealStatus.DIAGNOSING)

        for pattern, info in self.ISSUE_PATTERNS.items():
            if pattern.lower() in record.issue_description.lower():
                record.root_cause = info["root_cause"]
                record.responsible_agent = info["responsible_agent"]
                record.fix_confidence = info["confidence"]
                break

        if not record.root_cause:
            record.root_cause = "unknown"
            record.fix_confidence = 0.0

        return record

    def propose_fix(self, record: HealRecord) -> Dict[str, Any]:
        """Propose a fix strategy with confidence score."""
        record.update_status(HealStatus.FIX_PROPOSED)

        for pattern, info in self.ISSUE_PATTERNS.items():
            if pattern.lower() in record.issue_description.lower():
                fix = {
                    "strategy": info["fix_strategy"],
                    "confidence": info["confidence"],
                    "action_category": info["action_category"],
                    "description": f"Apply {info['fix_strategy']} for {info['root_cause']}",
                }
                record.fix_description = fix["description"]
                record.fix_confidence = fix["confidence"]
                return fix

        return {
            "strategy": None,
            "confidence": 0.0,
            "action_category": ActionCategory.UNCERTAIN_DECISION,
            "description": "No known fix strategy for this issue",
        }

    def should_auto_fix(self, fix: Dict[str, Any], authority_level: AuthorityLevel) -> bool:
        """Confidence-gated decision: only auto-fix when confident enough."""
        if authority_level != AuthorityLevel.AUTO:
            return False
        if fix.get("strategy") is None:
            return False
        if fix.get("confidence", 0.0) < CONFIDENCE_THRESHOLD:
            return False
        return True

    def apply_fix(self, record: HealRecord, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply the fix to the context dict.
        NEVER modifies agent code - only the context passed between stages.
        Returns modified context.
        """
        strategy = None
        for pattern, info in self.ISSUE_PATTERNS.items():
            if pattern.lower() in record.issue_description.lower():
                strategy = info["fix_strategy"]
                break

        if strategy == "refresh_catalog_and_retry":
            context = self._fix_refresh_catalog(context, record)
        elif strategy == "skip_unmatched_and_retry":
            context = self._fix_skip_unmatched(context, record)
        elif strategy == "adjust_portions_and_retry":
            context = self._fix_adjust_portions(context, record)
        elif strategy == "remove_invalid_item_and_retry":
            context = self._fix_remove_invalid(context, record)
        elif strategy == "skip_unavailable_items":
            context = self._fix_skip_unavailable(context, record)

        record.fix_applied = True
        record.update_status(HealStatus.AUTO_FIXED)
        record.record_attempt(
            action=strategy or "no_strategy",
            result="fix_applied",
            confidence=record.fix_confidence,
        )

        return context

    def verify_fix(self, record: HealRecord, new_result: Dict[str, Any]) -> bool:
        """Verify that the fix resolved the issue."""
        success = new_result.get("success", False)
        record.verification_passed = success
        if success:
            record.update_status(HealStatus.VERIFIED)
        else:
            record.update_status(HealStatus.FAILED_TO_FIX)
        return success

    def escalate(self, record: HealRecord, reason: str) -> Dict[str, Any]:
        """Create escalation payload with full context."""
        record.escalation_reason = reason
        record.update_status(HealStatus.ESCALATED)
        return {
            "what_happened": record.issue_description,
            "what_we_tried": record.attempts_history,
            "why_it_failed": reason,
            "options": self._suggest_options(record),
            "impact_on_goal": f"Open failure in stage {record.detected_in_stage}",
        }

    # ─── Proactive Mode ───────────────────────────────────────────────────

    def run_proactive_scan(
        self,
        recent_runs: List[Dict[str, Any]],
        metrics: SystemMetrics,
    ) -> List[ImprovementItem]:
        """
        Periodic proactive scan. Returns improvement items for detected issues.
        Does NOT fix anything - only detects and reports.
        """
        improvements = []

        # Scan 1: Deviation trending up
        deviation_improvement = self._scan_deviation_trend(recent_runs)
        if deviation_improvement:
            improvements.append(deviation_improvement)

        # Scan 2: Recurring failures (same stage, same error 3+ times)
        failure_improvements = self._scan_recurring_failures()
        improvements.extend(failure_improvements)

        # Scan 3: Performance degradation
        perf_improvement = self._scan_performance(recent_runs)
        if perf_improvement:
            improvements.append(perf_improvement)

        # Scan 4: Consistency issues
        consistency_improvement = self._scan_consistency(recent_runs)
        if consistency_improvement:
            improvements.append(consistency_improvement)

        return improvements

    # ─── Fix Strategies (context-based, never code-based) ─────────────────

    def _fix_refresh_catalog(
        self, context: Dict[str, Any], record: HealRecord
    ) -> Dict[str, Any]:
        """Re-run food matching with medium-confidence matches promoted."""
        food_matches = context.get("resolve_foods_output", {})
        if isinstance(food_matches, dict):
            low_conf = food_matches.get("low_confidence", [])
            matches = food_matches.get("matches", [])
            # Promote medium-confidence matches
            for item in low_conf:
                if item.get("confidence_score", 0) >= 0.5:
                    matches.append(item)
            food_matches["matches"] = matches
            food_matches["low_confidence"] = [
                i for i in low_conf if i.get("confidence_score", 0) < 0.5
            ]
            context["resolve_foods_output"] = food_matches
        return context

    def _fix_skip_unmatched(
        self, context: Dict[str, Any], record: HealRecord
    ) -> Dict[str, Any]:
        """Remove unmatched items from context so planner can proceed."""
        food_matches = context.get("resolve_foods_output", {})
        if isinstance(food_matches, dict):
            food_matches["unmatched"] = []
            context["resolve_foods_output"] = food_matches
        return context

    def _fix_adjust_portions(
        self, context: Dict[str, Any], record: HealRecord
    ) -> Dict[str, Any]:
        """Add portion adjustment hint to context."""
        context["_portion_adjustment"] = {
            "scale_factor": 0.95,  # Reduce portions by 5%
            "reason": "auto_fix_deviation",
        }
        return context

    def _fix_remove_invalid(
        self, context: Dict[str, Any], record: HealRecord
    ) -> Dict[str, Any]:
        """Remove food items with invalid nutrition data."""
        food_matches = context.get("resolve_foods_output", {})
        if isinstance(food_matches, dict):
            matches = food_matches.get("matches", [])
            food_matches["matches"] = [
                m for m in matches
                if not self._has_negative_nutrition(m)
            ]
            context["resolve_foods_output"] = food_matches
        return context

    def _fix_skip_unavailable(
        self, context: Dict[str, Any], record: HealRecord
    ) -> Dict[str, Any]:
        """Mark items with insufficient inventory as not-from-inventory."""
        context["_skip_unavailable_inventory"] = True
        return context

    def _has_negative_nutrition(self, match: Dict) -> bool:
        """Check if a food match has negative nutrition values."""
        nutrition = match.get("nutrition_per_100g", {})
        for key in ("calories_kcal", "protein_g", "carbs_g", "fat_g"):
            if nutrition.get(key, 0) < 0:
                return True
        return False

    # ─── Proactive Scan Implementations ───────────────────────────────────

    def _scan_deviation_trend(
        self, recent_runs: List[Dict]
    ) -> Optional[ImprovementItem]:
        """Check if calorie deviation is trending upward."""
        deviations = []
        for run in recent_runs[-10:]:
            dev = run.get("calorie_deviation_pct")
            if dev is not None:
                deviations.append(abs(dev))

        if len(deviations) < 3:
            return None

        # Check if trending up (last 3 worse than first 3)
        first_avg = sum(deviations[:3]) / 3
        last_avg = sum(deviations[-3:]) / 3
        if last_avg > first_avg and last_avg > 3.0:
            return ImprovementItem.create(
                improvement_type=ImprovementType.DEVIATION_REDUCTION,
                description=f"Deviation trending up: {first_avg:.1f}% -> {last_avg:.1f}%",
                detected_by=AgentId.AUTONOMY,
                target_agent=AgentId.PLANNER,
                expected_vs_actual={
                    "metric": "average_deviation",
                    "expected": 5.0,
                    "actual": last_avg,
                    "gap": last_avg - 5.0,
                },
                proposed_action="Review portion calculation logic and food selection",
                priority=TaskPriority.HIGH,
            )
        return None

    def _scan_recurring_failures(self) -> List[ImprovementItem]:
        """Detect same stage + same error 3+ times."""
        improvements = []
        patterns = Counter(
            (r.detected_in_stage, r.issue_type)
            for r in self._heal_history
            if r.detected_in_stage
        )
        for (stage, issue), count in patterns.items():
            if count >= 3:
                improvements.append(ImprovementItem.create(
                    improvement_type=ImprovementType.CONSISTENCY_FIX,
                    description=(
                        f"Recurring failure: {issue} in stage {stage} "
                        f"({count} occurrences)"
                    ),
                    detected_by=AgentId.AUTONOMY,
                    target_agent=AgentId.ORCHESTRATOR,
                    expected_vs_actual={
                        "metric": "recurring_failure_count",
                        "expected": 0,
                        "actual": count,
                        "gap": count,
                    },
                    proposed_action=f"Investigate root cause of {issue} in {stage}",
                    priority=TaskPriority.HIGH,
                ))
        return improvements

    def _scan_performance(
        self, recent_runs: List[Dict]
    ) -> Optional[ImprovementItem]:
        """Check for stages getting slower over time."""
        if len(recent_runs) < 5:
            return None

        for stage_name in ("generate_meal_plan", "resolve_foods", "calculate_targets"):
            durations = []
            for run in recent_runs:
                stages = run.get("stages", {})
                stage = stages.get(stage_name, {})
                dur = stage.get("duration_ms")
                if dur:
                    durations.append(dur)

            if len(durations) < 3:
                continue

            first_avg = sum(durations[:3]) / 3
            last_avg = sum(durations[-3:]) / 3
            if last_avg > first_avg * 2 and last_avg > 1000:
                return ImprovementItem.create(
                    improvement_type=ImprovementType.PERFORMANCE_BOOST,
                    description=(
                        f"Stage {stage_name} slowing: "
                        f"{first_avg:.0f}ms -> {last_avg:.0f}ms"
                    ),
                    detected_by=AgentId.AUTONOMY,
                    target_agent=AgentId.DATA_MANAGER,
                    expected_vs_actual={
                        "metric": f"{stage_name}_duration_ms",
                        "expected": first_avg,
                        "actual": last_avg,
                        "gap": last_avg - first_avg,
                    },
                    proposed_action=f"Optimize {stage_name} stage performance",
                    priority=TaskPriority.NORMAL,
                )
        return None

    def _scan_consistency(
        self, recent_runs: List[Dict]
    ) -> Optional[ImprovementItem]:
        """Check for same inputs producing different outputs."""
        if len(recent_runs) < 2:
            return None

        # Group runs by user_id and check if targets differ
        by_user: Dict[str, List[float]] = {}
        for run in recent_runs:
            uid = run.get("user_id")
            cal = run.get("target_calories")
            if uid and cal:
                by_user.setdefault(uid, []).append(cal)

        for uid, cals in by_user.items():
            if len(cals) >= 2:
                unique = set(cals)
                if len(unique) > 1:
                    return ImprovementItem.create(
                        improvement_type=ImprovementType.CONSISTENCY_FIX,
                        description=(
                            f"Inconsistent targets for user {uid}: "
                            f"{sorted(unique)}"
                        ),
                        detected_by=AgentId.AUTONOMY,
                        target_agent=AgentId.NUTRITION,
                        expected_vs_actual={
                            "metric": "target_consistency",
                            "expected": 1,
                            "actual": len(unique),
                            "gap": len(unique) - 1,
                        },
                        proposed_action="Verify nutrition calculation determinism",
                        priority=TaskPriority.HIGH,
                    )
        return None

    def _suggest_options(self, record: HealRecord) -> List[str]:
        """Generate options for escalation."""
        options = ["Accept current state and continue"]
        if record.root_cause == "plan_deviation_too_high":
            options.extend([
                "Adjust target calories",
                "Add more food items to catalog",
                "Accept higher deviation threshold",
            ])
        elif record.root_cause == "stale_food_reference":
            options.extend([
                "Update food catalog",
                "Remove stale food references",
            ])
        elif record.root_cause == "unknown":
            options.append("Investigate manually")
        return options

    # ─── Accessors ────────────────────────────────────────────────────────

    def get_history(self, limit: int = 50) -> List[Dict]:
        return [r.to_dict() for r in self._heal_history[-limit:]]

    def get_auto_fixes(self, limit: int = 20) -> List[Dict]:
        return [
            r.to_dict() for r in self._heal_history
            if r.status in (HealStatus.AUTO_FIXED, HealStatus.VERIFIED)
        ][-limit:]

    def get_failed_fixes(self, limit: int = 20) -> List[Dict]:
        return [
            r.to_dict() for r in self._heal_history
            if r.status in (HealStatus.FAILED_TO_FIX, HealStatus.ESCALATED)
        ][-limit:]
