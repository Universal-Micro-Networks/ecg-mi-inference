"""
Inference API endpoints.
Handles inference execution and status polling.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
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


@router.post("/inferences")
def run_inference(
    payload: InferenceRequest,
    db: Session = Depends(get_db),
):
    """
    Start a new inference task for an examination.

    Returns immediately with status "実行中". Client should poll the status endpoint.
    """
    # Get examination
    exam = db.query(Examination).filter(Examination.id == payload.examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    # Create new inference record
    inference = Inference(examination_id=payload.examination_id, status="実行中")
    db.add(inference)
    db.commit()
    db.refresh(inference)

    # Start inference task
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

    Statuses:
    - 未実行: Not started
    - 実行中: Running
    - 完了: Completed successfully
    - エラー: Failed with error
    """
    # Get from database
    inference = db.query(Inference).filter(Inference.id == inference_id).first()
    if not inference:
        raise HTTPException(status_code=404, detail="Inference not found")

    # Get status from service (for running tasks)
    if inference.status == "実行中":
        service_status = inference_service.get_inference_status(inference_id)

        if service_status and service_status.get("status") == "完了":
            # Update database with result
            inference.status = "完了"
            inference.result = service_status.get("result")
            inference.confidence_score = service_status.get("confidence_score")
            inference.mi_probability = service_status.get("mi_probability")
            inference.updated_at = datetime.utcnow()
            db.commit()

    # Return current status
    result = {
        "id": inference.id,
        "examination_id": inference.examination_id,
        "status": inference.status,
        "result": inference.result,
        "error_message": inference.error_message,
        "confidence_score": inference.confidence_score,
        "mi_probability": inference.mi_probability,
        "created_at": inference.created_at.isoformat(),
        "updated_at": inference.updated_at.isoformat(),
    }

    # Remove None values
    return {k: v for k, v in result.items() if v is not None}
