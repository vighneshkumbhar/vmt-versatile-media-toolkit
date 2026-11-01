"""
registry.py
Extension registry managing known extensions.
"""
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict

from extensions.manifest import ExtensionManifest, load_manifest_from_dict
from extensions.paths import get_extension_config_path
from extensions.api.base import VMTExtension

logger = logging.getLogger(__name__)

@dataclass
class ExtensionRecord:
    id: str
    name: str
    version: str
    path: Path
    enabled: bool
    manifest: ExtensionManifest
    pinned: bool = False
    instance: Optional[VMTExtension] = None
    load_error: Optional[str] = None

class ExtensionRegistry:
    def __init__(self):
        self._extensions: Dict[str, ExtensionRecord] = {}
        self._config_path = get_extension_config_path()

    def load_from_disk(self) -> None:
        # Reloads are used after install/disable/uninstall.  Do not retain
        # records that were removed from the on-disk registry.
        self._extensions.clear()
        if not self._config_path.exists():
            return
            
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for ext_id, ext_data in data.items():
                try:
                    manifest_data = ext_data["manifest"]
                    manifest = load_manifest_from_dict(manifest_data)
                    record = ExtensionRecord(
                        id=manifest.id,
                        name=manifest.name,
                        version=manifest.version,
                        path=Path(ext_data["path"]),
                        enabled=ext_data["enabled"],
                        manifest=manifest,
                        pinned=bool(ext_data.get("pinned", False)),
                    )
                    self._extensions[manifest.id] = record
                except Exception as e:
                    logger.error(f"Failed to load extension record for {ext_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to load extension registry: {e}")

    def save_to_disk(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for ext_id, record in self._extensions.items():
                data[ext_id] = {
                    "path": str(record.path),
                    "enabled": record.enabled,
                    "pinned": record.pinned,
                    "manifest": asdict(record.manifest)
                }
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save extension registry: {e}")

    def register(self, record: ExtensionRecord) -> None:
        self._extensions[record.id] = record
        self.save_to_disk()

    def unregister(self, ext_id: str) -> None:
        if ext_id in self._extensions:
            del self._extensions[ext_id]
            self.save_to_disk()

    def get(self, ext_id: str) -> Optional[ExtensionRecord]:
        return self._extensions.get(ext_id)

    def list_all(self) -> List[ExtensionRecord]:
        return list(self._extensions.values())

    def list_enabled(self) -> List[ExtensionRecord]:
        return [r for r in self._extensions.values() if r.enabled]
        
    def get_dynamic_pages(self) -> List[dict]:
        # This function would be used by UI to collect all pages from loaded extensions
        # Currently handled via callback in UIContext.
        return []
