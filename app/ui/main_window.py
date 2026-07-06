"""Main application window — layout aligned with V-Guard UI mockup."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.analysis.scan_worker import ScanWorker
from app.analysis.visual_strictness import resolve_visual_threshold
from app.config import (
    APP_NAME,
    BLOCKED_WORDS_PATH,
    DEFAULT_MODERATION_MODE,
    SCAN_INITIAL_UNLOCK_SEC,
    SCAN_STATUS_LABELS,
    SETTING_AUTO_SCAN_ON_LOAD,
    SETTING_MODERATION_MODE,
    SETTING_REQUIRE_SCAN_BEFORE_PLAY,
    SETTING_VISUAL_STRICTNESS,
    SETTING_VISUAL_THRESHOLD,
    THESIS_FIGURES_DIR,
    VIDEO_EXTENSIONS,
)
from app.database.db import VGuardDatabase
from app.moderation.moderation_controller import ModerationController
from app.playback.playback_controller import PlaybackController
from app.playback.vlc_player import VLCPlayer
from app.reporting.model_evaluation import ModelEvaluationRunner
from app.reporting.thesis_figures import ThesisFigureGenerator
from app.ui.about_panel import AboutPanel
from app.ui.branding import app_icon
from app.ui.downloads_panel import DownloadsPanel
from app.ui.library_panel import LibraryPanel
from app.ui.moderation_cards import ModerationCards
from app.ui.right_panel import RightPanel
from app.ui.fullscreen_controls_overlay import FullscreenControlsDock
from app.ui.player_controls import PlayerControls
from app.ui.video_player_area import VideoPlayerArea
from app.ui.scan_results_dialog import ScanResultsDialog
from app.ui.settings_panel import SettingsPanel
from app.ui.sidebar import Sidebar
from app.utils.file_utils import file_display_name

NAV_PAGES = {
    "player": 0,
    "library": 1,
    "downloads": 2,
    "settings": 3,
    "about": 4,
}


class MainWindow(QMainWindow):
    """Three-column UI with navigation, player, settings, and library."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        icon = app_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.resize(1180, 720)

        self._db = VGuardDatabase()
        self._current_video_id: int | None = None
        self._current_path: str | None = None
        self._duration_saved = False
        self._scan_worker: ScanWorker | None = None
        self._progress: QProgressDialog | None = None
        self._vlc_bound = False
        self._moderation = ModerationController(self._db)
        self._moderation_auto_muted = False
        self._video_fullscreen = False
        self._volume_before_mute = 80
        self._playback_unlocked = True
        self._auto_play_after_scan = False
        self._scanned_until_sec = 0.0
        self._ahead_of_scan_shown = False
        self._last_chunk_ui_refresh = 0.0

        self._window_margin = 12
        central = QWidget()
        self.setCentralWidget(central)
        self._root_layout = QHBoxLayout(central)
        self._root_layout.setContentsMargins(
            self._window_margin, self._window_margin, self._window_margin, 8
        )
        self._root_layout.setSpacing(12)
        root = self._root_layout

        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._on_nav)
        root.addWidget(self.sidebar)

        self._stack = QStackedWidget()

        # --- Player page ---
        self._player_page = QWidget()
        player_layout = QHBoxLayout(self._player_page)
        self._player_page_margin = 0
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(12)

        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(10)

        self._player_view = QWidget()
        player_view_layout = QVBoxLayout(self._player_view)
        player_view_layout.setContentsMargins(0, 0, 0, 0)
        player_view_layout.setSpacing(0)

        self.video_area = VideoPlayerArea()
        player_view_layout.addWidget(self.video_area, stretch=1)

        center.addWidget(self._player_view, stretch=1)

        self.controls_host = QWidget()
        controls_layout = QVBoxLayout(self.controls_host)
        controls_layout.setContentsMargins(0, 8, 0, 0)
        controls_layout.setSpacing(0)
        self.controls = PlayerControls(overlay=False)
        controls_layout.addWidget(self.controls)
        center.addWidget(self.controls_host)

        self._fs_dock = FullscreenControlsDock(self)
        self._fs_dock.dock_controls(
            self.controls, self.controls_host, controls_layout
        )
        self._fs_dock.attach_video_area(self.video_area)
        self._fs_dock.attach_pointer_targets(
            self._player_view,
            self._player_page,
            central,
            self.video_area,
            self.video_area.video_surface,
        )
        self._fs_dock.set_key_handlers(self._fullscreen_key_handlers())

        self._fs_layout_timer = QTimer(self)
        self._fs_layout_timer.setSingleShot(True)
        self._fs_layout_timer.timeout.connect(self._finish_fullscreen_layout)

        self.vlc_player = VLCPlayer(self.video_area.video_surface)
        self.video_area.set_frame_provider(self.vlc_player.capture_snapshot_png)
        self.playback = PlaybackController(self.vlc_player, self)

        self.moderation_cards = ModerationCards()
        self.moderation_cards.mode_changed.connect(self._on_moderation_changed)
        center.addWidget(self.moderation_cards)

        player_layout.addLayout(center, stretch=1)

        self.right_panel = RightPanel()
        self.right_panel.scan_clicked.connect(self._on_scan_clicked)
        self.right_panel.view_results_clicked.connect(self._on_view_results)
        self.right_panel.generate_figures_clicked.connect(self._on_generate_figures)
        player_layout.addWidget(self.right_panel)

        self._stack.addWidget(self._player_page)

        self._library_panel = LibraryPanel(self._db)
        self._library_panel.open_video.connect(self._open_video_path)
        self._stack.addWidget(self._library_panel)

        self._downloads_panel = DownloadsPanel(self._db)
        self._downloads_panel.open_video.connect(self._open_video_path)
        self._stack.addWidget(self._downloads_panel)

        self._settings_panel = SettingsPanel(self._db)
        self._settings_panel.settings_saved.connect(self._on_settings_saved)
        self._stack.addWidget(self._settings_panel)

        self._stack.addWidget(AboutPanel())

        root.addWidget(self._stack, stretch=1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(f"{APP_NAME} | Safe Media. Smart Protection.")

        self._wire_signals()
        self._load_settings()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._vlc_bound:
            self.vlc_player._bind_output()
            self._vlc_bound = True

    def _fullscreen_key_handlers(self) -> dict[int, object]:
        return {
            Qt.Key.Key_Escape: lambda: self._set_video_fullscreen(False),
            Qt.Key.Key_Space: self._guarded_toggle_play_pause,
            Qt.Key.Key_Left: lambda: self._seek_relative(-10),
            Qt.Key.Key_J: lambda: self._seek_relative(-10),
            Qt.Key.Key_Right: lambda: self._seek_relative(10),
            Qt.Key.Key_L: lambda: self._seek_relative(10),
            Qt.Key.Key_F: self._toggle_video_fullscreen,
            Qt.Key.Key_M: lambda: self._on_mute_toggled(
                not self.controls.is_muted()
            ),
        }

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        if self._video_fullscreen:
            handlers = self._fullscreen_key_handlers()
            if key in handlers:
                handlers[key]()
                return
        if self._stack.currentIndex() == NAV_PAGES["player"]:
            if key == Qt.Key.Key_Space:
                self._guarded_toggle_play_pause()
                return
            if key in (Qt.Key.Key_Left, Qt.Key.Key_J):
                self._seek_relative(-10)
                return
            if key in (Qt.Key.Key_Right, Qt.Key.Key_L):
                self._seek_relative(10)
                return
            if key == Qt.Key.Key_F:
                self._toggle_video_fullscreen()
                return
            if key == Qt.Key.Key_M:
                self._on_mute_toggled(not self.controls.is_muted())
                return
        super().keyPressEvent(event)

    def _on_prev_clicked(self) -> None:
        self._seek_relative(-10)

    def _on_next_clicked(self) -> None:
        self._seek_relative(10)

    def _finish_fullscreen_layout(self) -> None:
        if self._video_fullscreen:
            self._fs_dock.position_at_bottom(self)
            if self.vlc_player.current_path:
                self.vlc_player.rebind_output()
        else:
            if self.vlc_player.current_path:
                self.vlc_player.rebind_output()

    def _schedule_fullscreen_layout(self) -> None:
        self._fs_layout_timer.start(80)

    def _wire_signals(self) -> None:
        self.controls.open_clicked.connect(self._on_open)
        self.controls.play_pause_clicked.connect(self._guarded_toggle_play_pause)
        self.controls.stop_clicked.connect(self._on_stop)
        self.controls.prev_btn.clicked.connect(self._on_prev_clicked)
        self.controls.next_btn.clicked.connect(self._on_next_clicked)
        self.controls.seek_started.connect(self.playback.begin_seek)
        self.controls.seek_released.connect(self.playback.end_seek)
        self.controls.volume_changed.connect(self._on_volume_changed)
        self.controls.mute_toggled.connect(self._on_mute_toggled)
        self.controls.fullscreen_clicked.connect(self._toggle_video_fullscreen)
        self.controls.settings_clicked.connect(
            lambda: self._go_to_page("settings")
        )
        self.video_area.double_clicked.connect(self._toggle_video_fullscreen)

        self.playback.position_changed.connect(self.controls.set_position_fraction)
        self.playback.time_changed.connect(self._on_time_changed)
        self.playback.media_loaded.connect(self._on_media_loaded)
        self.playback.error_occurred.connect(self._show_error)
        self.playback.state_changed.connect(self._on_play_state)
        self.playback.tick_seconds.connect(self._on_playback_tick)

        vol = int(self._db.get_setting("volume_level", "80") or 80)
        self._volume_before_mute = vol
        self.controls.set_volume(vol)
        self.playback.set_volume(vol)

    def _load_settings(self) -> None:
        mode = self._db.get_setting(SETTING_MODERATION_MODE, DEFAULT_MODERATION_MODE)
        self.moderation_cards.set_mode_key(mode or DEFAULT_MODERATION_MODE)
        self._reload_moderation(mode or DEFAULT_MODERATION_MODE)

    def _on_settings_saved(self) -> None:
        mode = self._db.get_setting(SETTING_MODERATION_MODE, DEFAULT_MODERATION_MODE)
        self.moderation_cards.set_mode_key(mode or DEFAULT_MODERATION_MODE)
        self._reload_moderation(mode or DEFAULT_MODERATION_MODE)
        self.status.showMessage("Settings saved.")
        QMessageBox.information(self, APP_NAME, "Settings saved successfully.")

    def _go_to_page(self, key: str) -> None:
        if key in NAV_PAGES:
            self._stack.setCurrentIndex(NAV_PAGES[key])
            for k, btn in self.sidebar._nav_buttons.items():
                btn.setChecked(k == key)
            if key == "library":
                self._library_panel.refresh()
            if key == "downloads":
                self._downloads_panel.refresh()

    def _on_nav(self, key: str) -> None:
        if self._video_fullscreen:
            self._set_video_fullscreen(False)
        self._go_to_page(key)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open video",
            "",
            f"Video files ({VIDEO_EXTENSIONS});;All files (*.*)",
        )
        if path:
            self._open_video_path(path)

    def _open_video_path(self, path: str) -> None:
        """Load video and run scan gate; playback starts only after scan rules pass."""
        self._go_to_page("player")
        self._auto_play_after_scan = False
        if self.playback.open_file(path):
            self.playback.stop()
            self.controls.set_playing(False)

    def _on_stop(self) -> None:
        self.playback.stop()
        self.controls.set_playing(False)
        self._restore_normal_playback()

    def _on_volume_changed(self, level: int) -> None:
        self._db.set_setting("volume_level", str(level))
        if not self.controls.is_muted():
            self._volume_before_mute = level
            self.playback.set_volume(level)

    def _on_mute_toggled(self, muted: bool) -> None:
        if muted:
            if not self.controls.is_muted():
                self._volume_before_mute = self.controls.volume_slider.value()
            self.playback.set_mute(True)
        else:
            self.playback.set_mute(False)
            self.playback.set_volume(self._volume_before_mute)
            self.controls.set_volume(self._volume_before_mute)
        self.controls.set_muted(muted)

    def _toggle_video_fullscreen(self) -> None:
        self._set_video_fullscreen(not self._video_fullscreen)

    def _set_video_fullscreen(self, enabled: bool) -> None:
        self._video_fullscreen = enabled
        self.controls.set_fullscreen_active(enabled)
        self._stack.setCurrentIndex(NAV_PAGES["player"])

        if enabled:
            self.sidebar.hide()
            self.right_panel.hide()
            self.moderation_cards.hide()
            self.statusBar().hide()
            self.controls_host.hide()
            self._apply_fullscreen_chrome(True)
            self.showFullScreen()
            self._fs_dock.enter_fullscreen(self)
        else:
            self._fs_dock.exit_fullscreen()
            self.showNormal()
            self._apply_fullscreen_chrome(False)
            self.sidebar.show()
            self.right_panel.show()
            self.moderation_cards.show()
            self.statusBar().show()
            self.controls_host.show()

        self._schedule_fullscreen_layout()

    def _apply_fullscreen_chrome(self, enabled: bool) -> None:
        m = 0 if enabled else self._window_margin
        self._root_layout.setContentsMargins(m, m, m, 0 if enabled else 8)
        self._root_layout.setSpacing(0 if enabled else 12)
        self.video_area.set_fullscreen_fill(enabled)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._video_fullscreen and self._fs_dock.isVisible():
            self._fs_dock.position_at_bottom(self)

    def _on_media_loaded(self, path: str) -> None:
        self._current_path = path
        self._duration_saved = False
        video_id = self._db.upsert_video(path)
        self._current_video_id = video_id
        record = self._db.get_video_by_id(video_id)

        name = file_display_name(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        duration_str = "—"
        if record and record.duration:
            from app.utils.time_utils import format_timestamp

            duration_str = format_timestamp(record.duration, hms=True)

        self.right_panel.set_now_playing(
            name,
            path=path,
            duration=duration_str,
            resolution="—",
            size=f"{size_mb:.1f} MB",
        )
        self.right_panel.scan_btn.setEnabled(True)
        if record:
            self._refresh_scan_ui(record.scan_status)
            self._refresh_detection_counts(video_id)
        mode = self._db.get_setting(SETTING_MODERATION_MODE, DEFAULT_MODERATION_MODE)
        self._reload_moderation(mode or DEFAULT_MODERATION_MODE)
        self._scanned_until_sec = float(record.scan_progress_sec) if record else 0.0
        self._ahead_of_scan_shown = False
        self._apply_scan_gate()

    def _setting_bool(self, key: str, default: bool) -> bool:
        raw = self._db.get_setting(key)
        if raw is None:
            return default
        return raw.strip().lower() in ("true", "1", "yes", "on")

    def _apply_scan_gate(self) -> None:
        """Prompt or auto-scan before playback when required."""
        if not self._current_video_id or not self._current_path:
            return

        if self._scan_worker and self._scan_worker.isRunning():
            self._playback_unlocked = False
            return

        require_scan = self._setting_bool(SETTING_REQUIRE_SCAN_BEFORE_PLAY, True)
        auto_scan = self._setting_bool(SETTING_AUTO_SCAN_ON_LOAD, False)

        if not require_scan:
            self._playback_unlocked = True
            return

        record = self._db.get_video_by_id(self._current_video_id)
        status = (record.scan_status if record else "not_scanned") or "not_scanned"
        progress = float(record.scan_progress_sec) if record else 0.0
        duration = float(record.duration) if record and record.duration else 0.0
        needs_scan = status != "complete" or auto_scan

        if not needs_scan:
            self._playback_unlocked = True
            self._scanned_until_sec = duration or progress
            self.status.showMessage(
                "Pre-scan complete — press Play to watch with moderation."
            )
            return

        if self._can_unlock_playback(progress, duration) and status == "scanning":
            self._playback_unlocked = True
            self._scanned_until_sec = progress
            self.status.showMessage(
                f"Partial scan ready ({progress:.0f}s) — press Play; "
                "scan continues in background."
            )
            self._start_scan(
                auto_play_when_done=False,
                resume=True,
            )
            return

        self._playback_unlocked = False

        if auto_scan:
            self.status.showMessage(
                "Progressive scan starting — playback unlocks after first chunk…"
            )
            self._start_scan(auto_play_when_done=True, resume=False)
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(APP_NAME)
        box.setText("Scan this video before watching?")
        box.setInformativeText(
            "V-Guard scans the video in chunks (like lazy loading). The first "
            f"~{int(SCAN_INITIAL_UNLOCK_SEC)} seconds are analyzed quickly so you can "
            "start watching; the rest continues in the background.\n\n"
            "Enable “Automatically scan every video when opened” in Settings "
            "to skip this message."
        )
        scan_btn = box.addButton("Scan now", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Not now", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == scan_btn:
            self._start_scan(auto_play_when_done=True)
        else:
            self.status.showMessage(
                "Playback blocked — run Pre-scan from the right panel when ready."
            )

    def _can_unlock_playback(self, scanned_sec: float, duration_sec: float) -> bool:
        if scanned_sec <= 0:
            return False
        if duration_sec > 0:
            unlock_at = min(SCAN_INITIAL_UNLOCK_SEC, duration_sec)
        else:
            unlock_at = SCAN_INITIAL_UNLOCK_SEC
        return scanned_sec >= unlock_at - 0.25

    def _guarded_toggle_play_pause(self) -> None:
        if not self._playback_unlocked:
            if self._scan_worker and self._scan_worker.isRunning():
                record = self._db.get_video_by_id(self._current_video_id or 0)
                progress = float(record.scan_progress_sec) if record else 0.0
                duration = float(record.duration) if record and record.duration else 0.0
                if self._can_unlock_playback(progress, duration):
                    self._playback_unlocked = True
                else:
                    self.status.showMessage(
                        "Please wait — first scan chunk is still processing…"
                    )
                    return
            self._apply_scan_gate()
            if not self._playback_unlocked:
                return
        self.playback.toggle_play_pause()

    def _on_time_changed(self, current: str, total: str) -> None:
        self.controls.set_time_label(current, total)
        if (
            self._current_video_id
            and not self._duration_saved
            and total != "--:--"
        ):
            length_ms = self.vlc_player.get_length_ms()
            if length_ms > 0:
                from app.utils.time_utils import format_timestamp

                self._db.update_duration(
                    self._current_video_id,
                    length_ms / 1000.0,
                )
                self._duration_saved = True
                if self._current_path:
                    self.right_panel.meta_duration.setText(
                        f"Duration: {format_timestamp(length_ms / 1000.0, hms=True)}"
                    )

    def _on_play_state(self, playing: bool) -> None:
        self.controls.set_playing(playing)
        self._fs_dock.set_playing(playing)
        self.status.showMessage(
            "Playing…" if playing else "Paused / stopped"
        )

    def _on_moderation_changed(self, key: str) -> None:
        self._db.set_setting(SETTING_MODERATION_MODE, key)
        self._reload_moderation(key)

    def _reload_moderation(self, mode: str) -> None:
        if self._current_video_id:
            self._moderation.load(self._current_video_id, mode)
        else:
            self._moderation.clear()
        self._restore_normal_playback()

    def _on_playback_tick(self, time_sec: float) -> None:
        if (
            self._scan_worker
            and self._scan_worker.isRunning()
            and self._scanned_until_sec > 0
            and time_sec > self._scanned_until_sec + 1.0
        ):
            if not self._ahead_of_scan_shown:
                self._ahead_of_scan_shown = True
                self.status.showMessage(
                    f"Playback is ahead of the scan ({self._scanned_until_sec:.0f}s "
                    "analyzed) — moderation only applies to scanned portions.",
                )
        elif time_sec <= self._scanned_until_sec:
            self._ahead_of_scan_shown = False

        if not self._moderation.is_active or not self.playback.is_playing():
            if self._moderation_auto_muted or self.video_area.blackout_overlay.isVisible():
                self._restore_normal_playback()
            return

        action = self._moderation.evaluate(time_sec)

        if action.skip_to_sec is not None:
            self.vlc_player.set_time_ms(int(action.skip_to_sec * 1000))
            return

        self.video_area.show_blackout(action.hide_video)

        if action.mute_audio:
            if not self.playback.is_muted():
                self.playback.set_mute(True)
                self.controls.set_muted(True)
                self._moderation_auto_muted = True
        elif self._moderation_auto_muted:
            self.playback.set_mute(self.controls.is_muted())
            if not self.controls.is_muted():
                self.playback.set_volume(self._volume_before_mute)
            self._moderation_auto_muted = False

    def _restore_normal_playback(self) -> None:
        self.video_area.show_blackout(False)
        if self._moderation_auto_muted:
            self.playback.set_mute(self.controls.is_muted())
            if not self.controls.is_muted():
                self.playback.set_volume(self._volume_before_mute)
            self._moderation_auto_muted = False

    def _seek_relative(self, seconds: float) -> None:
        length = self.vlc_player.get_length_ms()
        if length > 0:
            target = self.vlc_player.get_time_ms() + int(seconds * 1000)
            target = max(0, min(length, target))
            self.vlc_player.set_time_ms(target)
            if self._video_fullscreen:
                self._fs_dock.notify_activity()

    def _refresh_scan_ui(self, status: str) -> None:
        label = SCAN_STATUS_LABELS.get(status, status)
        self.right_panel.set_scan_status(label, is_success=status != "failed")
        self.right_panel.results_btn.setEnabled(status == "complete")

    def _refresh_detection_counts(self, video_id: int) -> None:
        visual_all = self._db.get_detections(video_id, detection_type="visual")
        audio_all = self._db.get_detections(video_id, detection_type="audio")
        visual_on = sum(1 for d in visual_all if d.enabled)
        audio_on = sum(1 for d in audio_all if d.enabled)
        self.right_panel.set_detection_counts(visual_on, audio_on)

    def _on_scan_clicked(self) -> None:
        if not self._current_video_id or not self._current_path:
            self._show_error("Open a video before scanning.")
            return
        self._start_scan(auto_play_when_done=False, user_initiated=True)

    def _start_scan(
        self,
        *,
        auto_play_when_done: bool = False,
        user_initiated: bool = False,
        resume: bool = False,
    ) -> None:
        if not self._current_video_id or not self._current_path:
            self._show_error("Open a video before scanning.")
            return
        if self._scan_worker and self._scan_worker.isRunning():
            return

        self._auto_play_after_scan = auto_play_when_done
        if auto_play_when_done or self._setting_bool(
            SETTING_REQUIRE_SCAN_BEFORE_PLAY, True
        ):
            self._playback_unlocked = False

        self.right_panel.scan_btn.setEnabled(False)
        self._progress = QProgressDialog("Starting scan…", "Cancel", 0, 100, self)
        self._progress.setWindowTitle("Pre-scan — please wait")
        self._progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress.setMinimumDuration(0)
        self._progress.canceled.connect(self._cancel_scan)
        if not user_initiated and auto_play_when_done:
            self._progress.setCancelButtonText("Cancel scan")

        self._scan_worker = ScanWorker(
            self._db,
            self._current_video_id,
            self._current_path,
            self,
            resume=resume,
        )
        self._scan_worker.scanner.progress.connect(self._on_scan_progress)
        self._scan_worker.scanner.chunk_ready.connect(self._on_scan_chunk_ready)
        self._scan_worker.scanner.finished.connect(self._on_scan_finished)
        self._scan_worker.scanner.failed.connect(self._on_scan_failed)
        self._scan_worker.finished.connect(self._on_scan_thread_done)
        self._scan_worker.start()
        self._refresh_scan_ui("scanning")
        if not user_initiated:
            self.status.showMessage(
                "Progressive scan running — playback unlocks after the first chunk."
            )

    def _on_scan_chunk_ready(
        self,
        video_id: int,
        scanned_until_sec: float,
        _visual_count: int,
    ) -> None:
        if video_id != self._current_video_id:
            return

        self._scanned_until_sec = scanned_until_sec
        import time

        now = time.monotonic()
        if now - self._last_chunk_ui_refresh >= 1.0:
            self._last_chunk_ui_refresh = now
            self._refresh_detection_counts(video_id)
            mode = self._db.get_setting(SETTING_MODERATION_MODE, DEFAULT_MODERATION_MODE)
            self._reload_moderation(mode or DEFAULT_MODERATION_MODE)

        record = self._db.get_video_by_id(video_id)
        duration = float(record.duration) if record and record.duration else 0.0
        pct = int(100 * scanned_until_sec / duration) if duration > 0 else 0
        self._refresh_scan_ui("scanning")
        self.right_panel.set_scan_progress_hint(
            f"Scanned {scanned_until_sec:.0f}s"
            + (f" ({pct}%)" if duration > 0 else "")
            + " — moderation active for this portion"
        )

        if self._try_unlock_playback_after_chunk(scanned_until_sec, duration):
            if self._progress:
                self._progress.setLabelText(
                    "First chunk ready — you can press Play. Scan continues in background."
                )
                self._progress.setCancelButtonText("Hide")
            if self._auto_play_after_scan and not self.playback.is_playing():
                self._auto_play_after_scan = False
                self.playback.play()
                self.controls.set_playing(True)

    def _try_unlock_playback_after_chunk(
        self,
        scanned_until_sec: float,
        duration_sec: float,
    ) -> bool:
        if not self._can_unlock_playback(scanned_until_sec, duration_sec):
            return False
        self._playback_unlocked = True
        self.status.showMessage(
            f"Playback unlocked — moderation active through {scanned_until_sec:.0f}s. "
            "Background scan continues."
        )
        return True

    def _on_scan_progress(self, percent: int, message: str) -> None:
        if self._progress:
            self._progress.setValue(percent)
            self._progress.setLabelText(message)

    def _on_scan_finished(
        self,
        video_id: int,
        frame_count: int,
        visual_count: int,
        audio_count: int,
        warning: str = "",
    ) -> None:
        record = self._db.get_video_by_id(video_id)
        if record:
            self._refresh_scan_ui(record.scan_status)
            self._scanned_until_sec = float(record.duration or record.scan_progress_sec)
        self.right_panel.set_scan_progress_hint("")
        self._refresh_detection_counts(video_id)
        mode = self._db.get_setting(SETTING_MODERATION_MODE, DEFAULT_MODERATION_MODE)
        self._reload_moderation(mode or DEFAULT_MODERATION_MODE)
        self._playback_unlocked = True
        thresh = resolve_visual_threshold(
            strictness_raw=self._db.get_setting(SETTING_VISUAL_STRICTNESS),
            threshold_raw=self._db.get_setting(SETTING_VISUAL_THRESHOLD),
        )
        self.status.showMessage(
            f"Scan complete — {frame_count} frames, "
            f"{visual_count} visual, {audio_count} audio segment(s) "
            f"(NSFW threshold {thresh:.2f})"
        )
        if warning.strip():
            QMessageBox.information(
                self,
                APP_NAME,
                f"Scan finished. Visual moderation is active.\n\n{warning.strip()}",
            )
        if self._auto_play_after_scan:
            self._auto_play_after_scan = False
            self.playback.play()
            self.controls.set_playing(True)

    def _on_view_results(self) -> None:
        if not self._current_video_id:
            self._show_error("Scan a video first to view results.")
            return
        record = self._db.get_video_by_id(self._current_video_id)
        name = record.file_name if record else "Video"
        dialog = ScanResultsDialog(
            self._db,
            self._current_video_id,
            name,
            self,
        )
        dialog.detections_changed.connect(self._on_detections_changed)
        dialog.exec()

    def _on_detections_changed(self) -> None:
        if not self._current_video_id:
            return
        self._refresh_detection_counts(self._current_video_id)
        mode = self._db.get_setting(SETTING_MODERATION_MODE, DEFAULT_MODERATION_MODE)
        self._reload_moderation(mode or DEFAULT_MODERATION_MODE)
        self.status.showMessage(
            "Detection list updated — only enabled segments will be moderated."
        )

    def _on_generate_figures(self) -> None:
        try:
            scan_paths = ThesisFigureGenerator(self._db).generate_all(
                video_id=self._current_video_id
            )
            eval_results = ModelEvaluationRunner(THESIS_FIGURES_DIR).run_all()
            folder = THESIS_FIGURES_DIR.resolve()
            v = eval_results.get("visual", {})
            k = eval_results.get("keyword", {})
            extra = ""
            if "accuracy" in v:
                extra += f"\nVisual F1: {v['f1_score']} | Brier: {v['brier_score']}"
            if "word_level_f1" in k:
                extra += f"\nKeyword F1: {k['word_level_f1']}"
            QMessageBox.information(
                self,
                APP_NAME,
                f"Generated {len(scan_paths)} scan chart(s) + model metrics in:\n"
                f"{folder}{extra}",
            )
        except Exception as exc:  # noqa: BLE001
            self._show_error(f"Could not generate figures:\n{exc}")

    def _on_scan_failed(self, message: str) -> None:
        self._refresh_scan_ui("failed")
        self._playback_unlocked = False
        self._auto_play_after_scan = False
        self._show_error(f"Scan failed:\n{message}")

    def _on_scan_thread_done(self) -> None:
        if self._progress:
            self._progress.close()
            self._progress = None
        self.right_panel.scan_btn.setEnabled(bool(self._current_path))
        self._scan_worker = None

    def _cancel_scan(self) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.request_cancel()
            self._scan_worker.wait(3000)
            if self._scan_worker.isRunning():
                self._scan_worker.terminate()
                self._scan_worker.wait(2000)
        self._auto_play_after_scan = False
        if self._setting_bool(SETTING_REQUIRE_SCAN_BEFORE_PLAY, True):
            self._playback_unlocked = False
        self._on_scan_thread_done()
        self.status.showMessage("Pre-scan cancelled — playback still blocked.")

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, APP_NAME, message)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._video_fullscreen:
            self._set_video_fullscreen(False)
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.terminate()
            self._scan_worker.wait(1000)
        self.playback.shutdown()
        super().closeEvent(event)
