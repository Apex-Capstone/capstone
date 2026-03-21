"""Turn repository for database operations."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from domain.entities.turn import Turn


class TurnRepository:
    """Repository for Turn entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, turn_id: int) -> Optional[Turn]:
        """Get turn by ID."""
        return self.db.query(Turn).filter(Turn.id == turn_id).first()
    
    def get_by_session(
        self,
        session_id: int,
        skip: int = 0,
        limit: int = 1000,
    ) -> list[Turn]:
        """Get all turns for a session."""
        return (
            self.db.query(Turn)
            .filter(Turn.session_id == session_id)
            .order_by(Turn.turn_number.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(self, turn: Turn) -> Turn:
        """Create a new turn."""
        self.db.add(turn)
        self.db.commit()
        self.db.refresh(turn)
        return turn
    
    def update(self, turn: Turn) -> Turn:
        """Update an existing turn."""
        self.db.commit()
        self.db.refresh(turn)
        return turn
    
    def delete(self, turn_id: int) -> bool:
        """Delete a turn by ID."""
        turn = self.get_by_id(turn_id)
        if turn:
            self.db.delete(turn)
            self.db.commit()
            return True
        return False
    
    def get_next_turn_number(self, session_id: int) -> int:
        """Get the next turn number for a session."""
        from sqlalchemy import func
        
        max_turn = (
            self.db.query(func.max(Turn.turn_number))
            .filter(Turn.session_id == session_id)
            .scalar()
        )
        return (max_turn or 0) + 1
    
    def get_by_session_and_number(self, session_id: int, turn_number: int) -> Optional[Turn]:
        """Get turn by session ID and turn number."""
        return (
            self.db.query(Turn)
            .filter(Turn.session_id == session_id, Turn.turn_number == turn_number)
            .first()
        )

    def get_expired_assistant_audio(
        self,
        cutoff: datetime,
        limit: int | None = None,
    ) -> list[Turn]:
        """Get assistant turns with expired persisted audio."""
        query = (
            self.db.query(Turn)
            .filter(
                Turn.role == "assistant",
                Turn.audio_url.isnot(None),
                Turn.audio_expires_at.isnot(None),
                Turn.audio_expires_at <= cutoff,
            )
            .order_by(Turn.audio_expires_at.asc())
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

