import os
from datetime import datetime
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


def test_parse_exam_datetime_compact_and_slashed() -> None:
    assert file_importer._parse_exam_datetime("20260101123045") == datetime(2026, 1, 1, 12, 30, 45)
    assert file_importer._parse_exam_datetime("202601011230451234") == datetime(
        2026, 1, 1, 12, 30, 45
    )
    assert file_importer._parse_exam_datetime("2014/10/02 08:54:37") == datetime(
        2014, 10, 2, 8, 54, 37
    )
    assert file_importer._parse_exam_datetime("2014-10-02 09:06:45") == datetime(
        2014, 10, 2, 9, 6, 45
    )


def test_gender_from_mwf_sex() -> None:
    assert file_importer._gender_from_mwf_sex("M") == "男性"
    assert file_importer._gender_from_mwf_sex("f") == "女性"
    assert file_importer._gender_from_mwf_sex("1") == "男性"
    assert file_importer._gender_from_mwf_sex("2") == "女性"
    assert file_importer._gender_from_mwf_sex("男") == "男性"
    assert file_importer._gender_from_mwf_sex("女性") == "女性"
    assert file_importer._gender_from_mwf_sex(None) is None


def test_age_from_mwf_age_numeric_and_birth() -> None:
    exam = datetime(2026, 6, 15, 10, 0, 0)
    assert file_importer._age_from_mwf_age("65", exam) == 65
    assert file_importer._age_from_mwf_age("19900101", exam) == 36
    assert file_importer._age_from_mwf_age("1990-01-01", exam) == 36


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
            "MWF_SEX": "M",
            "MWF_AGE": "45",
        },
    )
    monkeypatch.setenv("MFER_PROCESSED_FOLDER", str(tmp_path / "processed"))
    monkeypatch.setenv("MFER_ERROR_FOLDER", str(tmp_path / "error"))

    file_importer.import_mfer_file(str(mwf))

    assert (tmp_path / "processed" / "sample.XML").is_file()
    assert not (tmp_path / "sample.XML").exists()

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_external_id).first()
        assert patient is not None
        assert patient.gender == "男性"
        assert patient.age == 45
        exam = db.query(Examination).filter(Examination.patient_id == patient.id).first()
        assert exam is not None
        assert "processed" in exam.csv_file_path
    finally:
        db.close()
        _cleanup(patient_external_id)


def test_import_accepts_slashed_exam_time_in_xml(tmp_path: Path, monkeypatch):
    """付帯 XML の effectiveTime が YYYY/MM/DD HH:MM:SS の機器向け。"""
    patient_external_id = "UT-FI-SLASH"
    _cleanup(patient_external_id)

    mwf = tmp_path / "kpum.MWF"
    mwf.write_bytes(b"dummy")
    _write_sample_xml(tmp_path / "kpum.XML", patient_external_id, "2014/10/02 08:54:37")

    monkeypatch.setattr(
        file_importer,
        "extract_mfer_header",
        lambda _p: {
            "MWF_PID": patient_external_id,
            "MWF_PNM": "スラッシュ日時患者",
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
        assert exam.exam_date == datetime(2014, 10, 2, 8, 54, 37)
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

    assert (tmp_path / "processed" / "dup1.xml").is_file()
    assert (tmp_path / "processed" / "dup2.XML").is_file()

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_external_id).first()
        assert patient is not None
        exams = db.query(Examination).filter(Examination.patient_id == patient.id).all()
        assert len(exams) == 1
    finally:
        db.close()
        _cleanup(patient_external_id)


def test_import_blank_xml_patient_id_uses_synthetic_per_file(tmp_path: Path, monkeypatch):
    """XML の id extension が空白のみの機器でも、ファイルごとに別患者として取り込む。"""
    monkeypatch.setattr(file_importer, "extract_mfer_header", lambda _p: {})
    monkeypatch.setenv("MFER_PROCESSED_FOLDER", str(tmp_path / "processed"))
    monkeypatch.setenv("MFER_ERROR_FOLDER", str(tmp_path / "error"))

    for stem in ("000000264017_20190411155308", "000000264018_20190411160000"):
        _cleanup(f"pid_unknown:{stem}")
        mwf = tmp_path / f"{stem}.mwf"
        mwf.write_bytes(b"x")
        _write_sample_xml(
            tmp_path / f"{stem}.xml",
            " ",
            "20190411155308" if stem.endswith("55308") else "20190411160000",
        )

    file_importer.import_mfer_file(str(tmp_path / "000000264017_20190411155308.mwf"))
    file_importer.import_mfer_file(str(tmp_path / "000000264018_20190411160000.mwf"))

    db = SessionLocal()
    try:
        p1 = (
            db.query(Patient)
            .filter(Patient.patient_id == "pid_unknown:000000264017_20190411155308")
            .first()
        )
        p2 = (
            db.query(Patient)
            .filter(Patient.patient_id == "pid_unknown:000000264018_20190411160000")
            .first()
        )
        assert p1 is not None
        assert p2 is not None
        assert p1.id != p2.id
    finally:
        db.close()
        _cleanup("pid_unknown:000000264017_20190411155308")
        _cleanup("pid_unknown:000000264018_20190411160000")


def test_import_invalid_file_moves_to_error_folder(tmp_path: Path, monkeypatch):
    mwf = tmp_path / "broken.MWF"
    mwf.write_bytes(b"broken")
    # 付帯 XML はあるが中身が無効（患者IDが取れない）— MWF と一緒に error へ移動する経路を確認
    (tmp_path / "broken.XML").write_text("<not-hl7 />")

    monkeypatch.setattr(file_importer, "extract_mfer_header", lambda _p: {})
    monkeypatch.setenv("MFER_PROCESSED_FOLDER", str(tmp_path / "processed"))
    monkeypatch.setenv("MFER_ERROR_FOLDER", str(tmp_path / "error"))

    with pytest.raises(file_importer.FileImporterError):
        file_importer.import_mfer_file(str(mwf))

    assert (tmp_path / "error" / "broken.MWF").is_file()
    assert (tmp_path / "error" / "broken.XML").is_file()


def test_companion_xml_paths_unique_inodes(tmp_path: Path):
    """列挙結果に同一 (dev, inode) が含まれない（ケース別名の同一ファイルの二重 move 防止）。"""
    mwf = tmp_path / "x.mwf"
    mwf.touch()
    (tmp_path / "x.XML").write_text("a")
    try:
        if not (tmp_path / "x.xml").exists():
            os.link(tmp_path / "x.XML", tmp_path / "x.xml")
    except OSError:
        pass
    paths = file_importer._companion_xml_paths(mwf)
    keys = {(p.stat().st_dev, p.stat().st_ino) for p in paths}
    assert len(keys) == len(paths)
