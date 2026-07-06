"""libVLC wrapper for embedding video in a Qt widget."""

from __future__ import annotations

import sys
from pathlib import Path

import vlc
from PySide6.QtWidgets import QApplication, QWidget

from app.config import VLC_ARGS


class VLCPlayer:
    """Thin wrapper around python-vlc MediaPlayer."""

    def __init__(self, video_widget: QWidget) -> None:
        self._widget = video_widget
        self._instance = vlc.Instance(*VLC_ARGS)
        self._player = self._instance.media_player_new()
        self._current_path: str | None = None
        self._bind_output()

    def _bind_output(self) -> None:
        """Attach VLC video output to the Qt widget native handle."""
        self._widget.update()
        QApplication.processEvents()
        win_id = int(self._widget.winId())
        if sys.platform.startswith("win"):
            self._player.set_hwnd(win_id)
        elif sys.platform == "darwin":
            self._player.set_nsobject(win_id)
        else:
            self._player.set_xwindow(win_id)

    def rebind_output(self) -> None:
        """
        Re-attach video output after resize without restarting playback.
        Avoids the backward jump caused by play()+seek on fullscreen toggle.
        """
        self._bind_output()
        try:
            self._player.video_set_scale(0)
        except (AttributeError, TypeError):
            pass

    def load(self, file_path: str | Path) -> bool:
        """Load a local media file. Returns True on success."""
        path = Path(file_path)
        if not path.is_file():
            return False
        media = self._instance.media_new(str(path.resolve()))
        self._player.set_media(media)
        self._current_path = str(path.resolve())
        return True

    @property
    def current_path(self) -> str | None:
        return self._current_path

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def get_position(self) -> float:
        """Normalized position 0.0–1.0."""
        return float(self._player.get_position() or 0.0)

    def set_position(self, fraction: float) -> None:
        fraction = max(0.0, min(1.0, fraction))
        self._player.set_position(fraction)

    def get_time_ms(self) -> int:
        return int(self._player.get_time() or 0)

    def set_time_ms(self, ms: int) -> None:
        self._player.set_time(max(0, ms))

    def get_length_ms(self) -> int:
        return int(self._player.get_length() or 0)

    def get_volume(self) -> int:
        return int(self._player.audio_get_volume() or 0)

    def set_volume(self, level: int) -> None:
        self._player.audio_set_volume(max(0, min(100, level)))

    def set_mute(self, muted: bool) -> None:
        self._player.audio_set_mute(muted)

    def is_muted(self) -> bool:
        return bool(self._player.audio_get_mute())

    def capture_snapshot_png(self) -> bytes | None:
        """
        Grab the current video frame as PNG bytes for the moderation blur overlay.

        Returns None if playback is unavailable or snapshot fails.
        """
        if not self._current_path:
            return None
        import os
        import tempfile

        from app.config import (
            MODERATION_SHIELD_SNAPSHOT_HEIGHT,
            MODERATION_SHIELD_SNAPSHOT_WIDTH,
        )

        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            rc = self._player.video_take_snapshot(
                0,
                path,
                MODERATION_SHIELD_SNAPSHOT_WIDTH,
                MODERATION_SHIELD_SNAPSHOT_HEIGHT,
            )
            if rc != 0:
                return None
            return Path(path).read_bytes()
        except (OSError, AttributeError):
            return None
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def release(self) -> None:
        """Stop playback and release resources."""
        self.stop()
        self._player.release()
        self._instance.release()
