"""Tests for GET /api/examinations filters and pagination."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.auth_security import hash_password, set_system_password_hash
from app.database import SessionLocal
from app.main import app
from app.models import Examination, Patient

_PREFIX = "UT-EL-"


def _cleanup():
    db = SessionLocal()
    try:
        patients = db.query(Patient).filter(Patient.patient_id.like(f"{_PREFIX}%")).all()
        for p in patients:
            db.query(Examination).filter(Examination.patient_id == p.id).delete()
            db.delete(p)
        db.commit()
    finally:
        db.close()


def _seed_three_same_day():
    """Three examinations on 2026-03-15 with distinct patient_id / name."""
    _cleanup()
    db = SessionLocal()
    try:
        day = datetime(2026, 3, 15, 10, 0, 0)
        p1 = Patient(name="山田-alpha", patient_id=f"{_PREFIX}001", age=40, gender="男性")
        p2 = Patient(name="佐藤-beta", patient_id=f"{_PREFIX}002", age=50, gender="女性")
        p3 = Patient(name="高橋-gamma", patient_id=f"{_PREFIX}003", age=60, gender="男性")
        db.add_all([p1, p2, p3])
        db.flush()
        db.add_all(
            [
                Examination(
                    patient_id=p1.id,
                    exam_date=day.replace(hour=9),
                    csv_file_path="/tmp/a.csv",
                ),
                Examination(
                    patient_id=p2.id,
                    exam_date=day.replace(hour=11),
                    csv_file_path="/tmp/b.csv",
                ),
                Examination(
                    patient_id=p3.id,
                    exam_date=day.replace(hour=13),
                    csv_file_path="/tmp/c.csv",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture
def auth_headers(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)
    db = SessionLocal()
    try:
        set_system_password_hash(db, hash_password("ValidPass1!"))
    finally:
        db.close()
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"password": "ValidPass1!"})
        assert login.status_code == 200
        token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_without_exam_date_returns_all_dates(auth_headers):
    """exam_date 省略時は日付で絞らない（MFER 取り込みが別日付でも一覧に出せる）。"""
    _seed_three_same_day()
    try:
        with TestClient(app) as client:
            r = client.get("/api/examinations", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 3
        ids = {it["id"] for it in body["items"]}
        assert len(ids) == len(body["items"])
    finally:
        _cleanup()


def test_list_returns_items_and_total(auth_headers):
    _seed_three_same_day()
    try:
        with TestClient(app) as client:
            r = client.get(
                "/api/examinations",
                params={"exam_date": "2026-03-15"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3
        assert all("external_id" in it["patient"] for it in body["items"])
    finally:
        _cleanup()


def test_patient_id_filter(auth_headers):
    _seed_three_same_day()
    try:
        with TestClient(app) as client:
            r = client.get(
                "/api/examinations",
                params={"exam_date": "2026-03-15", "patient_id": "002"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["patient"]["patient_id"] == f"{_PREFIX}002"
    finally:
        _cleanup()


def test_patient_name_filter(auth_headers):
    _seed_three_same_day()
    try:
        with TestClient(app) as client:
            r = client.get(
                "/api/examinations",
                params={"exam_date": "2026-03-15", "patient_name": "alpha"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert "alpha" in body["items"][0]["patient"]["name"]
    finally:
        _cleanup()


def test_limit_offset(auth_headers):
    _seed_three_same_day()
    try:
        with TestClient(app) as client:
            p1 = client.get(
                "/api/examinations",
                params={
                    "exam_date": "2026-03-15",
                    "limit": 2,
                    "offset": 0,
                    "sort_by": "exam_date",
                    "sort_order": "asc",
                },
                headers=auth_headers,
            )
            p2 = client.get(
                "/api/examinations",
                params={
                    "exam_date": "2026-03-15",
                    "limit": 2,
                    "offset": 2,
                    "sort_by": "exam_date",
                    "sort_order": "asc",
                },
                headers=auth_headers,
            )
        assert p1.status_code == 200 and p2.status_code == 200
        b1, b2 = p1.json(), p2.json()
        assert b1["total"] == 3
        assert len(b1["items"]) == 2
        assert b2["total"] == 3
        assert len(b2["items"]) == 1
    finally:
        _cleanup()
