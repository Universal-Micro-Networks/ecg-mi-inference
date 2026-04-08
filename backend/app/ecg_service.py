"""
ECG image generation service.
CSV file to PNG image conversion with caching support.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MultipleLocator

logger = logging.getLogger(__name__)

# ECG image cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ecg_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Bump when PNG layout / 解像度が変わったとき（古いキャッシュを使わない）
_ECG_CACHE_VERSION = "v9-12lead-column-ylim-cal"

# PNG 書き出し DPI（figsize[in] × dpi ≒ 辺のピクセル数）。
# 12 誘導は面積が大きいため 800 だと生成・転送・表示で負荷が極端になることが多い。
_ECG_EXPORT_DPI_12_LEAD = 400
# 単誘導モーダル用。細部確認向けに高め（必要なら 600 などに変更可）。
_ECG_EXPORT_DPI_SINGLE_LEAD = 1200

# 12 誘導を 6 行 × 2 列で配置（上から肢体誘導 → 胸誘導）
STANDARD_12_LEAD_GRID: tuple[tuple[str, ...], ...] = (
    ("I", "V1"),
    ("II", "V2"),
    ("III", "V3"),
    ("aVR", "V4"),
    ("aVL", "V5"),
    ("aVF", "V6"),
)
STANDARD_LEAD_NAMES: tuple[str, ...] = tuple(name for row in STANDARD_12_LEAD_GRID for name in row)
LEFT_COLUMN_LEADS: tuple[str, ...] = tuple(row[0] for row in STANDARD_12_LEAD_GRID)
RIGHT_COLUMN_LEADS: tuple[str, ...] = tuple(row[1] for row in STANDARD_12_LEAD_GRID)

# ECG 用紙スケール:
# - 25 mm/s: 0.04 s / 小マス, 0.20 s / 大マス
# - 10 mm/mV: 0.1 mV(=100 μV) / 小マス, 0.5 mV(=500 μV) / 大マス
_ECG_SEC_PER_SMALL_BOX = 0.04
_ECG_SEC_PER_BIG_BOX = 0.20
_ECG_UV_PER_SMALL_BOX = 100.0
_ECG_UV_PER_BIG_BOX = 500.0
_ECG_CAL_PULSE_SEC = 0.20
_ECG_CAL_PULSE_UV = 1000.0  # 1 mV


def _ecg_second_label_formatter(x: float, _pos: int) -> str:
    # 目盛りは 0.20 秒ごとに置きつつ、表示ラベルは 1 秒刻みだけにして詰まりを防ぐ。
    if np.isclose(x % 1.0, 0.0, atol=1e-9) or np.isclose(x % 1.0, 1.0, atol=1e-9):
        return f"{x:.0f}"
    return ""


def _apply_ecg_grid(ax: Axes) -> None:
    ax.xaxis.set_major_locator(MultipleLocator(_ECG_SEC_PER_BIG_BOX))
    ax.xaxis.set_minor_locator(MultipleLocator(_ECG_SEC_PER_SMALL_BOX))
    ax.yaxis.set_major_locator(MultipleLocator(_ECG_UV_PER_BIG_BOX))
    ax.yaxis.set_minor_locator(MultipleLocator(_ECG_UV_PER_SMALL_BOX))
    # 紙グリッド風に、major をやや濃く、minor を薄く描画
    ax.grid(True, which="major", color="#9ca3af", alpha=0.45, linewidth=0.5)
    ax.grid(True, which="minor", color="#d1d5db", alpha=0.6, linewidth=0.3)


def _draw_calibration_pulse(ax: Axes) -> None:
    """
    標準校正波（1 mV, 0.2 s）の矩形パルスを描画する。
    心電図用紙の基準（10 mm/mV, 25 mm/s）に対応。
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x_span = x1 - x0
    y_span = y1 - y0
    if x_span <= 0 or y_span <= 0:
        return

    # 左下寄りに配置（波形と重なりにくい位置）
    base_y = y0 + y_span * 0.08
    if base_y + _ECG_CAL_PULSE_UV > y1 - y_span * 0.05:
        base_y = y1 - y_span * 0.05 - _ECG_CAL_PULSE_UV
    if base_y < y0:
        return

    start_x = x0 + x_span * 0.02
    end_x = start_x + _ECG_CAL_PULSE_SEC
    if end_x > x1 - x_span * 0.01:
        return

    ax.plot(
        [start_x, start_x, end_x, end_x],
        [base_y, base_y + _ECG_CAL_PULSE_UV, base_y + _ECG_CAL_PULSE_UV, base_y],
        "k-",
        linewidth=0.8,
        zorder=4,
    )
    # 校正波描画で limits が動かないように戻す
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)


