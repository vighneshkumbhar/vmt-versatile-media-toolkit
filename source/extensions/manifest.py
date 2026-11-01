"""
manifest.py
Manifest dataclass and validator.
"""
import re
import json
from dataclasses import dataclass, field
from typing import Optional, List
from packaging.version import parse as parse_version, InvalidVersion

from extensions.capabilities import ALLOWED_CAPABILITIES

class ManifestError(Exception):
    pass

@dataclass
class ExtensionManifest:
    id: str
    name: str
    version: str
    author: str
    description: str
    min_vmt_version: str
    max_vmt_version: Optional[str] = None
    category: str = "general"
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entrypoint: str = "extension"
    website: str = ""
    repository: str = ""

def validate_manifest(data: dict) -> ExtensionManifest:
    # Check required fields
    required = ["id", "name", "version", "author", "description", "min_vmt_version"]
    for req in required:
        if req not in data:
            raise ManifestError(f"Missing required field: {req}")

    # ID validation
    ext_id = data["id"]
    if not re.match(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){2,}$", ext_id):
        raise ManifestError(f"Invalid extension ID format: {ext_id}")

    # Version validation
    try:
        parse_version(data["version"])
    except InvalidVersion:
        raise ManifestError(f"Invalid version format: {data['version']}")

    try:
        parse_version(data["min_vmt_version"])
    except InvalidVersion:
        raise ManifestError(f"Invalid min_vmt_version format: {data['min_vmt_version']}")
        
    if data.get("max_vmt_version"):
        try:
            parse_version(data["max_vmt_version"])
        except InvalidVersion:
            raise ManifestError(f"Invalid max_vmt_version format: {data['max_vmt_version']}")

    # Permissions validation
    permissions = data.get("permissions", [])
    for p in permissions:
        if p not in ALLOWED_CAPABILITIES:
            raise ManifestError(f"Invalid permission requested: {p}")

    # Note: 'verified' field in manifest is silently ignored — only the backend's verification_status is authoritative.

    return ExtensionManifest(
        id=ext_id,
        name=data["name"],
        version=data["version"],
        author=data["author"],
        description=data["description"],
        min_vmt_version=data["min_vmt_version"],
        max_vmt_version=data.get("max_vmt_version"),
        category=data.get("category", "general"),
        permissions=permissions,
        dependencies=data.get("dependencies", []),
        entrypoint=data.get("entrypoint", "extension"),
        website=data.get("website", ""),
        repository=data.get("repository", "")
    )

def load_manifest_from_dict(data: dict) -> ExtensionManifest:
    return validate_manifest(data)

def load_manifest_from_json(path: str) -> ExtensionManifest:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return validate_manifest(data)
    except json.JSONDecodeError as e:
        raise ManifestError(f"Invalid JSON in manifest: {e}")
    except OSError as e:
        raise ManifestError(f"Could not read manifest file: {e}")
