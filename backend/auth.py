"""Auth router: register, login, me, logout, refresh."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from limiter import limiter

JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 60 * 24  # 1 day for typing app convenience
REFRESH_TTL_DAYS = 30

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), h.encode("utf-8"))
    except Exception:
        return False


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def _set_auth_cookies(response: Response, access: str, refresh: str):
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TTL_MIN * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=REFRESH_TTL_DAYS * 24 * 3600,
        path="/",
    )


async def ensure_indexes(db):
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.sessions.create_index("id", unique=True)
    await db.sessions.create_index([("user_id", 1), ("created_at", -1)])


def _user_public(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user.get("role", "user"),
        "daily_goal": user.get("daily_goal", 3),
        "created_at": user.get("created_at"),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        db = request.app.state.db
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------- schemas ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: Optional[str] = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginIn(BaseModel):
    credential: str

class UpdateProfileIn(BaseModel):
    name: Optional[str] = None
    daily_goal: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)


# ---------- endpoints ----------
@router.post("/register")
@limiter.limit("5/minute")
async def register(payload: RegisterIn, request: Request, response: Response):
    db = request.app.state.db
    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": (payload.name or email.split("@")[0]).strip(),
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    access = create_access_token(user_doc["id"], email)
    refresh = create_refresh_token(user_doc["id"])
    _set_auth_cookies(response, access, refresh)
    return {"user": _user_public(user_doc), "token": access}


@router.post("/login")
@limiter.limit("5/minute")
async def login(payload: LoginIn, request: Request, response: Response):
    db = request.app.state.db
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user["id"] = user.get("id") or str(user.get("_id"))
    access = create_access_token(user["id"], email)
    refresh = create_refresh_token(user["id"])
    _set_auth_cookies(response, access, refresh)
    return {"user": _user_public(user), "token": access}

@router.post("/google")
@limiter.limit("5/minute")
async def google_login(payload: GoogleLoginIn, request: Request, response: Response):
    db = request.app.state.db
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="Google Auth is not configured on the server")
        
    try:
        id_info = id_token.verify_oauth2_token(
            payload.credential, 
            google_requests.Request(), 
            client_id
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = id_info.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
        
    user = await db.users.find_one({"email": email})
    if not user:
        # Create user
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "password_hash": hash_password(str(uuid.uuid4())), # random password
            "name": id_info.get("name", email.split("@")[0]).strip(),
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user)
        
    access = create_access_token(user["id"], email)
    refresh = create_refresh_token(user["id"])
    _set_auth_cookies(response, access, refresh)
    return {"user": _user_public(user), "token": access}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return _user_public(user)

@router.put("/me")
async def update_me(
    payload: UpdateProfileIn,
    request: Request,
    user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    updates = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.daily_goal is not None:
        updates["daily_goal"] = payload.daily_goal
    if payload.password is not None:
        updates["password_hash"] = hash_password(payload.password)
        
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return _user_public(updated_user)


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        db = request.app.state.db
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user["id"], user["email"])
        response.set_cookie(
            "access_token",
            access,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=ACCESS_TTL_MIN * 60,
            path="/",
        )
        return {"token": access}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
