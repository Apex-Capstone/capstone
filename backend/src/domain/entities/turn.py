"""Turn entity model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.base import Base


class Turn(Base):
    """Turn model for individual dialogue exchanges."""
    
    __tablename__ = "turns"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    role = Column(String, nullable=False)  # user, assistant (patient)
    text = Column(Text, nullable=False)
    audio_url = Column(String, nullable=True)  # URL to stored audio file
    metrics_json = Column(Text)  # JSON with turn-level metrics (empathy score, question type, etc.)
    spikes_stage = Column(String)  # SPIKES stage during this turn
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="turns")
    
    def __repr__(self) -> str:
        return f"<Turn(id={self.id}, session_id={self.session_id}, turn={self.turn_number}, role={self.role})>"

