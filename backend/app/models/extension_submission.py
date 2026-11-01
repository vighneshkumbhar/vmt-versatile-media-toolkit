from sqlalchemy import Column, String, DateTime, Text, ForeignKey
import uuid
from datetime import datetime, timezone
from app.database import Base

class ExtensionSubmission(Base):
    __tablename__ = "extension_submissions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    developer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    extension_id = Column(String, nullable=False, index=True)
    repository_url = Column(String, nullable=False)
    release_tag = Column(String, nullable=False)
    submitted_version = Column(String, nullable=False)
    asset_filename = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # "pending" | "reviewing" | "approved" | "rejected" | "withdrawn"
    package_quarantine_path = Column(String, nullable=True)
    static_analysis_warnings = Column(Text, nullable=True)  # JSON formatted array
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
