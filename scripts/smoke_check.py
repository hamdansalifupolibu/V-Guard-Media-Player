"""Pre-flight check: dependencies, models, FFmpeg, VLC. Run before demos or packaging."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def main() -> int:
    print("V-Guard smoke check\n")
    failures = 0

    print("Python packages:")
    for mod in ("PySide6", "vlc", "cv2", "onnxruntime", "vosk", "requests", "yt_dlp"):
        try:
            __import__(mod)
            _ok(mod)
        except ImportError:
            _fail(f"{mod} — pip install -r requirements.txt")
            failures += 1

    print("\nPaths and models:")
    from app.config import (
        BLOCKED_WORDS_PATH,
        DEFAULT_VOSK_MODEL_DIR,
        VISUAL_MODEL_PATH,
    )
    from app.analysis.explicit_audio_detector import ExplicitAudioDetector

    if BLOCKED_WORDS_PATH.is_file():
        _ok(f"blocked words ({BLOCKED_WORDS_PATH.name})")
    else:
        _fail("data/blocked_words.txt missing")
        failures += 1

    if VISUAL_MODEL_PATH.is_file():
        _ok("Open-NSFW ONNX model")
    else:
        _fail("visual model — run: python scripts/download_visual_model.py")
        failures += 1

    if DEFAULT_VOSK_MODEL_DIR.is_dir():
        _ok("Vosk speech model")
    else:
        _fail("Vosk model — run: python scripts/download_vosk_model.py")
        failures += 1

    if ExplicitAudioDetector.is_model_available():
        _ok("Explicit audio CNN weights")
    else:
        _fail(
            "explicit audio model — run: python scripts/download_explicit_audio_model.py"
        )
        failures += 1

    print("\nExternal tools:")
    from app.utils.ffmpeg_path import is_ffmpeg_available, resolve_ffmpeg_dir

    ff = resolve_ffmpeg_dir()
    if is_ffmpeg_available():
        _ok(f"FFmpeg ({ff})")
    else:
        _fail("FFmpeg — run: python scripts/install_ffmpeg.py")
        failures += 1

    try:
        import vlc

        vlc.Instance("--intf=dummy")
        _ok("libVLC (VLC must be installed on the system)")
    except Exception as exc:  # noqa: BLE001
        _fail(f"VLC — install from https://www.videolan.org/vlc/ ({exc})")
        failures += 1

    print("\nDatabase:")
    try:
        from app.database.db import VGuardDatabase

        test_db = PROJECT_ROOT / "data" / "_smoke_test.db"
        db = VGuardDatabase(test_db)
        db.set_setting("_smoke", "1")
        assert db.get_setting("_smoke") == "1"
        _ok("SQLite read/write")
        del db
        import gc

        gc.collect()
        test_db.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        _fail(f"database — {exc}")
        failures += 1

    print()
    if failures:
        print(f"Smoke check finished with {failures} issue(s).")
        return 1
    print("Smoke check passed — ready to run: python app/main.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
