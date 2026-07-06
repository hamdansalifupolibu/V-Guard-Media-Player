"""V-Guard logo and window icons (taskbar, dialogs, sidebar)."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from app.config import (
    APP_ICON_PATH,
    APP_LOGO_PATH,
    APP_MARK_PATH,
    LOGO_ABOUT_MAX_WIDTH,
    LOGO_SIDEBAR_MAX_WIDTH,
)

_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


@lru_cache(maxsize=1)
def logo_pixmap() -> QPixmap:
    """Trimmed full logo (shield + V-GUARD wordmark)."""
    if APP_LOGO_PATH.is_file():
        return QPixmap(str(APP_LOGO_PATH))
    return QPixmap()


@lru_cache(maxsize=1)
def mark_pixmap() -> QPixmap:
    """Shield-only mark for small chrome."""
    if APP_MARK_PATH.is_file():
        return QPixmap(str(APP_MARK_PATH))
    return logo_pixmap()


def _scale_pixmap(pix: QPixmap, *, max_width: int, max_height: int | None = None) -> QPixmap:
    if pix.isNull():
        return pix
    if max_height is None:
        if pix.width() <= max_width:
            return pix
        return pix.scaledToWidth(
            max_width,
            Qt.TransformationMode.SmoothTransformation,
        )
    return pix.scaled(
        max_width,
        max_height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


@lru_cache(maxsize=1)
def app_icon() -> QIcon:
    """
    Taskbar / window icon: shield mark at small sizes, full logo at large sizes.
    """
    icon = QIcon()
    if APP_ICON_PATH.is_file():
        ico = QIcon(str(APP_ICON_PATH))
        if not ico.isNull():
            return ico

    mark = mark_pixmap()
    full = logo_pixmap()
    if mark.isNull() and full.isNull():
        return icon

    for size in _ICON_SIZES:
        source = mark if size <= 48 and not mark.isNull() else full
        if source.isNull():
            source = full if not full.isNull() else mark
        scaled = source.scaled(
            QSize(size, size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        icon.addPixmap(scaled)
    return icon


def apply_app_icon(app: QApplication) -> None:
    """Set default icon for all windows and the Windows taskbar."""
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)


def make_logo_label(
    parent: QWidget | None = None,
    *,
    max_width: int = LOGO_SIDEBAR_MAX_WIDTH,
    max_height: int | None = 200,
    tooltip: str = "",
) -> QLabel:
    """Sidebar logo — uses trimmed asset at readable size."""
    label = QLabel(parent)
    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    label.setMinimumHeight(min(max_height or 120, 120))
    if tooltip:
        label.setToolTip(tooltip)
    pix = _scale_pixmap(
        logo_pixmap(),
        max_width=max_width,
        max_height=max_height,
    )
    if pix.isNull():
        label.setText("V-Guard")
        label.setObjectName("appTitle")
        return label
    label.setPixmap(pix)
    label.setScaledContents(False)
    return label


def make_about_logo_label(parent: QWidget | None = None) -> QLabel:
    """About page — large trimmed logo."""
    label = QLabel(parent)
    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    pix = _scale_pixmap(
        logo_pixmap(),
        max_width=LOGO_ABOUT_MAX_WIDTH,
        max_height=360,
    )
    if not pix.isNull():
        label.setPixmap(pix)
    return label
