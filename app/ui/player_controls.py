"""Playback control bar matching V-Guard mockup."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

ICON_PLAY = "▶"
ICON_PAUSE = "⏸"
ICON_VOLUME_ON = "🔊"
ICON_VOLUME_OFF = "🔇"
ICON_FULLSCREEN_ENTER = "⛶"


class PlayerControls(QWidget):
    """Timeline, transport buttons, volume, mute, and fullscreen."""

    ICON_FULLSCREEN_EXIT = "🗗"

    open_clicked = Signal()
    play_pause_clicked = Signal()
    stop_clicked = Signal()
    seek_started = Signal()
    seek_released = Signal(float)
    volume_changed = Signal(int)
    mute_toggled = Signal(bool)
    fullscreen_clicked = Signal()
    settings_clicked = Signal()

    def __init__(
        self, parent: QWidget | None = None, *, overlay: bool = False
    ) -> None:
        super().__init__(parent)
        self._overlay = overlay
        self._building_ui = False
        self._is_muted = False
        self._is_playing = False
        self._is_fullscreen = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        top = 4 if self._overlay else 10
        layout.setContentsMargins(0, top, 0, 0)
        layout.setSpacing(6 if self._overlay else 8)

        timeline_row = QHBoxLayout()
        self.time_start = QLabel("00:00:00")
        self.time_start.setMinimumWidth(72)
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.time_end = QLabel("00:00:00")
        self.time_end.setMinimumWidth(72)
        self.time_end.setAlignment(Qt.AlignmentFlag.AlignRight)
        timeline_row.addWidget(self.time_start)
        timeline_row.addWidget(self.seek_slider, stretch=1)
        timeline_row.addWidget(self.time_end)
        layout.addLayout(timeline_row)

        transport = QHBoxLayout()

        self.open_btn = QPushButton("📂")
        self.open_btn.setToolTip("Open video file")
        self.open_btn.clicked.connect(self.open_clicked.emit)
        transport.addWidget(self.open_btn)

        self.mute_btn = QPushButton(ICON_VOLUME_ON)
        self.mute_btn.setCheckable(True)
        self.mute_btn.setToolTip("Mute / unmute (M)")
        self.mute_btn.clicked.connect(self._on_mute_click)
        transport.addWidget(self.mute_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        transport.addWidget(self.volume_slider)

        transport.addStretch()

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setToolTip("Back 10 seconds")
        transport.addWidget(self.prev_btn)

        self.play_pause_btn = QPushButton(ICON_PLAY)
        self.play_pause_btn.setObjectName("playBtn")
        self.play_pause_btn.setToolTip("Play (Space)")
        self.play_pause_btn.clicked.connect(self.play_pause_clicked.emit)
        transport.addWidget(self.play_pause_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        transport.addWidget(self.stop_btn)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setToolTip("Forward 10 seconds")
        transport.addWidget(self.next_btn)

        transport.addStretch()

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        transport.addWidget(self.settings_btn)

        self.fullscreen_btn = QPushButton(ICON_FULLSCREEN_ENTER)
        self.fullscreen_btn.setToolTip("Fullscreen video (F)")
        self.fullscreen_btn.clicked.connect(self.fullscreen_clicked.emit)
        transport.addWidget(self.fullscreen_btn)

        layout.addLayout(transport)

    def set_playing(self, playing: bool) -> None:
        """Update play/pause button icon to match playback state."""
        self._is_playing = playing
        self.play_pause_btn.setText(ICON_PAUSE if playing else ICON_PLAY)
        self.play_pause_btn.setToolTip(
            "Pause (Space)" if playing else "Play (Space)"
        )

    def _on_mute_click(self) -> None:
        self._is_muted = not self._is_muted
        self.mute_btn.setChecked(self._is_muted)
        self._update_mute_icon()
        self.mute_toggled.emit(self._is_muted)

    def _on_seek_pressed(self) -> None:
        self.seek_started.emit()

    def _on_seek_released(self) -> None:
        self.seek_released.emit(self.seek_slider.value() / 1000.0)

    def _on_volume_changed(self, value: int) -> None:
        if not self._building_ui:
            if value > 0 and self._is_muted:
                self.set_muted(False, emit_signal=True)
            self.volume_changed.emit(value)

    def _update_mute_icon(self) -> None:
        self.mute_btn.setText(ICON_VOLUME_OFF if self._is_muted else ICON_VOLUME_ON)

    def set_muted(self, muted: bool, *, emit_signal: bool = False) -> None:
        self._is_muted = muted
        self.mute_btn.blockSignals(True)
        self.mute_btn.setChecked(muted)
        self._update_mute_icon()
        self.mute_btn.blockSignals(False)
        if emit_signal:
            self.mute_toggled.emit(muted)

    def is_muted(self) -> bool:
        return self._is_muted

    def set_fullscreen_active(self, active: bool) -> None:
        self._is_fullscreen = active
        self.fullscreen_btn.setText(
            self.ICON_FULLSCREEN_EXIT if active else ICON_FULLSCREEN_ENTER
        )
        self.fullscreen_btn.setToolTip(
            "Exit fullscreen (Esc)" if active else "Fullscreen video (F)"
        )
        if active:
            self.fullscreen_btn.setStyleSheet(
                "background-color: #7C3AED; color: white; border-radius: 6px;"
            )
        else:
            self.fullscreen_btn.setStyleSheet("")

    def set_position_fraction(self, fraction: float) -> None:
        self._building_ui = True
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(int(max(0.0, min(1.0, fraction)) * 1000))
        self.seek_slider.blockSignals(False)
        self._building_ui = False

    def set_time_label(self, current: str, total: str) -> None:
        self.time_start.setText(current)
        self.time_end.setText(total if total != "--:--" else "00:00:00")

    def set_volume(self, level: int) -> None:
        self._building_ui = True
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(level)
        self.volume_slider.blockSignals(False)
        self._building_ui = False
