"""
Hello VMT Example Extension
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from extensions.api.base import VMTExtension
from extensions.api.context import VMTContext

class HelloWidget(QWidget):
    def __init__(self, manifest):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel(f"Hello from VMT Extension System!\n\n"
                       f"Extension ID: {manifest.id}\n"
                       f"Name: {manifest.name}\n"
                       f"Version: {manifest.version}\n"
                       f"Author: {manifest.author}")
        layout.addWidget(label)
        self.setLayout(layout)

class HelloVMTExtension(VMTExtension):
    def on_load(self, ctx: VMTContext) -> None:
        # Register a page in the UI
        ctx.ui.register_page(
            page_id="hello_page",
            label="Hello VMT",
            widget_class=lambda: HelloWidget(ctx._manifest),
            description="A minimal example extension."
        )

    def on_unload(self, ctx: VMTContext) -> None:
        pass
