"""
File importer for MFER metadata registration.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Examination, Inference, Patient

try:
    from mfer_tools import extract_mfer_header
except Exception:  # pragma: no cover
    extract_mfer_header = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class FileImporterError(Exception):
    pass


@dataclass
class ImportMetadata:
    patient_external_id: str
    patient_name: str
    gender: str | None
    exam_datetime: datetime
    exam_type: str | None


def _is_mfer_extension(path: Path) -> bool:
    return path.suffix.lower() == ".mwf"


def _parse_yyyymmddhhmmss(raw: str) -> datetime:
    return datetime.strptime(raw[:14], "%Y%m%d%H%M%S")


def _text(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    t = elem.text.strip()
    return t or None


def _extract_from_xml(xml_path: Path) -> dict[str, str | None]:
    if not xml_path.exists():
        return {}
    root = ET.parse(xml_path).getroot()
    ns = {"hl7": "urn:hl7-org:v3"}
    patient_id = root.find(".//hl7:recordTarget//hl7:patientPatient/hl7:id", ns)
    family_name = root.find(
        ".//hl7:recordTarget//hl7:patientPatient/hl7:name[@use='IDE']/hl7:family", ns
    )
    gender = root.find(".//hl7:recordTarget//hl7:patientPatient/hl7:administrativeGenderCode", ns)
    exam_low = root.find(".//hl7:effectiveTime/hl7:low", ns)
    exam_code = root.find(".//hl7:code", ns)
    exam_text = root.find(".//hl7:text", ns)
    return {
        "patient_id": patient_id.get("extension") if patient_id is not None else None,
        "patient_name": _text(family_name),
        "gender_code": gender.get("code") if gender is not None else None,
        "exam_time": exam_low.get("value") if exam_low is not None else None,
        "exam_type": exam_code.get("displayName") if exam_code is not None else _text(exam_text),
    }


def _gender_label(code: str | None) -> str | None:
    if code == "M":
        return "男性"
    if code == "F":
        return "女性"
    return None


def _build_metadata(file_path: Path) -> ImportMetadata:
    header: dict[str, str] = {}
    if extract_mfer_header:
        try:
            raw = extract_mfer_header(str(file_path))
            if isinstance(raw, dict):
                header = {str(k): str(v) for k, v in raw.items()}
        except Exception:
            logger.debug("extract_mfer_header failed for %s", file_path.name, exc_info=True)

    xml_meta = _extract_from_xml(file_path.with_suffix(".XML"))
    if not xml_meta:
        xml_meta = _extract_from_xml(file_path.with_suffix(".xml"))

    patient_external_id = header.get("MWF_PID") or xml_meta.get("patient_id")
    exam_raw = header.get("MWF_TIM") or xml_meta.get("exam_time")
    patient_name = header.get("MWF_PNM") or xml_meta.get("patient_name") or "不明"
    gender = _gender_label(xml_meta.get("gender_code"))
    exam_type = xml_meta.get("exam_type")

    if not patient_external_id:
        raise FileImporterError("ValidationError: missing patient_id")
    if not exam_raw:
        raise FileImporterError("ValidationError: missing exam_time")

    try:
        exam_datetime = _parse_yyyymmddhhmmss(exam_raw)
    except Exception as e:
        raise FileImporterError(f"ValidationError: invalid exam_time={exam_raw}") from e

    return ImportMetadata(
        patient_external_id=patient_external_id,
        patient_name=patient_name,
        gender=gender,
        exam_datetime=exam_datetime,
        exam_type=exam_type,
    )


def _get_or_create_patient(db: Session, meta: ImportMetadata) -> Patient:
    patient = db.query(Patient).filter(Patient.patient_id == meta.patient_external_id).first()
    if patient:
        logger.info("patient reused: %s", meta.patient_external_id)
        return patient
    patient = Patient(
        patient_id=meta.patient_external_id,
        name=meta.patient_name,
        gender=meta.gender,
        age=None,
    )
    db.add(patient)
    db.flush()
    logger.info("patient created: %s", meta.patient_external_id)
    return patient


def _ensure_exam_and_inference(
    db: Session, patient: Patient, file_path: Path, meta: ImportMetadata
) -> Examination | None:
    exists = (
        db.query(Examination)
        .filter(Examination.patient_id == patient.id, Examination.exam_date == meta.exam_datetime)
        .first()
    )
    if exists:
        logger.warning(
            "duplicate exam skipped: patient=%s exam=%s", patient.patient_id, meta.exam_datetime
        )
        return None

    exam = Examination(
        patient_id=patient.id,
        exam_date=meta.exam_datetime,
        # Current schema has csv_file_path mandatory. Keep original path as placeholder.
        csv_file_path=str(file_path.resolve()),
        notes=f"imported_mfer_path={file_path.resolve()} exam_type={meta.exam_type or ''}".strip(),
    )
    db.add(exam)
    db.flush()
    db.add(Inference(examination_id=exam.id, status="未実行"))
    logger.info("examination created: patient=%s exam_id=%s", patient.patient_id, exam.id)
    return exam


def _move_file(file_path: Path, success: bool) -> Path:
    processed_dir = Path(os.getenv("MFER_PROCESSED_FOLDER", "./processed"))
    error_dir = Path(os.getenv("MFER_ERROR_FOLDER", "./error"))
    target_dir = processed_dir if success else error_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / file_path.name
    shutil.move(str(file_path), str(target))
    return target.resolve()


def _update_exam_file_path(exam_id: str, moved_to: Path) -> None:
    db = SessionLocal()
    try:
        exam = db.query(Examination).filter(Examination.id == exam_id).first()
        if not exam:
            return
        exam.csv_file_path = str(moved_to)
        note = exam.notes or ""
        exam.notes = f"{note} moved_mfer_path={moved_to}".strip()
        db.commit()
    finally:
        db.close()


def import_mfer_file(file_path: str) -> None:
    path = Path(file_path)
    logger.info("file-importer start: %s", path.name)

    if not path.exists():
        raise FileImporterError(f"FileError: file not found: {path}")
    if not path.is_file():
        raise FileImporterError(f"FileError: not a file: {path}")
    if not _is_mfer_extension(path):
        raise FileImporterError(f"ValidationError: unsupported extension: {path.suffix}")
    if not os.access(path, os.R_OK):
        raise FileImporterError(f"FileError: file is not readable: {path}")

    db = SessionLocal()
    exam_id: str | None = None
    try:
        meta = _build_metadata(path)
        patient = _get_or_create_patient(db, meta)
        exam = _ensure_exam_and_inference(db, patient, path, meta)
        exam_id = exam.id if exam else None
        db.commit()
        moved_to = _move_file(path, success=True)
        if exam_id:
            _update_exam_file_path(exam_id, moved_to)
        logger.info("file-importer success: %s -> %s", path.name, moved_to.name)
    except Exception as e:
        db.rollback()
        logger.error("file-importer failed: %s (%s)", path.name, type(e).__name__)
        logger.debug("file-importer error detail", exc_info=True)
        try:
            moved_to = _move_file(path, success=False)
            logger.info("file moved to error: %s -> %s", path.name, moved_to.name)
        except Exception:
            logger.warning("failed to move file to error folder: %s", path.name, exc_info=True)
        raise
    finally:
        db.close()

    if not exam_id:
        # Duplicate is considered successful end for watcher flow.
        return


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.file_importer <mfer-file-path>")
        raise SystemExit(1)
    try:
        import_mfer_file(sys.argv[1])
    except Exception:
        raise SystemExit(1) from None
    raise SystemExit(0)
