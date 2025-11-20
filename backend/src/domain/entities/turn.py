"""Turn entity model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.base import Base


class Turn(Base):
    """Turn model for individual dialogue exchanges."""
    
    __tablename__ = "turns"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("core.sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("core.users.id"), nullable=True)
    turn_number = Column(Integer, nullable=False)
    role = Column(String, nullable=False)  # user, assistant (patient)
    text = Column(Text, nullable=False)
    audio_url = Column(String, nullable=True)  # URL to stored audio file
    metrics_json = Column(Text)  # JSON with turn-level metrics (empathy score, question type, etc.) - kept for backward compatibility
    spans_json = Column(Text, nullable=True)  # JSON with detected spans (EO, elicitation, response, SPIKES) with character offsets
    relations_json = Column(Text, nullable=True)  # JSON with span-relation links (will be populated in Part 2)
    spikes_stage = Column(String)  # SPIKES stage during this turn (single primary stage; multi-stage stored in spans_json)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="turns")
    
    def __repr__(self) -> str:
        return f"<Turn(id={self.id}, session_id={self.session_id}, turn={self.turn_number}, role={self.role})>"

