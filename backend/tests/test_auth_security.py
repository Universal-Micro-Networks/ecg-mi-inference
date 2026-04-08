import pytest

from app.auth_security import (
    generate_token_pair,
    get_system_password_hash,
    hash_password,
    init_system_password_if_missing,
    set_system_password_hash,
    validate_password_policy,
    verify_access_token,
    verify_password,
)
from app.database import SessionLocal
from app.models import SystemConfig


def test_validate_password_policy_detects_weak_password():
    errors = validate_password_policy("abc")
    assert errors


def test_validate_password_policy_accepts_strong_password():
    errors = validate_password_policy("StrongPass1!")
    assert errors == []


def test_generate_and_verify_access_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    pair = generate_token_pair()
    payload = verify_access_token(pair.access_token)
    assert payload["type"] == "access"
    assert "jti" in payload


def test_resync_initial_admin_password_overwrites_hash(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("RESYNC_INITIAL_ADMIN_PASSWORD", raising=False)
    db = SessionLocal()
    try:
        db.query(SystemConfig).filter(SystemConfig.key == "system_password").delete()
        db.commit()

        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "FirstPass1!")
        init_system_password_if_missing(db)
        h = get_system_password_hash(db)
        assert h and verify_password("FirstPass1!", h)

        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "SecondPass1!")
        init_system_password_if_missing(db)
        assert verify_password("FirstPass1!", get_system_password_hash(db))
        assert not verify_password("SecondPass1!", get_system_password_hash(db))

        monkeypatch.setenv("RESYNC_INITIAL_ADMIN_PASSWORD", "1")
        init_system_password_if_missing(db)
        assert verify_password("SecondPass1!", get_system_password_hash(db))
    finally:
        set_system_password_hash(db, hash_password("ValidPass1!"))
        monkeypatch.delenv("RESYNC_INITIAL_ADMIN_PASSWORD", raising=False)
        db.close()
