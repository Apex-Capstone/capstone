"""Sessions controller/router."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from adapters.asr.whisper_adapter import WhisperAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from adapters.storage.s3_storage import S3StorageAdapter
from core.deps import get_current_user, get_db
from domain.entities.user import User
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


@router.post("/{session_id}:close", response_model=FeedbackResponse)
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
    return await scoring_service.generate_feedback(session_id)


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

