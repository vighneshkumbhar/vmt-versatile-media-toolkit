from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Extension(Base):
    __tablename__ = "extensions"
    
    id = Column(String, primary_key=True)  # Reverse-domain ID, immutable
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_download_count = Column(Integer, default=0)
    is_disabled = Column(Boolean, default=False)
    
    versions = relationship("ExtensionVersion", back_populates="extension", cascade="all, delete-orphan")
    author = relationship("User")
