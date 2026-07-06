"""Download the small English Vosk model for offline speech recognition."""

from __future__ import annotations

import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import DEFAULT_VOSK_MODEL_DIR, VOSK_MODEL_DIR, VOSK_MODEL_EXTRACTED

ZIP_NAME = "vosk-model-small-en-us-0.15.zip"
MODEL_URL = f"https://alphacephei.com/vosk/models/{ZIP_NAME}"


def download() -> Path:
    VOSK_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if DEFAULT_VOSK_MODEL_DIR.is_dir() and _model_ok(DEFAULT_VOSK_MODEL_DIR):
        print(f"Vosk model already available: {DEFAULT_VOSK_MODEL_DIR}")
        return DEFAULT_VOSK_MODEL_DIR

    zip_path = VOSK_MODEL_DIR / ZIP_NAME
    if not zip_path.is_file():
        print(f"Downloading {MODEL_URL} …")
        urllib.request.urlretrieve(MODEL_URL, zip_path)

    print("Extracting model…")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(VOSK_MODEL_DIR)

    print(f"Model extracted to {VOSK_MODEL_EXTRACTED}")
    return VOSK_MODEL_EXTRACTED


def _model_ok(path: Path) -> bool:
    return (path / "am").is_dir() or (path / "graph").is_dir()


if __name__ == "__main__":
    try:
        path = download()
        print(f"Done. Set Vosk path to: {path}")
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        sys.exit(1)
