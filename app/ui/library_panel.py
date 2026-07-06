"""Video library — open previously registered videos."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database.db import VGuardDatabase


class LibraryPanel(QWidget):
    """List videos from SQLite; double-click or Open to load."""

    open_video = Signal(str)

    def __init__(self, database: VGuardDatabase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = database

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Library")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        hint = QLabel("Videos you have opened or scanned are listed here.")
        hint.setStyleSheet("color: #6B7280;")
        layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget)

        open_btn = QPushButton("Open selected")
        open_btn.setObjectName("primaryBtn")
        open_btn.clicked.connect(self._open_selected)
        layout.addWidget(open_btn)

        refresh_btn = QPushButton("Refresh list")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        self.refresh()

    def refresh(self) -> None:
        self.list_widget.clear()
        for video in self._db.list_videos():
            status = video.scan_status.replace("_", " ")
            item = QListWidgetItem(
                f"{video.file_name}  —  {status}"
            )
            item.setData(256, video.file_path)
            self.list_widget.addItem(item)

    def _open_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            path = item.data(256)
            if path:
                self.open_video.emit(path)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        path = item.data(256)
        if path:
            self.open_video.emit(path)
