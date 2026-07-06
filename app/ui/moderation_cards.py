"""Horizontal moderation mode cards (mockup-aligned)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import MODERATION_MODES
from app.ui.styles import COLORS


class _ModeCard(QFrame):
    """Clickable card; forwards clicks to selection handler."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("moderationModeCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ModerationCards(QWidget):
    """Selectable cards for moderation mode with clear active styling."""

    mode_changed = Signal(str)

    _CARD_IDLE = (
        f"QFrame#moderationModeCard {{"
        f" background-color: #FFFFFF;"
        f" border: 2px solid #E5E7EB;"
        f" border-radius: 10px;"
        f"}}"
    )
    _CARD_ACTIVE = (
        f"QFrame#moderationModeCard {{"
        f" background-color: {COLORS['primary_light']};"
        f" border: 2px solid {COLORS['primary']};"
        f" border-radius: 10px;"
        f"}}"
    )
    _TITLE_IDLE = "color: #374151; font-weight: 600; font-size: 13px; border: none;"
    _TITLE_ACTIVE = (
        f"color: {COLORS['primary']}; font-weight: 700; font-size: 13px; border: none;"
    )
    _SUB_IDLE = "color: #6B7280; font-size: 11px;"
    _SUB_ACTIVE = f"color: {COLORS['primary_hover']}; font-size: 11px; font-weight: 500;"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)

        title = QLabel("MODERATION MODE")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(8)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._cards: dict[str, _ModeCard] = {}
        self._titles: dict[str, QPushButton] = {}
        self._subs: dict[str, QLabel] = {}
        self._active_key = "none"

        subtitles = {
            "none": "Play normally — no filtering",
            "mute_audio": "Mute flagged speech only",
            "hide_video": "Blur shield on sex scenes + mute that same section",
            "hide_and_mute": "Best for demos — blur shield + mute",
            "skip_scene": "Jump past flagged segments",
        }

        for index, (key, label) in enumerate(MODERATION_MODES):
            card = _ModeCard()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)

            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._TITLE_IDLE)
            sub = QLabel(subtitles.get(key, ""))
            sub.setWordWrap(True)
            sub.setStyleSheet(self._SUB_IDLE)

            card_layout.addWidget(btn)
            card_layout.addWidget(sub)

            self._group.addButton(btn, index)
            btn.clicked.connect(lambda checked, k=key: self._select(k))
            card.clicked.connect(lambda k=key: self._select(k))

            self._cards[key] = card
            self._titles[key] = btn
            self._subs[key] = sub
            grid.addWidget(card, 0, index)

        self._group.idClicked.connect(self._on_group_id)
        layout.addLayout(grid)

        self.set_mode_key("none")

    def _on_group_id(self, index: int) -> None:
        key = MODERATION_MODES[index][0]
        self._apply_active_style(key)
        self.mode_changed.emit(key)

    def _select(self, key: str) -> None:
        if key == self._active_key:
            return
        self.set_mode_key(key)
        self.mode_changed.emit(key)

    def _apply_active_style(self, active_key: str) -> None:
        self._active_key = active_key
        for key, card in self._cards.items():
            selected = key == active_key
            card.setStyleSheet(self._CARD_ACTIVE if selected else self._CARD_IDLE)
            self._titles[key].setStyleSheet(
                self._TITLE_ACTIVE if selected else self._TITLE_IDLE
            )
            self._subs[key].setStyleSheet(
                self._SUB_ACTIVE if selected else self._SUB_IDLE
            )

    def set_mode_key(self, key: str) -> None:
        for index, (mode_key, _) in enumerate(MODERATION_MODES):
            if mode_key == key:
                btn = self._group.button(index)
                if btn:
                    btn.setChecked(True)
                self._apply_active_style(key)
                break