class EcgWaveformLoadError(Exception):
    """波形 CSV から利用可能な誘導データを読み込めない（合成波形は用いない）。"""

    def __init__(self, reason: str, csv_path: str):
        self.reason = reason
        self.csv_path = csv_path
        super().__init__(f"{reason} (path={csv_path})")


@dataclass(frozen=True)
class EcgWaveformBundle:
    """CSV から読み込んだ時系列と、存在する誘導ごとの波形。"""

    time_sec: np.ndarray
    leads: dict[str, np.ndarray]
    sampling_rate_hz: int


def _default_sampling_rate_hz() -> int:
    return 250


def _infer_sampling_rate_from_time(time_sec: np.ndarray) -> int:
    if len(time_sec) < 2:
        return _default_sampling_rate_hz()
    dt = float(np.median(np.diff(time_sec.astype(np.float64))))
    if dt <= 0:
        return _default_sampling_rate_hz()
    return max(1, int(round(1.0 / dt)))


def load_ecg_waveforms_from_csv(csv_path: str) -> EcgWaveformBundle:
    """
    CSV から時刻列・標準12誘導名の列を読み込む。
    MFER 由来の `save_wave_csv` 出力（time + I, II, ...）を想定。
    列が足りない誘導は generate_ecg_image 側で空欄表示する。
    読み込み不能時は EcgWaveformLoadError を送出する（デモ用合成波形は返さない）。
    """
    if not os.path.exists(csv_path):
        reason = "指定パスのファイルが存在しません"
        logger.warning("ECG: 波形CSVを読み込めません path=%s reason=%s", csv_path, reason)
        raise EcgWaveformLoadError(reason, csv_path)

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        reason = f"CSVの解析に失敗しました: {type(e).__name__}: {e}"
        logger.warning("ECG: 波形CSVを読み込めません path=%s reason=%s", csv_path, reason)
        raise EcgWaveformLoadError(reason, csv_path) from e

    time_col = "time" if "time" in df.columns else None

    leads: dict[str, np.ndarray] = {}
    for name in STANDARD_LEAD_NAMES:
        if name in df.columns:
            leads[name] = df[name].to_numpy(dtype=np.float64, copy=True)

    if time_col is not None:
        time_sec = df[time_col].to_numpy(dtype=np.float64, copy=True)
        fs = _infer_sampling_rate_from_time(time_sec)
    else:
        if not leads:
            first = next(
                (c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])),
                None,
            )
            if first is not None:
                leads["II"] = df[first].to_numpy(dtype=np.float64, copy=True)
        n = len(df) if not leads else min(len(df), min(len(v) for v in leads.values()))
        fs = _default_sampling_rate_hz()
        time_sec = np.arange(n, dtype=np.float64) / fs

    if not leads:
        reason = "標準誘導列（I, II, III, aVR, …）または数値列がなく、利用可能な波形がありません"
        logger.warning("ECG: 波形CSVを読み込めません path=%s reason=%s", csv_path, reason)
        raise EcgWaveformLoadError(reason, csv_path)

    lengths = [len(time_sec)] + [len(v) for v in leads.values()]
    n = min(lengths)
    time_sec = time_sec[:n]
    leads = {k: v[:n] for k, v in leads.items()}

    return EcgWaveformBundle(
        time_sec=time_sec,
        leads=leads,
        sampling_rate_hz=int(fs),
    )


