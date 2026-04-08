"""
Auth API endpoints (single-user, password-only).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from passlib.exc import UnknownHashError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth_security import (
    blacklist_access_token_jti,
    generate_token_pair,
    get_system_password_hash,
    hash_password,
    set_system_password_hash,
    validate_password_policy,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)
from ..database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    message: str


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    password_hash = get_system_password_hash(db)
    try:
        ok = bool(password_hash and verify_password(payload.password, password_hash))
    except UnknownHashError:
        ok = False
    if not ok:
        logger.info("login_failed: invalid_password")
        raise HTTPException(status_code=401, detail="パスワードが正しくありません")

    pair = generate_token_pair()
    expires_in = int((pair.access_expires_at - datetime.now(UTC)).total_seconds())
    if expires_in < 0:
        expires_in = 0
    logger.info("login_success")

    return {
        "access_token": pair.access_token,
        "refresh_token": pair.refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


@router.post("/auth/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest):
    try:
        verify_refresh_token(payload.refresh_token)
    except Exception:
        logger.warning("refresh_failed: invalid_or_expired_token")
        raise HTTPException(
            status_code=401, detail="セッションの有効期限が切れました。再度ログインしてください"
        ) from None

    pair = generate_token_pair()
    expires_in = int((pair.access_expires_at - datetime.now(UTC)).total_seconds())
    if expires_in < 0:
        expires_in = 0
    return {"access_token": pair.access_token, "token_type": "bearer", "expires_in": expires_in}


@router.post("/auth/logout", response_model=MessageResponse)
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        logger.info("logout_failed: missing_authorization_header")
        raise HTTPException(status_code=401, detail="認可が必要です")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = verify_access_token(token)
    except Exception:
        logger.info("logout_failed: invalid_access_token")
        raise HTTPException(status_code=401, detail="認可が必要です") from None

    blacklist_access_token_jti(db, payload["jti"], int(payload["exp"]))
    logger.info("logout_success")
    return {"message": "logged out"}


@router.put("/auth/password", response_model=MessageResponse)
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db)):
    password_hash = get_system_password_hash(db)
    if not password_hash or not verify_password(payload.current_password, password_hash):
        raise HTTPException(status_code=401, detail="パスワードが正しくありません")

    policy_errors = validate_password_policy(payload.new_password)
    if policy_errors:
        raise HTTPException(status_code=422, detail=" / ".join(policy_errors))

    set_system_password_hash(db, hash_password(payload.new_password))
    return {"message": "password updated"}
