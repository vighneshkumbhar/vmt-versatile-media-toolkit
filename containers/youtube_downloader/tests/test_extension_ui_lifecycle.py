"""Headless acceptance test for VMT's installed-extension UI lifecycle.

Run with ``QT_QPA_PLATFORM=offscreen``.  It deliberately exercises the
extracted .vmte package through MainWindow, not the container source directly.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_APP_DATA = tempfile.TemporaryDirectory(prefix="vmt-extension-ui-")
os.environ["APPDATA"] = _APP_DATA.name

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "source"))

from PySide6.QtWidgets import QApplication
from extensions.lifecycle import ExtensionLifecycle
from extensions.loader import ExtensionLoader
from extensions.registry import ExtensionRegistry
from ui.main_window import MainWindow


EXT_ID = "org.vmt.youtubedownloader"
PAGE_ID = "youtube_downloader"
PACKAGE = ROOT / "containers" / "youtube_downloader" / "build" / "YouTubeDownloader.vmte"


def _events(app):
    app.processEvents()
    app.processEvents()


def test_install_open_disable_enable_restart_uninstall():
    assert PACKAGE.exists(), "Build the .vmte package before running this test"
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    lifecycle = ExtensionLifecycle(ExtensionRegistry(), ExtensionLoader(), window)

    try:
        record = lifecycle.install(PACKAGE)
        _events(app)
        assert record.enabled and record.instance is not None
        assert PAGE_ID in window._pages
        assert PAGE_ID not in window._nav_btns
        assert PAGE_ID in window._more_page._extensions_panel._extensions

        window._switch_page(PAGE_ID)
        page, _ = window._pages[PAGE_ID]
        assert window._current_page_id == PAGE_ID
        assert page.url_edit.placeholderText()
        assert page.quality_combo.findText("720p") >= 0
        assert page.fmt_combo.findText("MP4") >= 0

        window._set_extension_pinned(PAGE_ID, True)
        _events(app)
        assert PAGE_ID in window._nav_btns
        window._set_extension_pinned(PAGE_ID, False)
        _events(app)
        assert PAGE_ID not in window._nav_btns

        lifecycle.disable(EXT_ID)
        _events(app)
        assert not lifecycle._registry.get(EXT_ID).enabled
        assert PAGE_ID not in window._pages and PAGE_ID not in window._nav_btns

        lifecycle.enable(EXT_ID)
        _events(app)
        assert lifecycle._registry.get(EXT_ID).enabled
        assert PAGE_ID in window._pages and PAGE_ID not in window._nav_btns

        # A new host process/window must restore enabled extensions from disk.
        window.close()
        _events(app)
        restarted = MainWindow()
        _events(app)
        assert PAGE_ID in restarted._pages and PAGE_ID not in restarted._nav_btns

        restart_lifecycle = ExtensionLifecycle(
            restarted._ext_registry, restarted._ext_loader, restarted
        )
        restart_lifecycle.uninstall(EXT_ID)
        _events(app)
        assert restarted._ext_registry.get(EXT_ID) is None
        assert PAGE_ID not in restarted._pages and PAGE_ID not in restarted._nav_btns
        restarted.close()
    finally:
        record = lifecycle._registry.get(EXT_ID)
        if record:
            lifecycle.uninstall(EXT_ID)
        window.deleteLater()
