from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.extension_version import VerificationStatus

class VersionResponse(BaseModel):
    version: str
    verification_status: VerificationStatus
    verification_reason: Optional[str] = None
    changelog: str
    created_at: datetime
    permissions: list[str]
    min_vmt_version: str

class ExtensionSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    author: str
    category: str
    recommended_version: Optional[VersionResponse] = None
    total_download_count: int
    is_disabled: bool

class ExtensionDetailResponse(ExtensionSummaryResponse):
    versions: list[VersionResponse]
    website: Optional[str] = None
    repository: Optional[str] = None
