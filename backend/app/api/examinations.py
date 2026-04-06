"""
Examination API endpoints.
Handles examination list, detail, and ECG image retrieval.
"""

import os
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..ecg_service import generate_ecg_image, get_ecg_cache_path
from ..mfer_wave_export import MferWaveExportError, export_mfer_wave_csv
from ..models import Examination, Inference, Patient

router = APIRouter()


@router.get("/examinations")
def list_examinations(
    exam_date: date,
    sort_by: str = "exam_date",
    sort_order: str = "desc",
    patient_id: str | None = Query(None, description="患者ID（部分一致）"),
    patient_name: str | None = Query(None, description="氏名（部分一致）"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List examinations for a specific date with optional sorting, filters, and pagination.

    Query Parameters:
    - exam_date: Filter by examination date (YYYY-MM-DD format)
    - sort_by: Sort field (exam_date, patient_id, patient_name, age)
    - sort_order: Sort direction (asc, desc)
    - patient_id: Optional substring filter on patient external ID
    - patient_name: Optional substring filter on patient name
    - limit / offset: Page size and skip count
    """
    # Parse exam_date to datetime range (day boundaries)
    exam_date_start = datetime.combine(exam_date, datetime.min.time())
    exam_date_end = datetime.combine(exam_date, datetime.max.time())

    # Query examinations for the date
    query = (
        db.query(Examination)
        .filter(
            and_(Examination.exam_date >= exam_date_start, Examination.exam_date <= exam_date_end)
        )
        .join(Patient)
    )

    if patient_id and patient_id.strip():
        query = query.filter(Patient.patient_id.contains(patient_id.strip(), autoescape=True))
    if patient_name and patient_name.strip():
        query = query.filter(Patient.name.contains(patient_name.strip(), autoescape=True))

    total = query.count()

    # Sort
    if sort_by == "patient_id":
        query = query.order_by(
            Patient.patient_id.desc() if sort_order == "desc" else Patient.patient_id.asc()
        )
    elif sort_by == "patient_name":
        query = query.order_by(Patient.name.desc() if sort_order == "desc" else Patient.name.asc())
    elif sort_by == "age":
        query = query.order_by(Patient.age.desc() if sort_order == "desc" else Patient.age.asc())
    else:  # exam_date
        query = query.order_by(
            Examination.exam_date.desc() if sort_order == "desc" else Examination.exam_date.asc()
        )

    examinations = query.limit(limit).offset(offset).all()

    # Format response
    result = []
    for exam in examinations:
        result.append(
            {
                "id": exam.id,
                "patient": exam.patient.to_dict(),
                "exam_date": exam.exam_date.isoformat(),
                "mfer_file_path": exam.mfer_file_path,
                "csv_file_path": exam.csv_file_path,
                "notes": exam.notes,
            }
        )

    return {"items": result, "total": total}


@router.get("/examinations/{examination_id}")
def get_examination(
    examination_id: str,
    db: Session = Depends(get_db),
):
    """
    Get examination detail by ID.
    Includes patient information and latest inference result.
    """
    exam = db.query(Examination).filter(Examination.id == examination_id).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    # Get latest inference if exists
    latest_inference = (
        db.query(Inference)
        .filter(Inference.examination_id == examination_id)
        .order_by(Inference.created_at.desc())
        .first()
    )

    result = {
        "id": exam.id,
        "patient": exam.patient.to_dict(),
        "exam_date": exam.exam_date.isoformat(),
        "created_at": exam.created_at.isoformat(),
        "mfer_file_path": exam.mfer_file_path,
        "csv_file_path": exam.csv_file_path,
        "notes": exam.notes,
    }

    if latest_inference:
        inf = latest_inference.to_dict()
        result["latest_inference"] = inf
        result["inference"] = {"status": latest_inference.status}

    return result


@router.post("/examinations/{examination_id}/export-wave-csv")
def export_examination_wave_csv(
    examination_id: str,
    db: Session = Depends(get_db),
):
    """
    Re-read MFER waveform and write CSV (mfer_tools.extract_mfer_data + save_wave_csv).
    Updates csv_file_path to the new CSV; clears ECG PNG cache for old and new paths.
    """
    exam = db.query(Examination).filter(Examination.id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    old_csv = exam.csv_file_path
    try:
        new_path = export_mfer_wave_csv(examination_id, exam)
    except MferWaveExportError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    for path in {old_csv, new_path}:
        if not path:
            continue
        try:
            cache_file = get_ecg_cache_path(path)
            if os.path.isfile(cache_file):
                os.remove(cache_file)
        except OSError:
            pass

    exam.csv_file_path = new_path
    exam.ecg_image_etag = None
    db.commit()

    return {"csv_file_path": new_path, "message": "波形 CSV を出力しました"}


@router.get("/examinations/{examination_id}/ecg-image")
def get_ecg_image(
    examination_id: str,
    if_none_match: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Get ECG image for examination.
    Generates PNG from CSV file on first access, then caches.

    Supports ETag caching via If-None-Match header.
    """
    exam = db.query(Examination).filter(Examination.id == examination_id).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    # Generate ECG image
    image_bytes, etag = generate_ecg_image(exam.csv_file_path, use_cache=True)

    # Update database with cache path and etag
    exam.ecg_image_etag = etag
    db.commit()

    # Check If-None-Match header for conditional GET
    if if_none_match == etag:
        return Response(status_code=304)  # Not Modified

    # Return image with cache headers
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "ETag": f'"{etag}"',
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            "Content-Disposition": f"inline; filename=ecg_{examination_id}.png",
        },
    )
