"""
Inference API endpoints.
Handles inference execution and status polling.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..inference_payload import inference_row_to_client_dict, strip_none
from ..inference_service import inference_service
from ..models import Examination, Inference

router = APIRouter()


class InferenceRequest(BaseModel):
    """Request to start a new inference."""

    examination_id: str


class InferenceResponse(BaseModel):
    """Inference response model."""

    id: str
    examination_id: str
    status: str
    result: str | None = None
    error_message: str | None = None
    confidence_score: float | None = None
    mi_probability: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _get_inference_by_path_id(db: Session, inference_or_exam_id: str) -> Inference | None:
    """パスが推論 UUID のときはその行。見つからなければ診察 UUID とみなし最新推論を返す（フロント互換）。"""
    row = db.query(Inference).filter(Inference.id == inference_or_exam_id).first()
    if row:
        return row
    return (
        db.query(Inference)
        .filter(Inference.examination_id == inference_or_exam_id)
        .order_by(Inference.created_at.desc())
        .first()
    )


@router.post("/inferences")
def run_inference(
    payload: InferenceRequest,
    db: Session = Depends(get_db),
):
    """
    Start a new inference task for an examination.

    Returns immediately with status "実行中". Client should poll the status endpoint.
    """
    exam = db.query(Examination).filter(Examination.id == payload.examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    inference = Inference(examination_id=payload.examination_id, status="実行中")
    db.add(inference)
    db.commit()
    db.refresh(inference)

    inference_service.start_inference(inference.id, payload.examination_id)

    return {
        "id": inference.id,
        "examination_id": payload.examination_id,
        "status": "実行中",
        "created_at": inference.created_at.isoformat(),
    }


@router.get("/inferences/{inference_id}")
def get_inference_status(
    inference_id: str,
    db: Session = Depends(get_db),
):
    """
    Get inference status and results.

    `inference_id` は推論レコードの UUID、または診察 UUID（その場合は最新の推論）を受け付ける。

    Statuses:
    - 未実行: Not started
    - 実行中: Running
    - 完了: Completed successfully
    - エラー: Failed with error
    """
    inference = _get_inference_by_path_id(db, inference_id)
    if not inference:
        raise HTTPException(status_code=404, detail="Inference not found")

    if inference.status == "実行中":
        service_status = inference_service.get_inference_status(inference.id)

        if service_status and service_status.get("status") == "完了":
            inference.status = "完了"
            inference.result = service_status.get("result")
            inference.confidence_score = service_status.get("confidence_score")
            inference.mi_probability = service_status.get("mi_probability")
            inference.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(inference)

    return strip_none(inference_row_to_client_dict(inference))
