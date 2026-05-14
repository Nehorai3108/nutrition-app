"""SystemMetrics - snapshot of system state used for all decisions."""

from dataclasses import dataclass
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SystemMetrics:
    """
    Every decision in the system is based on these metrics.
    No event-driven actions - metrics drive everything.
    """
    timestamp: datetime
    average_deviation: float        # Mean calorie deviation % across recent runs
    success_rate: float             # % of runs completing without failures (0-100)
    auto_fix_rate: float            # % of failures auto-resolved (0-100)
    avg_fix_time_seconds: float     # Mean time from failure to verified fix
    escalation_count: int           # Number of items pending owner decision
    open_failures: int              # Unresolved failures
    stuck_tasks: int                # Tasks marked STUCK
    total_runs: int                 # Total pipeline runs executed
    total_tasks: int                # Total tasks in system
    completed_tasks: int            # Tasks that reached CLOSED
    demo_readiness: bool            # Calculated by GoalTracker
    open_critical_failures: int     # Critical priority failures (for focus mode)
    pending_verifications: int      # Tasks in FIXED awaiting verification

    def as_dict_for_goals(self) -> dict:
        """Returns metrics as a flat dict for GoalTracker evaluation."""
        return {
            "average_deviation": self.average_deviation,
            "success_rate": self.success_rate,
            "auto_fix_rate": self.auto_fix_rate,
            "avg_fix_time_seconds": self.avg_fix_time_seconds,
            "escalation_count": self.escalation_count,
            "open_failures": self.open_failures,
            "stuck_tasks": self.stuck_tasks,
            "total_runs": self.total_runs,
            "open_critical_failures": self.open_critical_failures,
            "pending_verifications": self.pending_verifications,
        }

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "average_deviation": self.average_deviation,
            "success_rate": self.success_rate,
            "auto_fix_rate": self.auto_fix_rate,
            "avg_fix_time_seconds": self.avg_fix_time_seconds,
            "escalation_count": self.escalation_count,
            "open_failures": self.open_failures,
            "stuck_tasks": self.stuck_tasks,
            "total_runs": self.total_runs,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "demo_readiness": self.demo_readiness,
            "open_critical_failures": self.open_critical_failures,
            "pending_verifications": self.pending_verifications,
        }

    @classmethod
    def empty(cls) -> "SystemMetrics":
        """Initial empty metrics."""
        return cls(
            timestamp=_utcnow(),
            average_deviation=0.0,
            success_rate=0.0,
            auto_fix_rate=0.0,
            avg_fix_time_seconds=0.0,
            escalation_count=0,
            open_failures=0,
            stuck_tasks=0,
            total_runs=0,
            total_tasks=0,
            completed_tasks=0,
            demo_readiness=False,
            open_critical_failures=0,
            pending_verifications=0,
        )
