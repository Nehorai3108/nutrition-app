"""Enums for the autonomy layer."""

from enum import Enum


class ActionCategory(str, Enum):
    """Categories for authority classification."""
    # AUTO-level actions (system handles alone)
    TECHNICAL_FIX = "technical_fix"
    CALCULATION = "calculation"
    DATA_PROCESSING = "data_processing"
    VALIDATION = "validation"
    RERUN_AFTER_FIX = "rerun_after_fix"
    OUTPUT_COMPARISON = "output_comparison"
    CLEANUP = "cleanup"
    OPTIMIZATION = "optimization"
    DOCUMENTATION = "documentation"
    # ESCALATE-level actions (require owner approval)
    BUSINESS_LOGIC_CHANGE = "business_logic_change"
    PRIORITY_CHANGE = "priority_change"
    ARCHITECTURE_CHANGE = "architecture_change"
    SECURITY_CHANGE = "security_change"
    PRICING_CHANGE = "pricing_change"
    DATA_DELETION = "data_deletion"
    METHODOLOGY_CHANGE = "methodology_change"
    UNCERTAIN_DECISION = "uncertain_decision"


class AuthorityLevel(str, Enum):
    """Whether system can act alone or must escalate."""
    AUTO = "auto"
    ESCALATE = "escalate"


class FeedbackType(str, Enum):
    """Types of feedback the owner can submit."""
    BAD_RESULT = "bad_result"
    WRONG_MAPPING = "wrong_mapping"
    SCREENSHOT_GAP = "screenshot_gap"
    UX_COMMENT = "ux_comment"
    PERFORMANCE_ISSUE = "performance_issue"
    DATA_ERROR = "data_error"
    FEATURE_REQUEST = "feature_request"


class FeedbackStatus(str, Enum):
    """Lifecycle status of a feedback item."""
    RECEIVED = "received"
    INVESTIGATING = "investigating"
    NEEDS_INFO = "needs_info"
    FIXED = "fixed"
    REJECTED_WITH_REASON = "rejected_with_reason"
    NEEDS_OWNER_DECISION = "needs_owner_decision"


class TaskStatus(str, Enum):
    """Full lifecycle status for tasks with anti-loop enforcement."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    FIXED = "fixed"
    VERIFIED = "verified"
    ESCALATED = "escalated"
    STUCK = "stuck"           # Terminal - never returns to IN_PROGRESS
    CLOSED = "closed"         # Only after verification_result exists


class TaskPriority(str, Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class HealStatus(str, Enum):
    """Self-healing lifecycle status."""
    DETECTED = "detected"
    DIAGNOSING = "diagnosing"
    FIX_PROPOSED = "fix_proposed"
    AUTO_FIXED = "auto_fixed"
    ESCALATED = "escalated"
    VERIFIED = "verified"
    FAILED_TO_FIX = "failed_to_fix"


class AgentId(str, Enum):
    """Identifiers for all agents in the system."""
    CONTRACTS = "agent_1_contracts"
    NUTRITION = "agent_2_nutrition"
    FOOD_CATALOG = "agent_3_food"
    INVENTORY = "agent_4_inventory"
    PLANNER = "agent_5_planner"
    AI_LAYER = "agent_6_ai"
    DATA_MANAGER = "agent_7_data_performance"
    ORCHESTRATOR = "orchestrator"
    AUTONOMY = "autonomy_system"


class ImprovementType(str, Enum):
    """Types of improvements the engine can detect."""
    DEVIATION_REDUCTION = "deviation_reduction"
    PERFORMANCE_BOOST = "performance_boost"
    CONSISTENCY_FIX = "consistency_fix"
    COVERAGE_GAP = "coverage_gap"
    QUALITY_UPLIFT = "quality_uplift"


class GoalStatus(str, Enum):
    """Status of a goal."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    BLOCKED = "blocked"
