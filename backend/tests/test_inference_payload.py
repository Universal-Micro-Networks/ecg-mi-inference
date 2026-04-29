"""inference_payload のログ用ヘルパー。"""

import json
from datetime import datetime

from app.inference_payload import inference_log_detail_dict
from app.models import Inference


def test_inference_log_detail_dict_parses_result_and_risk() -> None:
    inf = Inference(
        examination_id="exam-1",
        status="完了",
        result=json.dumps(
            {
                "model": "ecg_bnp",
                "bnp_predicted_pg_ml": 120.5,
                "risk_level": "中",
                "risk_score": 40,
            },
            ensure_ascii=False,
        ),
        confidence_score=None,
        mi_probability=None,
    )
    inf.id = "inf-1"
    inf.created_at = datetime(2026, 1, 1, 10, 0, 0)
    inf.updated_at = datetime(2026, 1, 1, 10, 1, 0)

    svc = {"completed_at": "2026-01-01T10:01:00", "risk_level": "中", "risk_score": 40}
    d = inference_log_detail_dict(inf, service_status=svc, event="test")

    assert d["event"] == "test"
    assert d["examination_id"] == "exam-1"
    assert d["inference_id"] == "inf-1"
    assert d["result"]["bnp_predicted_pg_ml"] == 120.5
    assert d["risk_fields"]["risk_level"] == "中"
    assert d["risk_fields"]["risk_score"] == 40
    assert "service_status_snapshot" in d
