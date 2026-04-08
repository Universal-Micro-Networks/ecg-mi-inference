"""
Export MFER waveform to CSV using mfer_tools (extract_mfer_data / save_wave_csv).
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from .models import Examination

logger = logging.getLogger(__name__)

try:
    from mfer_tools import extract_mfer_data, save_wave_csv
except Exception:  # pragma: no cover
    extract_mfer_data = None  # type: ignore[assignment]
    save_wave_csv = None  # type: ignore[assignment]


class MferWaveExportError(Exception):
    """User-visible export failure."""


WAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "waves")
os.makedirs(WAVE_DIR, exist_ok=True)


def _paths_from_notes(notes: str | None) -> list[str]:
    if not notes:
        return []
    out: list[str] = []
    for key in ("moved_mfer_path=", "imported_mfer_path="):
        for m in re.finditer(re.escape(key) + r"(\S+)", notes):
            out.append(m.group(1))
    return out


def resolve_mfer_path(exam: Examination) -> Path:
    """Pick first existing .mwf path from DB fields and notes."""
    candidates: list[str] = []
    mfer_stored = exam.mfer_file_path
    if mfer_stored:
        candidates.append(mfer_stored)
    if exam.csv_file_path and exam.csv_file_path.lower().endswith(".mwf"):
        candidates.append(exam.csv_file_path)
    candidates.extend(_paths_from_notes(exam.notes))

    seen: set[str] = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        path = Path(c).expanduser()
        if path.is_file() and path.suffix.lower() == ".mwf":
            return path.resolve()

    raise MferWaveExportError("MFER ファイル（.mwf）が見つかりません")


def export_mfer_wave_csv(exam_id: str, exam: Examination) -> str:
    """
    Read MFER, write waveform CSV under data/waves/{exam_id}.csv.
    Returns absolute path to the CSV.
    """
    if extract_mfer_data is None or save_wave_csv is None:
        raise MferWaveExportError(
            "mfer_tools が利用できません（extract_mfer_data / save_wave_csv）"
        )

    mfer_path = resolve_mfer_path(exam)
    try:
        _header, df_wave = extract_mfer_data(str(mfer_path))
    except Exception as e:
        logger.exception("extract_mfer_data failed for %s", mfer_path)
        raise MferWaveExportError(f"MFER の読み込みに失敗しました: {e}") from e

    out_path = os.path.join(WAVE_DIR, f"{exam_id}.csv")
    try:
        save_wave_csv(df_wave, out_path)
    except Exception as e:
        logger.exception("save_wave_csv failed for %s", out_path)
        raise MferWaveExportError(f"波形 CSV の保存に失敗しました: {e}") from e

    return os.path.abspath(out_path)


def ensure_wave_csv_for_ecg(exam_id: str, exam: Examination) -> tuple[str, bool]:
    """
    心電図 PNG 生成の前に、mfer_tools 経由の波形 CSV を優先して用意する。

    1. ``data/waves/{exam_id}.csv`` が既にあればその絶対パスを返す。
    2. なければ MFER から ``extract_mfer_data`` + ``save_wave_csv`` で作成を試みる
       （mfer-tools の推奨フローに沿う）。
    3. 失敗時は、DB の ``csv_file_path`` が実在する ``.csv`` ならそのパスを返す。
    4. 残るパスが ``.mwf`` のみのときは CSV として読めないため :class:`MferWaveExportError` を送出する。
    5. 上記以外の拡張子で実在するパスは従来どおり返す（読み込みは ``ecg_service`` 側で検証）。

    Returns:
        (csv_path_for_ecg, should_update_db_csv_file_path)
        後者が True のとき、呼び出し側は ``exam.csv_file_path`` を前者に更新して commit する。
    """
    canonical = os.path.abspath(os.path.join(WAVE_DIR, f"{exam_id}.csv"))

    if os.path.isfile(canonical):
        if exam.csv_file_path != canonical:
            logger.info(
                "ECG: 既存の波形CSVを使用します（DBパスを同期します） exam_id=%s path=%s",
                exam_id,
                canonical,
            )
            return canonical, True
        logger.debug("ECG: 既存の波形CSVを使用します exam_id=%s path=%s", exam_id, canonical)
        return canonical, False

    if extract_mfer_data is not None and save_wave_csv is not None:
        try:
            new_path = export_mfer_wave_csv(exam_id, exam)
        except MferWaveExportError as e:
            logger.warning(
                "ECG: 画像生成前の MFER→CSV 自動出力に失敗しました exam_id=%s: %s",
                exam_id,
                e,
            )
        else:
            logger.info(
                "ECG: MFER→CSV を自動出力しました（続けてPNGを生成します） exam_id=%s path=%s",
                exam_id,
                new_path,
            )
            return os.path.abspath(new_path), True

    p = exam.csv_file_path
    if p and p.lower().endswith(".csv"):
        expanded = os.path.abspath(os.path.expanduser(p))
        if os.path.isfile(expanded):
            logger.debug("ECG: DB上のCSVパスを使用します exam_id=%s path=%s", exam_id, expanded)
            return expanded, False

    if p:
        expanded = os.path.abspath(os.path.expanduser(p))
        if Path(expanded).suffix.lower() == ".mwf":
            logger.warning(
                "ECG: 波形CSVが用意できず DB のパスは MFER のみです exam_id=%s path=%s",
                exam_id,
                expanded,
            )
            raise MferWaveExportError(
                "波形CSVがありません。MFER からの自動出力に失敗したか、mfer_tools が利用できません。"
            )
        return expanded, False

    return canonical, False
