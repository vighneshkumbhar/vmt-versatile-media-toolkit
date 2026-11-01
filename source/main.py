"""
main.py
Entry point for VMT — Versatile Media Toolkit.
"""
import sys
import os

# ── Add source directory to path so imports work ──────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from ui.styles import apply as apply_style
from ui.main_window import MainWindow


def main() -> None:
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("VMT")
    app.setApplicationVersion("1.0.0-beta")
    app.setOrganizationName("VMT")

    icon_path = os.path.abspath(os.path.join(_HERE, "..", "assets", "runner_icon.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply global stylesheet
    apply_style(app)

    # Set a clean font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
