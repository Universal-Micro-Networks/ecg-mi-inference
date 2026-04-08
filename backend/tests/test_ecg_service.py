"""Tests for 12-lead ECG PNG generation."""

from pathlib import Path

import numpy as np
import pytest

from app import ecg_service


def test_generate_ecg_image_single_lead(tmp_path: Path) -> None:
    n = 80
    t = np.arange(n) / 250.0
    lines = ["time,I,II"]
    for i in range(n):
        lines.append(
            f"{t[i]:.6f},{0.1 * np.sin(i * 0.1):.6f},{0.2 * np.cos(i * 0.1):.6f}",
        )
    csv_path = tmp_path / "wave.csv"
    csv_path.write_text("\n".join(lines), encoding="utf-8")

    png, etag = ecg_service.generate_ecg_image(str(csv_path), use_cache=False, lead="II")
    assert len(png) > 1500
    assert len(etag) == 32
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_ecg_image_multilead_csv(tmp_path: Path) -> None:
    n = 100
    t = np.arange(n) / 250.0
    # minimal CSV: time + subset of leads
    lines = ["time,I,II,V1"]
    for i in range(n):
        lines.append(
            f"{t[i]:.6f},{0.1 * np.sin(i * 0.1):.6f},{0.2 * np.cos(i * 0.1):.6f},{0.05 * i:.6f}"
        )
    csv_path = tmp_path / "wave.csv"
    csv_path.write_text("\n".join(lines), encoding="utf-8")

    png, etag = ecg_service.generate_ecg_image(str(csv_path), use_cache=False)
    assert len(png) > 2000
    assert len(etag) == 32
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_load_bundle_single_numeric_column_maps_to_lead_ii(tmp_path: Path) -> None:
    csv_path = tmp_path / "single.csv"
    csv_path.write_text("noise\n0.1\n0.2\n0.15\n", encoding="utf-8")
    b = ecg_service.load_ecg_waveforms_from_csv(str(csv_path))
    assert "II" in b.leads
    assert len(b.time_sec) == 3


def test_ylim_for_lead_group_expands_for_small_amplitude() -> None:
    """タイトな振幅でも大マス整列後の縦幅に 1 mV 校正が収まること。"""
    n = 100
    t = np.arange(n) / 250.0
    y = 50.0 * np.sin(np.linspace(0, 4 * np.pi, n))
    bundle = ecg_service.EcgWaveformBundle(
        time_sec=t,
        leads={"II": y},
        sampling_rate_hz=250,
    )
    lim = ecg_service._ylim_for_lead_group(bundle, ecg_service.LEFT_COLUMN_LEADS)
    assert lim is not None
    y0, y1 = lim
    assert y1 - y0 >= ecg_service._ECG_CAL_PULSE_UV


def test_load_missing_csv_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    with pytest.raises(ecg_service.EcgWaveformLoadError) as exc_info:
        ecg_service.load_ecg_waveforms_from_csv(str(missing))
    assert "存在" in exc_info.value.reason
