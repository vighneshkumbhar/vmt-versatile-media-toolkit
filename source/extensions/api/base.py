"""
base.py
VMTExtension — the base class that all VMT extensions must inherit from.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from extensions.api.context import VMTContext

class VMTExtension(ABC):
    """Base class for all VMT extensions. Override on_load and on_unload."""
    
    @abstractmethod
    def on_load(self, ctx: "VMTContext") -> None:
        """Called when the extension is enabled. Set up pages, register hooks."""
        pass
    
    def on_unload(self, ctx: "VMTContext") -> None:
        """Called when the extension is disabled or uninstalled. Clean up."""
        pass
