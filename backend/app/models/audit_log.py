from sqlalchemy import Column, String, DateTime, Text
import uuid
from datetime import datetime, timezone
from app.database import Base

class AuditLog(Base):
    """
    Application Append-Only Security Audit Log.
    No API endpoints permit updating or deleting audit log records.
    Never log passwords, password hashes, secrets, or authentication tokens.
    """
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    details_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
