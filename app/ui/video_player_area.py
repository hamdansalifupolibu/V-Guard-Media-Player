"""Video surface + moderation blur shield (controls live below video in normal mode)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QSizePolicy, QStackedLayout, QWidget

from app.ui.moderation_overlay import FrameProvider, ModerationShieldOverlay
from app.ui.styles import COLORS


class VideoPlayerArea(QFrame):
    """Native VLC render target with optional blurred moderation shield."""

    double_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("videoPlayerArea")
        self.setStyleSheet(
            f"QFrame#videoPlayerArea {{ background: {COLORS['video_bg']}; "
            "border-radius: 10px; }"
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.video_surface = QWidget()
        self.video_surface.setMinimumSize(320, 180)
        self.video_surface.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.video_surface.setStyleSheet(
            "background-color: #111827; border-radius: 8px;"
        )
        self.video_surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_surface.setAttribute(
            Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True
        )
        stack.addWidget(self.video_surface)

        self.moderation_shield = ModerationShieldOverlay()
        stack.addWidget(self.moderation_shield)

        # Legacy attribute name used in main_window
        self.blackout_overlay = self.moderation_shield

    def set_frame_provider(self, provider: FrameProvider | None) -> None:
        self.moderation_shield.set_frame_provider(provider)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def set_fullscreen_fill(self, enabled: bool) -> None:
        """Edge-to-edge video surface when the main window is fullscreen."""
        radius = "0" if enabled else "10px"
        inner_radius = "0" if enabled else "8px"
        self.setStyleSheet(
            f"QFrame#videoPlayerArea {{ background: {COLORS['video_bg']}; "
            f"border-radius: {radius}; }}"
        )
        self.video_surface.setStyleSheet(
            f"background-color: #111827; border-radius: {inner_radius};"
        )
        self.moderation_shield.setStyleSheet(
            f"background-color: #1a1528; border-radius: {inner_radius};"
        )

    def show_blackout(self, visible: bool) -> None:
        """Show or hide the blurred moderation shield."""
        self.moderation_shield.set_active(visible)
