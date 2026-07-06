"""
Add a WAV clip to the explicit-sound training set (mel PNG + VOC XML).

Creates files under data/explicit_audio_training/{train|validation}/ so you can
re-run: python scripts/train_explicit_audio_cnn.py

Examples:
  # Positive: 10 s clip with moan between 3s and 6s
  python scripts/prepare_explicit_audio_clip.py ^
    --wav "data/my_clips/got_scene.wav" ^
    --split train --label positive --moan-start 3 --moan-end 6

  # Negative: safe dialogue (no moan regions)
  python scripts/prepare_explicit_audio_clip.py ^
    --wav "data/my_clips/safe_dialogue.wav" ^
    --split train --label negative
"""

from __future__ import annotations

import argparse
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.analysis.explicit_audio.mel_features import (
    SAMPLE_RATE,
    export_training_spectrogram_png,
    load_audio_mono,
)

DATA_ROOT = PROJECT_ROOT / "data" / "explicit_audio_training"


def _write_voc_xml(
    path: Path,
    *,
    filename: str,
    width: int,
    height: int,
    moan_ranges: list[tuple[int, int]],
) -> None:
    root = ET.Element("annotation")
    ET.SubElement(root, "folder").text = "images"
    ET.SubElement(root, "filename").text = filename
    ET.SubElement(root, "path").text = f"images/{filename}"
    src = ET.SubElement(root, "source")
    ET.SubElement(src, "database").text = "V-Guard"
    size = ET.SubElement(root, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = "3"
    ET.SubElement(root, "segmented").text = "0"
    for xmin, xmax in moan_ranges:
        obj = ET.SubElement(root, "object")
        ET.SubElement(obj, "name").text = "Moan"
        ET.SubElement(obj, "pose").text = "Unspecified"
        ET.SubElement(obj, "truncated").text = "0"
        ET.SubElement(obj, "difficult").text = "0"
        box = ET.SubElement(obj, "bndbox")
        ET.SubElement(box, "xmin").text = str(max(0, xmin))
        ET.SubElement(box, "ymin").text = "0"
        ET.SubElement(box, "xmax").text = str(min(width, xmax))
        ET.SubElement(box, "ymax").text = str(height)
    tree = ET.ElementTree(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=False)


def _sec_to_pixels(start_sec: float, end_sec: float, duration_sec: float, width: int) -> tuple[int, int]:
    if duration_sec <= 0:
        return 0, width
    xmin = int(start_sec / duration_sec * width)
    xmax = int(end_sec / duration_sec * width)
    return max(0, xmin), max(xmin + 1, xmax)


def main() -> int:
    parser = argparse.ArgumentParser(description="Add WAV clip to explicit-audio training set")
    parser.add_argument("--wav", required=True, help="Path to .wav clip (mono/stereo OK)")
    parser.add_argument(
        "--split",
        choices=["train", "validation"],
        default="train",
        help="train or validation folder",
    )
    parser.add_argument(
        "--label",
        choices=["positive", "negative"],
        required=True,
        help="positive = contains moan/suggestive vocal; negative = safe",
    )
    parser.add_argument(
        "--moan-start",
        type=float,
        action="append",
        default=[],
        help="Start time (seconds) of a moan region; repeat for multiple regions",
    )
    parser.add_argument(
        "--moan-end",
        type=float,
        action="append",
        default=[],
        help="End time (seconds) matching each --moan-start",
    )
    args = parser.parse_args()

    wav_path = Path(args.wav)
    if not wav_path.is_file():
        print(f"File not found: {wav_path}")
        return 1

    if args.label == "positive" and len(args.moan_start) != len(args.moan_end):
        print("Provide the same number of --moan-start and --moan-end values.")
        return 1
    if args.label == "positive" and not args.moan_start:
        print("Positive clips need at least one --moan-start / --moan-end pair.")
        return 1

    clip_id = uuid.uuid4().hex
    split_dir = DATA_ROOT / args.split
    images_dir = split_dir / "images"
    ann_dir = split_dir / "annotations"
    images_dir.mkdir(parents=True, exist_ok=True)
    ann_dir.mkdir(parents=True, exist_ok=True)

    audio = load_audio_mono(str(wav_path))
    duration_sec = len(audio) / SAMPLE_RATE
    png_path = images_dir / f"{clip_id}.png"
    height, width = export_training_spectrogram_png(audio, png_path)

    moan_px: list[tuple[int, int]] = []
    if args.label == "positive":
        for start, end in zip(args.moan_start, args.moan_end, strict=True):
            moan_px.append(_sec_to_pixels(start, end, duration_sec, width))

    _write_voc_xml(
        ann_dir / f"{clip_id}.xml",
        filename=f"{clip_id}.png",
        width=width,
        height=height,
        moan_ranges=moan_px,
    )

    print(f"Added {args.label} clip to {args.split}:")
    print(f"  {png_path}")
    print(f"  {ann_dir / f'{clip_id}.xml'}")
    print("Retrain with: python scripts/train_explicit_audio_cnn.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
