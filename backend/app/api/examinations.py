"""
Examination API endpoints.
Handles examination list, detail, and ECG image retrieval.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..ecg_service import generate_ecg_image
from ..models import Examination, Inference, Patient

router = APIRouter()


@router.get("/examinations")
def list_examinations(
    exam_date: date,
    sort_by: str = "exam_date",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    """
    List examinations for a specific date with optional sorting.

    Query Parameters:
    - exam_date: Filter by examination date (YYYY-MM-DD format)
    - sort_by: Sort field (exam_date, patient_id, patient_name, age)
    - sort_order: Sort direction (asc, desc)
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

    examinations = query.all()

    # Format response
    result = []
    for exam in examinations:
        result.append(
            {
                "id": exam.id,
                "patient": exam.patient.to_dict(),
                "exam_date": exam.exam_date.isoformat(),
                "csv_file_path": exam.csv_file_path,
                "notes": exam.notes,
            }
        )

    return result


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
        "csv_file_path": exam.csv_file_path,
        "notes": exam.notes,
    }

    if latest_inference:
        result["latest_inference"] = latest_inference.to_dict()

    return result


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
