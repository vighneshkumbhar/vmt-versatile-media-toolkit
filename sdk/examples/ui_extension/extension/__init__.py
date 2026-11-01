from vmt_sdk import VMTExtension, VMTContext
from .page import UIExamplePage

class UIExampleExtension(VMTExtension):
    def on_load(self, ctx: VMTContext) -> None:
        ctx.ui.register_page("ui_example", "UI Example", UIExamplePage)
        
    def on_unload(self, ctx: VMTContext) -> None:
        pass
