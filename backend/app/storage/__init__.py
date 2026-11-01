from app.storage.local import LocalPackageStorage
from app.config import settings

_storage = None

def get_storage():
    global _storage
    if _storage is None:
        if settings.STORAGE_BACKEND == "local":
            _storage = LocalPackageStorage(settings.LOCAL_STORAGE_PATH)
        else:
            raise NotImplementedError("Only local storage is implemented")
    return _storage
