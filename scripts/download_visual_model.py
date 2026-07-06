"""Download the Open-NSFW ONNX model into models/visual_model/."""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "visual_model"  # noqa: same as VISUAL_MODEL_DIR
OUTPUT_PATH = MODEL_DIR / "open_nsfw.onnx"

# Hugging Face mirror of the Yahoo Open-NSFW ONNX weights (~24 MB)
MODEL_URL = (
    "https://huggingface.co/bluefoxcreation/open-nsfw/resolve/main/open-nsfw.onnx"
)


def download() -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.is_file():
        print(f"Model already exists: {OUTPUT_PATH}")
        return OUTPUT_PATH

    print(f"Downloading from {MODEL_URL} …")
    urllib.request.urlretrieve(MODEL_URL, OUTPUT_PATH)
    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved {OUTPUT_PATH} ({size_mb:.1f} MB)")
    return OUTPUT_PATH


if __name__ == "__main__":
    try:
        download()
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        sys.exit(1)
