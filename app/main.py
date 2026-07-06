"""V-Guard Media Player entry point."""

import sys
from pathlib import Path

# Allow running as `python app/main.py` from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, APP_VERSION
from app.ui.branding import apply_app_icon
from app.ui.main_window import MainWindow
from app.ui.styles import APP_STYLESHEET
from app.utils.ffmpeg_path import ensure_ffmpeg_on_path


def main() -> int:
    ensure_ffmpeg_on_path()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("V-Guard")
    app.setStyleSheet(APP_STYLESHEET)
    apply_app_icon(app)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
