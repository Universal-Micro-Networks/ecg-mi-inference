from fastapi.testclient import TestClient

import app.api.auth as auth_api
from app.auth_security import set_system_password_hash
from app.database import SessionLocal
from app.main import app


def test_login_success_and_failure(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)

    db = SessionLocal()
    try:
        # Startup hash generationを避けるため、先に存在だけ作る
        set_system_password_hash(db, "dummy-hash")
    finally:
        db.close()

    monkeypatch.setattr(auth_api, "verify_password", lambda plain, _hash: plain == "ValidPass1!")

    with TestClient(app) as client:
        fail = client.post("/api/auth/login", json={"password": "wrong"})
        assert fail.status_code == 401

        ok = client.post("/api/auth/login", json={"password": "ValidPass1!"})
        assert ok.status_code == 200
        data = ok.json()
        assert "access_token" in data
        assert "refresh_token" in data


def test_protected_route_requires_auth_and_logout_invalidates_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)

    db = SessionLocal()
    try:
        set_system_password_hash(db, "dummy-hash")
    finally:
        db.close()

    monkeypatch.setattr(auth_api, "verify_password", lambda plain, _hash: plain == "ValidPass1!")

    with TestClient(app) as client:
        no_auth = client.get("/api/examinations", params={"exam_date": "2026-03-09"})
        assert no_auth.status_code == 401

        login = client.post("/api/auth/login", json={"password": "ValidPass1!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        ok = client.get("/api/examinations", params={"exam_date": "2026-03-09"}, headers=headers)
        assert ok.status_code == 200

        logout = client.post("/api/auth/logout", headers=headers)
        assert logout.status_code == 200

        rejected = client.get(
            "/api/examinations", params={"exam_date": "2026-03-09"}, headers=headers
        )
        assert rejected.status_code == 401
