"""
ECG→BNP 推論（inference_ecg_bnp）の取り込み。

- 通常: ``uv sync`` で ``inference-ecg-bnp`` と PyTorch 群がメイン依存として入る。
- フォールバック: ``backend/vendor/inference_ecg_bnp/src`` を ``sys.path`` に足す（``make vendor-inference-bnp``）。

**設定の渡し方（優先順位は上ほど強い）**

1. ``set_bnp_inference_config({...})`` … アプリ起動時など呼び出し側の Python から辞書で指定（YAML ファイル不要）。
2. 環境変数 ``ECG_BNP_INFERENCE_CONFIG_JSON`` … JSON 文字列（コンテナの env 注入向け）。
3. 環境変数 ``ECG_BNP_INFERENCE_CONFIG`` … 従来どおり YAML ファイルパス。

辞書／JSON の場合は内部で ``data/bnp_infer_runtime_config.yaml`` に書き出してから
``ECGBNPInferencer`` に渡します（上流 API はファイルパス前提のため）。
``checkpoint_path`` / ``norm_csv_path`` が相対パスのときは ``path_base``（未指定時は ``backend/`` ルート）基準で絶対パスに直してから書き込みます。
"""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ``app/`` の親がバックエンドルート（リポジトリでは ``backend/``、Docker では ``/app``）
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_VENDOR_SRC = _BACKEND_ROOT / "vendor" / "inference_ecg_bnp" / "src"
_RUNTIME_CONFIG_PATH = _BACKEND_ROOT / "data" / "bnp_infer_runtime_config.yaml"

_inferencer = None
_inferencer_error: str | None = None
_runtime_config: dict[str, Any] | None = None
_runtime_path_base: Path = _BACKEND_ROOT


def set_bnp_inference_config(
    config: dict[str, Any],
    *,
    path_base: Path | None = None,
) -> None:
    """
    BNP 推論の設定を辞書で渡す（YAML ファイルを置かなくてよい）。

    ``checkpoint_path`` は必須。相対パスは ``path_base``（既定: backend ディレクトリ）からの相対。

    初回推論より前に呼ぶこと。呼び出し後は inferencer のキャッシュを破棄し、次回ロードし直す。
    """
    global _inferencer, _inferencer_error, _runtime_config, _runtime_path_base
    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    if not config.get("checkpoint_path"):
        raise ValueError("config must include a non-empty checkpoint_path")
    _inferencer = None
    _inferencer_error = None
    _runtime_config = copy.deepcopy(config)
    _runtime_path_base = (path_base or _BACKEND_ROOT).resolve()


def clear_bnp_inference_config() -> None:
    """実行時設定（辞書／JSON 由来）を消し、inferencer キャッシュを破棄する。"""
    global _inferencer, _inferencer_error, _runtime_config, _runtime_path_base
    _inferencer = None
    _inferencer_error = None
    _runtime_config = None
    _runtime_path_base = _BACKEND_ROOT


def _resolve_paths_in_mapping(cfg: dict[str, Any], base: Path) -> dict[str, Any]:
    out = copy.deepcopy(cfg)
    for key in ("checkpoint_path", "norm_csv_path"):
        raw = out.get(key)
        if raw is None or raw == "":
            continue
        p = Path(str(raw))
        if not p.is_absolute():
            out[key] = str((base / p).resolve())
    return out


def _materialize_yaml_on_disk(resolved: dict[str, Any]) -> Path:
    import yaml

    _RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _RUNTIME_CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(resolved, f, allow_unicode=True, sort_keys=False)
    return _RUNTIME_CONFIG_PATH


