"""
File importer for MFER metadata registration.
"""

from __future__ import annotations

import logging
import os
import shutil
import unicodedata
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
    age: int | None
    exam_datetime: datetime
    exam_type: str | None


def _is_mfer_extension(path: Path) -> bool:
    return path.suffix.lower() == ".mwf"


def _clean_optional_str(value: str | None) -> str | None:
    """前後空白除去。空・空白のみは None（患者IDの ' ' 等で UNIQUE 衝突しないようにする）。"""
    if value is None:
        return None
    t = value.strip()
    return t if t else None


def _normalize_patient_name(value: str) -> str:
    """
    患者名の表記を取り込み時に正規化する。

    - 半角カタカナ → 全角カタカナ
    - 全角英数 → 半角英数
    - 半角スペース → 全角スペース
    """
    normalized = unicodedata.normalize("NFKC", value)
    return normalized.replace(" ", "　")


def _parse_exam_datetime(raw: str) -> datetime:
    """
    検査日時文字列を datetime に変換する。

    - HL7 DTM 風の 14 桁 ``YYYYMMDDHHMMSS``（先頭 14 文字がすべて数字）
    - 付帯 XML でよくある ``YYYY/MM/DD HH:MM:SS`` / ``YYYY-MM-DD HH:MM:SS``（秒省略可）
    """
    s = raw.strip()
    if not s:
        raise ValueError("empty exam_time")
    head14 = s[:14]
    if len(head14) == 14 and head14.isdigit():
        return datetime.strptime(head14, "%Y%m%d%H%M%S")
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized exam_time format: {raw!r}")


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


def _gender_from_mwf_sex(raw: str | None) -> str | None:
    """MWF_SEX（MFER ヘッダ）から性別ラベルへ。"""
    s = _clean_optional_str(raw)
    if not s:
        return None
    u = s.upper()
    if u in ("M", "MALE", "1", "男"):
        return "男性"
    if u in ("F", "FEMALE", "2", "女"):
        return "女性"
    if s == "男性":
        return "男性"
    if s == "女性":
        return "女性"
    if len(u) == 1 and u in "MF":
        return "男性" if u == "M" else "女性"
    return None


def _years_between_birth_and_exam(birth: datetime, exam: datetime) -> int:
    years = exam.year - birth.year
    if (exam.month, exam.day) < (birth.month, birth.day):
        years -= 1
    return max(0, years)


def _parse_birth_datetime(s: str) -> datetime | None:
    """生年月日文字列（YYYYMMDD 等）を datetime に。age_day 等は使わない。"""
    t = s.strip()
    if not t:
        return None
    if len(t) == 8 and t.isdigit():
        try:
            return datetime.strptime(t, "%Y%m%d")
        except ValueError:
            return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            part = t[:19] if len(t) >= 19 else t
            return datetime.strptime(part, fmt)
        except ValueError:
            continue
    return None


def _birth_datetime_from_mwf_field(raw: object) -> datetime | None:
    """mfer-tools の birthday 値（文字列想定）を datetime に。"""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        s = _clean_optional_str(raw)
        return _parse_birth_datetime(s) if s else None
    return None


def _age_from_mwf_age_dict(d: dict[str, object], exam_date: datetime) -> int | None:
    """
    MWF_AGE 辞書形式: age は常に存在、birthday は任意（age_day は無視）。
    birthday が解釈できれば検査日基準の年齢を優先し、否则 age を整数年齢として使う。
    """
    bday = d.get("birthday")
    if bday is not None:
        birth = _birth_datetime_from_mwf_field(bday)
        if birth is not None:
            return _years_between_birth_and_exam(birth, exam_date)
    age_val = d.get("age")
    if age_val is None:
        return None
    if isinstance(age_val, bool):
        return None
    if isinstance(age_val, float):
        if age_val != int(age_val):
            return None
        age_val = int(age_val)
    elif not isinstance(age_val, (int, str)):
        return None
    try:
        v = int(age_val)
    except (TypeError, ValueError):
        return None
    if 0 <= v <= 150:
        return v
    return None


def _age_from_mwf_age(raw: object | None, exam_date: datetime) -> int | None:
    """
    MWF_AGE: 従来どおり文字列（年齢または生年月日）、または辞書
    ``{'age': int, 'age_day': ...?, 'birthday'?: ...}``。
    生年月日の場合は検査日時基準で年齢を算出する。age_day は参照しない。
    """
    if raw is None:
        return None
    if isinstance(raw, dict):
        return _age_from_mwf_age_dict(raw, exam_date)
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if 0 <= raw <= 150 else None
    if isinstance(raw, float):
        if raw != int(raw):
            return None
        iv = int(raw)
        return iv if 0 <= iv <= 150 else None
    if not isinstance(raw, str):
        return None
    s = _clean_optional_str(raw)
    if not s:
        return None
    # 8桁数字は先に生年月日 YYYYMMDD として解釈（従来どおり）
    if len(s) == 8 and s.isdigit():
        birth = _parse_birth_datetime(s)
        if birth is not None:
            return _years_between_birth_and_exam(birth, exam_date)
    try:
        v = int(s)
        if 0 <= v <= 150:
            return v
    except ValueError:
        pass
    birth = _parse_birth_datetime(s)
    if birth is not None:
        return _years_between_birth_and_exam(birth, exam_date)
    return None


