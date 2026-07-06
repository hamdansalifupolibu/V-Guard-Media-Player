"""Scan results: review detections and enable/disable moderation per segment."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.db import VGuardDatabase
from app.database.models import DetectionRecord
from app.utils.time_utils import format_timestamp


class ScanResultsDialog(QDialog):
    """
    Review visual and audio detections; toggle which segments are moderated.
    """

    detections_changed = Signal()

    def __init__(
        self,
        database: VGuardDatabase,
        video_id: int,
        file_name: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = database
        self._video_id = video_id
        self._changed = False
        self._checkboxes: dict[int, QCheckBox] = {}

        self.setWindowTitle(f"Scan results — {file_name}")
        self.resize(720, 480)

        root = QVBoxLayout(self)
        self._summary_label = QLabel()
        root.addWidget(self._summary_label)

        self._tabs = QTabWidget()
        self._visual_table = self._make_table()
        self._audio_table = self._make_table()
        self._tabs.addTab(self._wrap_table(self._visual_table), "Visual scenes")
        self._tabs.addTab(self._wrap_table(self._audio_table), "Audio content")
        root.addWidget(self._tabs)

        self._reload_tables()

        # Bulk actions
        actions = QHBoxLayout()
        enable_all = QPushButton("Enable all")
        enable_all.clicked.connect(lambda: self._set_all(True))
        disable_all = QPushButton("Disable all")
        disable_all.clicked.connect(lambda: self._set_all(False))
        enable_vis = QPushButton("Enable visual only")
        enable_vis.clicked.connect(lambda: self._set_type("visual", True))
        enable_aud = QPushButton("Enable audio only")
        enable_aud.clicked.connect(lambda: self._set_type("audio", True))
        actions.addWidget(enable_all)
        actions.addWidget(disable_all)
        actions.addWidget(enable_vis)
        actions.addWidget(enable_aud)
        actions.addStretch()
        root.addLayout(actions)

        hint = QLabel(
            "Checked rows are moderated during playback (for your selected mode). "
            "Uncheck false positives to ignore them."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6B7280; font-size: 12px;")
        root.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    @staticmethod
    def _make_table() -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            ["Moderate", "Start", "End", "Confidence", "Label"]
        )
        table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    @staticmethod
    def _wrap_table(table: QTableWidget) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(table)
        return w

    def _reload_tables(self) -> None:
        self._checkboxes.clear()
        all_det = self._db.get_detections(self._video_id)
        visual = [d for d in all_det if d.detection_type == "visual"]
        audio = [d for d in all_det if d.detection_type == "audio"]

        enabled_v = sum(1 for d in visual if d.enabled)
        enabled_a = sum(1 for d in audio if d.enabled)
        self._summary_label.setText(
            f"Visual: {len(visual)} detected ({enabled_v} enabled for moderation)  |  "
            f"Audio: {len(audio)} detected ({enabled_a} enabled for moderation)"
        )

        self._fill_table(self._visual_table, visual)
        self._fill_table(self._audio_table, audio)

        if not all_det:
            self._tabs.setTabText(0, "Visual scenes (0)")
            self._tabs.setTabText(1, "Audio content (0)")
        else:
            self._tabs.setTabText(0, f"Visual scenes ({len(visual)})")
            self._tabs.setTabText(1, f"Audio content ({len(audio)})")

    def _fill_table(
        self,
        table: QTableWidget,
        detections: list[DetectionRecord],
    ) -> None:
        table.setRowCount(len(detections))
        for row, det in enumerate(detections):
            cb = QCheckBox()
            cb.blockSignals(True)
            cb.setChecked(det.enabled)
            cb.blockSignals(False)
            cb.setProperty("detection_id", det.id)
            cb.stateChanged.connect(
                lambda _state, detection_id=det.id: self._on_checkbox(detection_id)
            )
            self._checkboxes[det.id] = cb
            table.setCellWidget(row, 0, cb)

            table.setItem(row, 1, QTableWidgetItem(format_timestamp(det.start_time, hms=True)))
            table.setItem(row, 2, QTableWidgetItem(format_timestamp(det.end_time, hms=True)))
            conf = (
                f"{det.confidence:.2f}"
                if det.confidence is not None
                else "—"
            )
            table.setItem(row, 3, QTableWidgetItem(conf))
            table.setItem(row, 4, QTableWidgetItem(det.label or "—"))

    def _on_checkbox(self, detection_id: int) -> None:
        cb = self._checkboxes.get(detection_id)
        if cb is None:
            return
        enabled = cb.isChecked()
        self._db.set_detection_enabled(detection_id, enabled)
        self._changed = True
        self.detections_changed.emit()
        self._update_summary_only()

    def _update_summary_only(self) -> None:
        visual = self._db.get_detections(self._video_id, detection_type="visual")
        audio = self._db.get_detections(self._video_id, detection_type="audio")
        enabled_v = sum(1 for d in visual if d.enabled)
        enabled_a = sum(1 for d in audio if d.enabled)
        self._summary_label.setText(
            f"Visual: {len(visual)} detected ({enabled_v} enabled for moderation)  |  "
            f"Audio: {len(audio)} detected ({enabled_a} enabled for moderation)"
        )

    def _set_all(self, enabled: bool) -> None:
        for det in self._db.get_detections(self._video_id):
            self._db.set_detection_enabled(det.id, enabled)
        self._changed = True
        self.detections_changed.emit()
        self._checkboxes.clear()
        self._reload_tables()

    def _set_type(self, detection_type: str, enabled: bool) -> None:
        for det in self._db.get_detections(
            self._video_id, detection_type=detection_type
        ):
            self._db.set_detection_enabled(det.id, enabled)
        self._changed = True
        self.detections_changed.emit()
        self._checkboxes.clear()
        self._reload_tables()

    @property
    def has_changes(self) -> bool:
        return self._changed
