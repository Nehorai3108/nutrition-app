"""
nutrition_app/db/supabase_client.py — Re-export shim.

The canonical Supabase client lives in `auth/supabase_client.py`. This module
exists only so existing imports like
    `from nutrition_app.db.supabase_client import get_supabase`
keep working.

The canonical client already provides everything this module used to
re-implement inline: one Supabase client per Streamlit session (so JWTs never
bleed between concurrent users), JWT auto-refresh, and a forced
``client.postgrest.auth(token)`` so supabase-py v2 RLS policies
(``auth.uid() = user_id``) work on every write.
"""
from __future__ import annotations

from auth.supabase_client import (  # noqa: F401
    get_supabase,
    is_supabase_configured,
    get_current_user,
)
