"""
Dependencies — auth, DB, shared resources
"""
import os
from fastapi import Header, HTTPException
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def get_current_user(authorization: str = Header(None)) -> dict:
    """מאמת JWT token מ-Supabase. אם Supabase לא מוגדר — dev bypass."""
    if not SUPABASE_URL:
        return {"id": "ui_user_001", "email": "dev@bitefit.local"}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ")[1]
    try:
        sb = get_supabase()
        user = sb.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": user.user.id, "email": user.user.email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
