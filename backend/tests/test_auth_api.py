from fastapi.testclient import TestClient

from app.auth_security import hash_password, set_system_password_hash
from app.database import SessionLocal
from app.main import app
from app.models import SystemConfig


def test_login_success_and_failure(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)

    db = SessionLocal()
    try:
        set_system_password_hash(db, hash_password("ValidPass1!"))
    finally:
        db.close()

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
        set_system_password_hash(db, hash_password("ValidPass1!"))
    finally:
        db.close()

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


def test_bootstrap_flow_when_password_not_configured(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    db = SessionLocal()
    try:
        db.query(SystemConfig).filter(SystemConfig.key == "system_password").delete()
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        st = client.get("/api/auth/bootstrap-status")
        assert st.status_code == 200
        assert st.json()["requires_setup"] is True

        no_setup_login = client.post("/api/auth/login", json={"password": "AnyPass1!"})
        assert no_setup_login.status_code == 403

        bad_bootstrap = client.post("/api/auth/bootstrap", json={"new_password": "weak"})
        assert bad_bootstrap.status_code == 422

        ok_bootstrap = client.post("/api/auth/bootstrap", json={"new_password": "ValidPass1!"})
        assert ok_bootstrap.status_code == 200

        login = client.post("/api/auth/login", json={"password": "ValidPass1!"})
        assert login.status_code == 200

        st2 = client.get("/api/auth/bootstrap-status")
        assert st2.status_code == 200
        assert st2.json()["requires_setup"] is False
