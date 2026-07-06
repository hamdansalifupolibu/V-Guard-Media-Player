"""Left navigation sidebar (mockup-aligned)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import LOGO_SIDEBAR_MAX_HEIGHT, LOGO_SIDEBAR_MAX_WIDTH, SIDEBAR_WIDTH
from app.ui.branding import make_logo_label


class Sidebar(QFrame):
    """Logo, navigation tabs, and footer tagline."""

    nav_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 14)
        layout.setSpacing(8)

        layout.addWidget(
            make_logo_label(
                self,
                max_width=LOGO_SIDEBAR_MAX_WIDTH,
                max_height=LOGO_SIDEBAR_MAX_HEIGHT,
                tooltip="V-Guard Media Player",
            ),
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        layout.addSpacing(6)

        self._nav_buttons: dict[str, QPushButton] = {}
        for key, label, icon in [
            ("player", "Player", "▶"),
            ("library", "Library", "📁"),
            ("downloads", "Downloads", "⬇"),
            ("settings", "Settings", "⚙"),
            ("about", "About", "ℹ"),
        ]:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
            layout.addWidget(btn)
            self._nav_buttons[key] = btn

        self._nav_buttons["player"].setChecked(True)
        layout.addStretch()

        footer = QLabel("✓ Safe Media.\nSmart Protection.")
        footer.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
        footer.setWordWrap(True)
        layout.addWidget(footer)

    def _on_nav(self, key: str) -> None:
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)
        self.nav_changed.emit(key)
