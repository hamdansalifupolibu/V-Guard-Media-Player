"""Background thread for video pre-scan."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread

from app.analysis.video_scanner import VideoScanner
from app.database.db import VGuardDatabase


class ScanWorker(QThread):
    """Runs VideoScanner.run_scan on a background thread."""

    def __init__(
        self,
        database: VGuardDatabase,
        video_id: int,
        file_path: str | Path,
        parent=None,
        *,
        resume: bool = False,
    ) -> None:
        super().__init__(parent)
        self._video_id = video_id
        self._file_path = file_path
        self._resume = resume
        self.scanner = VideoScanner(database)

    def request_cancel(self) -> None:
        self.scanner.request_cancel()

    def run(self) -> None:
        self.scanner.run_scan(self._video_id, self._file_path, resume=self._resume)
