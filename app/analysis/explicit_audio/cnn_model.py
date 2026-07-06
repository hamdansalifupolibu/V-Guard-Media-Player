"""
Small CNN for pornographic-sound detection on log-mel patches.

Architecture inspired by Lovenia et al., 2022 (32-filter convolutions, binary output).
"""

from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn

from app.analysis.explicit_audio.mel_features import N_MELS


class ExplicitAudioCNN(nn.Module):
    """Binary classifier: 1 = sexual / moan-like sound, 0 = safe."""

    def __init__(self, n_mels: int = N_MELS, time_frames: int = 64) -> None:
        super().__init__()
        self.n_mels = n_mels
        self.time_frames = time_frames
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 8)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 8, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        return self.classifier(x)


def save_checkpoint(path: Path, model: ExplicitAudioCNN, meta: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state_dict": model.state_dict(),
        "n_mels": model.n_mels,
        "time_frames": model.time_frames,
        "meta": meta or {},
    }
    torch.save(payload, path)


def load_checkpoint(path: Path, *, map_location: str = "cpu") -> tuple[ExplicitAudioCNN, dict]:
    try:
        payload = torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        payload = torch.load(path, map_location=map_location)
    model = ExplicitAudioCNN(
        n_mels=int(payload.get("n_mels", N_MELS)),
        time_frames=int(payload.get("time_frames", 64)),
    )
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model, payload.get("meta", {})
