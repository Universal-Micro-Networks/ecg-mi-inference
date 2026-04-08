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
