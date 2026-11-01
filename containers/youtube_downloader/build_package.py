"""
build_package.py
Package builder and ecosystem publisher for VMT YouTube Downloader Extension.

Builds containers/youtube_downloader/ into YouTubeDownloader.vmte.
Publishes extension to backend (initially UNVERIFIED).
Provides an explicit separate admin verification function.
"""
import os
import sys
import json
import hashlib
import zipfile
import shutil
import logging
from pathlib import Path

# Add source folder to sys.path if running inside VMT tree
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_PATH = PROJECT_ROOT / "source"
if str(SOURCE_PATH) not in sys.path:
    sys.path.insert(0, str(SOURCE_PATH))

try:
    from extensions.package import validate_package
except Exception:
    validate_package = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CONTAINER_DIR = Path(__file__).resolve().parent
BUILD_DIR = CONTAINER_DIR / "build"
MANIFEST_PATH = CONTAINER_DIR / "manifest.json"
SOURCE_DIR = CONTAINER_DIR / "source"
DEPS_DIR = CONTAINER_DIR / "dependencies"
OUTPUT_VMTE = BUILD_DIR / "YouTubeDownloader.vmte"
ROOT_VMTE = PROJECT_ROOT / "YouTubeDownloader.vmte"


def build_package() -> tuple[Path, str]:
    """
    Builds YouTubeDownloader.vmte package and returns (package_path, sha256_hash).
    """
    logger.info("==================================================")
    logger.info("BUILDING VMT YOUTUBE DOWNLOADER EXTENSION PACKAGE")
    logger.info("==================================================")

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    logger.info(f"Extension ID:      {manifest_data.get('id')}")
    logger.info(f"Extension Version: {manifest_data.get('version')}")
    logger.info(f"Author:            {manifest_data.get('author')}")

    # Build ZIP archive
    if OUTPUT_VMTE.exists():
        OUTPUT_VMTE.unlink()

    with zipfile.ZipFile(OUTPUT_VMTE, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add manifest.json at root
        zf.write(MANIFEST_PATH, "manifest.json")

        # 2. Add source python files under extension/
        for p in SOURCE_DIR.rglob("*.py"):
            rel = p.relative_to(SOURCE_DIR)
            arcname = f"extension/{rel.as_posix()}"
            zf.write(p, arcname)

        # 3. Add isolated dependencies under extension/dependencies/
        if DEPS_DIR.exists():
            for p in DEPS_DIR.rglob("*"):
                if p.is_file() and not p.name.endswith((".pyc", ".pyo")):
                    rel = p.relative_to(DEPS_DIR)
                    arcname = f"extension/dependencies/{rel.as_posix()}"
                    zf.write(p, arcname)

    # Compute SHA-256
    pkg_bytes = OUTPUT_VMTE.read_bytes()
    sha256 = hashlib.sha256(pkg_bytes).hexdigest()

    # Validate package structure using VMT validator if available
    if validate_package:
        validate_package(OUTPUT_VMTE)

    # Copy to project root output artifact location if running in VMT tree
    if ROOT_VMTE.parent.exists():
        try:
            shutil.copy(OUTPUT_VMTE, ROOT_VMTE)
        except Exception:
            pass

    size_kb = len(pkg_bytes) / 1024
    logger.info(f"Package built successfully: {OUTPUT_VMTE} ({size_kb:.1f} KB)")
    logger.info(f"Root artifact:             {ROOT_VMTE}")
    logger.info(f"SHA-256 Hash:              {sha256}")
    logger.info("==================================================\n")

    return OUTPUT_VMTE, sha256


def publish_unverified(backend_url: str, dev_token: str) -> dict:
    """
    Publishes the built package to the VMT backend.
    Status defaults to UNVERIFIED per specification.
    """
    import requests
    logger.info(f"Publishing {OUTPUT_VMTE.name} to VMT backend at {backend_url}...")

    headers = {"Authorization": f"Bearer {dev_token}"}
    with open(OUTPUT_VMTE, "rb") as f:
        files = {"package": (OUTPUT_VMTE.name, f, "application/octet-stream")}
        resp = requests.post(f"{backend_url}/developer/", headers=headers, files=files)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to publish extension: HTTP {resp.status_code} - {resp.text}")

    res = resp.json()
    logger.info(f"✓ Extension published. Status: {res.get('verification_status', 'unverified')}")
    return res


def admin_verify_extension(backend_url: str, admin_token: str, ext_id: str, version: str) -> dict:
    """
    EXPLICIT SEPARATE ADMIN OPERATION:
    Verifies a specific extension version on the backend server.
    """
    import requests
    logger.info(f"Executing explicit admin verification for {ext_id} v{version}...")

    headers = {"Authorization": f"Bearer {admin_token}"}
    url = f"{backend_url}/admin/extensions/{ext_id}/versions/{version}/verify"
    resp = requests.post(url, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"Failed admin verification: HTTP {resp.status_code} - {resp.text}")

    res = resp.json()
    logger.info(f"✓ Explicit Admin Verification Successful! Status is now: {res.get('verification_status')}")
    return res


if __name__ == "__main__":
    pkg, sha = build_package()
