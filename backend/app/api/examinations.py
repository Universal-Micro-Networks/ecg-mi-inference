"""
Examination API endpoints.
Handles examination list, detail, and ECG image retrieval.
"""

import asyncio
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session

from .. import examination_events
from ..database import get_db
from ..ecg_service import (
    STANDARD_LEAD_NAMES,
    EcgWaveformLoadError,
    generate_ecg_image,
    invalidate_ecg_cache_for_csv,
)
from ..inference_payload import inference_row_to_client_dict, strip_none
from ..mfer_wave_export import (
    MferWaveExportError,
    ensure_wave_csv_for_ecg,
    export_mfer_wave_csv,
)
from ..models import Examination, Inference, Patient

router = APIRouter()


def _normalize_if_none_match(value: str | None) -> str | None:
    if not value:
        return None
    s = value.strip()
    if s.upper().startswith("W/"):
        s = s[2:].lstrip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s or None


@router.get("/examinations")
def list_examinations(
    exam_date: date | None = Query(
        None,
        description="検査日で絞り込み（YYYY-MM-DD）。省略時は日付条件なし（全期間・ページングは limit/offset）",
    ),
    sort_by: str = "exam_date",
    sort_order: str = "desc",
    patient_id: str | None = Query(None, description="患者ID（部分一致）"),
    patient_name: str | None = Query(None, description="氏名（部分一致）"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List examinations with optional sorting, filters, and pagination.

    Query Parameters:
    - exam_date: Optional. Filter by examination calendar day (YYYY-MM-DD). Omit to list across all dates.
    - sort_by: Sort field (exam_date, patient_id, patient_name, age)
    - sort_order: Sort direction (asc, desc)
    - patient_id: Optional substring filter on patient external ID
    - patient_name: Optional substring filter on patient name
    - limit / offset: Page size and skip count
    """
    query = db.query(Examination).join(Patient)

    if exam_date is not None:
        exam_date_start = datetime.combine(exam_date, datetime.min.time())
        exam_date_end = datetime.combine(exam_date, datetime.max.time())
        query = query.filter(
            and_(Examination.exam_date >= exam_date_start, Examination.exam_date <= exam_date_end)
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


@router.get("/examinations/events")
async def stream_examination_events():
    """
    Server-Sent Events: MFER 取り込みなどで診察一覧が変わったときに `examinations_changed` を送る。
    認証はルーター共通の JWT 依存。
    """

    async def event_generator():
        q = examination_events.subscribe()
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25.0)
                except TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
        finally:
            examination_events.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
        result["latest_inference"] = latest_inference.to_dict()
        inf_client = inference_row_to_client_dict(latest_inference)
        inf_client.pop("result", None)
        result["inference"] = strip_none(inf_client)

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
        invalidate_ecg_cache_for_csv(path)

    exam.csv_file_path = new_path
    exam.ecg_image_etag = None
    db.commit()

    return {"csv_file_path": new_path, "message": "波形 CSV を出力しました"}


@router.get("/examinations/{examination_id}/ecg-image")
def get_ecg_image(
    examination_id: str,
    if_none_match: str | None = None,
    lead: str | None = Query(
        None,
        description="標準誘導名（例: II）。指定時はその1誘導のみのPNG。",
    ),
    db: Session = Depends(get_db),
):
    """
    Get ECG image for examination.

    先に mfer_tools による波形 CSV（``data/waves/{id}.csv`` または MFER からの自動出力）を
    確保し、その CSV を入力として PNG を生成する。キャッシュは CSV パス単位。

    Supports ETag caching via If-None-Match header（12誘導全体のときのみ DB の etag と照合）。
    """
    exam = db.query(Examination).filter(Examination.id == examination_id).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    lead_norm: str | None = None
    if lead is not None and lead.strip():
        lead_norm = lead.strip()
        if lead_norm not in STANDARD_LEAD_NAMES:
            raise HTTPException(
                status_code=400,
                detail=f"不明な誘導名: {lead_norm}",
            )

    client_etag = _normalize_if_none_match(if_none_match)
    if (
        lead_norm is None
        and client_etag
        and exam.ecg_image_etag
        and client_etag == exam.ecg_image_etag
    ):
        return Response(status_code=304)

    old_csv = exam.csv_file_path
    try:
        csv_path, persist_csv = ensure_wave_csv_for_ecg(examination_id, exam)
    except MferWaveExportError as e:
        raise HTTPException(
            status_code=422,
            detail=f"心電図波形を生成できません: {e}",
        ) from e

    if persist_csv:
        for path in {old_csv, csv_path}:
            if not path:
                continue
            invalidate_ecg_cache_for_csv(path)
        exam.csv_file_path = csv_path
        exam.ecg_image_etag = None

    try:
        image_bytes, etag = generate_ecg_image(csv_path, use_cache=True, lead=lead_norm)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except EcgWaveformLoadError as e:
        raise HTTPException(
            status_code=422,
            detail=f"心電図波形を生成できません: {e.reason}",
        ) from e

    if lead_norm is None:
        exam.ecg_image_etag = etag
        db.commit()
    else:
        db.commit()

    fname = f"ecg_{examination_id}_{lead_norm}.png" if lead_norm else f"ecg_{examination_id}.png"
    # Return image with cache headers
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "ETag": f'"{etag}"',
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            "Content-Disposition": f"inline; filename={fname}",
        },
    )
