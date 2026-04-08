"""
Authentication/authorization helpers.

Single-user, password-only auth with JWT access/refresh tokens.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from sqlalchemy.orm import Session

from .database import get_db
from .models import SystemConfig, TokenBlacklist

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _dt_to_ts(dt: datetime) -> int:
    return int(dt.timestamp())


def _ts_to_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)


def _get_access_exp_hours() -> int:
    return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "8"))


def _get_refresh_exp_hours() -> int:
    return int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_HOURS", "24"))


def _initial_admin_password_from_env() -> str | None:
    raw = os.getenv("INITIAL_ADMIN_PASSWORD")
    if raw is None:
        return None
    s = raw.strip()
    return s if s else None


def _env_flag(name: str) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def stored_password_hash_is_usable(stored: str | None) -> bool:
    """True if `stored` is a hash passlib can verify (bcrypt in this app)."""
    if not stored or not stored.strip():
        return False
    try:
        return pwd_context.identify(stored.strip()) == "bcrypt"
    except UnknownHashError:
        return False


def get_system_password_hash(db: Session) -> str | None:
    row = db.query(SystemConfig).filter(SystemConfig.key == "system_password").first()
    return row.value if row else None


def set_system_password_hash(db: Session, password_hash: str) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.key == "system_password").first()
    if row:
        row.value = password_hash
    else:
        db.add(SystemConfig(key="system_password", value=password_hash))
    db.commit()


def init_system_password_if_missing(db: Session) -> None:
    """
    On startup, ensure the system password is set.

    - RESYNC_INITIAL_ADMIN_PASSWORD=1 と INITIAL_ADMIN_PASSWORD があれば、既存の bcrypt があっても
      常に上書き（開発・パスワード取り違えリカバリ用。本番では原則無効のまま）。
    - 上記以外で DB に有効な bcrypt がある場合は何もしない（.env のパスワード変更はログインに反映されない）。
    - 未設定かつ INITIAL_ADMIN_PASSWORD あり: 初回 bcrypt 保存。
    - 無効なプレースホルダのみ: INITIAL_ADMIN_PASSWORD で差し替え。
    """
    current = get_system_password_hash(db)
    initial = _initial_admin_password_from_env()

    if _env_flag("RESYNC_INITIAL_ADMIN_PASSWORD"):
        if not initial:
            raise RuntimeError(
                "RESYNC_INITIAL_ADMIN_PASSWORD が有効ですが INITIAL_ADMIN_PASSWORD が空です。"
            )
        logger.warning(
            "RESYNC_INITIAL_ADMIN_PASSWORD: 管理者パスワードを INITIAL_ADMIN_PASSWORD で上書きしました。"
        )
        set_system_password_hash(db, hash_password(initial))
        return

    if current and stored_password_hash_is_usable(current):
        return

    if current and not stored_password_hash_is_usable(current):
        if not initial:
            raise RuntimeError(
                "DB の system_password が有効な bcrypt ではありません。"
                " INITIAL_ADMIN_PASSWORD を設定して再起動するか、system_config を修正してください。"
            )
        logger.warning(
            "DB の system_password を無効な値から差し替えます（開発用プレースホルダ等）。"
            " INITIAL_ADMIN_PASSWORD を使用して bcrypt を保存します。"
        )
        set_system_password_hash(db, hash_password(initial))
        return

    if not initial:
        raise RuntimeError(
            "System password is not initialized. Set INITIAL_ADMIN_PASSWORD and restart."
        )

    set_system_password_hash(db, hash_password(initial))


def _jwt_secret() -> str:
    return _require_env("JWT_SECRET_KEY")


def require_jwt_secret() -> None:
    _jwt_secret()


def validate_password_policy(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < 8:
        errors.append("パスワードは8文字以上である必要があります")

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    kinds = sum([has_upper, has_lower, has_digit, has_symbol])
    if kinds < 3:
        errors.append("パスワードは大文字・小文字・数字・記号のうち3種類以上を含めてください")

    return errors


def generate_token_pair() -> TokenPair:
    now = _now_utc()
    access_exp = now + timedelta(hours=_get_access_exp_hours())
    refresh_exp = now + timedelta(hours=_get_refresh_exp_hours())

    access_payload = {
        "type": "access",
        "jti": str(uuid4()),
        "iat": _dt_to_ts(now),
        "exp": _dt_to_ts(access_exp),
    }
    refresh_payload = {
        "type": "refresh",
        "iat": _dt_to_ts(now),
        "exp": _dt_to_ts(refresh_exp),
    }

    access_token = jwt.encode(access_payload, _jwt_secret(), algorithm="HS256")
    refresh_token = jwt.encode(refresh_payload, _jwt_secret(), algorithm="HS256")

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_exp,
        refresh_expires_at=refresh_exp,
    )


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except JWTError as e:
        raise InvalidTokenError() from e

    if payload.get("type") != "access":
        raise InvalidTokenError()
    if "jti" not in payload:
        raise InvalidTokenError()
    return payload


def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except JWTError as e:
        raise InvalidTokenError() from e

    if payload.get("type") != "refresh":
        raise InvalidTokenError()
    return payload


def blacklist_access_token_jti(db: Session, jti: str, exp_ts: int) -> None:
    expires_at = _ts_to_dt(exp_ts)
    exists = db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == jti).first()
    if exists:
        return
    db.add(TokenBlacklist(token_jti=jti, expires_at=expires_at))
    db.commit()


def is_blacklisted(db: Session, jti: str) -> bool:
    row = db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == jti).first()
    return row is not None


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """
    FastAPI dependency to protect endpoints.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認可が必要です")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = verify_access_token(token)
    except (InvalidTokenError, TokenExpiredError):
        raise HTTPException(status_code=401, detail="認可が必要です") from None

    jti = payload["jti"]
    if is_blacklisted(db, jti):
        raise HTTPException(status_code=401, detail="認可が必要です")

    # Single-user model: no user identity beyond "authorized".
    return {"authorized": True, "jti": jti}
