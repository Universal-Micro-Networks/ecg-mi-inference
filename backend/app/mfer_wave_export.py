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
