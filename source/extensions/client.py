"""
client.py
HTTP client for the VMT backend.
STUB - to be wired to the live backend by integration agent.
"""
import requests
import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_URL_DEFAULT = "http://localhost:8000"

@dataclass
class ExtensionSummary:
    id: str
    name: str
    description: str
    author: str
    version: str                  # recommended version string
    verification_status: str      # "verified" | "unverified" | "rejected" | "disabled"
    category: str
    download_count: int

@dataclass
class VersionInfo:
    version: str
    verification_status: str
    verification_reason: Optional[str]
    changelog: str
    permissions: list[str]
    min_vmt_version: str

@dataclass
class ExtensionDetail(ExtensionSummary):
    versions: list[VersionInfo]
    min_vmt_version: str
    permissions: list[str]
    website: str
    repository: str

class VMTBackendClient:
    def __init__(self, base_url: str = BASE_URL_DEFAULT):
        self._base = base_url.rstrip("/")
        self._timeout = 10  # seconds
        self._token: Optional[str] = None
        self._user_info: Optional[dict] = None

    def set_token(self, token: Optional[str]):
        self._token = token

    @property
    def token(self) -> Optional[str]:
        return self._token

    def is_healthy(self) -> bool:
        """Check if backend is reachable."""
        try:
            resp = requests.get(f"{self._base}/extensions/", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def login(self, username: str, password: str) -> dict:
        """Login user and save JWT token."""
        url = f"{self._base}/auth/login"
        resp = requests.post(url, json={"username": username, "password": password}, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        self._token = data.get("access_token")
        self._user_info = {"username": username}
        return data

    def logout(self):
        self._token = None
        self._user_info = None

    def get_my_extensions(self) -> list[dict]:
        """Fetch extensions owned by developer."""
        if not self._token:
            raise RuntimeError("Not authenticated")
        headers = {"Authorization": f"Bearer {self._token}"}
        resp = requests.get(f"{self._base}/developer/", headers=headers, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def upload_extension(self, package_bytes: bytes, filename: str = "package.vmte") -> dict:
        """Upload a new extension package."""
        if not self._token:
            raise RuntimeError("Not authenticated")
        headers = {"Authorization": f"Bearer {self._token}"}
        files = {"package": (filename, package_bytes, "application/octet-stream")}
        resp = requests.post(f"{self._base}/developer/", headers=headers, files=files, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def upload_version(self, ext_id: str, package_bytes: bytes, filename: str = "package.vmte") -> dict:
        """Upload a new version for an existing extension."""
        if not self._token:
            raise RuntimeError("Not authenticated")
        headers = {"Authorization": f"Bearer {self._token}"}
        files = {"package": (filename, package_bytes, "application/octet-stream")}
        resp = requests.post(f"{self._base}/developer/{ext_id}/versions", headers=headers, files=files, timeout=60)
        resp.raise_for_status()
        return resp.json()
    
    def search(
        self,
        q: str = "",
        category: str = "",
        verified_only: bool = False,
        page: int = 1,
    ) -> list[ExtensionSummary]:
        """Search for extensions. Returns empty list on error."""
        try:
            params = {"page": page}
            if q:
                params["q"] = q
            if category:
                params["category"] = category
            if verified_only:
                params["verified"] = "true"
            
            resp = requests.get(
                f"{self._base}/extensions/",
                params=params,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            items = resp.json()
            
            result = []
            for item in items:
                rec = item.get("recommended_version") or {}
                result.append(ExtensionSummary(
                    id=item["id"],
                    name=item["name"],
                    description=item.get("description", ""),
                    author=item.get("author", ""),
                    version=rec.get("version", ""),
                    verification_status=rec.get("verification_status", "unverified"),
                    category=item.get("category", "utility"),
                    download_count=item.get("total_download_count", 0),
                ))
            return result
        except Exception as e:
            logger.warning(f"search() failed: {e}")
            return []
    
    def get_detail(self, ext_id: str) -> Optional[ExtensionDetail]:
        """Get full extension detail. Returns None on error."""
        try:
            resp = requests.get(
                f"{self._base}/extensions/{ext_id}",
                timeout=self._timeout,
            )
            resp.raise_for_status()
            item = resp.json()
            rec = item.get("recommended_version") or {}
            
            versions = [
                VersionInfo(
                    version=v["version"],
                    verification_status=v.get("verification_status", "unverified"),
                    verification_reason=v.get("verification_reason"),
                    changelog=v.get("changelog", ""),
                    permissions=v.get("permissions", []),
                    min_vmt_version=v.get("min_vmt_version", "1.0.0"),
                )
                for v in item.get("versions", [])
            ]
            
            return ExtensionDetail(
                id=item["id"],
                name=item["name"],
                description=item.get("description", ""),
                author=item.get("author", ""),
                version=rec.get("version", ""),
                verification_status=rec.get("verification_status", "unverified"),
                category=item.get("category", "utility"),
                download_count=item.get("total_download_count", 0),
                versions=versions,
                min_vmt_version=rec.get("min_vmt_version", "1.0.0"),
                permissions=rec.get("permissions", []),
                website=item.get("website", ""),
                repository=item.get("repository", ""),
            )
        except Exception as e:
            logger.warning(f"get_detail({ext_id}) failed: {e}")
            return None
    
    def download(
        self, ext_id: str, version: str = None
    ) -> tuple[bytes, str]:
        """
        Download a .vmte package.
        Returns (package_bytes, sha256_hash).
        sha256 comes from X-Package-Hash response header.
        Raises RuntimeError on failure.
        """
        try:
            if version:
                url = f"{self._base}/extensions/{ext_id}/versions/{version}/download"
            else:
                url = f"{self._base}/extensions/{ext_id}/download"
            
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            
            sha256 = resp.headers.get("X-Package-Hash", "")
            return resp.content, sha256
        except Exception as e:
            raise RuntimeError(f"Download failed for {ext_id}: {e}")

