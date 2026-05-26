"""
nutrition_app.utils — shared utilities package.
Backward-compatible: exposes utcnow() that was previously in utils.py
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now. Replaces deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)
