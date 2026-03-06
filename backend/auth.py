import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException

from db import get_db

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(data: dict) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def authenticate_user(username: str, password: str) -> Optional[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.username, u.email, u.password_hash, u.role, u.is_active,
                       u.company_id, c.name, c.status, c.trial_ends_at
                FROM users u
                LEFT JOIN companies c ON u.company_id = c.id
                WHERE u.username = %s
            """, (username,))
            row = cur.fetchone()

    if not row:
        return None

    uid, uname, email, pw_hash, role, is_active, company_id, company_name, company_status, trial_ends_at = row

    if not is_active:
        return {"error": "account_disabled"}

    if not verify_password(password, pw_hash):
        return None

    # Superadmin bypasses company checks
    if role != "superadmin":
        if company_status == "inactive":
            return {"error": "company_inactive"}
        if company_status == "trial" and trial_ends_at:
            if datetime.now(timezone.utc) > trial_ends_at:
                return {"error": "trial_expired"}

    return {
        "user_id": str(uid),
        "username": uname,
        "email": email,
        "role": role,
        "company_id": str(company_id) if company_id else None,
        "company_name": company_name,
        "company_status": company_status,
    }


# ── FastAPI dependencies ──────────────────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return decode_token(authorization.split(" ")[1])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_superadmin(user: dict = Depends(get_current_user)):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return user


def require_admin_or_above(user: dict = Depends(get_current_user)):
    if user.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
