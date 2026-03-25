"""Feedback repository for database operations."""

from collections import defaultdict
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from domain.entities.feedback import Feedback


class FeedbackRepository:
    """Repository for Feedback entity operations."""
    
    def __init__(self, db: Session):
        self.db = db

    def _serialize_json_fields(self, feedback: Feedback) -> None:
        """Ensure JSON-ish fields are stored as strings (for SQLite compatibility).

        Feedback uses Text columns (JSONType) for many dict/list fields. When running
        against SQLite, we must not persist raw dict/list objects. This helper
        defensively json-serializes any such values. On Postgres (where Text is also
        acceptable for pre-serialized JSON), this is a no-op behavior change.
        """
        import json

        json_fields: tuple[str, ...] = (
            "eo_counts_by_dimension",
            "elicitation_counts_by_type",
            "response_counts_by_type",
            "eo_counts",
            "linkage_stats",
            "missed_opportunities",
            "missed_opportunities_by_dimension",
            "eo_to_elicitation_links",
            "eo_to_response_links",
            "response_types",
            "spikes_coverage",
            "spikes_timestamps",
            "spikes_strategies",
            "question_breakdown",
            "bias_probe_info",
            "evaluator_meta",
        )

        for field in json_fields:
            value: Any = getattr(feedback, field, None)
            if value is None:
                continue
            # If already a string, assume it's serialized JSON
            if isinstance(value, str):
                continue
            # For dict/list (or other JSON-serializable objects), serialize
            try:
                serialized = json.dumps(value)
            except TypeError:
                # Best-effort: fall back to repr() to avoid breaking persistence
                serialized = json.dumps(repr(value))
            setattr(feedback, field, serialized)
    
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
        self._serialize_json_fields(feedback)
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def update(self, feedback: Feedback) -> Feedback:
        """Update existing feedback."""
        self._serialize_json_fields(feedback)
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

    def get_average_overall_by_month(self) -> list[dict[str, Any]]:
        """Average overall_score per calendar month from feedback.created_at (YYYY-MM keys)."""
        rows = (
            self.db.query(Feedback.created_at, Feedback.overall_score)
            .filter(Feedback.created_at.isnot(None))
            .all()
        )
        sums: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        for created_at, overall_score in rows:
            if overall_score is None:
                continue
            key = created_at.strftime("%Y-%m")
            sums[key] += float(overall_score)
            counts[key] += 1
        out: list[dict[str, Any]] = []
        for month in sorted(sums.keys()):
            n = counts[month]
            if n == 0:
                continue
            out.append({"month": month, "score": round(sums[month] / n, 2)})
        return out

