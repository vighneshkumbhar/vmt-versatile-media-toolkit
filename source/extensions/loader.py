"""
loader.py
Loads and unloads Python extension modules.
"""
import sys
from typing import Optional
import importlib.util
import logging
from pathlib import Path

from extensions.registry import ExtensionRecord
from extensions.api.base import VMTExtension
from extensions.api.context import VMTContext

logger = logging.getLogger(__name__)

class ExtensionLoader:
    def load(self, record: ExtensionRecord, ctx: VMTContext) -> Optional[VMTExtension]:
        try:
            entrypoint = record.manifest.entrypoint
            module_name = f"vmt_ext_{record.id.replace('.', '_')}"
            
            # Find the __init__.py of the extension module
            init_path = record.path / entrypoint / "__init__.py"
            if not init_path.exists():
                init_path = record.path / f"{entrypoint}.py"
                
            if not init_path.exists():
                raise FileNotFoundError(f"Could not find entrypoint {entrypoint} at {record.path}")

            package_locations = [str(init_path.parent)] if init_path.name == "__init__.py" else None
            spec = importlib.util.spec_from_file_location(
                module_name, str(init_path), submodule_search_locations=package_locations
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create module spec for {init_path}")
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find VMTExtension subclass
            ext_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, VMTExtension) and attr is not VMTExtension:
                    ext_class = attr
                    break
                    
            if ext_class is None:
                raise TypeError("No subclass of VMTExtension found in module")
                
            instance = ext_class()
            instance.on_load(ctx)
            
            record.instance = instance
            if ctx._main_window is not None:
                active = getattr(ctx._main_window, "_active_extension_instances", None)
                if active is None:
                    active = {}
                    ctx._main_window._active_extension_instances = active
                active[record.id] = instance
            record.load_error = None
            return instance
            
        except Exception as e:
            logger.error(f"Failed to load extension {record.id}: {e}", exc_info=True)
            record.load_error = str(e)
            record.instance = None
            return None

    def unload(self, record: ExtensionRecord, ctx: VMTContext) -> None:
        try:
            instance = record.instance
            if instance is None and ctx._main_window is not None:
                instance = getattr(ctx._main_window, "_active_extension_instances", {}).get(record.id)
            if instance:
                instance.on_unload(ctx)
            if ctx._main_window is not None:
                getattr(ctx._main_window, "_active_extension_instances", {}).pop(record.id, None)
                
            module_name = f"vmt_ext_{record.id.replace('.', '_')}"
            if module_name in sys.modules:
                del sys.modules[module_name]
                
            record.instance = None
            record.load_error = None
            
        except Exception as e:
            logger.error(f"Failed to unload extension {record.id}: {e}", exc_info=True)