def _config_from_json_env() -> dict[str, Any] | None:
    raw = os.environ.get("ECG_BNP_INFERENCE_CONFIG_JSON", "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("ECG_BNP_INFERENCE_CONFIG_JSON is not valid JSON: %s", e)
        return None
    if not isinstance(data, dict):
        logger.warning("ECG_BNP_INFERENCE_CONFIG_JSON must be a JSON object")
        return None
    return data


def _resolve_ecg_bnp_config_env_path(raw: str) -> Path:
    """``ECG_BNP_INFERENCE_CONFIG`` の値を絶対パスに解決（ファイルの有無は見ない）。"""
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (_BACKEND_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def bnp_config_path() -> Path | None:
    """環境変数 ``ECG_BNP_INFERENCE_CONFIG`` の YAML ファイルパス（存在する場合のみ）。"""
    raw = os.environ.get("ECG_BNP_INFERENCE_CONFIG", "").strip()
    if not raw:
        return None
    p = _resolve_ecg_bnp_config_env_path(raw)
    return p if p.is_file() else None


def bnp_effective_inferencer_yaml_path() -> Path | None:
    """
    ``ECGBNPInferencer`` に渡す YAML のパス。

    実行時辞書 / JSON 環境変数が有効なときは ``data/bnp_infer_runtime_config.yaml`` を更新して返す。
    """
    if _runtime_config is not None:
        resolved = _resolve_paths_in_mapping(_runtime_config, _runtime_path_base)
        return _materialize_yaml_on_disk(resolved)

    env_dict = _config_from_json_env()
    if env_dict is not None:
        if not env_dict.get("checkpoint_path"):
            logger.warning("ECG_BNP_INFERENCE_CONFIG_JSON must include checkpoint_path")
            return None
        resolved = _resolve_paths_in_mapping(env_dict, _BACKEND_ROOT)
        return _materialize_yaml_on_disk(resolved)

    return bnp_config_path()


def ensure_inference_ecg_bnp_importable() -> bool:
    """パッケージとして入っているか、vendor の src をフォールバックで使えるか。"""
    try:
        import inference_ecg_bnp  # noqa: F401
    except ImportError:
        if not _VENDOR_SRC.is_dir():
            return False
        s = str(_VENDOR_SRC)
        if s not in sys.path:
            sys.path.insert(0, s)
        try:
            import inference_ecg_bnp  # noqa: F401
        except ImportError:
            return False
    return True


def use_real_bnp_inference() -> bool:
    if not ensure_inference_ecg_bnp_importable():
        logger.warning(
            "BNP inference: inference_ecg_bnp が import できません。"
            " `uv sync`（依存インストール）または `make vendor-inference-bnp` を確認してください。"
        )
        return False

    path = bnp_effective_inferencer_yaml_path()
    if path is None:
        pfile = os.environ.get("ECG_BNP_INFERENCE_CONFIG", "").strip()
        if (
            pfile
            and _runtime_config is None
            and not os.environ.get("ECG_BNP_INFERENCE_CONFIG_JSON", "").strip()
        ):
            attempted = _resolve_ecg_bnp_config_env_path(pfile)
            logger.warning(
                "ECG_BNP_INFERENCE_CONFIG is set but file not found: env=%s resolved=%s backend_root=%s",
                pfile,
                attempted,
                _BACKEND_ROOT,
            )
        return False

    try:
        import torch  # noqa: F401  # pyright: ignore[reportMissingImports]
        from inference_ecg_bnp import (  # pyright: ignore[reportMissingImports]
            ECGBNPInferencer,  # noqa: F401
        )
    except ImportError:
        logger.warning(
            "BNP inference: PyTorch / inference_ecg_bnp import failed; run `uv sync` to install dependencies"
        )
        return False
    return True


def get_bnp_inferencer():
    """遅延初期化。失敗時は例外を投げ、以降は同じエラーを再送出する。"""
    global _inferencer, _inferencer_error
    if _inferencer_error is not None:
        raise RuntimeError(_inferencer_error)
    if _inferencer is not None:
        return _inferencer
    cfg_path = bnp_effective_inferencer_yaml_path()
    if cfg_path is None:
        raise RuntimeError(
            "BNP inference is not configured: use set_bnp_inference_config(), "
            "or set ECG_BNP_INFERENCE_CONFIG_JSON, or set ECG_BNP_INFERENCE_CONFIG to a YAML file"
        )
    try:
        from inference_ecg_bnp import ECGBNPInferencer  # pyright: ignore[reportMissingImports]

        _inferencer = ECGBNPInferencer(str(cfg_path))
        return _inferencer
    except Exception as e:
        _inferencer_error = str(e)
        logger.exception("BNP inferencer init failed")
        raise RuntimeError(_inferencer_error) from e


def bnp_to_risk_fields(bnp_pg_ml: float) -> tuple[str, int]:
    """
    UI 互換の risk_level / risk_score（BNP pg/mL の2値層別化。診断目的ではない）。

    閾値は 200 pg/mL:
    - 200 未満: 低
    - 200 以上: 高
    """
    b = float(bnp_pg_ml)
    if b < 200.0:
        return "低", int(min(49, max(0, round((b / 200.0) * 49))))
    return "高", int(min(100, max(50, round(50 + ((b - 200.0) / 200.0) * 50))))
