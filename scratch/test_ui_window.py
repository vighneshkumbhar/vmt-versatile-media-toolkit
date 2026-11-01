import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SOURCE_DIR = os.path.join(_PROJECT_ROOT, "source")
if _SOURCE_DIR not in sys.path:
    sys.path.insert(0, _SOURCE_DIR)

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.extension_manager_window import ExtensionManagerWindow

def test_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    print("MainWindow initialized successfully!")
    
    mgr = ExtensionManagerWindow(parent=window)
    print("ExtensionManagerWindow initialized successfully!")
    sys.exit(0)

if __name__ == "__main__":
    test_ui()
