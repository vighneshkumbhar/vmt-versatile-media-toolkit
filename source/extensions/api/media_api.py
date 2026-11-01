"""
media_api.py
Media API for extensions.
"""
from typing import TYPE_CHECKING, List, Optional, Any
from extensions.capabilities import Capability

if TYPE_CHECKING:
    from extensions.api.context import VMTContext

class MediaContext:
    def __init__(self, ctx: "VMTContext"):
        self._ctx = ctx

    def get_selected_files(self) -> List[str]:
        self._ctx._check_capability(Capability.MEDIA_READ)
        if hasattr(self._ctx._main_window, "get_selected_files"):
            return self._ctx._main_window.get_selected_files()
        return []

    def get_media_info(self, path: str) -> Optional[Any]:
        self._ctx._check_capability(Capability.MEDIA_READ)
        if hasattr(self._ctx._main_window, "get_media_info"):
            return self._ctx._main_window.get_media_info(path)
        return None

    def get_output_folder(self) -> str:
        self._ctx._check_capability(Capability.MEDIA_WRITE)
        if hasattr(self._ctx._main_window, "get_output_folder"):
            return self._ctx._main_window.get_output_folder()
        return ""
