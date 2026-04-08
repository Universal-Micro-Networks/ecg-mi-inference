"""
Inference service for managing MI detection inference execution.
Handles status transitions and result storage.

本番の推論ライブラリ接続前は、診察ごとに「推論を実行」するたび
リスクあり（高）／リスクなし（低）が交互になるモックを返す。
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

# 診察 ID ごとに実行回数を数え、奇数回目→陽性、偶数回目→陰性
_examination_run_count: defaultdict[str, int] = defaultdict(int)

# 推論完了までの待ち（秒）。UI で短い「実行中」を見せるため短めにする。
_MOCK_COMPLETE_AFTER_SEC = 0.45


class InferenceService:
    """Service for managing inference execution and status."""

    _running_tasks: dict[str, dict[str, Any]] = {}

    @staticmethod
    def start_inference(inference_id: str, examination_id: str) -> dict[str, Any]:
        _examination_run_count[examination_id] += 1
        n = _examination_run_count[examination_id]
        mock_positive = n % 2 == 1

        InferenceService._running_tasks[inference_id] = {
            "status": "実行中",
            "started_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "examination_id": examination_id,
            "mock_positive": mock_positive,
        }

        return {"id": inference_id, "status": "実行中", "examination_id": examination_id}

    @staticmethod
    def get_inference_status(inference_id: str) -> dict[str, Any] | None:
        if inference_id not in InferenceService._running_tasks:
            return None

        task = InferenceService._running_tasks[inference_id]
        started_at = datetime.fromisoformat(task["started_at"])
        elapsed_seconds = (datetime.utcnow() - started_at).total_seconds()

        if elapsed_seconds < _MOCK_COMPLETE_AFTER_SEC:
            return {
                "id": inference_id,
                "status": "実行中",
                "examination_id": task["examination_id"],
                "progress": min(99, int((elapsed_seconds / _MOCK_COMPLETE_AFTER_SEC) * 100)),
            }

        InferenceService._running_tasks.pop(inference_id, None)
        examination_id = task["examination_id"]
        positive = bool(task.get("mock_positive", True))

        if positive:
            risk_level = "高"
            risk_score = 78
            confidence_score = 0.91
            mi_probability = 0.84
        else:
            risk_level = "低"
            risk_score = 14
            confidence_score = 0.88
            mi_probability = 0.11

        result_payload = {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "mock_alternating_demo": True,
        }

        return {
            "id": inference_id,
            "status": "完了",
            "examination_id": examination_id,
            "result": json.dumps(result_payload, ensure_ascii=False),
            "confidence_score": confidence_score,
            "mi_probability": mi_probability,
            "completed_at": datetime.utcnow().isoformat(),
            "risk_level": risk_level,
            "risk_score": risk_score,
        }

    @staticmethod
    def cancel_inference(inference_id: str) -> bool:
        if inference_id in InferenceService._running_tasks:
            del InferenceService._running_tasks[inference_id]
            return True
        return False

    @staticmethod
    def simulate_inference_with_ecg(csv_path: str, examination_id: str) -> dict[str, Any]:
        """
        Simulate inference based on ECG pattern.

        In a real implementation, this would:
        1. Load ECG from CSV
        2. Extract features (QRS complex, ST segment, T wave)
        3. Run ML model to detect MI patterns
        4. Return confidence scores and classification
        """
        _examination_run_count[examination_id] += 1
        positive = _examination_run_count[examination_id] % 2 == 1
        if positive:
            risk_level = "高"
            risk_score = 72
            mi_type = "STEMI"
            severity = "high"
            confidence = 0.87
            mi_prob = 0.82
        else:
            risk_level = "低"
            risk_score = 18
            mi_type = "normal"
            severity = "low"
            confidence = 0.86
            mi_prob = 0.12

        result_payload = {
            "mi_type": mi_type,
            "severity": severity,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "mock_alternating_demo": True,
        }

        return {
            "status": "完了",
            "result": json.dumps(result_payload, ensure_ascii=False),
            "confidence_score": round(confidence, 3),
            "mi_probability": round(mi_prob, 3),
            "risk_level": risk_level,
            "risk_score": risk_score,
        }


inference_service = InferenceService()
