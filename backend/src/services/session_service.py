"""Session management service."""

from datetime import datetime

from sqlalchemy import exc as sa_exceptions
from sqlalchemy.orm import Session

from fastapi import HTTPException

from config.settings import get_settings
from core.errors import NotFoundError
from core.plugin_manager import _load_class_from_path
from domain.entities.session import Session as SessionEntity
from domain.models.sessions import (
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    TurnResponse,
)
from plugins.registry import PluginRegistry
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
        """Create a new session.

        Behaviour:
        - force_new=False: return the most recent open session for (user, case) if it exists,
          otherwise create one. Concurrent calls that race to create will be collapsed by the
          database unique constraint and this method will re-query and return the existing row.
        - force_new=True: always create a new session (callers must only use this when they
          truly want a new run, e.g. "Start New Session" in the UI).
        """
        # Verify case exists
        case = self.case_repo.get_by_id(session_data.case_id)
        if not case:
            raise NotFoundError(f"Case with ID {session_data.case_id} not found")

        # Reuse any existing open session for this case/user
        if not session_data.force_new:
            existing_session = self.session_repo.get_active_for_user_case(user_id, session_data.case_id)
            if existing_session:
                return self._session_to_response(existing_session, case_title=case.title)

        # Resolve evaluator plugin at creation time: case override else settings.
        # Sessions are frozen to the evaluator in use when they were started.
        settings = get_settings()
        case_override = getattr(case, "evaluator_plugin", None)
        plugin_name: str | None = case_override if case_override else getattr(settings, "evaluator_plugin", None)

        evaluator_version: str | None = None
        if plugin_name:
            try:
                evaluator_cls = PluginRegistry.get_evaluator(plugin_name)
            except ValueError:
                # Case override must exist in registry; do not auto-load.
                if case_override:
                    raise HTTPException(status_code=400, detail="Invalid evaluator plugin")
                # Backward compatibility: no case override, load from settings path.
                evaluator_cls = _load_class_from_path(plugin_name)
                PluginRegistry.register_evaluator(plugin_name, evaluator_cls)

            evaluator_version = getattr(evaluator_cls, "version", None)
            # Freeze the plugin name as stored on the plugin class (registry key).
            plugin_name = getattr(evaluator_cls, "name", plugin_name)

        # Create session entity
        session = SessionEntity(
            user_id=user_id,
            case_id=session_data.case_id,
            state="active",
            current_spikes_stage="setting",
            evaluator_plugin=plugin_name,
            evaluator_version=evaluator_version,
        )

        # Persist, handling potential uniqueness races for non-forced creation
        try:
            created_session = self.session_repo.create(session)
        except sa_exceptions.IntegrityError:
            # For force_new=True we intentionally bubble up integrity errors rather than
            # silently reusing, because callers explicitly asked for a new session.
            if session_data.force_new:
                raise

            # For non-forced creation, treat integrity errors as a signal that another
            # request created the open session first. Re-query and return that row.
            self.db.rollback()
            existing_session = self.session_repo.get_active_for_user_case(user_id, session_data.case_id)
            if not existing_session:
                # Fallback: if we truly cannot find it, re-raise so the caller sees the error.
                raise
            created_session = existing_session

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

