"""
__init__.py
Main entrypoint for VMT YouTube Downloader Extension.
Inherits from extensions.api.base.VMTExtension.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure dependencies folder is accessible
_CONTAINER_DIR = Path(__file__).resolve().parent.parent
_DEPS_DIR = _CONTAINER_DIR / "dependencies"
if _DEPS_DIR.exists() and str(_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPS_DIR))

# Also support installed directory layout
_INST_DEPS_DIR = Path(__file__).resolve().parent / "dependencies"
if _INST_DEPS_DIR.exists() and str(_INST_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_INST_DEPS_DIR))

from extensions.api.base import VMTExtension
from extensions.api.context import VMTContext
from .ui_page import YouTubeDownloaderPage


class YouTubeDownloaderExtension(VMTExtension):
    """
    First-party VMT extension providing high-performance YouTube video & audio downloading.
    """

    def __init__(self):
        super().__init__()
        self.page: Optional[YouTubeDownloaderPage] = None

    def on_load(self, ctx: VMTContext) -> None:
        """
        Called when the extension is loaded by VMT ExtensionLoader.
        Registers the YouTube Downloader UI page with VMT.
        """
        self.ctx = ctx
        ffmpeg_path = ""
        try:
            if hasattr(ctx, 'get_ffmpeg_path'):
                ffmpeg_path = ctx.get_ffmpeg_path()
        except Exception:
            pass

        def create_page() -> YouTubeDownloaderPage:
            self.page = YouTubeDownloaderPage(ffmpeg_path=ffmpeg_path)
            return self.page

        # Register through VMT's public extension UI API. The host owns the
        # created widget and places it in its navigation stack.
        ctx.ui.register_page(
            "youtube_downloader", "YouTube Downloader", create_page,
            "Download YouTube video and audio with yt-dlp and FFmpeg.",
        )

        logger.info("VMT YouTube Downloader Extension loaded successfully.")

    def on_unload(self, ctx: Optional[VMTContext] = None) -> None:
        """
        Called when the extension is disabled or uninstalled.
        """
        if self.page:
            try:
                if self.page.download_thread and self.page.download_thread.isRunning():
                    self.page.download_thread.cancel()
                    self.page.download_thread.wait(2000)
            except Exception:
                pass
            self.page = None

        logger.info("VMT YouTube Downloader Extension unloaded.")


# Export entrypoint class for loader discovery
__extension_class__ = YouTubeDownloaderExtension
