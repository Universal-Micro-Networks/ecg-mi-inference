"""
Inference API endpoints.
Handles inference execution and status polling.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..inference_payload import inference_row_to_client_dict, strip_none
from ..inference_service import inference_service
from ..models import Examination, Inference

router = APIRouter()
logger = logging.getLogger(__name__)


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

    logger.info(
        "推論を開始しました examination_id=%s inference_id=%s",
        payload.examination_id,
        inference.id,
    )

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
        # 判定結果を永続化しないモードでは、完了後に inferences 行を削除するため
        # 診察 UUID 指定時は「未実行」扱いで返して UI エラーを避ける。
        exam = db.query(Examination).filter(Examination.id == inference_id).first()
        if exam:
            return {"examination_id": inference_id, "status": "未実行"}
        raise HTTPException(status_code=404, detail="Inference not found")

    response_override: dict | None = None

    if inference.status == "実行中":
        service_status = inference_service.get_inference_status(inference.id)

        if service_status and service_status.get("status") == "完了":
            # セキュリティ方針: 判定結果（result / score など）は DB に永続化しない。
            inference.status = "未実行"
            inference.result = None
            inference.confidence_score = None
            inference.mi_probability = None
            inference.error_message = None
            inference.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(inference)
            response_override = strip_none(
                {
                    **inference_row_to_client_dict(inference),
                    "status": "完了",
                    "result": service_status.get("result"),
                    "confidence_score": service_status.get("confidence_score"),
                    "mi_probability": service_status.get("mi_probability"),
                    "risk_level": service_status.get("risk_level"),
                    "risk_score": service_status.get("risk_score"),
                    "executed_at": service_status.get("completed_at"),
                }
            )
            db.delete(inference)
            db.commit()
            logger.info(
                "推論結果詳細（完了・DB非永続） %s",
                json.dumps(
                    {
                        "event": "inference_not_persisted_complete",
                        "examination_id": inference.examination_id,
                        "inference_id": inference.id,
                        "db_status": inference.status,
                        "service_status": {
                            k: v for k, v in service_status.items() if v is not None
                        },
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            )
        elif service_status and service_status.get("status") == "エラー":
            inference.status = "未実行"
            inference.error_message = None
            inference.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(inference)
            response_override = strip_none(
                {
                    **inference_row_to_client_dict(inference),
                    "status": "エラー",
                    "error_message": service_status.get("error_message"),
                    "executed_at": service_status.get("completed_at"),
                }
            )
            db.delete(inference)
            db.commit()
            logger.warning(
                "推論結果詳細（エラー・DB非永続） %s",
                json.dumps(
                    {
                        "event": "inference_not_persisted_error",
                        "examination_id": inference.examination_id,
                        "inference_id": inference.id,
                        "db_status": inference.status,
                        "service_status": {
                            k: v for k, v in service_status.items() if v is not None
                        },
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            )

    if response_override is not None:
        return response_override
    return strip_none(inference_row_to_client_dict(inference))
