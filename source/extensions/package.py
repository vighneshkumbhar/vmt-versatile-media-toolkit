"""
package.py
.vmte package format handler.
A .vmte file is a ZIP archive containing: manifest.json, extension/__init__.py,
and optionally: assets/, README.md, CHANGELOG.md.

Security: all entry names are validated to prevent path traversal.
The 'verified' field in manifest is silently ignored — only the backend's
verification_status is authoritative.
"""
import zipfile
import json
import hashlib
from pathlib import Path
from extensions.manifest import ExtensionManifest, load_manifest_from_dict, ManifestError

class PackageError(Exception):
    pass

def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def _is_safe_path(name: str) -> bool:
    path = Path(name)
    if path.is_absolute():
        return False
    if ".." in path.parts:
        return False
    return True

def validate_package(zip_path: Path) -> ExtensionManifest:
    if not zipfile.is_zipfile(zip_path):
        raise PackageError(f"Not a valid ZIP file: {zip_path}")
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Check path traversal
        for info in zf.infolist():
            if not _is_safe_path(info.filename):
                raise PackageError(f"Unsafe path in archive: {info.filename}")
        
        # Check required files
        names = zf.namelist()
        if "manifest.json" not in names:
            raise PackageError("Missing manifest.json in package")
        if "extension/__init__.py" not in names:
            raise PackageError("Missing extension/__init__.py in package")
            
        # Parse manifest
        try:
            with zf.open("manifest.json") as f:
                data = json.load(f)
            return load_manifest_from_dict(data)
        except json.JSONDecodeError:
            raise PackageError("Invalid JSON in manifest.json")
        except ManifestError as e:
            raise PackageError(str(e))

def extract_package(zip_path: Path, dest_dir: Path) -> ExtensionManifest:
    manifest = validate_package(zip_path)
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if _is_safe_path(info.filename):
                zf.extract(info, dest_dir)
                
    return manifest

def create_package(source_dir: Path, output_path: Path) -> str:
    """Creates .vmte, returns SHA-256"""
    manifest_path = source_dir / "manifest.json"
    if not manifest_path.exists():
        raise PackageError("Source directory missing manifest.json")
    
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in source_dir.rglob("*"):
            if p.is_file():
                rel_path = p.relative_to(source_dir)
                zf.write(p, rel_path)
                
    return compute_sha256(output_path)
