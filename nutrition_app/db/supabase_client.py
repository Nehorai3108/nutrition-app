"""
nutrition_app/db/supabase_client.py — Re-export shim.

The canonical Supabase client lives in `auth/supabase_client.py`. This module
exists only so existing imports like
    `from nutrition_app.db.supabase_client import get_supabase`
keep working.
"""
from __future__ import annotations

from auth.supabase_client import (  # noqa: F401
    get_supabase,
    is_supabase_configured,
    get_current_user,
)
