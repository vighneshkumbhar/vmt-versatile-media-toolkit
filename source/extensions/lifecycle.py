"""
lifecycle.py
Orchestrates install/uninstall/enable/disable.
"""
import shutil
import logging
from pathlib import Path

from extensions.registry import ExtensionRegistry, ExtensionRecord
from extensions.loader import ExtensionLoader
from extensions.package import extract_package, compute_sha256
from extensions.paths import get_extension_dir
from extensions.api.context import VMTContext

logger = logging.getLogger(__name__)

class ExtensionLifecycle:
    def __init__(self, registry: ExtensionRegistry, loader: ExtensionLoader, main_window):
        self._registry = registry
        self._loader = loader
        self._main_window = main_window

    def install(self, package_path: Path, expected_sha256: str = None) -> ExtensionRecord:
        if expected_sha256:
            actual_sha256 = compute_sha256(package_path)
            if actual_sha256 != expected_sha256:
                raise ValueError("SHA-256 mismatch")
                
        # Validate and get ID without full extract first, but extract_package validates too.
        # Let's extract to a temporary folder or directly to target.
        # For simplicity, extract directly but rollback on failure.
        
        # Actually, we need the manifest first to get the ID.
        from extensions.package import validate_package
        manifest = validate_package(package_path)
        
        if self._registry.get(manifest.id):
            raise ValueError(f"Extension {manifest.id} is already installed.")
            
        ext_dir = get_extension_dir(manifest.id)
        if ext_dir.exists():
            shutil.rmtree(ext_dir)
            
        try:
            extract_package(package_path, ext_dir)
            
            record = ExtensionRecord(
                id=manifest.id,
                name=manifest.name,
                version=manifest.version,
                path=ext_dir,
                enabled=False,
                manifest=manifest
            )
            
            self._registry.register(record)
            
            # Enable by default if you want:
            self.enable(manifest.id)
            
            return record
            
        except Exception as e:
            if ext_dir.exists():
                shutil.rmtree(ext_dir)
            raise e

    def uninstall(self, ext_id: str) -> None:
        record = self._registry.get(ext_id)
        if not record:
            return
            
        if record.enabled:
            self.disable(ext_id)
            
        self._registry.unregister(ext_id)
        
        ext_dir = get_extension_dir(ext_id)
        if ext_dir.exists():
            shutil.rmtree(ext_dir, ignore_errors=True)

    def enable(self, ext_id: str) -> None:
        record = self._registry.get(ext_id)
        if not record:
            raise ValueError(f"Extension {ext_id} not found")
            
        if record.enabled and record.instance:
            return # Already enabled and loaded
            
        ctx = VMTContext(record.manifest, self._main_window)
        instance = self._loader.load(record, ctx)
        
        if instance:
            record.enabled = True
            self._registry.save_to_disk()
        else:
            raise RuntimeError(f"Failed to load extension {ext_id}: {record.load_error}")

    def disable(self, ext_id: str) -> None:
        record = self._registry.get(ext_id)
        if not record:
            return
            
        if not record.enabled:
            return
            
        ctx = VMTContext(record.manifest, self._main_window)
        self._loader.unload(record, ctx)
        
        # If UI context had registered pages, we might need a way to unregister them.
        # For now, UI main window could handle dynamic cleanup if needed.
        if hasattr(self._main_window, "unregister_extension_pages"):
            self._main_window.unregister_extension_pages(ext_id)
            
        record.enabled = False
        self._registry.save_to_disk()
