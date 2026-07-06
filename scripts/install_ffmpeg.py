"""Download portable FFmpeg into tools/ffmpeg (Windows). Run once if not on PATH."""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools" / "ffmpeg"
# BtbN win64 GPL build (essentials — includes ffmpeg.exe)
FFMPEG_ZIP_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)


def find_ffmpeg_exe(root: Path) -> Path | None:
    for candidate in root.rglob("ffmpeg.exe"):
        return candidate
    return None


def install() -> Path:
    existing = find_ffmpeg_exe(TOOLS_DIR)
    if existing and existing.is_file():
        print(f"FFmpeg already installed: {existing}")
        return existing.parent

    zip_path = TOOLS_DIR / "ffmpeg-download.zip"
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading FFmpeg from {FFMPEG_ZIP_URL} …")
    urlretrieve(FFMPEG_ZIP_URL, zip_path)  # noqa: S310

    extract_dir = TOOLS_DIR / "_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)

    print("Extracting…")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    exe = find_ffmpeg_exe(extract_dir)
    if not exe:
        raise RuntimeError("ffmpeg.exe not found in downloaded archive")

    bin_dir = TOOLS_DIR / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for tool in ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe"):
        src = exe.parent / tool
        if src.is_file():
            shutil.copy2(src, bin_dir / tool)

    shutil.rmtree(extract_dir, ignore_errors=True)
    zip_path.unlink(missing_ok=True)

    out = bin_dir / "ffmpeg.exe"
    if not out.is_file():
        raise RuntimeError("Failed to install ffmpeg.exe")
    print(f"Installed: {out}")
    return bin_dir


if __name__ == "__main__":
    try:
        install()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
