"""Extract mel spectrogram training data from upstream release (no YOLO .h5)."""

from __future__ import annotations

import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data" / "explicit_audio_training"
ZIP_URL = (
    "https://github.com/xaverhimmelsbach/sexual-content-audio-classifier/"
    "releases/download/v1.0.0/dataset.zip"
)
ZIP_CACHE = PROJECT_ROOT / "data" / "_explicit_audio_cache" / "dataset.zip"

SKIP_PREFIXES = ("dataset/models/detection_model",)


def main() -> int:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    ZIP_CACHE.parent.mkdir(parents=True, exist_ok=True)

    if not ZIP_CACHE.is_file() or ZIP_CACHE.stat().st_size < 50_000_000:
        print("Downloading dataset.zip (~297 MB, one-time cache)…")
        urllib.request.urlretrieve(ZIP_URL, ZIP_CACHE)
    else:
        print(f"Using cached zip: {ZIP_CACHE}")

    extracted = 0
    with zipfile.ZipFile(ZIP_CACHE) as zf:
        for info in zf.infolist():
            if any(info.filename.startswith(p) for p in SKIP_PREFIXES):
                continue
            if not (
                info.filename.startswith("dataset/train/")
                or info.filename.startswith("dataset/validation/")
            ):
                continue
            if info.filename.endswith("/"):
                continue
            target = DATA_ROOT / Path(*Path(info.filename).parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(info.filename))
            extracted += 1

    print(f"Extracted {extracted} files to {DATA_ROOT}")
    print("Next: python scripts/train_explicit_audio_cnn.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
