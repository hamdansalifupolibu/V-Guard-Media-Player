"""Coordinates VLC player state with the UI (moderation hooks added later)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from app.playback.vlc_player import VLCPlayer
from app.utils.time_utils import format_timestamp


class PlaybackController(QObject):
    """Bridge between VLCPlayer and UI controls."""

    position_changed = Signal(float)  # normalized 0–1
    time_changed = Signal(str, str)  # current, total formatted
    tick_seconds = Signal(float)  # current playback time (for moderation)
    state_changed = Signal(bool)  # is_playing
    media_loaded = Signal(str)  # file path
    error_occurred = Signal(str)

    def __init__(self, vlc_player: VLCPlayer, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = vlc_player
        self._duration_ms = 0
        self._seeking = False

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)

    def open_file(self, path: str | Path) -> bool:
        if not self._player.load(path):
            self.error_occurred.emit(f"Could not load file: {path}")
            return False
        self._duration_ms = 0
        self.media_loaded.emit(str(path))
        return True

    def play(self) -> None:
        if not self._player.current_path:
            self.error_occurred.emit("Open a video file first.")
            return
        self._player.play()
        self._timer.start()
        self.state_changed.emit(True)

    def pause(self) -> None:
        self._player.pause()
        self._timer.stop()
        self.state_changed.emit(False)

    def stop(self) -> None:
        self._player.stop()
        self._timer.stop()
        self._duration_ms = 0
        self.position_changed.emit(0.0)
        self.time_changed.emit(
            format_timestamp(0, hms=True),
            format_timestamp(0, hms=True),
        )
        self.state_changed.emit(False)

    def toggle_play_pause(self) -> None:
        if self._player.is_playing():
            self.pause()
        else:
            self.play()

    def set_volume(self, level: int) -> None:
        self._player.set_volume(level)

    def set_mute(self, muted: bool) -> None:
        self._player.set_mute(muted)

    def is_muted(self) -> bool:
        return self._player.is_muted()

    def is_playing(self) -> bool:
        return self._player.is_playing()

    def begin_seek(self) -> None:
        self._seeking = True

    def end_seek(self, fraction: float) -> None:
        self._seeking = False
        self._player.set_position(fraction)

    def _on_tick(self) -> None:
        if self._seeking:
            return
        length_ms = self._player.get_length_ms()
        if length_ms > 0:
            self._duration_ms = length_ms
        time_ms = self._player.get_time_ms()
        self.tick_seconds.emit(time_ms / 1000.0)
        if self._duration_ms > 0:
            fraction = time_ms / self._duration_ms
            self.position_changed.emit(fraction)
            self.time_changed.emit(
                format_timestamp(time_ms / 1000.0, hms=True),
                format_timestamp(self._duration_ms / 1000.0, hms=True),
            )
        else:
            self.time_changed.emit(
                format_timestamp(time_ms / 1000.0, hms=True),
                "--:--",
            )

    def shutdown(self) -> None:
        self._timer.stop()
        self._player.release()
