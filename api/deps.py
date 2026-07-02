"""
Dependencies — auth, DB, shared resources
"""
import os
from dotenv import load_dotenv
# path מוחלט — עובד בכל CWD
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from fastapi import Header, HTTPException
from supabase import create_client, Client

def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    return create_client(url, key)

async def get_current_user(authorization: str = Header(None)) -> dict:
    """מאמת JWT token מ-Supabase.

    Dev bypass קיים רק כשמפעילים אותו במפורש (DEV_AUTH_BYPASS=1) *וגם* אין Supabase —
    כדי שאובדן משתנה סביבה בפרודקשן לא יחשוף את כל הנתונים כ-ui_user_001.
    """
    if os.environ.get("DEV_AUTH_BYPASS") == "1" and not os.environ.get("SUPABASE_URL"):
        return {"id": "ui_user_001", "email": "dev@bitefit.local"}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ")[1]
    try:
        sb = get_supabase()
        user = sb.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        # שמור את ה-JWT לבקשה הזו כדי שלקוח הנתונים יעבוד מול RLS
        try:
            from nutrition_app.db.supabase_client import set_api_jwt
            set_api_jwt(token)
        except Exception:
            pass
        return {"id": user.user.id, "email": user.user.email}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
