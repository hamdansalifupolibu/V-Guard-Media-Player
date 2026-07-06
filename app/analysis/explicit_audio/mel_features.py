"""
Log-mel feature extraction for explicit-sound CNN (Lovenia et al., 2022).

Spectrogram layout matches the sexual-content-audio-classifier mel images:
time increases along the horizontal axis; mel bands on the vertical axis.
"""

from __future__ import annotations

import numpy as np

try:
    import librosa
except ImportError:  # pragma: no cover
    librosa = None  # type: ignore

# Aligned with Lovenia et al. (2022) and our upstream mel_spectrogram reference.
SAMPLE_RATE = 16_000
N_FFT = 2048
HOP_LENGTH = 512
N_MELS = 64


def load_audio_mono(path: str, *, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    if librosa is None:
        raise ImportError("librosa is required for explicit audio detection")
    audio, _ = librosa.load(path, sr=sample_rate, mono=True, dtype=np.float32)
    return audio


def compute_log_mel(
    audio: np.ndarray,
    *,
    sample_rate: int = SAMPLE_RATE,
    n_mels: int = N_MELS,
    hop_length: int = HOP_LENGTH,
    n_fft: int = N_FFT,
) -> np.ndarray:
    """Return log-mel matrix shaped (n_mels, time_frames)."""
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sample_rate,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    return log_mel.astype(np.float32)


def normalize_log_mel(log_mel: np.ndarray) -> np.ndarray:
    """
    Per-clip min–max scaling to [0, 1].

    Matches inverted mel PNGs from sexual-content-audio-classifier training data.
    """
    lo = float(log_mel.min())
    hi = float(log_mel.max())
    span = hi - lo
    if span < 1e-6:
        return np.zeros_like(log_mel, dtype=np.float32)
    return ((log_mel - lo) / span).astype(np.float32)


def frames_for_seconds(seconds: float, hop_length: int = HOP_LENGTH) -> int:
    return max(1, int(seconds * SAMPLE_RATE / hop_length))


def extract_time_window(
    log_mel: np.ndarray,
    start_frame: int,
    window_frames: int,
) -> np.ndarray:
    """Crop (n_mels, window_frames) with edge padding if needed."""
    n_mels, total = log_mel.shape
    end = start_frame + window_frames
    if start_frame >= total:
        patch = np.zeros((n_mels, window_frames), dtype=np.float32)
    else:
        patch = log_mel[:, start_frame:min(end, total)]
        if patch.shape[1] < window_frames:
            pad = np.zeros((n_mels, window_frames - patch.shape[1]), dtype=np.float32)
            patch = np.concatenate([patch, pad], axis=1)
    return patch


def export_training_spectrogram_png(
    audio: np.ndarray,
    output_path: str | Path,
    *,
    sample_rate: int = SAMPLE_RATE,
    n_mels: int = 128,
    hop_length: int = HOP_LENGTH,
    n_fft: int = N_FFT,
) -> tuple[int, int]:
    """
    Save inverted log-mel PNG for the training pipeline (upstream format).

    Returns (height, width) of the image.
    """
    from pathlib import Path

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Pillow is required to export training spectrograms") from exc

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sample_rate,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    lo = float(log_mel.min())
    hi = float(log_mel.max())
    span = hi - lo if hi - lo > 1e-6 else 1.0
    scaled = ((log_mel - lo) / span * 255.0).astype(np.uint8)
    scaled = np.flip(scaled, axis=0)
    inverted = 255 - scaled
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(inverted).save(path)
    h, w = inverted.shape
    return h, w


def patch_from_spectrogram_image(
    image_gray: np.ndarray,
    x_start: int,
    patch_width: int,
) -> np.ndarray:
    """Crop a horizontal patch from a saved mel PNG (bands x time)."""
    h, w = image_gray.shape
    x_end = min(w, x_start + patch_width)
    crop = image_gray[:, x_start:x_end]
    if crop.shape[1] < patch_width:
        pad = np.zeros((h, patch_width - crop.shape[1]), dtype=np.uint8)
        crop = np.concatenate([crop, pad], axis=1)
    # PNGs store inverted mel: black = high energy (see upstream mel_spectrogram.py)
    return (255.0 - crop.astype(np.float32)) / 255.0
