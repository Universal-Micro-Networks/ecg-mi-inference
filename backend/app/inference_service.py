"""
Inference service for managing inference execution and status.

- ``ECG_BNP_INFERENCE_CONFIG`` 等で BNP 設定が有効で、``inference_ecg_bnp`` が import できる場合:
  ``inference_ecg_bnp`` による BNP 回帰推論（パッケージは ``uv sync`` でメイン依存として入る）。
- それ以外: 従来どおり診察ごとに交互のモック（短い遅延で完了）。
"""

from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .bnp_inference import bnp_to_risk_fields, get_bnp_inferencer, use_real_bnp_inference

logger = logging.getLogger(__name__)

# 診察 ID ごとに実行回数を数え、奇数回目→陽性、偶数回目→陰性（モック）
_examination_run_count: defaultdict[str, int] = defaultdict(int)

# 推論完了までの待ち（秒）。UI で短い「実行中」を見せるため短めにする。
_MOCK_COMPLETE_AFTER_SEC = 0.45

_bnp_lock = threading.Lock()
_bnp_running: set[str] = set()
_bnp_results: dict[str, dict[str, Any]] = {}
# inference_id -> (error_message, examination_id)
_bnp_errors: dict[str, tuple[str, str]] = {}
_bnp_cancelled: set[str] = set()


def _bnp_worker(inference_id: str, examination_id: str) -> None:
    from .database import SessionLocal
    from .mfer_wave_export import MferWaveExportError, export_mfer_wave_csv_ephemeral
    from .models import Examination

    logger.info(
        "BNP推論ワーカー開始 examination_id=%s inference_id=%s",
        examination_id,
        inference_id,
    )

    err_msg: str | None = None
    out: dict[str, Any] | None = None

    try:
        csv_path: str | None = None
        db = SessionLocal()
        try:
            exam = db.query(Examination).filter(Examination.id == examination_id).first()
            if not exam:
                err_msg = "診察が見つかりません"
                logger.warning(
                    "BNP推論: 診察レコードがありません examination_id=%s inference_id=%s",
                    examination_id,
                    inference_id,
                )
            else:
                csv_path = export_mfer_wave_csv_ephemeral(examination_id, exam)
        finally:
            db.close()

        if err_msg is None and csv_path is not None:
            inferencer = get_bnp_inferencer()
            bnp_val = float(inferencer.predict_from_file(csv_path))
            risk_level, risk_score = bnp_to_risk_fields(bnp_val)
            result_payload = {
                "model": "ecg_bnp",
                "bnp_predicted_pg_ml": round(bnp_val, 2),
                "risk_level": risk_level,
                "risk_score": risk_score,
            }
            out = {
                "status": "完了",
                "examination_id": examination_id,
                "result": json.dumps(result_payload, ensure_ascii=False),
                "confidence_score": None,
                "mi_probability": None,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "completed_at": datetime.utcnow().isoformat(),
            }
            logger.info(
                "BNP推論ワーカー成功（ポーリング待ち・詳細JSON） %s",
                json.dumps(
                    {
                        "examination_id": examination_id,
                        "inference_id": inference_id,
                        "wave_csv_path": csv_path,
                        "wave_csv_basename": Path(csv_path).name,
                        "result": result_payload,
                    },
                    ensure_ascii=False,
                ),
            )
    except MferWaveExportError as e:
        err_msg = str(e)
        logger.warning(
            "BNP推論: 波形CSVエラー examination_id=%s inference_id=%s: %s",
            examination_id,
            inference_id,
            e,
        )
    except Exception as e:
        err_msg = f"推論に失敗しました: {e}"
        logger.exception(
            "BNP推論失敗 examination_id=%s inference_id=%s",
            examination_id,
            inference_id,
        )
    finally:
        if csv_path:
            try:
                Path(csv_path).unlink(missing_ok=True)
            except OSError:
                logger.warning(
                    "BNP推論: 一時CSVの削除に失敗しました examination_id=%s inference_id=%s path=%s",
                    examination_id,
                    inference_id,
                    csv_path,
                )

    with _bnp_lock:
        if inference_id in _bnp_cancelled:
            _bnp_cancelled.discard(inference_id)
            _bnp_running.discard(inference_id)
            logger.info(
                "BNP推論はキャンセルされ結果を破棄しました examination_id=%s inference_id=%s",
                examination_id,
                inference_id,
            )
            return
        _bnp_running.discard(inference_id)
        if err_msg is not None:
            _bnp_errors[inference_id] = (err_msg, examination_id)
            logger.warning(
                "BNP推論ワーカー終了（エラー格納・ポーリング待ち） examination_id=%s inference_id=%s error_message=%s",
                examination_id,
                inference_id,
                err_msg,
            )
        elif out is not None:
            _bnp_results[inference_id] = out


