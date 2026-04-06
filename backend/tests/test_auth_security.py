import pytest

from app.auth_security import generate_token_pair, validate_password_policy, verify_access_token


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
