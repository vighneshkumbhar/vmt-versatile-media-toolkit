"""
settings_api.py
Namespaced settings API for extensions.

All keys are automatically prefixed with 'ext.<extension_id>.' so extensions
cannot accidentally read or overwrite each other's settings.
"""
from typing import TYPE_CHECKING, Any
from extensions.capabilities import Capability
import core.settings as _settings_module

if TYPE_CHECKING:
    from extensions.api.context import VMTContext


class SettingsContext:
    def __init__(self, ctx: "VMTContext"):
        self._ctx = ctx
        self._prefix = f"ext.{self._ctx._manifest.id}."

    def get(self, key: str, default: Any = None) -> Any:
        """Read a setting namespaced to this extension."""
        self._ctx._check_capability(Capability.SETTINGS_READ)
        return _settings_module.get(self._prefix + key, default)

    def set(self, key: str, value: Any) -> None:
        """Write a setting namespaced to this extension."""
        self._ctx._check_capability(Capability.SETTINGS_WRITE)
        _settings_module.set(self._prefix + key, value)
        _settings_module.save()
