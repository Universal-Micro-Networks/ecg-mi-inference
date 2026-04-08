"""Tests for MFER wave CSV export API."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.auth_security import hash_password, set_system_password_hash
from app.database import SessionLocal
from app.main import app
from app.mfer_wave_export import MferWaveExportError, ensure_wave_csv_for_ecg
from app.models import Examination, Patient


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


def test_export_wave_csv_success(tmp_path: Path, monkeypatch, auth_headers):
    mwf = tmp_path / "sample.MWF"
    mwf.write_bytes(b"dummy")

    db = SessionLocal()
    try:
        p = Patient(
            name="CSV患者",
            patient_id=f"UT-WAVE-{uuid4().hex[:12]}",
            age=40,
            gender="男性",
        )
        db.add(p)
        db.flush()
        exam = Examination(
            patient_id=p.id,
            exam_date=datetime(2026, 4, 1, 12, 0, 0),
            csv_file_path=str(mwf.resolve()),
            mfer_file_path=str(mwf.resolve()),
            notes="test",
        )
        db.add(exam)
        db.commit()
        exam_id = exam.id
    finally:
        db.close()

    wave_dir = tmp_path / "waves"
    wave_dir.mkdir()

    def fake_extract(_path: str):
        return ({}, pd.DataFrame({"II": [0.0, 0.1, -0.1, 0.0]}))

    def fake_save(df, path: str):
        wave_dir.mkdir(parents=True, exist_ok=True)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)

    monkeypatch.setattr("app.mfer_wave_export.WAVE_DIR", str(wave_dir))
    monkeypatch.setattr("app.mfer_wave_export.extract_mfer_data", fake_extract)
    monkeypatch.setattr("app.mfer_wave_export.save_wave_csv", fake_save)

    with TestClient(app) as client:
        r = client.post(
            f"/api/examinations/{exam_id}/export-wave-csv",
            headers=auth_headers,
        )

    assert r.status_code == 200
    body = r.json()
    assert "csv_file_path" in body
    assert body["csv_file_path"].endswith(f"{exam_id}.csv")

    db = SessionLocal()
    try:
        ex = db.query(Examination).filter(Examination.id == exam_id).first()
        assert ex is not None
        assert ex.csv_file_path == body["csv_file_path"]
    finally:
        db.close()


def test_ensure_wave_csv_uses_canonical_when_present(tmp_path: Path, monkeypatch):
    wave_dir = tmp_path / "waves"
    wave_dir.mkdir(parents=True)
    monkeypatch.setattr("app.mfer_wave_export.WAVE_DIR", str(wave_dir))

    db = SessionLocal()
    try:
        p = Patient(name="A", patient_id="p1", age=1, gender="男性")
        db.add(p)
        db.flush()
        exam = Examination(
            patient_id=p.id,
            exam_date=datetime(2026, 4, 1, 12, 0, 0),
            csv_file_path="/wrong/old.csv",
            notes="",
        )
        db.add(exam)
        db.commit()
        eid = exam.id
    finally:
        db.close()

    canonical = wave_dir / f"{eid}.csv"
    canonical.write_text("time,I\n0,1\n", encoding="utf-8")

    db = SessionLocal()
    try:
        ex = db.query(Examination).filter(Examination.id == eid).first()
        path, persist = ensure_wave_csv_for_ecg(eid, ex)
    finally:
        db.close()

    assert path == str(canonical.resolve())
    assert persist is True


def test_ensure_wave_csv_exports_when_canonical_missing(tmp_path: Path, monkeypatch):
    mwf = tmp_path / "x.MWF"
    mwf.write_bytes(b"x")
    wave_dir = tmp_path / "waves"
    wave_dir.mkdir()

    def fake_extract(_path: str):
        return ({}, pd.DataFrame({"II": [0.0, 0.1]}))

    def fake_save(df, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)

    monkeypatch.setattr("app.mfer_wave_export.WAVE_DIR", str(wave_dir))
    monkeypatch.setattr("app.mfer_wave_export.extract_mfer_data", fake_extract)
    monkeypatch.setattr("app.mfer_wave_export.save_wave_csv", fake_save)

    db = SessionLocal()
    try:
        p = Patient(name="B", patient_id="p2", age=2, gender="女性")
        db.add(p)
        db.flush()
        exam = Examination(
            patient_id=p.id,
            exam_date=datetime(2026, 4, 2, 12, 0, 0),
            csv_file_path=str(mwf.resolve()),
            mfer_file_path=str(mwf.resolve()),
        )
        db.add(exam)
        db.commit()
        eid = exam.id
    finally:
        db.close()

    db = SessionLocal()
    try:
        ex = db.query(Examination).filter(Examination.id == eid).first()
        path, persist = ensure_wave_csv_for_ecg(eid, ex)
    finally:
        db.close()

    assert persist is True
    assert path.endswith(f"{eid}.csv")
    assert Path(path).is_file()


def test_ensure_wave_csv_raises_when_only_mwf_and_no_tools(tmp_path: Path, monkeypatch):
    mwf = tmp_path / "only.MWF"
    mwf.write_bytes(b"x")
    wave_dir = tmp_path / "waves"
    wave_dir.mkdir()
    monkeypatch.setattr("app.mfer_wave_export.WAVE_DIR", str(wave_dir))
    monkeypatch.setattr("app.mfer_wave_export.extract_mfer_data", None)
    monkeypatch.setattr("app.mfer_wave_export.save_wave_csv", None)

    db = SessionLocal()
    try:
        p = Patient(name="C", patient_id="p3", age=3, gender="男性")
        db.add(p)
        db.flush()
        exam = Examination(
            patient_id=p.id,
            exam_date=datetime(2026, 4, 3, 12, 0, 0),
            csv_file_path=str(mwf.resolve()),
            mfer_file_path=str(mwf.resolve()),
        )
        db.add(exam)
        db.commit()
        eid = exam.id
    finally:
        db.close()

    db = SessionLocal()
    try:
        ex = db.query(Examination).filter(Examination.id == eid).first()
        with pytest.raises(MferWaveExportError):
            ensure_wave_csv_for_ecg(eid, ex)
    finally:
        db.close()


def test_export_wave_csv_requires_mfer_file(auth_headers):
    with TestClient(app) as client:
        r = client.post(
            "/api/examinations/00000000-0000-0000-0000-000000000000/export-wave-csv",
            headers=auth_headers,
        )
    assert r.status_code == 404
