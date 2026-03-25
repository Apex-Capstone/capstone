"""Feedback entity model (expanded, theory-grounded)."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text, String, Boolean
from sqlalchemy.orm import relationship

# Prefer JSONB on Postgres; fall back to Text (serialized JSON) elsewhere.

JSONType = Text  # store stringified JSON

from db.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)

    # Aggregate scores (UI-facing, 0-100 unless noted)
    empathy_score = Column(Float, default=0.0)              # UI empathy score (0-100)
    communication_score = Column(Float, nullable=True)      # UI communication score (0-100)
<<<<<<< HEAD
    clinical_reasoning_score = Column(Float, nullable=True)  # legacy DB column; not exposed in FeedbackResponse
    professionalism_score = Column(Float, nullable=True)  # legacy DB column; not exposed in FeedbackResponse
    spikes_completion_score = Column(Float, default=0.0)    # SPIKES completion metric (0-10)
=======
    clinical_reasoning_score = Column(Float, nullable=True) # UI clinical reasoning score (0-100)
    professionalism_score = Column(Float, nullable=True)    # UI professionalism score (0-100)
    spikes_completion_score = Column(Float, default=0.0)    # SPIKES completion metric (0-100)
>>>>>>> origin/staging
    overall_score = Column(Float, default=0.0)              # weighted blend (0-100)

    # ---- AFCE-structured empathy metrics
    eo_counts_by_dimension = Column(JSONType, nullable=True)  # {"Feeling": {"explicit": int, "implicit": int}, "Judgment": {...}, "Appreciation": {...}}
    elicitation_counts_by_type = Column(JSONType, nullable=True)  # {"direct": {"Feeling": int, "Judgment": int, "Appreciation": int}, "indirect": {...}}
    response_counts_by_type = Column(JSONType, nullable=True)  # {"understanding": int, "sharing": int, "acceptance": int}
    
    # ---- Legacy empathy metrics (kept for backward compatibility, stop computing)
    eo_counts = Column(JSONType, nullable=True)             # {"implicit": int, "explicit": int, "total": int} - deprecated
    elicitation_count = Column(Integer, nullable=True)      # deprecated - use elicitation_counts_by_type
    empathy_response_count = Column(Integer, nullable=True)  # deprecated - use response_counts_by_type
    linkage_stats = Column(JSONType, nullable=True)         # will be computed in Part 2 with span relations
    missed_opportunities = Column(JSONType, nullable=True)  # will be computed in Part 2 with span relations
    missed_opportunities_by_dimension = Column(JSONType, nullable=True)  # {"Feeling": int, "Judgment": int, "Appreciation": int} - will be computed in Part 2
    eo_to_elicitation_links = Column(JSONType, nullable=True)  # will be computed in Part 2
    eo_to_response_links = Column(JSONType, nullable=True)  # will be computed in Part 2
    response_types = Column(JSONType, nullable=True)        # deprecated - use response_counts_by_type

    # ---- SPIKES coverage (fine-grained)
    spikes_coverage = Column(JSONType)          # {"covered": ["S","P","I","K","E","S2"], "percent": float} - will update to exclude Setting in Part 2
    spikes_timestamps = Column(JSONType)        # {"S": {"start_ts": "...", "end_ts": "..."}, ...}
    spikes_strategies = Column(JSONType)        # {"stage": [{"strategy": "summarize", "turn": 17}]}

    # ---- Questioning & style
    question_breakdown = Column(JSONType)       # {"open": int, "closed": int, "eliciting": int, "ratio_open": float}
    
    # ---- Fairness & reliability scaffolding
    bias_probe_info = Column(JSONType)          # {"variant_id": "case123_female_55", "score_delta_from_control": {"empathy_score": -0.07}}
    evaluator_meta = Column(JSONType)           # {"rubric_version": "v1.0", "roles": ["nursing_prof", "comm_trainer"], "agreement": {"kappa": 0.82}}

    # ---- Performance hooks (optional)
    latency_ms_avg = Column(Float, default=0.0)

    # Existing textual feedback
    strengths = Column(Text)                    # AI-generated strengths
    areas_for_improvement = Column(Text)        # AI-generated improvement areas
    detailed_feedback = Column(Text)            # Comprehensive AI feedback

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, session_id={self.session_id}, overall_score={self.overall_score})>"
