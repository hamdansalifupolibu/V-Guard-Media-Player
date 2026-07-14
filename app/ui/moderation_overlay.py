"""Live blurred shield overlay when visual moderation hides explicit scenes."""

from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QStackedLayout, QVBoxLayout, QWidget

from app.config import (
    MODERATION_SHIELD_BLUR_SIGMA,
    MODERATION_SHIELD_CAPTURE_HEIGHT,
    MODERATION_SHIELD_CAPTURE_WIDTH,
    MODERATION_SHIELD_DOWNSAMPLE_FACTOR,
    MODERATION_SHIELD_FPS,
    MODERATION_SHIELD_FROST_ALPHA,
)

FrameProvider = Callable[[], bytes | None]


class ModerationShieldOverlay(QWidget):
    """
    Covers the VLC surface with a heavily blurred live feed plus a frosted tint.

    VLC renders to a native window on Windows, so a semi-transparent QWidget cannot
    composite over it. We snapshot the playing frame, blur it, and paint that
    so motion is still visible but content is obscured.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("moderationShield")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #1a1528; border-radius: 8px;")
        self.hide()

        self._frame_provider: FrameProvider | None = None
        self._active = False

        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._image = QLabel()
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image.setScaledContents(True)
        self._image.setStyleSheet("background: #1a1528; border: none;")
        stack.addWidget(self._image)

        badge_host = QWidget()
        badge_host.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        badge_layout = QVBoxLayout(badge_host)
        badge_layout.setContentsMargins(12, 12, 12, 14)
        badge_layout.addStretch()
        self._badge = QLabel("  🛡  Content shielded — scene blurred for safety  ")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(
            "background-color: rgba(124, 58, 237, 0.92);"
            "color: white;"
            "font-size: 12px;"
            "font-weight: 600;"
            "padding: 8px 16px;"
            "border-radius: 6px;"
        )
        badge_layout.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignHCenter)
        stack.addWidget(badge_host)

        self._timer = QTimer(self)
        self._timer.setInterval(max(50, int(1000 / MODERATION_SHIELD_FPS)))
        self._timer.timeout.connect(self._refresh_frame)

    def set_frame_provider(self, provider: FrameProvider | None) -> None:
        self._frame_provider = provider

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        if active:
            self.show()
            self.raise_()
            self._refresh_frame()
            self._timer.start()
        else:
            self._timer.stop()
            self._image.clear()
            self.hide()

    def _refresh_frame(self) -> None:
        if not self._active or not self._frame_provider:
            return
        try:
            raw = self._frame_provider()
        except Exception:  # noqa: BLE001
            return
        if not raw:
            return
        pix = _blur_png_bytes(raw)
        if not pix.isNull():
            self._image.setPixmap(pix)

    def show_blackout(self, visible: bool) -> None:
        """Backwards-compatible alias."""
        self.set_active(visible)


def _blur_png_bytes(data: bytes) -> QPixmap:
    """Decode snapshot bytes, apply strong blur + frosted tint."""
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return QPixmap()

    h, w = frame.shape[:2]
    target_w = MODERATION_SHIELD_CAPTURE_WIDTH
    target_h = MODERATION_SHIELD_CAPTURE_HEIGHT
    if w > target_w or h > target_h:
        scale = min(target_w / w, target_h / h)
        frame = cv2.resize(
            frame,
            (max(1, int(w * scale)), max(1, int(h * scale))),
            interpolation=cv2.INTER_AREA,
        )

    blurred = cv2.GaussianBlur(
        frame, (0, 0), sigmaX=MODERATION_SHIELD_BLUR_SIGMA, sigmaY=MODERATION_SHIELD_BLUR_SIGMA
    )
    bh, bw = blurred.shape[:2]
    factor = MODERATION_SHIELD_DOWNSAMPLE_FACTOR
    tiny = cv2.resize(
        blurred,
        (max(1, bw // factor), max(1, bh // factor)),
        interpolation=cv2.INTER_LINEAR,
    )
    blurred = cv2.resize(tiny, (bw, bh), interpolation=cv2.INTER_LINEAR)

    frost = float(MODERATION_SHIELD_FROST_ALPHA)
    if frost > 0:
        tint = np.array([235, 228, 255], dtype=np.float32)
        blurred = blurred.astype(np.float32)
        blurred = blurred * (1.0 - frost) + tint * frost
        blurred = np.clip(blurred, 0, 255).astype(np.uint8)

    rgb = cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)
    qimg = QImage(rgb.data, bw, bh, 3 * bw, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)
