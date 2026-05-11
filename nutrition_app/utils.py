"""
Shared utilities.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now. Replaces deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)
