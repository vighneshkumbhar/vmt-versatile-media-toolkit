"""
ui_api.py
UI API for extensions to register pages.
"""
from typing import TYPE_CHECKING, Type, Any
from extensions.capabilities import Capability

if TYPE_CHECKING:
    from extensions.api.context import VMTContext

class UIContext:
    def __init__(self, ctx: "VMTContext"):
        self._ctx = ctx

    def register_page(self, page_id: str, label: str, widget_class: Type[Any], description: str = "") -> None:
        self._ctx._check_capability(Capability.UI_REGISTER)
        # Call back into main window to add the page
        if hasattr(self._ctx._main_window, "register_extension_page"):
            self._ctx._main_window.register_extension_page(self._ctx._manifest.id, page_id, label, widget_class, description)

    def show_notification(self, message: str, level: str = "info") -> None:
        self._ctx._check_capability(Capability.UI_REGISTER)
        if hasattr(self._ctx._main_window, "show_notification"):
            self._ctx._main_window.show_notification(message, level)
