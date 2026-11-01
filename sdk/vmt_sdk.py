"""
vmt_sdk.py
VMT Extension SDK — public API for VMT extension developers.

IMPORTANT: Extensions run inside VMT's Python process and share its privileges.
The capability system is for user disclosure and API organization, not sandboxing.
Only publish extensions you would trust running on your own computer.

Usage:
    from vmt_sdk import VMTExtension, VMTContext

    class MyExtension(VMTExtension):
        def on_load(self, ctx: VMTContext) -> None:
            ctx.ui.register_page("my_tool", "🔧 My Tool", MyToolWidget)
        
        def on_unload(self, ctx: VMTContext) -> None:
            pass
"""

try:
    from extensions.api.base import VMTExtension
    from extensions.api.context import VMTContext
    from extensions.capabilities import Capability, VMTCapabilityError
except ImportError:
    # Fall back to stub types (when developing/testing outside VMT)
    class VMTContext:
        pass
    class VMTExtension:
        def on_load(self, ctx: VMTContext) -> None:
            pass
        def on_unload(self, ctx: VMTContext) -> None:
            pass
    class Capability:
        pass
    class VMTCapabilityError(Exception):
        pass

__all__ = ["VMTExtension", "VMTContext", "Capability", "VMTCapabilityError"]