def _ylim_for_lead_group(
    bundle: EcgWaveformBundle,
    group: tuple[str, ...],
) -> tuple[float, float] | None:
    """
    単誘導表示と同じ規則で、列（肢体誘導群 or 胸誘導群）の縦軸範囲を決める。
    大マス 500 µV に合わせ、1 mV 校正波が収まりやすい余裕を持たせる。
    """
    group_arrays = [bundle.leads[name] for name in group if name in bundle.leads]
    if not group_arrays:
        return None
    y_min = min(float(np.min(a)) for a in group_arrays)
    y_max = max(float(np.max(a)) for a in group_arrays)
    if not (np.isfinite(y_min) and np.isfinite(y_max)):
        return None
    pad = max(0.1, (y_max - y_min) * 0.05)
    if y_max <= y_min:
        pad = max(0.1, abs(y_max) * 0.05)
    y0 = np.floor((y_min - pad) / _ECG_UV_PER_BIG_BOX) * _ECG_UV_PER_BIG_BOX
    y1 = np.ceil((y_max + pad) / _ECG_UV_PER_BIG_BOX) * _ECG_UV_PER_BIG_BOX
    if y1 <= y0:
        y1 = y0 + _ECG_UV_PER_BIG_BOX
    return (float(y0), float(y1))


def _plot_12_lead_figure(bundle: EcgWaveformBundle) -> Figure:
    n = len(bundle.time_sec)
    n_rows, n_cols = 6, 2
    # 左列・右列それぞれで縦横スケールを統一する（列内比較しやすくする）。
    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(9.5, 16),
        dpi=100,
        sharex="col",
        sharey="col",
    )
    t = bundle.time_sec

    for r, row in enumerate(STANDARD_12_LEAD_GRID):
        for c, lead in enumerate(row):
            ax = axes[r, c]
            ax.set_ylabel(lead, rotation=0, ha="right", va="center", fontsize=9, labelpad=8)
            if lead in bundle.leads:
                y = bundle.leads[lead]
                m = min(len(y), n)
                ax.plot(t[:m], y[:m], "k-", linewidth=0.25)
            else:
                ax.text(
                    0.5,
                    0.5,
                    "—",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=11,
                    color="#9ca3af",
                )
            _apply_ecg_grid(ax)
            ax.tick_params(axis="both", labelsize=7, labelleft=False, labelbottom=False)

    for c, group in enumerate((LEFT_COLUMN_LEADS, RIGHT_COLUMN_LEADS)):
        ylim = _ylim_for_lead_group(bundle, group)
        if ylim is not None:
            for r in range(n_rows):
                axes[r, c].set_ylim(ylim)

    duration = float(t[-1]) if n > 0 else 0.0
    for ax in axes[-1]:
        ax.set_xlabel("Time (s)", fontsize=9)
        if duration > 0:
            ax.set_xlim(0, duration)
        ax.xaxis.set_major_formatter(FuncFormatter(_ecg_second_label_formatter))
    for row_axes in axes:
        for ax in row_axes:
            _draw_calibration_pulse(ax)

    fig.suptitle(
        f"12-lead ECG ({bundle.sampling_rate_hz} Hz sampling)",
        fontsize=12,
        fontweight="bold",
    )
    fig.subplots_adjust(left=0.09, right=0.99, top=0.97, bottom=0.04, hspace=0.22, wspace=0.32)
    return fig


