"""モック推論の交互リスクと GET /api/inferences の診察 ID 解決。"""

import time
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.auth_security import hash_password, set_system_password_hash
from app.database import SessionLocal
from app.inference_service import inference_service
from app.main import app
from app.models import Examination, Inference, Patient

_PREFIX = "UT-INF-"


def _cleanup():
    db = SessionLocal()
    try:
        patients = db.query(Patient).filter(Patient.patient_id.like(f"{_PREFIX}%")).all()
        for p in patients:
            exams = db.query(Examination).filter(Examination.patient_id == p.id).all()
            for e in exams:
                db.query(Inference).filter(Inference.examination_id == e.id).delete()
                db.delete(e)
            db.delete(p)
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


def test_mock_alternates_high_and_low_per_run() -> None:
    """同一診察 ID で start のたびに 高 → 低 → 高 … と交互になる。"""
    exam_id = str(uuid.uuid4())
    for run in range(4):
        inf_id = str(uuid.uuid4())
        inference_service.start_inference(inf_id, exam_id)
        st_running = inference_service.get_inference_status(inf_id)
        assert st_running is not None
        assert st_running["status"] == "実行中"
        time.sleep(0.5)
        st_done = inference_service.get_inference_status(inf_id)
        assert st_done is not None
        assert st_done["status"] == "完了"
        want_high = run % 2 == 0
        assert st_done["risk_level"] == ("高" if want_high else "低")


def test_get_inference_resolves_examination_id(auth_headers) -> None:
    """GET /api/inferences/{診察UUID} で最新推論を取得できる。"""
    _cleanup()
    db = SessionLocal()
    try:
        p = Patient(name="t", patient_id=f"{_PREFIX}e1", age=1, gender="男性")
        db.add(p)
        db.flush()
        e = Examination(
            patient_id=p.id,
            exam_date=datetime(2026, 1, 1, 12, 0, 0),
            csv_file_path="/tmp/x.csv",
        )
        db.add(e)
        db.commit()
        exam_id = e.id
    finally:
        db.close()

    try:
        with TestClient(app) as client:
            post = client.post(
                "/api/inferences",
                json={"examination_id": exam_id},
                headers=auth_headers,
            )
            assert post.status_code == 200
            time.sleep(0.55)
            got = client.get(f"/api/inferences/{exam_id}", headers=auth_headers)
            assert got.status_code == 200
            body = got.json()
            assert body["status"] == "完了"
            assert body["risk_level"] == "高"
            assert body["risk_score"] == 78

            post2 = client.post(
                "/api/inferences",
                json={"examination_id": exam_id},
                headers=auth_headers,
            )
            assert post2.status_code == 200
            time.sleep(0.55)
            got2 = client.get(f"/api/inferences/{exam_id}", headers=auth_headers)
            assert got2.json()["risk_level"] == "低"
    finally:
        _cleanup()
