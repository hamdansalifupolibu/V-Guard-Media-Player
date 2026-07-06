"""Prepare explicit-sound CNN: training data + weights (~2 MB)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import EXPLICIT_AUDIO_MODEL_PATH


def main() -> int:
    train_data = PROJECT_ROOT / "data" / "explicit_audio_training" / "train" / "images"
    if not train_data.is_dir() or not any(train_data.glob("*.png")):
        print("Step 1/2: Download training spectrograms…")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "download_explicit_audio_data.py")],
            check=True,
        )
    else:
        print("Training data already present.")

    if EXPLICIT_AUDIO_MODEL_PATH.is_file():
        print(f"Model already exists: {EXPLICIT_AUDIO_MODEL_PATH}")
        return 0

    print("Step 2/2: Train explicit-sound CNN (CPU, a few minutes)…")
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "train_explicit_audio_cnn.py")],
        check=True,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
