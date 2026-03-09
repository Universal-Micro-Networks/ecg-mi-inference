EXAMINATIONS = [
    {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "exam_date": "2025-12-07T14:30:00",
        "created_at": "2025-12-07T14:31:00",
        "patient": {
            "id": "patient-1",
            "external_id": "P-001",
            "name": "山田太郎",
            "gender": "男性",
            "age": 75,
        },
    },
    {
        "id": "223e4567-e89b-12d3-a456-426614174000",
        "exam_date": "2025-12-07T13:15:00",
        "created_at": "2025-12-07T13:20:00",
        "patient": {
            "id": "patient-2",
            "external_id": "P-002",
            "name": "佐藤花子",
            "gender": "女性",
            "age": 60,
        },
    },
]

INFERENCES: dict[str, dict] = {}


def get_examination_detail(examination_id: str):
    for item in EXAMINATIONS:
        if item["id"] == examination_id:
            return {
                **item,
                "mfer_file_path": "/data/mfer/sample.mfer",
                "csv_file_path": "/data/ecg/sample.csv",
                "inference": INFERENCES.get(examination_id),
            }
    return None


def ensure_inference_status(examination_id: str):
    return INFERENCES.get(examination_id)
