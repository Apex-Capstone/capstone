"""Case entity model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from db.base import Base


class Case(Base):
    """Case model for simulation scenarios."""
    
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    script = Column(Text, nullable=False)  # Detailed scenario script
    objectives = Column(Text)  # JSON or text describing learning objectives
    difficulty_level = Column(String)  # beginner, intermediate, advanced
    category = Column(String)  # e.g., oncology, pediatrics, etc.
    patient_background = Column(Text)  # Patient history and context
    expected_spikes_flow = Column(Text)  # JSON describing expected SPIKES progression
    evaluator_plugin = Column(String, nullable=True)  # Optional case-level evaluator override (registry key)
    patient_model_plugin = Column(String, nullable=True)  # Optional case-level patient model override (registry key)
    metrics_plugins = Column(Text, nullable=True)  # JSON array of metrics plugin names, e.g. ["plugin.name:Class"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="case", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Case(id={self.id}, title={self.title}, difficulty={self.difficulty_level})>"

