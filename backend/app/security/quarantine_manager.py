import os
import uuid
from pathlib import Path
from fastapi import HTTPException
from app.config import settings

class QuarantineManager:
    """
    Manages isolated quarantine storage for submitted extension packages.
    Enforces strict path traversal checks and ensures submitted files remain
    completely isolated without code execution or import.
    """
    def __init__(self, quarantine_base: str | None = None):
        self.base_dir = Path(quarantine_base or settings.QUARANTINE_PATH).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_package(self, submission_id: str, filename: str, data: bytes) -> str:
        """
        Stores raw submitted package bytes in quarantine.
        Returns the absolute string path to the quarantined file.
        """
        if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(413, f"Package size exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB")

        # Sanitize filename
        safe_filename = Path(filename).name
        if not safe_filename or ".." in safe_filename or "\\" in safe_filename or "\x00" in safe_filename:
            safe_filename = f"package_{uuid.uuid4().hex[:8]}.vmte"

        sub_dir = (self.base_dir / submission_id).resolve()
        # Verify sub_dir is within base_dir
        if not str(sub_dir).startswith(str(self.base_dir)):
            raise HTTPException(400, "Path traversal detected in quarantine directory creation")

        sub_dir.mkdir(parents=True, exist_ok=True)
        dest_path = (sub_dir / safe_filename).resolve()

        if not str(dest_path).startswith(str(sub_dir)):
            raise HTTPException(400, "Path traversal detected in quarantine file placement")

        dest_path.write_bytes(data)
        return str(dest_path)

    def get_package_path(self, submission_id: str, filename: str) -> Path:
        """Resolves and validates a path to a quarantined package file."""
        target_path = (self.base_dir / submission_id / Path(filename).name).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise HTTPException(400, "Path traversal detected in quarantine access")
        if not target_path.exists():
            raise HTTPException(404, "Quarantined file not found")
        return target_path

quarantine_manager = QuarantineManager()
