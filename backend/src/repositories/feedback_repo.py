"""Feedback repository for database operations."""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from domain.entities.feedback import Feedback


class FeedbackRepository:
    """Repository for Feedback entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, feedback_id: int) -> Optional[Feedback]:
        """Get feedback by ID."""
        return self.db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    def get_by_session(self, session_id: int) -> Optional[Feedback]:
        """Get feedback for a session."""
        return self.db.query(Feedback).filter(Feedback.session_id == session_id).first()
    
    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Feedback]:
        """Get all feedback for a user's sessions."""
        from domain.entities.session import Session as SessionEntity
        
        return (
            self.db.query(Feedback)
            .join(SessionEntity)
            .filter(SessionEntity.user_id == user_id)
            .order_by(Feedback.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(self, feedback: Feedback) -> Feedback:
        """Create new feedback."""
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def update(self, feedback: Feedback) -> Feedback:
        """Update existing feedback."""
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def delete(self, feedback_id: int) -> bool:
        """Delete feedback by ID."""
        feedback = self.get_by_id(feedback_id)
        if feedback:
            self.db.delete(feedback)
            self.db.commit()
            return True
        return False
    
    def get_average_scores(self) -> dict[str, float]:
        """Get average scores across all feedback."""
        result = self.db.query(
            func.avg(Feedback.empathy_score).label("empathy"),
            func.avg(Feedback.communication_score).label("communication"),
            func.avg(Feedback.spikes_completion_score).label("spikes"),
            func.avg(Feedback.overall_score).label("overall"),
        ).first()
        
        if result:
            return {
                "empathy": float(result.empathy or 0),
                "communication": float(result.communication or 0),
                "spikes": float(result.spikes or 0),
                "overall": float(result.overall or 0),
            }
        return {
            "empathy": 0.0,
            "communication": 0.0,
            "spikes": 0.0,
            "overall": 0.0,
        }

