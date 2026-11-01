from vmt_sdk import VMTExtension, VMTContext
import logging

logger = logging.getLogger(__name__)

class HelloExtension(VMTExtension):
    def on_load(self, ctx: VMTContext) -> None:
        logger.info("Hello from Hello Extension!")
        
    def on_unload(self, ctx: VMTContext) -> None:
        logger.info("Goodbye from Hello Extension!")
