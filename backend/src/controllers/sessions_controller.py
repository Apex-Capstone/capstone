"""Sessions controller/router."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from adapters.asr.whisper_adapter import WhisperAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from adapters.storage.s3_storage import S3StorageAdapter
from core.deps import get_current_user, get_db
from core.errors import AuthorizationError, NotFoundError
from domain.entities.user import User
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from domain.models.sessions import (
    FeedbackResponse,
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    TurnCreate,
    TurnResponse,
)
from services.dialogue_service import DialogueService
from services.scoring_service import ScoringService
from services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _deserialize_json_field(value: str | None) -> dict | list | None:
    """Deserialize JSON string to dict/list, or return None."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    # If already dict/list, return as-is (shouldn't happen, but safe)
    return value if isinstance(value, (dict, list)) else None


class TurnResponseWithAudio(BaseModel):
    """Turn response with patient reply and audio."""
    turn: TurnResponse
    patient_reply: str
    audio_url: str | None = None
    spikes_stage: str | None = None


class TurnListResponse(BaseModel):
    """Paginated turn list."""
    turns: list[TurnResponse]
    total: int
    skip: int
    limit: int


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    session_data: SessionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create a new session for a case."""
    session_service = SessionService(db)
    return await session_service.create_session(current_user.id, session_data)


@router.post("/{session_id}/turns", response_model=TurnResponseWithAudio)
async def submit_turn(
    session_id: int,
    turn_data: TurnCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Submit trainee turn text; returns patient reply and updated SPIKES stage."""
    # Initialize services
    llm_adapter = OpenAIAdapter()
    nlu_adapter = SimpleRuleNLU()
    dialogue_service = DialogueService(db, llm_adapter, nlu_adapter)
    
    # Process turn and get patient response
    patient_turn = await dialogue_service.process_user_turn(session_id, turn_data)
    
    # Get updated session for SPIKES stage
    session_service = SessionService(db)
    session_detail = await session_service.get_session(session_id)
    
    return TurnResponseWithAudio(
        turn=patient_turn,
        patient_reply=patient_turn.text,
        audio_url=patient_turn.audio_url,
        spikes_stage=session_detail.current_spikes_stage,
    )


@router.post("/{session_id}/audio", response_model=TurnResponseWithAudio)
async def submit_audio_turn(
    session_id: int,
    audio_file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Upload audio file (wav/ogg/mp3). Server performs ASR and processes as turn."""
    # Read audio file
    audio_data = await audio_file.read()
    
    # Transcribe with ASR
    asr_adapter = WhisperAdapter()
    transcribed_text = await asr_adapter.transcribe_audio(
        audio_data,
        audio_format=audio_file.filename.split(".")[-1] if audio_file.filename else "wav",
    )
    
    # Store audio file
    storage_adapter = S3StorageAdapter()
    audio_url = await storage_adapter.put_file(
        audio_data,
        f"sessions/{session_id}/{audio_file.filename}",
        content_type=audio_file.content_type or "audio/wav",
    )
    
    # Process as turn
    turn_data = TurnCreate(text=transcribed_text, audio_url=audio_url)
    
    # Initialize dialogue service
    llm_adapter = OpenAIAdapter()
    nlu_adapter = SimpleRuleNLU()
    dialogue_service = DialogueService(db, llm_adapter, nlu_adapter)
    
    # Process turn
    patient_turn = await dialogue_service.process_user_turn(session_id, turn_data)
    
    # Get updated session
    session_service = SessionService(db)
    session_detail = await session_service.get_session(session_id)
    
    return TurnResponseWithAudio(
        turn=patient_turn,
        patient_reply=patient_turn.text,
        audio_url=patient_turn.audio_url,
        spikes_stage=session_detail.current_spikes_stage,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get session detail (state, metrics snapshot)."""
    session_service = SessionService(db)
    return await session_service.get_session(session_id)


@router.get("/{session_id}/turns", response_model=TurnListResponse)
async def get_session_turns(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """Get paginated transcript of session turns."""
    from repositories.turn_repo import TurnRepository
    
    turn_repo = TurnRepository(db)
    turns = turn_repo.get_by_session(session_id, skip=skip, limit=limit)
    total_turns = turn_repo.get_by_session(session_id)  # Get all for count
    
    return TurnListResponse(
        turns=[TurnResponse.model_validate(turn) for turn in turns],
        total=len(total_turns),
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{session_id}:close",
    response_model=FeedbackResponse,
    response_model_exclude_none=True,  # Exclude None values from response
)
async def close_session_and_get_feedback(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Close session and finalize feedback."""
    # Close session
    session_service = SessionService(db)
    await session_service.close_session(session_id)
    
    # Generate and return feedback
    scoring_service = ScoringService(db)
    feedback = await scoring_service.generate_feedback(session_id)
    # Post-process to remove empty values (FastAPI will use model_dump)
    return feedback


@router.get(
    "/{session_id}/feedback",
    response_model=FeedbackResponse,
    response_model_exclude_none=True,  # Exclude None values from response
)
async def get_session_feedback(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get feedback for a closed session."""
    # Get session and verify it exists
    session_repo = SessionRepository(db)
    session = session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Session with ID {session_id} not found")
    
    # Verify session ownership
    if session.user_id != current_user.id:
        raise AuthorizationError("You do not have permission to access this session's feedback")
    
    # Get feedback
    feedback_repo = FeedbackRepository(db)
    feedback = feedback_repo.get_by_session(session_id)
    if not feedback:
        raise NotFoundError(f"Feedback not found for session {session_id}. Session may not be closed yet.")
    
    # Deserialize JSON fields before creating response (matching scoring_service pattern)
    feedback.eo_counts_by_dimension = _deserialize_json_field(feedback.eo_counts_by_dimension)
    feedback.elicitation_counts_by_type = _deserialize_json_field(feedback.elicitation_counts_by_type)
    feedback.response_counts_by_type = _deserialize_json_field(feedback.response_counts_by_type)
    feedback.linkage_stats = _deserialize_json_field(feedback.linkage_stats)
    feedback.missed_opportunities_by_dimension = _deserialize_json_field(feedback.missed_opportunities_by_dimension)
    feedback.eo_to_elicitation_links = _deserialize_json_field(feedback.eo_to_elicitation_links)
    feedback.eo_to_response_links = _deserialize_json_field(feedback.eo_to_response_links)
    feedback.missed_opportunities = _deserialize_json_field(feedback.missed_opportunities)
    feedback.spikes_coverage = _deserialize_json_field(feedback.spikes_coverage)
    feedback.spikes_timestamps = _deserialize_json_field(feedback.spikes_timestamps)
    feedback.spikes_strategies = _deserialize_json_field(feedback.spikes_strategies)
    feedback.question_breakdown = _deserialize_json_field(feedback.question_breakdown)
    feedback.bias_probe_info = _deserialize_json_field(feedback.bias_probe_info)
    feedback.evaluator_meta = _deserialize_json_field(feedback.evaluator_meta)
    
    # Set span-level fields to None (computed during generation, not stored)
    feedback.eo_spans = None
    feedback.elicitation_spans = None
    feedback.response_spans = None
    feedback.relations = None
    
    # Create response and let exclude_none=True and _remove_empty_values handle cleanup
    return FeedbackResponse.model_validate(feedback)


@router.get("", response_model=SessionListResponse)
async def list_user_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """List current user's sessions."""
    session_service = SessionService(db)
    return await session_service.list_user_sessions(current_user.id, skip, limit)

