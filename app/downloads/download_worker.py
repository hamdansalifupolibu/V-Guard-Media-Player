"""Background thread for legal video downloads."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.downloads.download_manager import DownloadManager, DownloadResult
from app.database.db import VGuardDatabase


class DownloadWorker(QThread):
    """Runs DownloadManager.download on a worker thread."""

    progress = Signal(int, int, str)  # received, total, message
    finished = Signal(object)  # DownloadResult
    failed = Signal(str)

    def __init__(
        self,
        database: VGuardDatabase,
        download_id: int,
        url: str,
        dest_path: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = database
        self._download_id = download_id
        self._url = url
        self._dest_path = dest_path
        self._use_extractor = False
        self._cancelled = False
        self._manager = DownloadManager()

    def set_use_extractor(self, enabled: bool) -> None:
        self._use_extractor = enabled

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        self._db.update_download(self._download_id, status="downloading")

        def on_progress(received: int, total: int, message: str) -> None:
            self.progress.emit(received, total, message)

        result = self._manager.download(
            self._url,
            self._dest_path,
            on_progress=on_progress,
            cancel_check=lambda: self._cancelled,
            use_stream_extractor=self._use_extractor,
        )

        if result.ok and result.file_path:
            self._db.update_download(
                self._download_id,
                file_path=result.file_path,
                status="complete",
            )
            self.finished.emit(result)
        else:
            self._db.update_download(self._download_id, status="failed")
            self.failed.emit(result.message)
