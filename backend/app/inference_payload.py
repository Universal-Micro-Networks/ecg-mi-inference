"""推論 API / 診察詳細向けに result JSON から risk 系フィールドを展開する。"""

from __future__ import annotations

import json
from typing import Any

from .models import Inference


def _risk_fields_from_result_json(result_text: str | None) -> dict[str, Any]:
    if not result_text:
        return {}
    try:
        data = json.loads(result_text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, Any] = {}
    if "risk_level" in data:
        out["risk_level"] = data["risk_level"]
    if "risk_score" in data:
        try:
            out["risk_score"] = int(data["risk_score"])
        except (TypeError, ValueError):
            pass
    return out


def inference_row_to_client_dict(inference: Inference) -> dict[str, Any]:
    """DB の Inference 行をフロント向け dict にする（None は除かない／呼び出し側で filter）。"""
    base: dict[str, Any] = {
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
    base.update(_risk_fields_from_result_json(inference.result))
    if inference.status == "完了":
        base["executed_at"] = inference.updated_at.isoformat()
    return base


def strip_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def inference_log_detail_dict(
    inference: Inference,
    *,
    service_status: dict[str, Any] | None = None,
    event: str = "inference_persisted",
) -> dict[str, Any]:
    """
    推論1件の運用ログ用 dict（JSON 1行に載せやすい）。
    ``service_status`` はポーリング時に ``get_inference_status`` が返した値（DB 保存直前のスナップショット）。
    """
    detail: dict[str, Any] = {
        "event": event,
        "examination_id": inference.examination_id,
        "inference_id": inference.id,
        "status": inference.status,
        "confidence_score": inference.confidence_score,
        "mi_probability": inference.mi_probability,
        "db_created_at": inference.created_at.isoformat(),
        "db_updated_at": inference.updated_at.isoformat(),
    }
    if inference.error_message:
        detail["error_message"] = inference.error_message
    if inference.result:
        try:
            parsed = json.loads(inference.result)
            if isinstance(parsed, (dict, list)):
                detail["result"] = parsed
            else:
                detail["result"] = str(parsed)
        except json.JSONDecodeError:
            raw = inference.result
            detail["result_json_invalid"] = True
            detail["result_raw_head"] = raw[:8000] + ("...(truncated)" if len(raw) > 8000 else "")
    detail["risk_fields"] = _risk_fields_from_result_json(inference.result)
    if service_status:
        snap = {
            k: service_status[k]
            for k in sorted(service_status)
            if k not in {"result"} and service_status[k] is not None
        }
        if snap:
            detail["service_status_snapshot"] = snap
    return detail
