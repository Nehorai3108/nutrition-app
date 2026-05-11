"""AuthorityPolicy - stateless rule engine for auto vs escalate decisions.

Supreme Rule:
    Technical/computational/operational -> AUTO (system solves first)
    Business/logical/uncertain -> ESCALATE (always)
"""

from typing import Dict, Optional, Set

from ..models.autonomy_enums import ActionCategory, AgentId, AuthorityLevel


class AuthorityPolicy:
    """
    Stateless, rule-based authority engine.
    Every decision in the system flows through here.
    """

    # Supreme rule: action category -> authority level
    ACTION_AUTHORITY: Dict[ActionCategory, AuthorityLevel] = {
        # AUTO - system handles alone
        ActionCategory.TECHNICAL_FIX: AuthorityLevel.AUTO,
        ActionCategory.CALCULATION: AuthorityLevel.AUTO,
        ActionCategory.DATA_PROCESSING: AuthorityLevel.AUTO,
        ActionCategory.VALIDATION: AuthorityLevel.AUTO,
        ActionCategory.RERUN_AFTER_FIX: AuthorityLevel.AUTO,
        ActionCategory.OUTPUT_COMPARISON: AuthorityLevel.AUTO,
        ActionCategory.CLEANUP: AuthorityLevel.AUTO,
        ActionCategory.OPTIMIZATION: AuthorityLevel.AUTO,
        ActionCategory.DOCUMENTATION: AuthorityLevel.AUTO,
        # ESCALATE - requires owner approval
        ActionCategory.BUSINESS_LOGIC_CHANGE: AuthorityLevel.ESCALATE,
        ActionCategory.PRIORITY_CHANGE: AuthorityLevel.ESCALATE,
        ActionCategory.ARCHITECTURE_CHANGE: AuthorityLevel.ESCALATE,
        ActionCategory.SECURITY_CHANGE: AuthorityLevel.ESCALATE,
        ActionCategory.PRICING_CHANGE: AuthorityLevel.ESCALATE,
        ActionCategory.DATA_DELETION: AuthorityLevel.ESCALATE,
        ActionCategory.METHODOLOGY_CHANGE: AuthorityLevel.ESCALATE,
        ActionCategory.UNCERTAIN_DECISION: AuthorityLevel.ESCALATE,
    }

    # What each agent is allowed to do autonomously
    AGENT_PERMISSIONS: Dict[AgentId, Set[ActionCategory]] = {
        AgentId.CONTRACTS: {
            ActionCategory.VALIDATION,
            ActionCategory.DOCUMENTATION,
        },
        AgentId.NUTRITION: {
            ActionCategory.CALCULATION,
            ActionCategory.VALIDATION,
        },
        AgentId.FOOD_CATALOG: {
            ActionCategory.DATA_PROCESSING,
            ActionCategory.VALIDATION,
            ActionCategory.TECHNICAL_FIX,
        },
        AgentId.INVENTORY: {
            ActionCategory.DATA_PROCESSING,
            ActionCategory.VALIDATION,
            ActionCategory.TECHNICAL_FIX,
        },
        AgentId.PLANNER: {
            ActionCategory.CALCULATION,
            ActionCategory.VALIDATION,
            ActionCategory.OPTIMIZATION,
        },
        AgentId.AI_LAYER: {
            ActionCategory.DATA_PROCESSING,
            ActionCategory.DOCUMENTATION,
        },
        AgentId.DATA_MANAGER: {
            ActionCategory.CLEANUP,
            ActionCategory.OPTIMIZATION,
            ActionCategory.DATA_PROCESSING,
            ActionCategory.VALIDATION,
        },
        AgentId.ORCHESTRATOR: {
            ActionCategory.RERUN_AFTER_FIX,
            ActionCategory.VALIDATION,
            ActionCategory.OUTPUT_COMPARISON,
        },
        AgentId.AUTONOMY: {
            ActionCategory.TECHNICAL_FIX,
            ActionCategory.RERUN_AFTER_FIX,
            ActionCategory.VALIDATION,
            ActionCategory.OUTPUT_COMPARISON,
            ActionCategory.CLEANUP,
            ActionCategory.OPTIMIZATION,
        },
    }

    # Keyword-based action classification (Hebrew + English)
    _CLASSIFICATION_KEYWORDS: Dict[ActionCategory, list] = {
        ActionCategory.TECHNICAL_FIX: [
            "fix", "repair", "patch", "תיקון", "תקלה", "bug",
            "error", "exception", "שגיאה",
        ],
        ActionCategory.CALCULATION: [
            "calculate", "compute", "bmr", "tdee", "macro", "calorie",
            "חישוב", "קלוריות", "מאקרו",
        ],
        ActionCategory.DATA_PROCESSING: [
            "process", "parse", "transform", "normalize", "עיבוד", "נתונים",
            "match", "search", "food", "מזון", "התאמה",
        ],
        ActionCategory.VALIDATION: [
            "validate", "check", "verify", "test", "assert",
            "בדיקה", "אימות", "תקינות",
        ],
        ActionCategory.RERUN_AFTER_FIX: [
            "rerun", "retry", "re-execute", "הרצה מחדש",
        ],
        ActionCategory.OUTPUT_COMPARISON: [
            "compare", "diff", "deviation", "השוואה", "סטייה",
        ],
        ActionCategory.CLEANUP: [
            "cleanup", "clean", "remove", "delete stale", "ניקוי", "מחיקת",
            "duplicate", "כפילות", "orphan",
        ],
        ActionCategory.OPTIMIZATION: [
            "optimize", "performance", "speed", "אופטימיזציה", "ביצועים",
            "compress", "compact",
        ],
        ActionCategory.DOCUMENTATION: [
            "document", "log", "record", "תיעוד",
        ],
        ActionCategory.BUSINESS_LOGIC_CHANGE: [
            "business", "logic", "rule change", "formula change",
            "לוגיקה עסקית", "שינוי חוק", "שינוי נוסחה",
        ],
        ActionCategory.PRIORITY_CHANGE: [
            "priority", "reorder", "עדיפות", "סדר עדיפויות",
        ],
        ActionCategory.ARCHITECTURE_CHANGE: [
            "architecture", "refactor major", "restructure",
            "ארכיטקטורה", "מבנה מערכת",
        ],
        ActionCategory.SECURITY_CHANGE: [
            "security", "auth", "permission", "אבטחה", "הרשאות",
        ],
        ActionCategory.METHODOLOGY_CHANGE: [
            "methodology", "approach", "strategy", "מתודולוגיה", "גישה",
        ],
    }

    def check_authority(self, action: ActionCategory) -> AuthorityLevel:
        """Check if an action category requires escalation or is auto-allowed."""
        return self.ACTION_AUTHORITY.get(action, AuthorityLevel.ESCALATE)

    def can_agent_perform(self, agent: AgentId, action: ActionCategory) -> bool:
        """Check if a specific agent is allowed to perform this action category."""
        if self.check_authority(action) == AuthorityLevel.ESCALATE:
            return False
        allowed = self.AGENT_PERMISSIONS.get(agent, set())
        return action in allowed

    def classify_action(
        self, description: str, context: Optional[Dict] = None
    ) -> ActionCategory:
        """
        Classify an action based on description and context.
        Context keys take priority over keyword matching.
        Returns UNCERTAIN_DECISION if no match (which triggers ESCALATE).
        """
        context = context or {}

        # Context-based classification (high priority)
        if context.get("error_type") == "validation_error":
            return ActionCategory.VALIDATION
        if context.get("error_type") == "calculation_error":
            return ActionCategory.CALCULATION
        if context.get("change_type") == "formula_change":
            return ActionCategory.METHODOLOGY_CHANGE
        if context.get("change_type") == "business_rule":
            return ActionCategory.BUSINESS_LOGIC_CHANGE
        if context.get("change_type") == "architecture":
            return ActionCategory.ARCHITECTURE_CHANGE
        if context.get("is_rerun"):
            return ActionCategory.RERUN_AFTER_FIX
        if context.get("is_cleanup"):
            return ActionCategory.CLEANUP

        # Keyword-based classification
        desc_lower = description.lower()
        best_match = None
        best_score = 0

        for category, keywords in self._CLASSIFICATION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in desc_lower)
            if score > best_score:
                best_score = score
                best_match = category

        if best_match and best_score > 0:
            return best_match

        # No match -> uncertain -> escalate
        return ActionCategory.UNCERTAIN_DECISION
