"""Right information panel: now playing, scan, detection counts."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.styles import COLORS


class RightPanel(QFrame):
    """Now playing metadata, scan status, and detection summary."""

    scan_clicked = Signal()
    view_results_clicked = Signal()
    generate_figures_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightPanel")
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        layout.addWidget(self._section_now_playing())
        layout.addWidget(self._section_scan())
        layout.addWidget(self._section_detections())
        layout.addStretch()

    def _section_now_playing(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        v = QVBoxLayout(box)
        v.addWidget(self._heading("NOW PLAYING"))

        self.now_playing_title = QLabel("No video selected")
        self.now_playing_title.setStyleSheet(
            f"color: {COLORS['primary']}; font-weight: 700; font-size: 14px;"
        )
        v.addWidget(self.now_playing_title)

        self.meta_path = QLabel("File Path: —")
        self.meta_duration = QLabel("Duration: —")
        self.meta_resolution = QLabel("Resolution: —")
        self.meta_size = QLabel("File Size: —")
        for lbl in (
            self.meta_path,
            self.meta_duration,
            self.meta_resolution,
            self.meta_size,
        ):
            lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
            lbl.setWordWrap(True)
            v.addWidget(lbl)
        return box

    def _section_scan(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        v = QVBoxLayout(box)
        v.addWidget(self._heading("SCAN STATUS"))

        self.scan_status_badge = QLabel("● Not Scanned")
        self.scan_status_badge.setStyleSheet(
            f"color: {COLORS['success']}; font-weight: 600;"
        )
        v.addWidget(self.scan_status_badge)

        self.scan_hint = QLabel(
            "Click 'Scan Video' to analyze for inappropriate content."
        )
        self.scan_hint.setWordWrap(True)
        self.scan_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        v.addWidget(self.scan_hint)

        self.scan_btn = QPushButton("🔍  Scan Video")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self.scan_clicked.emit)
        v.addWidget(self.scan_btn)

        self.results_btn = QPushButton("View results")
        self.results_btn.setEnabled(False)
        self.results_btn.clicked.connect(self.view_results_clicked.emit)
        v.addWidget(self.results_btn)

        self.figures_btn = QPushButton("Export thesis figures")
        self.figures_btn.setToolTip("Generate PNG charts for dissertation")
        self.figures_btn.clicked.connect(self.generate_figures_clicked.emit)
        v.addWidget(self.figures_btn)
        return box

    def _section_detections(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        v = QVBoxLayout(box)
        v.addWidget(self._heading("DETECTION RESULTS"))

        self.visual_row = self._badge_row(
            "👁 Visual (enabled)", COLORS["visual_badge"], COLORS["danger"]
        )
        self.audio_row = self._badge_row(
            "🔊 Audio (enabled)", COLORS["audio_badge"], COLORS["warning"]
        )
        v.addLayout(self.visual_row[0])
        v.addLayout(self.audio_row[0])
        self.visual_count_label = self.visual_row[1]
        self.audio_count_label = self.audio_row[1]
        return box

    @staticmethod
    def _heading(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        return lbl

    @staticmethod
    def _badge_row(title: str, bg: str, fg: str) -> tuple:
        row = QHBoxLayout()
        name = QLabel(title)
        count = QLabel("0")
        count.setStyleSheet(
            f"background: {bg}; color: {fg}; font-weight: 700;"
            " padding: 4px 12px; border-radius: 10px;"
        )
        count.setMinimumWidth(28)
        count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(name)
        row.addStretch()
        row.addWidget(count)
        return row, count

    def set_now_playing(
        self,
        title: str,
        *,
        path: str = "—",
        duration: str = "—",
        resolution: str = "—",
        size: str = "—",
    ) -> None:
        self.now_playing_title.setText(title)
        self.meta_path.setText(f"File Path: {path}")
        self.meta_duration.setText(f"Duration: {duration}")
        self.meta_resolution.setText(f"Resolution: {resolution}")
        self.meta_size.setText(f"File Size: {size}")

    def set_scan_status(self, status_label: str, *, is_success: bool = True) -> None:
        color = COLORS["success"] if is_success else COLORS["danger"]
        self.scan_status_badge.setText(f"● {status_label}")
        self.scan_status_badge.setStyleSheet(f"color: {color}; font-weight: 600;")

    def set_scan_progress_hint(self, text: str) -> None:
        if text:
            self.scan_hint.setText(text)
            self.scan_hint.setStyleSheet(f"color: {COLORS['primary']}; font-size: 12px;")
        else:
            self.scan_hint.setText(
                "Click 'Scan Video' to analyze for inappropriate content."
            )
            self.scan_hint.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 12px;"
            )

    def set_detection_counts(self, visual: int, audio: int) -> None:
        self.visual_count_label.setText(str(visual))
        self.audio_count_label.setText(str(audio))
