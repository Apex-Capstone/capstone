"""Session management service."""

from datetime import datetime

from sqlalchemy.orm import Session

from core.errors import NotFoundError
from domain.entities.session import Session as SessionEntity
from domain.models.sessions import (
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    TurnResponse,
)
from repositories.case_repo import CaseRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository


class SessionService:
    """Service for session operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.case_repo = CaseRepository(db)
        self.turn_repo = TurnRepository(db)
    
    @staticmethod
    def _row_to_dict(row) -> dict:
        # Only map real table columns -> values, avoiding SA's `.metadata`
        return {col.key: getattr(row, col.key) for col in row.__table__.columns}
    
    async def create_session(
        self,
        user_id: int,
        session_data: SessionCreate,
    ) -> SessionResponse:
        """Create a new session."""
        # Verify case exists
        case = self.case_repo.get_by_id(session_data.case_id)
        if not case:
            raise NotFoundError(f"Case with ID {session_data.case_id} not found")
        
        # Create session entity
        session = SessionEntity(
            user_id=user_id,
            case_id=session_data.case_id,
            state="active",
            current_spikes_stage="setting",
        )
        
        created_session = self.session_repo.create(session)
        return SessionResponse.model_validate(self._row_to_dict(created_session))
    
    async def get_session(self, session_id: int) -> SessionDetailResponse:
        """Get session with turns."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session with ID {session_id} not found")
        
        turns = self.turn_repo.get_by_session(session_id)
        
        return SessionDetailResponse(
            **SessionResponse.model_validate(self._row_to_dict(session)).model_dump(),
            turns=[TurnResponse.model_validate(self._row_to_dict(turn)) for turn in turns],
        )
    
    async def list_user_sessions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> SessionListResponse:
        """List sessions for a user."""
        sessions = self.session_repo.get_by_user(user_id, skip, limit)
        total = len(sessions)
        
        return SessionListResponse(
            sessions=[SessionResponse.model_validate(self._row_to_dict(s)) for s in sessions],
            total=total,
        )
    
    async def close_session(self, session_id: int) -> SessionResponse:
        """Close/complete a session."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session with ID {session_id} not found")
        
        session.state = "completed"
        session.ended_at = datetime.utcnow()
        
        if session.started_at:
            duration = (session.ended_at - session.started_at).total_seconds()
            session.duration_seconds = int(duration)
        
        updated_session = self.session_repo.update(session)
        return SessionResponse.model_validate(self._row_to_dict(updated_session))

