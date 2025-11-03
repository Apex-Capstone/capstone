"""Feedback entity model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from db.base import Base


class Feedback(Base):
    """Feedback model for session performance metrics."""
    
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    
    # Overall scores
    empathy_score = Column(Float, default=0.0)
    communication_score = Column(Float, default=0.0)
    spikes_completion_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    
    # Detailed metrics (stored as JSON)
    empathy_spikes = Column(Text)  # JSON: timestamps and scores of empathy moments
    question_ratios = Column(Text)  # JSON: open vs closed question ratios
    reassurance_moments = Column(Text)  # JSON: identified reassurance statements
    spikes_coverage = Column(Text)  # JSON: which SPIKES stages were covered
    
    # Textual feedback
    strengths = Column(Text)  # AI-generated strengths
    areas_for_improvement = Column(Text)  # AI-generated improvement areas
    detailed_feedback = Column(Text)  # Comprehensive AI feedback
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="feedback")
    
    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, session_id={self.session_id}, overall_score={self.overall_score})>"

