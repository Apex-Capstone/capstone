"""Session repository for database operations."""

from datetime import timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.time import utc_now
from domain.entities.case import Case as CaseEntity
from domain.entities.session import Session as SessionEntity


class SessionRepository:
    """Repository for Session entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, session_id: int) -> Optional[SessionEntity]:
        """Get session by ID."""
        return self.db.query(SessionEntity).filter(SessionEntity.id == session_id).first()
    
    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        state: str | None = None,
    ) -> list[SessionEntity]:
        """Get sessions for a user, optionally filtered by state."""
        q = self.db.query(SessionEntity).filter(SessionEntity.user_id == user_id)
        if state:
            q = q.filter(SessionEntity.state == state)
        return q.order_by(SessionEntity.started_at.desc()).offset(skip).limit(limit).all()

    def count_by_user_and_state(self, user_id: int, state: str) -> int:
        """Count sessions for a user in a given state."""
        return (
            self.db.query(SessionEntity)
            .filter(SessionEntity.user_id == user_id, SessionEntity.state == state)
            .count()
        )
    
    def get_by_case(
        self,
        case_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SessionEntity]:
        """Get all sessions for a case."""
        return (
            self.db.query(SessionEntity)
            .filter(SessionEntity.case_id == case_id)
            .order_by(SessionEntity.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_for_user_case(self, user_id: int, case_id: int) -> Optional[SessionEntity]:
        """Get the most recent non-completed session for a user/case."""
        return (
            self.db.query(SessionEntity)
            .filter(
                SessionEntity.user_id == user_id,
                SessionEntity.case_id == case_id,
                SessionEntity.state != "completed",
            )
            .order_by(SessionEntity.started_at.desc())
            .first()
        )
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[SessionEntity]:
        """Get all sessions with pagination."""
        return (
            self.db.query(SessionEntity)
            .order_by(SessionEntity.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(self, session: SessionEntity) -> SessionEntity:
        """Create a new session."""
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def update(self, session: SessionEntity) -> SessionEntity:
        """Update an existing session."""
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def delete(self, session_id: int) -> bool:
        """Delete a session by ID."""
        session = self.get_by_id(session_id)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False
    
    def count(self) -> int:
        """Count total sessions."""
        return self.db.query(SessionEntity).count()
    
    def count_by_state(self) -> dict[str, int]:
        """Count sessions by state."""
        results = (
            self.db.query(SessionEntity.state, func.count(SessionEntity.id))
            .group_by(SessionEntity.state)
            .all()
        )
        return {state: count for state, count in results}

    def count_by_case(self) -> dict[str, int]:
        """Count sessions per case, keyed by case title (joins cases for labels)."""
        results = (
            self.db.query(CaseEntity.title, func.count(SessionEntity.id))
            .select_from(SessionEntity)
            .join(CaseEntity, SessionEntity.case_id == CaseEntity.id)
            .group_by(CaseEntity.title)
            .all()
        )
        return {title: count for title, count in results}

    def get_average_duration(self) -> float:
        """Get average session duration in seconds."""
        result = self.db.query(func.avg(SessionEntity.duration_seconds)).scalar()
        return float(result) if result else 0.0
    
    def count_active_in_period(self, days: int = 30) -> int:
        """Count active sessions in the last N days."""
        cutoff_date = utc_now() - timedelta(days=days)
        return (
            self.db.query(SessionEntity)
            .filter(SessionEntity.started_at >= cutoff_date)
            .count()
        )

