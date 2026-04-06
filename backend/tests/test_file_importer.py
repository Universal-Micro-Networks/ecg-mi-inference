from pathlib import Path

import pytest

import app.file_importer as file_importer
from app.database import SessionLocal
from app.models import Examination, Patient


def _write_sample_xml(xml_path: Path, patient_id: str, exam_time: str) -> None:
    xml_path.write_text(
        f"""<?xml version="1.0" encoding="utf-8"?>
<ECGObservation xmlns="urn:hl7-org:v3">
  <effectiveTime><low value="{exam_time}" /></effectiveTime>
  <recordTarget>
    <patientRole>
      <patientPatient>
        <id extension="{patient_id}" />
        <name use="IDE"><family>テスト患者</family></name>
        <administrativeGenderCode code="M" />
      </patientPatient>
    </patientRole>
  </recordTarget>
  <code displayName="12誘導心電図" />
</ECGObservation>
"""
    )


def _cleanup(patient_external_id: str) -> None:
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_external_id).first()
        if patient:
            db.query(Examination).filter(Examination.patient_id == patient.id).delete()
            db.query(Patient).filter(Patient.id == patient.id).delete()
            db.commit()
    finally:
        db.close()


def test_import_accepts_uppercase_mwf_and_registers_db(tmp_path: Path, monkeypatch):
    patient_external_id = "UT-FI-001"
    _cleanup(patient_external_id)

    mwf = tmp_path / "sample.MWF"
    mwf.write_bytes(b"dummy")
    _write_sample_xml(tmp_path / "sample.XML", patient_external_id, "20260101123045")

    monkeypatch.setattr(
        file_importer,
        "extract_mfer_header",
        lambda _p: {
            "MWF_TIM": "20260101123045",
            "MWF_PID": patient_external_id,
            "MWF_PNM": "テスト患者",
        },
    )
    monkeypatch.setenv("MFER_PROCESSED_FOLDER", str(tmp_path / "processed"))
    monkeypatch.setenv("MFER_ERROR_FOLDER", str(tmp_path / "error"))

    file_importer.import_mfer_file(str(mwf))

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_external_id).first()
        assert patient is not None
        exam = db.query(Examination).filter(Examination.patient_id == patient.id).first()
        assert exam is not None
        assert "processed" in exam.csv_file_path
    finally:
        db.close()
        _cleanup(patient_external_id)


def test_import_skips_duplicate_exam(tmp_path: Path, monkeypatch):
    patient_external_id = "UT-FI-002"
    _cleanup(patient_external_id)

    monkeypatch.setattr(
        file_importer,
        "extract_mfer_header",
        lambda _p: {
            "MWF_TIM": "20260102120000",
            "MWF_PID": patient_external_id,
            "MWF_PNM": "重複患者",
        },
    )
    monkeypatch.setenv("MFER_PROCESSED_FOLDER", str(tmp_path / "processed"))
    monkeypatch.setenv("MFER_ERROR_FOLDER", str(tmp_path / "error"))

    mwf1 = tmp_path / "dup1.mwf"
    mwf1.write_bytes(b"dummy1")
    _write_sample_xml(tmp_path / "dup1.xml", patient_external_id, "20260102120000")
    file_importer.import_mfer_file(str(mwf1))

    mwf2 = tmp_path / "dup2.MWF"
    mwf2.write_bytes(b"dummy2")
    _write_sample_xml(tmp_path / "dup2.XML", patient_external_id, "20260102120000")
    file_importer.import_mfer_file(str(mwf2))

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_external_id).first()
        assert patient is not None
        exams = db.query(Examination).filter(Examination.patient_id == patient.id).all()
        assert len(exams) == 1
    finally:
        db.close()
        _cleanup(patient_external_id)


def test_import_invalid_file_moves_to_error_folder(tmp_path: Path, monkeypatch):
    mwf = tmp_path / "broken.MWF"
    mwf.write_bytes(b"broken")

    monkeypatch.setattr(file_importer, "extract_mfer_header", lambda _p: {})
    monkeypatch.setenv("MFER_PROCESSED_FOLDER", str(tmp_path / "processed"))
    monkeypatch.setenv("MFER_ERROR_FOLDER", str(tmp_path / "error"))

    with pytest.raises(file_importer.FileImporterError):
        file_importer.import_mfer_file(str(mwf))

    moved = tmp_path / "error" / "broken.MWF"
    assert moved.exists()
