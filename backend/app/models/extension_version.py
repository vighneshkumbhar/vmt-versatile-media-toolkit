import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    DISABLED = "disabled"

class ExtensionVersion(Base):
    __tablename__ = "extension_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    extension_id = Column(String, ForeignKey("extensions.id"), nullable=False)
    version = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    package_hash = Column(String, nullable=False)
    package_size_bytes = Column(Integer, nullable=False)
    changelog = Column(String, default="")
    min_vmt_version = Column(String, default="1.0.0")
    max_vmt_version = Column(String, nullable=True)
    permissions = Column(String, nullable=False) # JSON array string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.UNVERIFIED)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, ForeignKey("users.id"), nullable=True)
    verification_reason = Column(String, nullable=True)
    
    extension = relationship("Extension", back_populates="versions")
    verified_by_user = relationship("User", foreign_keys=[verified_by])