def _header_field_str(value: object | None) -> str | None:
    """MWF_* の文字列フィールド用（dict/list はヘッダ異常として扱わない）。"""
    if value is None or isinstance(value, (dict, list)):
        return None
    if isinstance(value, str):
        return _clean_optional_str(value)
    return _clean_optional_str(str(value))


def _header_value_preview(v: object, max_val: int) -> str:
    if isinstance(v, dict):
        s = repr(v)
    else:
        s = str(v)
    if len(s) > max_val:
        return f"{s[: max_val - 3]}..."
    return s


def _log_mfer_header_snapshot(file_path: Path, header: dict[str, object]) -> None:
    """MFER から取り込めたヘッダー内容を運用確認用に INFO で出す（値は長い場合は省略）。"""
    if extract_mfer_header is None:
        logger.info("mfer header: extract_mfer_header が利用できません (%s)", file_path.name)
        return
    if not header:
        logger.info(
            "mfer header: キーが1件も取れませんでした (%s)。MWF_PID/MWF_TIM 等が空の可能性があります",
            file_path.name,
        )
        return
    max_val = 80
    preview: dict[str, str] = {}
    for k, v in sorted(header.items()):
        preview[k] = _header_value_preview(v, max_val)
    logger.info(
        "mfer header: %s から %d キー — %s",
        file_path.name,
        len(header),
        preview,
    )


def _build_metadata(file_path: Path) -> ImportMetadata:
    header: dict[str, object] = {}
    if extract_mfer_header:
        try:
            raw = extract_mfer_header(str(file_path))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    ks = str(k)
                    if ks == "MWF_AGE" and isinstance(v, dict):
                        header[ks] = v
                    else:
                        header[ks] = "" if v is None else str(v)
        except Exception:
            logger.debug("extract_mfer_header failed for %s", file_path.name, exc_info=True)

    _log_mfer_header_snapshot(file_path, header)

    xml_meta = _extract_from_xml(file_path.with_suffix(".XML"))
    if not xml_meta:
        xml_meta = _extract_from_xml(file_path.with_suffix(".xml"))

    # MFER ヘッダ優先: (1)MWF_PNM (2)MWF_PID (3)MWF_AGE (4)MWF_SEX (5)MWF_TIM
    raw_pid = _header_field_str(header.get("MWF_PID")) or _clean_optional_str(
        xml_meta.get("patient_id")
    )
    exam_raw = _header_field_str(header.get("MWF_TIM")) or _clean_optional_str(
        xml_meta.get("exam_time")
    )
    patient_name = (
        _header_field_str(header.get("MWF_PNM"))
        or _clean_optional_str(xml_meta.get("patient_name"))
        or "不明"
    )
    patient_name = _normalize_patient_name(patient_name)
    gender = _gender_from_mwf_sex(_header_field_str(header.get("MWF_SEX"))) or _gender_label(
        xml_meta.get("gender_code")
    )
    exam_type = xml_meta.get("exam_type")

    if raw_pid:
        patient_external_id = raw_pid
    else:
        patient_external_id = f"pid_unknown:{file_path.stem}"
        logger.info(
            "patient_id missing or blank-only; using synthetic id %s (%s)",
            patient_external_id,
            file_path.name,
        )
    if not exam_raw:
        try:
            st = file_path.stat()
            ts = st.st_mtime
        except OSError as e:
            raise FileImporterError(
                "ValidationError: missing exam_time and cannot stat file"
            ) from e
        exam_datetime = datetime.fromtimestamp(ts)
        logger.warning(
            "exam_time missing in MFER/XML; using file mtime %s (%s)",
            exam_datetime.isoformat(timespec="seconds"),
            file_path.name,
        )
    else:
        try:
            exam_datetime = _parse_exam_datetime(exam_raw)
        except Exception as e:
            raise FileImporterError(f"ValidationError: invalid exam_time={exam_raw}") from e

    age = _age_from_mwf_age(header.get("MWF_AGE"), exam_datetime)

    return ImportMetadata(
        patient_external_id=patient_external_id,
        patient_name=patient_name,
        gender=gender,
        age=age,
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
        age=meta.age,
    )
    db.add(patient)
    db.flush()
    logger.info(
        "patient created: %s name=%r age=%s gender=%r",
        meta.patient_external_id,
        meta.patient_name,
        meta.age,
        meta.gender,
    )
    return patient


def _ensure_exam_and_inference(
    db: Session, patient: Patient, file_path: Path, meta: ImportMetadata
) -> Examination:
    exists = (
        db.query(Examination)
        .filter(Examination.patient_id == patient.id, Examination.exam_date == meta.exam_datetime)
        .first()
    )
    if exists:
        logger.warning(
            "duplicate exam skipped: patient=%s exam=%s", patient.patient_id, meta.exam_datetime
        )
        return exists

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


