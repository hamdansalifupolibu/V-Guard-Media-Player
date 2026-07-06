"""
Train the explicit-sound CNN from sexual-content-audio-classifier mel PNGs.

Uses Pascal VOC XML moan boxes on wide spectrogram images (dataset release).
Skips the 247 MB YOLO weights — trains a small PyTorch CNN (~2 MB).

Usage:
  python scripts/download_explicit_audio_data.py   # once (~50 MB without .h5)
  python scripts/train_explicit_audio_cnn.py
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from app.analysis.explicit_audio.cnn_model import ExplicitAudioCNN, save_checkpoint
from app.analysis.explicit_audio.mel_features import patch_from_spectrogram_image

PATCH_TIME_FRAMES = 64
from app.config import EXPLICIT_AUDIO_MODEL_PATH

DATA_ROOT = PROJECT_ROOT / "data" / "explicit_audio_training"
PATCH_WIDTH = 256


def _parse_moan_x_ranges(xml_bytes: bytes) -> list[tuple[int, int]]:
    root = ET.fromstring(xml_bytes)
    ranges: list[tuple[int, int]] = []
    for obj in root.findall("object"):
        name = obj.findtext("name", default="")
        if name.strip().lower() != "moan":
            continue
        box = obj.find("bndbox")
        if box is None:
            continue
        xmin = int(float(box.findtext("xmin", "0")))
        xmax = int(float(box.findtext("xmax", "0")))
        ranges.append((xmin, xmax))
    return ranges


def _patch_label(x_start: int, x_end: int, moan_ranges: list[tuple[int, int]]) -> int:
    for xmin, xmax in moan_ranges:
        if x_start < xmax and x_end > xmin:
            return 1
    return 0


class SpectrogramPatchDataset(Dataset):
    def __init__(self, split_dir: Path) -> None:
        self.samples: list[tuple[np.ndarray, int]] = []
        images_dir = split_dir / "images"
        ann_dir = split_dir / "annotations"
        if not images_dir.is_dir():
            return

        for img_path in sorted(images_dir.glob("*.png")):
            xml_path = ann_dir / f"{img_path.stem}.xml"
            moan_ranges: list[tuple[int, int]] = []
            if xml_path.is_file():
                moan_ranges = _parse_moan_x_ranges(xml_path.read_bytes())
            gray = np.array(Image.open(img_path).convert("L"))
            h, w = gray.shape
            step = PATCH_WIDTH // 2
            for x in range(0, max(1, w - PATCH_WIDTH), step):
                label = _patch_label(x, x + PATCH_WIDTH, moan_ranges)
                patch = patch_from_spectrogram_image(gray, x, PATCH_WIDTH)
                patch = _resize_to_model(patch)
                self.samples.append((patch, label))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        patch, label = self.samples[idx]
        x = torch.from_numpy(patch).float().unsqueeze(0)
        y = torch.tensor([float(label)], dtype=torch.float32)
        return x, y


def _resize_to_model(patch: np.ndarray) -> np.ndarray:
    n_mels, current = patch.shape
    target = PATCH_TIME_FRAMES
    if current == target and n_mels == 64:
        return patch
    out = np.zeros((64, target), dtype=np.float32)
    h_crop = min(n_mels, 64)
    out[:h_crop, : min(current, target)] = patch[:h_crop, : min(current, target)]
    return out


def train(
    *,
    epochs: int = 20,
    batch_size: int = 32,
    learning_rate: float = 3e-4,
) -> Path:
    train_ds = SpectrogramPatchDataset(DATA_ROOT / "train")
    val_ds = SpectrogramPatchDataset(DATA_ROOT / "validation")
    if len(train_ds) == 0:
        raise RuntimeError(
            f"No training patches under {DATA_ROOT}. "
            "Run: python scripts/download_explicit_audio_data.py"
        )

    sample_weights = [8.0 if label == 1 else 1.0 for _, label in train_ds.samples]
    sampler = WeightedRandomSampler(
        sample_weights, num_samples=len(sample_weights), replacement=True
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler)
    val_loader = DataLoader(val_ds, batch_size=batch_size) if len(val_ds) else None

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ExplicitAudioCNN().to(device)
    pos = sum(1 for _, y in train_ds.samples if y == 1)
    neg = len(train_ds) - pos
    pos_weight = torch.tensor([neg / max(pos, 1)], device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    best_f1 = -1.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())

        val_f1 = _eval_f1(model, val_loader, device) if val_loader else 0.0
        print(
            f"Epoch {epoch}/{epochs}  loss={total_loss / len(train_loader):.4f}  "
            f"val_f1={val_f1:.3f}  patches={len(train_ds)} (pos={pos})"
        )
        if val_f1 >= best_f1:
            best_f1 = val_f1
            save_checkpoint(
                EXPLICIT_AUDIO_MODEL_PATH,
                model.cpu(),
                meta={"val_f1": val_f1, "epochs": epoch},
            )
            if device == "cuda":
                model = model.cuda()

    if not EXPLICIT_AUDIO_MODEL_PATH.is_file():
        save_checkpoint(EXPLICIT_AUDIO_MODEL_PATH, model.cpu(), meta={"val_f1": best_f1})
    print(f"Saved model -> {EXPLICIT_AUDIO_MODEL_PATH}")
    return EXPLICIT_AUDIO_MODEL_PATH


def _eval_f1(model: ExplicitAudioCNN, loader: DataLoader | None, device: str) -> float:
    if loader is None or len(loader.dataset) == 0:
        return 0.0
    model.eval()
    tp = fp = fn = 0
    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            probs = torch.sigmoid(model(batch_x)).cpu().numpy().flatten()
            labels = batch_y.numpy().flatten()
            preds = (probs >= 0.5).astype(int)
            tp += int(((preds == 1) & (labels == 1)).sum())
            fp += int(((preds == 1) & (labels == 0)).sum())
            fn += int(((preds == 0) & (labels == 1)).sum())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train explicit-sound CNN")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    train(epochs=args.epochs, batch_size=args.batch_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
