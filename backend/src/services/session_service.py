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

    def _session_to_response(self, session: SessionEntity, case_title: str | None = None) -> SessionResponse:
        data = self._row_to_dict(session)
        derived_title = case_title or (session.case.title if getattr(session, "case", None) else None)
        if derived_title:
            data["case_title"] = derived_title
        data["status"] = "closed" if data.get("ended_at") else "active"
        return SessionResponse.model_validate(data)
    
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
        # Reuse any existing open session for this case/user
        if not session_data.force_new:
            existing_session = self.session_repo.get_active_for_user_case(user_id, session_data.case_id)
            if existing_session:
                return self._session_to_response(existing_session, case_title=case.title)
        
        # Create session entity
        session = SessionEntity(
            user_id=user_id,
            case_id=session_data.case_id,
            state="active",
            current_spikes_stage="setting",
        )
        
        created_session = self.session_repo.create(session)
        return self._session_to_response(created_session, case_title=case.title)
    
    async def get_session(self, session_id: int) -> SessionDetailResponse:
        """Get session with turns."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session with ID {session_id} not found")
        
        turns = self.turn_repo.get_by_session(session_id)
        
        session_response = self._session_to_response(session)
        return SessionDetailResponse(
            **session_response.model_dump(),
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
            sessions=[self._session_to_response(s) for s in sessions],
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
        return self._session_to_response(updated_session)

