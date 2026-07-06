"""Legal direct-link download manager UI (Stage 11)."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, DOWNLOADS_DIR
from app.database.db import VGuardDatabase
from app.downloads.download_manager import DownloadManager
from app.downloads.download_worker import DownloadWorker
from app.utils.ffmpeg_path import is_ffmpeg_available
from app.downloads.url_validator import validate_download_url


class DownloadsPanel(QWidget):
    """Paste a direct legal video URL, download with progress, view history."""

    open_video = Signal(str)

    def __init__(self, database: VGuardDatabase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = database
        self._manager = DownloadManager()
        self._worker: DownloadWorker | None = None
        self._active_download_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Downloads")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        legal = QLabel(
            "Educational downloads: paste any public video URL (direct file links, "
            "YouTube, Vimeo, university CDNs, etc.).\n\n"
            "You must confirm you have permission to download and use the content "
            "for education or research only."
        )
        legal.setWordWrap(True)
        legal.setStyleSheet("color: #6B7280; font-size: 12px;")
        layout.addWidget(legal)

        self.educational_confirm = QCheckBox(
            "I confirm this is for educational use and I have permission to download"
        )
        self.educational_confirm.setChecked(True)
        layout.addWidget(self.educational_confirm)

        ffmpeg_note = QLabel()
        if is_ffmpeg_available():
            ffmpeg_note.setText("FFmpeg detected — YouTube and high-quality merges are supported.")
            ffmpeg_note.setStyleSheet("color: #10B981; font-size: 11px;")
        else:
            ffmpeg_note.setText(
                "FFmpeg not found. YouTube may fail or use lower quality. "
                "Run: python scripts/install_ffmpeg.py  (or install FFmpeg system-wide)"
            )
            ffmpeg_note.setStyleSheet("color: #D97706; font-size: 11px;")
        ffmpeg_note.setWordWrap(True)
        layout.addWidget(ffmpeg_note)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "https://…/lecture.mp4  or  https://www.youtube.com/watch?v=…"
        )
        self.url_input.returnPressed.connect(self._start_download)
        url_row.addWidget(self.url_input, stretch=1)

        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("primaryBtn")
        self.download_btn.clicked.connect(self._start_download)
        url_row.addWidget(self.download_btn)
        layout.addLayout(url_row)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #6B7280;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        history_title = QLabel("Download history")
        history_title.setObjectName("sectionTitle")
        layout.addWidget(history_title)

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._on_history_double_click)
        layout.addWidget(self.history_list, stretch=1)

        actions = QHBoxLayout()
        self.play_btn = QPushButton("Play in player")
        self.play_btn.clicked.connect(self._play_selected)
        actions.addWidget(self.play_btn)

        self.folder_btn = QPushButton("Open downloads folder")
        self.folder_btn.clicked.connect(self._open_downloads_folder)
        actions.addWidget(self.folder_btn)

        self.cancel_btn = QPushButton("Cancel download")
        self.cancel_btn.clicked.connect(self._cancel_download)
        self.cancel_btn.hide()
        actions.addWidget(self.cancel_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        actions.addWidget(refresh_btn)
        actions.addStretch()
        layout.addLayout(actions)

        folder_hint = QLabel(f"Files save to: {DOWNLOADS_DIR.resolve()}")
        folder_hint.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        layout.addWidget(folder_hint)

        self.refresh()

    def refresh(self) -> None:
        self.history_list.clear()
        for record in self._db.list_downloads():
            status = record.status.replace("_", " ")
            name = ""
            if record.file_path:
                name = Path(record.file_path).name
            label = record.url if len(record.url) <= 60 else record.url[:57] + "…"
            if name:
                text = f"{name}  —  {status}"
            else:
                text = f"{label}  —  {status}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, record.id)
            item.setToolTip(record.url)
            if record.status == "failed":
                item.setForeground(Qt.GlobalColor.darkRed)
            elif record.status == "complete":
                item.setForeground(Qt.GlobalColor.darkGreen)
            self.history_list.addItem(item)

    def _start_download(self) -> None:
        if not self.educational_confirm.isChecked():
            QMessageBox.warning(
                self,
                APP_NAME,
                "Please confirm educational use and that you have permission "
                "to download this content.",
            )
            return

        url = self.url_input.text().strip()
        quick = validate_download_url(url, educational=True)
        if not quick.ok:
            QMessageBox.warning(self, APP_NAME, quick.message)
            return

        if self._worker and self._worker.isRunning():
            QMessageBox.information(
                self, APP_NAME, "A download is already in progress."
            )
            return

        probe = self._manager.probe_url(url)
        if not probe.ok:
            QMessageBox.warning(self, APP_NAME, probe.message)
            return
        if not probe.file_path:
            QMessageBox.warning(self, APP_NAME, "Could not determine save path.")
            return

        download_id = self._db.add_download(probe.url or url, status="pending")
        self._active_download_id = download_id
        self.refresh()

        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.cancel_btn.show()
        self.download_btn.setEnabled(False)
        self.status_label.setText("Starting download…")

        self._worker = DownloadWorker(
            self._db,
            download_id,
            probe.url or url,
            probe.file_path,
            self,
        )
        self._worker.set_use_extractor(probe.use_stream_extractor)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, received: int, total: int, message: str) -> None:
        if total > 0:
            pct = int(min(100, received * 100 / total))
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(pct)
            self.status_label.setText(f"{message} {pct}%")
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText(message)

    def _on_finished(self, result) -> None:
        self._cleanup_worker_ui()
        self.status_label.setText(result.message)
        self.url_input.clear()
        self.refresh()
        QMessageBox.information(self, APP_NAME, result.message)

    def _on_failed(self, message: str) -> None:
        self._cleanup_worker_ui()
        self.status_label.setText(message)
        self.refresh()
        QMessageBox.warning(self, APP_NAME, message)

    def _cleanup_worker_ui(self) -> None:
        self.progress_bar.hide()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.cancel_btn.hide()
        self.download_btn.setEnabled(True)
        self._worker = None
        self._active_download_id = None

    def _cancel_download(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.status_label.setText("Cancelling…")

    def _selected_record_path(self) -> str | None:
        item = self.history_list.currentItem()
        if not item:
            return None
        download_id = item.data(Qt.ItemDataRole.UserRole)
        for record in self._db.list_downloads():
            if record.id == download_id and record.file_path:
                path = Path(record.file_path)
                if path.is_file():
                    return str(path.resolve())
        return None

    def _play_selected(self) -> None:
        path = self._selected_record_path()
        if path:
            self.open_video.emit(path)
        else:
            QMessageBox.information(
                self,
                APP_NAME,
                "Select a completed download from the list.",
            )

    def _on_history_double_click(self, item: QListWidgetItem) -> None:
        download_id = item.data(Qt.ItemDataRole.UserRole)
        for record in self._db.list_downloads():
            if record.id == download_id and record.file_path:
                path = Path(record.file_path)
                if path.is_file():
                    self.open_video.emit(str(path.resolve()))
                    return
        QMessageBox.information(
            self, APP_NAME, "This entry has no playable file yet."
        )

    def _open_downloads_folder(self) -> None:
        folder = str(DOWNLOADS_DIR.resolve())
        os.makedirs(folder, exist_ok=True)
        if os.name == "nt":
            os.startfile(folder)  # noqa: S606
        else:
            import subprocess

            subprocess.run(["xdg-open", folder], check=False)
