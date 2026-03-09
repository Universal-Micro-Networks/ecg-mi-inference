"""
ECG image generation service.
CSV file to PNG image conversion with caching support.
"""

import hashlib
import io
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

# ECG image cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ecg_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _generate_synthetic_ecg(duration: float = 5.0, sampling_rate: int = 250) -> np.ndarray:
    """
    Generate synthetic ECG signal for demo purposes.
    This mimics a realistic ECG waveform with P-QRS-T complexes.
    """
    t = np.arange(0, duration, 1 / sampling_rate)
    ecg_signal = np.zeros_like(t)

    # Generate repeating PQRST complexes
    heart_rate = 70  # bpm
    rr_interval = 60 / heart_rate  # seconds

    for beat_num in range(int(duration / rr_interval) + 1):
        beat_start = beat_num * rr_interval
        beat_indices = np.where((t >= beat_start) & (t < beat_start + rr_interval))[0]

        if len(beat_indices) == 0:
            continue

        # Relative time within beat (0 to 1)
        beat_t = (t[beat_indices] - beat_start) / rr_interval

        # P wave (low amplitude, early)
        p_wave = 0.15 * np.exp(-20 * (beat_t - 0.2) ** 2)

        # QRS complex (high amplitude, rapid)
        q_wave = -0.1 * np.sin(np.pi * (beat_t - 0.35) / 0.05) * np.exp(-100 * (beat_t - 0.35) ** 2)
        r_wave = 1.0 * np.exp(-20 * (beat_t - 0.4) ** 2)
        s_wave = -0.3 * np.exp(-20 * (beat_t - 0.45) ** 2)

        # T wave (lower amplitude, later)
        t_wave = 0.3 * np.exp(-15 * (beat_t - 0.65) ** 2)

        # Baseline with slight drift
        baseline = 0.02 * beat_t

        # Combine components
        beat_signal = p_wave + q_wave + r_wave + s_wave + t_wave + baseline

        # Add small noise
        noise = np.random.normal(0, 0.02, len(beat_indices))
        ecg_signal[beat_indices] = beat_signal + noise

    return ecg_signal


def load_ecg_from_csv(csv_path: str) -> tuple[np.ndarray, int]:
    """
    Load ECG signal from CSV file.
    Expected CSV format: columns with ECG signal values or time/value pairs.

    Falls back to synthetic ECG if file doesn't exist (for demo purposes).

    Returns:
        Tuple of (ecg_signal, sampling_rate)
    """
    if not os.path.exists(csv_path):
        # Generate synthetic ECG for demo
        return _generate_synthetic_ecg(), 250

    try:
        df = pd.read_csv(csv_path)

        # Try to find ECG signal column
        # Common column names: 'ECG', 'ecg', 'II', 'aVF', 'V2', 'V3', 'V4', etc.
        ecg_column = None
        for col in ["ECG", "ecg", "II", "aVF", "V2", "V3", "V4", "lead_II"]:
            if col in df.columns:
                ecg_column = col
                break

        if ecg_column is None:
            # Use first numeric column
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                ecg_column = numeric_cols[0]

        if ecg_column is None:
            raise ValueError("No numeric ECG column found in CSV")

        ecg_signal = df[ecg_column].values.astype(np.float32)
        sampling_rate = 250  # Default assumption

        return ecg_signal, sampling_rate

    except Exception as e:
        print(f"Error loading ECG from {csv_path}: {e}")
        return _generate_synthetic_ecg(), 250


def generate_ecg_image(csv_path: str, use_cache: bool = True) -> tuple[bytes, str]:
    """
    Generate ECG image from CSV file.

    Args:
        csv_path: Path to CSV file containing ECG data
        use_cache: Whether to use cached image if available

    Returns:
        Tuple of (image_bytes, etag)
    """
    # Generate cache key from file path
    cache_key = hashlib.md5(csv_path.encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.png")

    # Check if cached version exists
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            image_bytes = f.read()
        etag = hashlib.md5(image_bytes).hexdigest()
        return image_bytes, etag

    # Load ECG signal
    ecg_signal, sampling_rate = load_ecg_from_csv(csv_path)

    # Create figure
    fig: Figure = plt.figure(figsize=(12, 4), dpi=100)
    ax = fig.add_subplot(111)

    # Time array
    duration = len(ecg_signal) / sampling_rate
    time = np.arange(len(ecg_signal)) / sampling_rate

    # Plot ECG
    ax.plot(time, ecg_signal, "b-", linewidth=1.0)
    ax.set_xlabel("Time (s)", fontsize=10)
    ax.set_ylabel("Voltage (mV)", fontsize=10)
    ax.set_title("12-lead ECG Signal", fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_xlim((0, duration))

    # Add grid lines every 0.2s (equivalent to 50mm on standard ECG paper at 25mm/s)
    ax.set_xticks(np.arange(0, duration + 0.2, 0.2))
    ax.set_xticks(np.arange(0, duration + 0.04, 0.04), minor=True)

    # Convert to PNG bytes
    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format="png", bbox_inches="tight", dpi=100)
    image_buffer.seek(0)
    image_bytes = image_buffer.getvalue()
    plt.close(fig)

    # Cache the image
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, "wb") as f:
            f.write(image_bytes)
    except Exception as e:
        print(f"Warning: Failed to cache ECG image: {e}")

    # Generate ETag
    etag = hashlib.md5(image_bytes).hexdigest()

    return image_bytes, etag


def get_ecg_cache_path(csv_path: str) -> str:
    """Get the cache file path for a CSV ECG file."""
    cache_key = hashlib.md5(csv_path.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{cache_key}.png")


def clear_ecg_cache():
    """Clear all cached ECG images."""
    try:
        for file in os.listdir(CACHE_DIR):
            if file.endswith(".png"):
                os.remove(os.path.join(CACHE_DIR, file))
    except Exception as e:
        print(f"Error clearing cache: {e}")
