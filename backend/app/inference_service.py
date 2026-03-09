"""
Inference service for managing MI detection inference execution.
Handles status transitions and result storage.
"""

import json
import random
from datetime import datetime
from typing import Any


class InferenceService:
    """Service for managing inference execution and status."""

    # Simulated inference task tracking
    _running_tasks: dict[str, dict[str, Any]] = {}

    @staticmethod
    def start_inference(inference_id: str, examination_id: str) -> dict[str, Any]:
        """
        Start a new inference task.

        Args:
            inference_id: Unique inference ID
            examination_id: Associated examination ID

        Returns:
            Dictionary with initial status
        """
        InferenceService._running_tasks[inference_id] = {
            "status": "実行中",
            "started_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "examination_id": examination_id,
        }

        return {"id": inference_id, "status": "実行中", "examination_id": examination_id}

    @staticmethod
    def get_inference_status(inference_id: str) -> dict[str, Any] | None:
        """
        Get current inference status.

        Simulates inference completing after a few checks (3-5 checks = ~15-25 seconds).
        """
        if inference_id not in InferenceService._running_tasks:
            return None

        task = InferenceService._running_tasks[inference_id]

        # Simulate inference completion
        # After 4-6 status checks (20-30 seconds), mark as complete
        started_at = datetime.fromisoformat(task["started_at"])
        elapsed_seconds = (datetime.utcnow() - started_at).total_seconds()

        if elapsed_seconds > random.uniform(18, 25):
            # Mark as complete
            result = {
                "mi_type": random.choice(["anterior", "inferior", "lateral", "posterior"]),
                "severity": random.choice(["low", "moderate", "high"]),
                "region": random.choice(["anterior_wall", "inferior_wall", "lateral_wall"]),
                "timing": "acute",
            }

            return {
                "id": inference_id,
                "status": "完了",
                "examination_id": task["examination_id"],
                "result": json.dumps(result),
                "confidence_score": round(random.uniform(0.75, 0.98), 3),
                "mi_probability": round(random.uniform(0.65, 0.95), 3),
                "completed_at": datetime.utcnow().isoformat(),
            }
        else:
            # Still running
            return {
                "id": inference_id,
                "status": "実行中",
                "examination_id": task["examination_id"],
                "progress": int((elapsed_seconds / random.uniform(20, 30)) * 100),
            }

    @staticmethod
    def cancel_inference(inference_id: str) -> bool:
        """Cancel a running inference task."""
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
        # Simulate simple rule-based detection
        has_st_elevation = random.random() > 0.6
        has_t_inversion = random.random() > 0.5
        qrs_duration = random.uniform(0.08, 0.12)

        # Rule-based MI detection
        mi_detected = has_st_elevation or (has_t_inversion and qrs_duration > 0.1)

        if mi_detected:
            mi_type = random.choice(["STEMI", "NSTEMI"])
            severity = "high" if mi_type == "STEMI" else "moderate"
            region = random.choice(["anterior", "inferior", "lateral"])
            confidence = random.uniform(0.80, 0.98)
        else:
            mi_type = "normal"
            severity = "low"
            region = "none"
            confidence = random.uniform(0.75, 0.95)

        return {
            "status": "完了",
            "result": json.dumps(
                {
                    "mi_type": mi_type,
                    "severity": severity,
                    "region": region,
                    "st_elevation": has_st_elevation,
                    "t_inversion": has_t_inversion,
                    "qrs_duration": round(qrs_duration, 3),
                }
            ),
            "confidence_score": round(confidence, 3),
            "mi_probability": round(confidence if mi_detected else 0.1, 3),
        }


# Global inference service instance
inference_service = InferenceService()
