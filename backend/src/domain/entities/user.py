"""User entity model."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.time import utc_now
from db.base import Base
from db.types import UTCDateTimeType


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    supabase_auth_id = Column(UUID(as_uuid=True), unique=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False, default="trainee")
    full_name = Column(String)
    gender = Column(String, nullable=True)
    race = Column(String, nullable=True)
    year_of_study = Column(String, nullable=True)
    created_at = Column(UTCDateTimeType(), default=utc_now)
    updated_at = Column(UTCDateTimeType(), default=utc_now, onupdate=utc_now)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