def _plot_single_lead_figure(bundle: EcgWaveformBundle, lead: str) -> Figure:
    """1 誘導のみを大きく描画（拡大表示用）。"""
    n = len(bundle.time_sec)
    fig, ax = plt.subplots(1, 1, figsize=(10.5, 3.8), dpi=100)
    t = bundle.time_sec
    if lead in bundle.leads:
        y = bundle.leads[lead]
        m = min(len(y), n)
        ax.plot(t[:m], y[:m], "k-", linewidth=0.25)
        ax.set_title(
            f"Lead {lead} — {bundle.sampling_rate_hz} Hz sampling",
            fontsize=12,
            fontweight="bold",
        )
    else:
        ax.text(
            0.5,
            0.5,
            "—",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=14,
            color="#9ca3af",
        )
        ax.set_title(f"Lead {lead} — no data", fontsize=12, fontweight="bold")
    ax.set_xlabel("Time (s)", fontsize=10)
    ax.set_ylabel("μV", fontsize=10)
    _apply_ecg_grid(ax)
    ax.tick_params(axis="both", labelsize=8, labelleft=False, labelbottom=False)
    group = LEFT_COLUMN_LEADS if lead in LEFT_COLUMN_LEADS else RIGHT_COLUMN_LEADS
    ylim = _ylim_for_lead_group(bundle, group)
    if ylim is not None:
        ax.set_ylim(ylim)
    duration = float(t[-1]) if n > 0 else 0.0
    if duration > 0:
        ax.set_xlim(0, duration)
    ax.xaxis.set_major_formatter(FuncFormatter(_ecg_second_label_formatter))
    _draw_calibration_pulse(ax)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.88, bottom=0.14)
    return fig


def get_ecg_cache_path(csv_path: str, lead: str | None = None) -> str:
    """CSV パスと任意の誘導名に対応するキャッシュ PNG のパス（12 誘導は lead=None）。"""
    lid = "12lead" if lead is None else lead
    cache_key = hashlib.md5(f"{_ECG_CACHE_VERSION}:{csv_path}:{lid}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{cache_key}.png")


def invalidate_ecg_cache_for_csv(csv_path: str) -> None:
    """指定 CSV に紐づく 12 誘導・単誘導のキャッシュ PNG をすべて削除する。"""
    for lid in (None, *STANDARD_LEAD_NAMES):
        p = get_ecg_cache_path(csv_path, lid)
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError as e:
            logger.warning("ECG: キャッシュ削除に失敗 path=%s err=%s", p, e)


def generate_ecg_image(
    csv_path: str,
    use_cache: bool = True,
    lead: str | None = None,
) -> tuple[bytes, str]:
    """
    Generate 12-lead ECG PNG from CSV (multi-column waveform per lead).
    lead を指定した場合はその 1 誘導のみの PNG を返す。

    Args:
        csv_path: Path to CSV file containing ECG data
        use_cache: Whether to use cached image if available
        lead: 単誘導 PNG を返すときの誘導名（STANDARD_LEAD_NAMES のいずれか）

    Returns:
        Tuple of (image_bytes, etag)

    Raises:
        EcgWaveformLoadError: CSV が存在しない・解析できない・利用可能な誘導がない場合
        ValueError: lead が標準誘導名でない場合
    """
    if lead is not None and lead not in STANDARD_LEAD_NAMES:
        raise ValueError(f"unknown lead: {lead}")

    cache_path = get_ecg_cache_path(csv_path, lead)

    if use_cache and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            image_bytes = f.read()
        etag = hashlib.md5(image_bytes).hexdigest()
        return image_bytes, etag

    bundle = load_ecg_waveforms_from_csv(csv_path)
    if lead is not None:
        fig = _plot_single_lead_figure(bundle, lead)
        export_dpi = _ECG_EXPORT_DPI_SINGLE_LEAD
    else:
        fig = _plot_12_lead_figure(bundle)
        export_dpi = _ECG_EXPORT_DPI_12_LEAD

    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format="png", bbox_inches="tight", dpi=export_dpi)
    image_buffer.seek(0)
    image_bytes = image_buffer.getvalue()
    plt.close(fig)

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, "wb") as f:
            f.write(image_bytes)
    except OSError as e:
        logger.warning("Failed to cache ECG image: %s", e)

    etag = hashlib.md5(image_bytes).hexdigest()
    return image_bytes, etag


def clear_ecg_cache():
    """Clear all cached ECG images."""
    try:
        for file in os.listdir(CACHE_DIR):
            if file.endswith(".png"):
                os.remove(os.path.join(CACHE_DIR, file))
    except OSError as e:
        logger.warning("Error clearing ECG cache: %s", e)
