"""実行時辞書／JSON による BNP 設定（YAML ファイル不要）。"""

import json

import pytest

from app import bnp_inference as bi


def test_set_bnp_inference_config_requires_checkpoint() -> None:
    bi.clear_bnp_inference_config()
    with pytest.raises(ValueError, match="checkpoint_path"):
        bi.set_bnp_inference_config({"device": "cpu"})


def test_set_bnp_inference_config_writes_resolved_yaml(tmp_path, monkeypatch) -> None:
    runtime_yaml = tmp_path / "runtime_bnp.yaml"
    monkeypatch.setattr(bi, "_RUNTIME_CONFIG_PATH", runtime_yaml)

    bi.clear_bnp_inference_config()
    ck = tmp_path / "model.pth"
    ck.write_bytes(b"x")

    bi.set_bnp_inference_config(
        {
            "device": "cpu",
            "checkpoint_path": "model.pth",
            "cqt_params": {"sampling_rate": 500},
            "model_params": {"input_ch": 12},
        },
        path_base=tmp_path,
    )

    p = bi.bnp_effective_inferencer_yaml_path()
    assert p == runtime_yaml
    text = runtime_yaml.read_text(encoding="utf-8")
    assert str(ck.resolve()) in text


def test_json_env_parsed_when_runtime_not_set(tmp_path, monkeypatch) -> None:
    runtime_yaml = tmp_path / "runtime_bnp2.yaml"
    monkeypatch.setattr(bi, "_RUNTIME_CONFIG_PATH", runtime_yaml)
    bi.clear_bnp_inference_config()

    ck = tmp_path / "w.pth"
    ck.write_bytes(b"y")

    cfg = {
        "device": "cpu",
        "checkpoint_path": str(ck),
        "cqt_params": {},
        "model_params": {},
    }
    monkeypatch.setenv("ECG_BNP_INFERENCE_CONFIG_JSON", json.dumps(cfg))

    p = bi.bnp_effective_inferencer_yaml_path()
    assert p == runtime_yaml
    assert str(ck.resolve()) in runtime_yaml.read_text(encoding="utf-8")

    monkeypatch.delenv("ECG_BNP_INFERENCE_CONFIG_JSON", raising=False)
    bi.clear_bnp_inference_config()


def test_runtime_dict_overrides_json_env(tmp_path, monkeypatch) -> None:
    runtime_yaml = tmp_path / "runtime_bnp3.yaml"
    monkeypatch.setattr(bi, "_RUNTIME_CONFIG_PATH", runtime_yaml)

    ck_json = tmp_path / "from_json.pth"
    ck_json.write_bytes(b"j")
    ck_runtime = tmp_path / "from_runtime.pth"
    ck_runtime.write_bytes(b"r")

    monkeypatch.setenv(
        "ECG_BNP_INFERENCE_CONFIG_JSON",
        json.dumps(
            {"device": "cpu", "checkpoint_path": str(ck_json), "cqt_params": {}, "model_params": {}}
        ),
    )

    bi.set_bnp_inference_config(
        {"device": "cpu", "checkpoint_path": str(ck_runtime), "cqt_params": {}, "model_params": {}},
    )

    text = bi.bnp_effective_inferencer_yaml_path().read_text(encoding="utf-8")
    assert str(ck_runtime.resolve()) in text
    assert str(ck_json.resolve()) not in text

    monkeypatch.delenv("ECG_BNP_INFERENCE_CONFIG_JSON", raising=False)
    bi.clear_bnp_inference_config()


def test_bnp_to_risk_fields_uses_binary_threshold_200() -> None:
    level_low, score_low = bi.bnp_to_risk_fields(199.9)
    level_high, score_high = bi.bnp_to_risk_fields(200.0)

    assert level_low == "低"
    assert level_high == "高"
    assert 0 <= score_low <= 49
    assert 50 <= score_high <= 100