class InferenceService:
    """Service for managing inference execution and status."""

    _running_tasks: dict[str, dict[str, Any]] = {}

    @staticmethod
    def start_inference(inference_id: str, examination_id: str) -> dict[str, Any]:
        if use_real_bnp_inference():
            with _bnp_lock:
                _bnp_cancelled.discard(inference_id)
                _bnp_running.add(inference_id)
            t = threading.Thread(
                target=_bnp_worker,
                args=(inference_id, examination_id),
                name=f"bnp-inference-{inference_id[:8]}",
                daemon=True,
            )
            t.start()
            logger.info(
                "BNP推論スレッドを起動しました examination_id=%s inference_id=%s",
                examination_id,
                inference_id,
            )
            return {"id": inference_id, "status": "実行中", "examination_id": examination_id}

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

        logger.info(
            "モック推論を開始しました examination_id=%s inference_id=%s mock_positive=%s",
            examination_id,
            inference_id,
            mock_positive,
        )
        return {"id": inference_id, "status": "実行中", "examination_id": examination_id}

    @staticmethod
    def get_inference_status(inference_id: str) -> dict[str, Any] | None:
        if use_real_bnp_inference():
            with _bnp_lock:
                if inference_id in _bnp_errors:
                    msg, _ = _bnp_errors.pop(inference_id)
                    return {
                        "id": inference_id,
                        "status": "エラー",
                        "error_message": msg,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                if inference_id in _bnp_results:
                    row = _bnp_results.pop(inference_id)
                    row["id"] = inference_id
                    return row
                if inference_id in _bnp_running:
                    return {
                        "id": inference_id,
                        "status": "実行中",
                        "examination_id": None,
                        "progress": 50,
                    }
            return None

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

        done_row = {
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
        logger.info(
            "モック推論完了（詳細JSON・DB反映前） %s",
            json.dumps(
                {
                    "examination_id": examination_id,
                    "inference_id": inference_id,
                    "mock_positive": positive,
                    "result": result_payload,
                    "confidence_score": confidence_score,
                    "mi_probability": mi_probability,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "completed_at": done_row["completed_at"],
                },
                ensure_ascii=False,
            ),
        )

        return done_row

    @staticmethod
    def cancel_inference(inference_id: str) -> bool:
        if use_real_bnp_inference():
            with _bnp_lock:
                if inference_id in _bnp_running:
                    _bnp_cancelled.add(inference_id)
                    _bnp_running.discard(inference_id)
                    return True
            return False

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
        if use_real_bnp_inference():
            try:
                inferencer = get_bnp_inferencer()
                bnp_val = float(inferencer.predict_from_file(csv_path))
                risk_level, risk_score = bnp_to_risk_fields(bnp_val)
                result_payload = {
                    "model": "ecg_bnp",
                    "bnp_predicted_pg_ml": round(bnp_val, 2),
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                }
                logger.info(
                    "simulate_inference_with_ecg (BNP) 成功（詳細JSON） %s",
                    json.dumps(
                        {
                            "examination_id": examination_id,
                            "csv_path": csv_path,
                            "csv_basename": Path(csv_path).name,
                            "result": result_payload,
                        },
                        ensure_ascii=False,
                    ),
                )
                return {
                    "status": "完了",
                    "result": json.dumps(result_payload, ensure_ascii=False),
                    "confidence_score": None,
                    "mi_probability": None,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                }
            except Exception as e:
                logger.exception(
                    "simulate_inference_with_ecg (BNP) 失敗 examination_id=%s",
                    examination_id,
                )
                return {
                    "status": "エラー",
                    "result": json.dumps({"error": str(e)}, ensure_ascii=False),
                    "confidence_score": None,
                    "mi_probability": None,
                    "risk_level": None,
                    "risk_score": None,
                }

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

        mock_out = {
            "status": "完了",
            "result": json.dumps(result_payload, ensure_ascii=False),
            "confidence_score": round(confidence, 3),
            "mi_probability": round(mi_prob, 3),
            "risk_level": risk_level,
            "risk_score": risk_score,
        }
        logger.info(
            "simulate_inference_with_ecg (モック) 完了（詳細JSON） %s",
            json.dumps(
                {
                    "examination_id": examination_id,
                    "result": result_payload,
                    "confidence_score": mock_out["confidence_score"],
                    "mi_probability": mock_out["mi_probability"],
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                },
                ensure_ascii=False,
            ),
        )

        return mock_out


inference_service = InferenceService()
