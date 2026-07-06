"""About V-Guard."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.config import APP_NAME, APP_VERSION
from app.ui.branding import make_about_logo_label


class AboutPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(
            make_about_logo_label(self),
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        text = QLabel(
            f"Version {APP_VERSION}\n\n"
            "BSc prototype — smart desktop media player with pre-scan "
            "visual and audio moderation.\n\n"
            "Safe Media. Smart Protection.\n\n"
            "All processing runs locally on your machine."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()
