from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.deps import get_supabase

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str = ""

@router.post("/login")
def login(body: LoginRequest):
    try:
        sb = get_supabase()
        res = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "access_token":  res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "user_id":       res.user.id,
            "email":         res.user.email,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/signup")
def signup(body: SignupRequest):
    try:
        sb = get_supabase()
        res = sb.auth.sign_up({"email": body.email, "password": body.password})
        return {
            "access_token":  res.session.access_token if res.session else None,
            "user_id":       res.user.id,
            "email":         res.user.email,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/refresh")
def refresh(refresh_token: str):
    try:
        sb = get_supabase()
        res = sb.auth.refresh_session(refresh_token)
        return {
            "access_token":  res.session.access_token,
            "refresh_token": res.session.refresh_token,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
