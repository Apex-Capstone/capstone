"""Session entity model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.base import Base


class Session(Base):
    """Session model for tracking simulation sessions."""
    
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("core.users.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("core.cases.id"), nullable=False)
    state = Column(String, nullable=False)  # active, paused, completed, abandoned
    current_spikes_stage = Column(String)  # setting, perception, invitation, knowledge, empathy, summary
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    session_metadata = Column("metadata", Text)  # JSON for additional session data
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    case = relationship("Case", back_populates="sessions")
    turns = relationship("Turn", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="session", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, case_id={self.case_id}, state={self.state})>"

