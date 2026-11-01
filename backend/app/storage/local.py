import os
from pathlib import Path
from app.storage.base import PackageStorage
from fastapi import HTTPException

class LocalPackageStorage(PackageStorage):
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def store(self, ext_id: str, version: str, data: bytes) -> str:
        storage_key = f"{ext_id}_{version}.vmte"
        file_path = self.base_path / storage_key
        file_path.write_bytes(data)
        return storage_key
    
    async def retrieve(self, storage_key: str) -> bytes:
        file_path = self.base_path / storage_key
        if not file_path.exists():
            raise HTTPException(404, "Package not found in storage")
        return file_path.read_bytes()
    
    async def delete(self, storage_key: str) -> None:
        file_path = self.base_path / storage_key
        if file_path.exists():
            file_path.unlink()
    
    async def get_size(self, storage_key: str) -> int:
        file_path = self.base_path / storage_key
        if not file_path.exists():
            return 0
        return file_path.stat().st_size