def _companion_xml_paths(mwf_path: Path) -> list[Path]:
    """
    同名の HL7 付帯 XML（.XML / .xml）。
    Docker Desktop 等でホスト側がケース非区別のとき、.XML と .xml が同一ファイルとして
    二重に列挙され、1 回目の move 後に 2 回目が FileNotFoundError になるのを防ぐため、
    (st_dev, st_ino) で重複を除く。
    """
    found: list[Path] = []
    seen_ino: set[tuple[int, int]] = set()
    for suf in (".XML", ".xml"):
        p = mwf_path.with_suffix(suf)
        if not p.is_file():
            continue
        st = p.stat()
        key = (st.st_dev, st.st_ino)
        if key in seen_ino:
            continue
        seen_ino.add(key)
        found.append(p)
    return found


def _import_destination_dir(success: bool) -> Path:
    processed_dir = Path(os.getenv("MFER_PROCESSED_FOLDER", "./processed"))
    error_dir = Path(os.getenv("MFER_ERROR_FOLDER", "./error"))
    d = processed_dir if success else error_dir
    d.mkdir(parents=True, exist_ok=True)
    return d.resolve()


def _next_available_target(dest_dir: Path, basename: str, suffix: str) -> Path:
    target = dest_dir / f"{basename}{suffix}"
    if not target.exists():
        return target
    i = 2
    while True:
        candidate = dest_dir / f"{basename}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _move_one_into_dir(src: Path, dest_dir: Path, *, target_name: str | None = None) -> Path:
    dest_dir = dest_dir.resolve()
    if target_name:
        target = _next_available_target(dest_dir, Path(target_name).stem, Path(target_name).suffix)
    else:
        target = _next_available_target(dest_dir, src.stem, src.suffix)
    shutil.move(str(src), str(target))
    return target.resolve()


def _move_mfer_bundle(
    mwf_path: Path, success: bool, *, base_name: str | None = None
) -> tuple[Path, list[Path]]:
    """
    MWF を processed / error に移動し、存在すれば同名の .XML / .xml も同じフォルダへ移動する。
    """
    xml_paths = _companion_xml_paths(mwf_path)
    dest_dir = _import_destination_dir(success)
    mwf_target_name = f"{base_name}{mwf_path.suffix}" if base_name else None
    mwf_dest = _move_one_into_dir(mwf_path, dest_dir, target_name=mwf_target_name)
    moved_xml: list[Path] = []
    for xp in xml_paths:
        try:
            xml_target_name = f"{base_name}{xp.suffix}" if base_name else None
            moved_xml_path = _move_one_into_dir(xp, dest_dir, target_name=xml_target_name)
            moved_xml.append(moved_xml_path)
            logger.info(
                "companion xml moved with mfer: %s -> %s/",
                moved_xml_path.name,
                dest_dir.name,
            )
        except Exception:
            logger.warning("companion xml move failed: %s", xp.name, exc_info=True)
    return mwf_dest, moved_xml


def _update_exam_file_path(exam_id: str, moved_to: Path, moved_xml_paths: list[Path]) -> None:
    db = SessionLocal()
    try:
        exam = db.query(Examination).filter(Examination.id == exam_id).first()
        if not exam:
            return
        exam.csv_file_path = str(moved_to)
        exam.mfer_file_path = str(moved_to)
        note = exam.notes or ""
        extra = [f"moved_mfer_path={moved_to}"]
        for xp in moved_xml_paths:
            extra.append(f"moved_xml_path={xp}")
        exam.notes = f"{note} {' '.join(extra)}".strip()
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
        exam_id = exam.id
        db.commit()
        moved_to, moved_xml_paths = _move_mfer_bundle(path, success=True, base_name=exam_id)
        _update_exam_file_path(exam_id, moved_to, moved_xml_paths)
        logger.info("file-importer success: %s -> %s", path.name, moved_to.name)
    except FileImporterError as e:
        db.rollback()
        logger.warning("file-importer rejected: %s — %s", path.name, e)
        try:
            moved_to, _ = _move_mfer_bundle(path, success=False)
            logger.info("file moved to error: %s -> %s", path.name, moved_to.name)
        except Exception:
            logger.warning("failed to move file to error folder: %s", path.name, exc_info=True)
        raise
    except Exception as e:
        db.rollback()
        logger.exception("file-importer failed: %s (%s)", path.name, type(e).__name__)
        try:
            moved_to, _ = _move_mfer_bundle(path, success=False)
            logger.info("file moved to error: %s -> %s", path.name, moved_to.name)
        except Exception:
            logger.warning("failed to move file to error folder: %s", path.name, exc_info=True)
        raise
    finally:
        db.close()

    if exam_id:
        try:
            from . import examination_events

            examination_events.notify_examinations_changed(
                examination_id=exam_id,
                reason="import",
            )
        except Exception:
            logger.debug("examination_events notify failed", exc_info=True)


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
