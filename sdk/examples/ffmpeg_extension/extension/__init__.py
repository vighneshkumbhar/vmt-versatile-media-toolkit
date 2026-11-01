from vmt_sdk import VMTExtension, VMTContext
from .page import FFmpegExamplePage

class FFmpegExampleExtension(VMTExtension):
    def on_load(self, ctx: VMTContext) -> None:
        ctx.ui.register_page("ffmpeg_example", "FFmpeg Example", FFmpegExamplePage)
        
    def on_unload(self, ctx: VMTContext) -> None:
        pass
