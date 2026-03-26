"""Session management service."""

import json

from sqlalchemy import exc as sa_exceptions
from sqlalchemy.orm import Session

from fastapi import HTTPException

from config.settings import get_settings
from core.errors import NotFoundError
from core.plugin_manager import _load_class_from_path
from core.time import utc_now
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

    @staticmethod
    def _resolve_turn_audio_url(turn_id: int, audio_url: str | None, audio_expires_at) -> str | None:
        if not audio_url:
            return None
        if audio_expires_at is not None and audio_expires_at <= utc_now():
            return None

        base_url = get_settings().public_base_url.rstrip("/")
        return f"{base_url}/v1/turns/{turn_id}/audio"

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

        # Resolve evaluator plugin at creation time: request override, else case, else settings.
        # Sessions are frozen to the evaluator in use when they were started.
        settings = get_settings()
        raw_request_eval = session_data.evaluator_plugin
        request_override: str | None = None
        if raw_request_eval is not None and str(raw_request_eval).strip():
            request_override = str(raw_request_eval).strip()
        case_override = getattr(case, "evaluator_plugin", None)
        if request_override:
            plugin_name: str | None = request_override
        elif case_override:
            plugin_name = case_override
        else:
            plugin_name = getattr(settings, "evaluator_plugin", None)

        evaluator_version: str | None = None
        if plugin_name:
            try:
                evaluator_cls = PluginRegistry.get_evaluator(plugin_name)
            except ValueError:
                # Explicit request or case override must exist in registry; do not auto-load.
                if request_override or case_override:
                    raise HTTPException(status_code=400, detail="Invalid evaluator plugin")
                # Backward compatibility: settings fallback only, load from settings path.
                evaluator_cls = _load_class_from_path(plugin_name)
                PluginRegistry.register_evaluator(plugin_name, evaluator_cls)

            evaluator_version = getattr(evaluator_cls, "version", None)
            # Freeze the plugin name as stored on the plugin class (registry key).
            plugin_name = getattr(evaluator_cls, "name", plugin_name)

        # Resolve patient model: case override else settings. Freeze name + version on session.
        patient_model_plugin: str | None = None
        patient_model_version: str | None = None
        case_patient = getattr(case, "patient_model_plugin", None)
        patient_name: str | None = case_patient if case_patient else getattr(settings, "patient_model_plugin", None)
        if patient_name:
            try:
                model_cls = PluginRegistry.get_patient_model(patient_name)
            except ValueError:
                if case_patient:
                    raise HTTPException(status_code=400, detail="Invalid plugin configuration")
                model_cls = _load_class_from_path(patient_name)
                PluginRegistry.register_patient_model(patient_name, model_cls)
            patient_model_plugin = getattr(model_cls, "name", patient_name)
            patient_model_version = getattr(model_cls, "version", None)

        # Resolve metrics plugins: case override else settings. Validate each and freeze list on session.
        metrics_list: list[str] = []
        case_metrics_override = False
        raw_case_metrics = getattr(case, "metrics_plugins", None)
        if isinstance(raw_case_metrics, str) and raw_case_metrics.strip():
            try:
                parsed = json.loads(raw_case_metrics)
                if isinstance(parsed, list):
                    metrics_list = [str(x) for x in parsed]
                    case_metrics_override = True
            except (json.JSONDecodeError, TypeError):
                pass
        if not metrics_list:
            metrics_list = list(getattr(settings, "metrics_plugins", []) or [])
        resolved_metrics_plugins: list[str] = []
        for name in metrics_list:
            if not name:
                continue
            try:
                metrics_cls = PluginRegistry.get_metrics_plugin(name)
            except ValueError:
                if case_metrics_override:
                    raise HTTPException(status_code=400, detail="Invalid plugin configuration")
                metrics_cls = _load_class_from_path(name)
                PluginRegistry.register_metrics_plugin(name, metrics_cls)
            resolved_metrics_plugins.append(getattr(metrics_cls, "name", name))
        metrics_plugins_json: str | None = (
            json.dumps(resolved_metrics_plugins) if resolved_metrics_plugins else None
        )

        # Create session entity
        session = SessionEntity(
            user_id=user_id,
            case_id=session_data.case_id,
            state="active",
            current_spikes_stage="setting",
            evaluator_plugin=plugin_name,
            evaluator_version=evaluator_version,
            patient_model_plugin=patient_model_plugin,
            patient_model_version=patient_model_version,
            metrics_plugins=metrics_plugins_json,
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
        turn_responses: list[TurnResponse] = []
        for turn in turns:
            turn_response = TurnResponse.model_validate(self._row_to_dict(turn))
            turn_responses.append(
                turn_response.model_copy(
                    update={
                        "audio_url": self._resolve_turn_audio_url(
                            turn_response.id,
                            turn_response.audio_url,
                            turn_response.audio_expires_at,
                        )
                    }
                )
            )

        return SessionDetailResponse(
            **session_response.model_dump(),
            turns=turn_responses,
        )
    
    async def list_user_sessions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        state: str | None = None,
    ) -> SessionListResponse:
        """List sessions for a user, optionally filtered by state."""
        sessions = self.session_repo.get_by_user(user_id, skip, limit, state=state)
        total = self.session_repo.count_by_user_and_state(user_id, state) if state else len(sessions)
        
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
        session.ended_at = utc_now()
        
        if session.started_at:
            duration = (session.ended_at - session.started_at).total_seconds()
            session.duration_seconds = int(duration)
        
        updated_session = self.session_repo.update(session)
        return self._session_to_response(updated_session)

