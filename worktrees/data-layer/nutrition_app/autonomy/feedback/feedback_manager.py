"""FeedbackManager - classify, route, track, auto-resolve owner feedback.

Flow:
    Owner submits feedback -> classify -> route to agent -> create TaskItem
    -> agent processes -> fix -> verify -> CLOSED
    No manual system restart needed.
"""

import json
import os
import re
import unicodedata
from typing import Dict, List, Optional

from ..models.autonomy_enums import (
    AgentId,
    FeedbackStatus,
    FeedbackType,
    TaskPriority,
    TaskStatus,
)
from ..models.feedback_item import FeedbackItem
from ..models.task_item import TaskItem


class FeedbackManager:
    """
    Manages the full lifecycle of owner feedback.
    Classifies (Hebrew+English), routes, creates tasks, tracks resolution.
    """

    def __init__(self, storage_dir: str = "storage/feedback"):
        self._items: List[FeedbackItem] = []
        self._storage_dir = storage_dir
        os.makedirs(self._storage_dir, exist_ok=True)

    # ─── Classification Keywords (Hebrew + English) ───────────────────────
    _CLASSIFICATION_KEYWORDS: Dict[FeedbackType, List[str]] = {
        FeedbackType.BAD_RESULT: [
            "result", "wrong", "incorrect", "bad", "תוצאה", "שגוי", "לא נכון",
            "לא טוב", "טעות", "שגיאה",
        ],
        FeedbackType.WRONG_MAPPING: [
            "mapping", "match", "food", "מיפוי", "התאמה", "מזון",
            "לא מתאים", "זיהוי שגוי",
        ],
        FeedbackType.SCREENSHOT_GAP: [
            "screenshot", "screen", "image", "visual", "צילום", "מסך",
            "תמונה", "פער ויזואלי",
        ],
        FeedbackType.UX_COMMENT: [
            "ux", "ui", "interface", "design", "text", "format",
            "ממשק", "עיצוב", "טקסט", "פורמט", "תצוגה",
        ],
        FeedbackType.PERFORMANCE_ISSUE: [
            "slow", "performance", "speed", "time", "איטי", "ביצועים",
            "מהירות", "זמן",
        ],
        FeedbackType.DATA_ERROR: [
            "data", "database", "missing", "corrupt", "נתון", "חסר",
            "מידע", "בסיס נתונים",
        ],
        FeedbackType.FEATURE_REQUEST: [
            "feature", "add", "new", "want", "פיצ'ר", "תוסיף",
            "חדש", "רוצה", "אפשרות",
        ],
    }

    # ─── Routing Table ────────────────────────────────────────────────────
    _DEFAULT_ROUTING: Dict[FeedbackType, AgentId] = {
        FeedbackType.BAD_RESULT: AgentId.AUTONOMY,       # Needs triage
        FeedbackType.WRONG_MAPPING: AgentId.FOOD_CATALOG,
        FeedbackType.SCREENSHOT_GAP: AgentId.AI_LAYER,
        FeedbackType.UX_COMMENT: AgentId.AI_LAYER,
        FeedbackType.PERFORMANCE_ISSUE: AgentId.DATA_MANAGER,
        FeedbackType.DATA_ERROR: AgentId.DATA_MANAGER,
        FeedbackType.FEATURE_REQUEST: AgentId.AUTONOMY,  # Escalates to owner
    }

    # Stage-based routing override for BAD_RESULT
    _STAGE_ROUTING: Dict[str, AgentId] = {
        "calculate_targets": AgentId.NUTRITION,
        "resolve_foods": AgentId.FOOD_CATALOG,
        "check_inventory": AgentId.INVENTORY,
        "generate_meal_plan": AgentId.PLANNER,
        "present_decision": AgentId.AI_LAYER,
        "deduct_inventory": AgentId.INVENTORY,
    }

    # ─── Public API ───────────────────────────────────────────────────────

    def submit_feedback(
        self,
        description: str,
        feedback_type: Optional[FeedbackType] = None,
        related_run_id: Optional[str] = None,
        related_stage: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
        target_agent: Optional[AgentId] = None,
    ) -> FeedbackItem:
        """
        Submit feedback from owner. Auto-classifies if type not specified.
        Returns the created FeedbackItem.
        """
        # Classify if not provided
        if feedback_type is None:
            feedback_type = self.classify(description)

        item = FeedbackItem.create(
            feedback_type=feedback_type,
            description=description,
            related_run_id=related_run_id,
            related_stage=related_stage,
            attachment_paths=attachment_paths,
        )

        # Route to agent
        if target_agent:
            item.assigned_agent = target_agent
        else:
            item.assigned_agent = self.route(
                feedback_type, related_stage
            )

        self._items.append(item)
        self._persist()
        return item

    def create_task_for_feedback(self, feedback: FeedbackItem) -> TaskItem:
        """Create a TaskItem linked to the feedback for the assigned agent."""
        priority = self._feedback_priority(feedback.feedback_type)
        task = TaskItem.create(
            owner=feedback.assigned_agent or AgentId.AUTONOMY,
            priority=priority,
            description=f"[Feedback] {feedback.feedback_type.value}: {feedback.description}",
            source="feedback",
            related_feedback_id=feedback.feedback_id,
        )
        feedback.linked_task_id = task.task_id
        feedback.update_status(FeedbackStatus.INVESTIGATING, "task_created")
        self._persist()
        return task

    def update_feedback_status(
        self, feedback_id: str, status: FeedbackStatus, reason: str
    ) -> Optional[FeedbackItem]:
        """Update feedback status."""
        for item in self._items:
            if item.feedback_id == feedback_id:
                item.update_status(status, reason)
                self._persist()
                return item
        return None

    def resolve_feedback(
        self, feedback_id: str, resolution: str
    ) -> Optional[FeedbackItem]:
        """Mark feedback as resolved."""
        for item in self._items:
            if item.feedback_id == feedback_id:
                item.resolution = resolution
                item.update_status(FeedbackStatus.FIXED, resolution)
                self._persist()
                return item
        return None

    def get_pending(self) -> List[Dict]:
        """Get all unresolved feedback items."""
        return [
            item.to_dict() for item in self._items
            if item.status not in (
                FeedbackStatus.FIXED,
                FeedbackStatus.REJECTED_WITH_REASON,
            )
        ]

    def get_all(self) -> List[Dict]:
        return [item.to_dict() for item in self._items]

    # ─── Classification ───────────────────────────────────────────────────

    def classify(self, description: str) -> FeedbackType:
        """Classify feedback using Hebrew+English keyword matching."""
        normalized = self._normalize(description)
        best_type = FeedbackType.BAD_RESULT  # Default
        best_score = 0

        for ftype, keywords in self._CLASSIFICATION_KEYWORDS.items():
            score = sum(
                1 for kw in keywords
                if kw.lower() in normalized
            )
            if score > best_score:
                best_score = score
                best_type = ftype

        return best_type

    def route(
        self, feedback_type: FeedbackType, stage: Optional[str] = None
    ) -> AgentId:
        """Route feedback to responsible agent."""
        # Stage-specific routing for BAD_RESULT
        if feedback_type == FeedbackType.BAD_RESULT and stage:
            agent = self._STAGE_ROUTING.get(stage)
            if agent:
                return agent

        return self._DEFAULT_ROUTING.get(feedback_type, AgentId.AUTONOMY)

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _normalize(self, text: str) -> str:
        """Normalize text for keyword matching (same as FoodCatalog approach)."""
        text = text.strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[^\w\s\u0590-\u05FF]", "", text)
        return text

    def _feedback_priority(self, ftype: FeedbackType) -> TaskPriority:
        """Map feedback type to task priority."""
        priority_map = {
            FeedbackType.BAD_RESULT: TaskPriority.HIGH,
            FeedbackType.WRONG_MAPPING: TaskPriority.HIGH,
            FeedbackType.SCREENSHOT_GAP: TaskPriority.NORMAL,
            FeedbackType.UX_COMMENT: TaskPriority.LOW,
            FeedbackType.PERFORMANCE_ISSUE: TaskPriority.NORMAL,
            FeedbackType.DATA_ERROR: TaskPriority.HIGH,
            FeedbackType.FEATURE_REQUEST: TaskPriority.LOW,
        }
        return priority_map.get(ftype, TaskPriority.NORMAL)

    def _persist(self) -> None:
        """Save all feedback items to disk."""
        path = os.path.join(self._storage_dir, "feedback.json")
        data = [item.to_dict() for item in self._items]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
