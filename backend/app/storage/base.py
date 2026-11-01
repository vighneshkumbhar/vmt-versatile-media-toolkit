from abc import ABC, abstractmethod

class PackageStorage(ABC):
    @abstractmethod
    async def store(self, ext_id: str, version: str, data: bytes) -> str:
        """Store bytes. Returns opaque storage_key."""
        pass
    
    @abstractmethod
    async def retrieve(self, storage_key: str) -> bytes:
        """Retrieve bytes by storage_key."""
        pass
    
    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete stored package."""
        pass
    
    @abstractmethod
    async def get_size(self, storage_key: str) -> int:
        """Return size in bytes."""
        pass
