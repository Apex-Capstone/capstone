"""User entity model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base import Base


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
