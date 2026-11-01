"""
context.py
VMTContext holds references to different APIs.
"""
from typing import Any, List
from extensions.manifest import ExtensionManifest
from extensions.capabilities import Capability, VMTCapabilityError
from extensions.api.media_api import MediaContext
from extensions.api.jobs_api import JobsContext
from extensions.api.ffmpeg_api import FFmpegContext
from extensions.api.ui_api import UIContext
from extensions.api.settings_api import SettingsContext

class VMTContext:
    def __init__(self, manifest: ExtensionManifest, main_window: Any):
        self._manifest = manifest
        self._main_window = main_window
        
        # Internal context cache
        self._media: MediaContext | None = None
        self._jobs: JobsContext | None = None
        self._ffmpeg: FFmpegContext | None = None
        self._ui: UIContext | None = None
        self._settings: SettingsContext | None = None

    def _check_capability(self, cap: Capability) -> None:
        if cap.value not in self._manifest.permissions:
            raise VMTCapabilityError(f"Extension '{self._manifest.id}' missing required capability: {cap.value}")

    def get_ffmpeg_path(self) -> str:
        """Return the host's configured FFmpeg executable path, if available."""
        return getattr(self._main_window, "_ffmpeg_path", "") if self._main_window else ""

    @property
    def media(self) -> MediaContext:
        if self._media is None:
            self._media = MediaContext(self)
        return self._media

    @property
    def jobs(self) -> JobsContext:
        if self._jobs is None:
            self._jobs = JobsContext(self)
        return self._jobs

    @property
    def ffmpeg(self) -> FFmpegContext:
        if self._ffmpeg is None:
            self._ffmpeg = FFmpegContext(self)
        return self._ffmpeg

    @property
    def ui(self) -> UIContext:
        if self._ui is None:
            self._ui = UIContext(self)
        return self._ui

    @property
    def settings(self) -> SettingsContext:
        if self._settings is None:
            self._settings = SettingsContext(self)
        return self._settings
