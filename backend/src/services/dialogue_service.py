"""Dialogue management service with SPIKES state machine."""

import json
import time
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from adapters.llm import LLMAdapter
from adapters.nlu import NLUAdapter
from adapters.storage.base import StorageAdapter
from config.logging import get_logger
from config.settings import get_settings
from core.errors import NotFoundError
from core.time import utc_now
from core.plugin_manager import _load_class_from_path
from interfaces.patient_model import PatientModel
from plugins.registry import PluginRegistry
from domain.entities.turn import Turn
from domain.models.sessions import TurnCreate, TurnResponse
from repositories.case_repo import CaseRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository
from services.stage_tracker import StageTracker
from services.nlu_pipeline import NLUPipeline
from services.dialogue_state import DialogueState
from services.patient_prompt_builder import PatientPromptBuilder
from services.patient_voice_profile import infer_patient_voice_profile
from services.turn_analysis import analyze_user_input, analyze_assistant_response

logger = get_logger(__name__)


class DialogueService:
    """Service for managing dialogue and SPIKES protocol."""
    
    # SPIKES protocol stages
    SPIKES_STAGES = [
        "setting",       # Setting up the interview
        "perception",    # Assessing patient's perception
        "invitation",    # Obtaining invitation to share information
        "knowledge",     # Giving knowledge and information
        "empathy",       # Addressing emotions with empathy
        "summary",       # Strategy and summary
    ]
    
    def __init__(
        self,
        db: Session,
        llm_adapter: LLMAdapter,
        nlu_adapter: NLUAdapter,
        tts_adapter=None,
        storage_adapter: StorageAdapter | None = None,
    ):
        self.db = db
        self.llm_adapter = llm_adapter
        self.nlu_adapter = nlu_adapter
        self.tts_adapter = tts_adapter
        self.storage_adapter = storage_adapter
        self.settings = get_settings()
        self.session_repo = SessionRepository(db)
        self.case_repo = CaseRepository(db)
        self.turn_repo = TurnRepository(db)
        self.stage_tracker = StageTracker(self.session_repo)
        # Consolidated NLU pipeline for dialogue analysis
        self.nlu_pipeline = NLUPipeline(
            span_detector=self.nlu_adapter,
            empathy_detector=self.nlu_adapter,
            question_classifier=self.nlu_adapter,
            tone_analyzer=self.nlu_adapter,
        )
        self.patient_prompt_builder = PatientPromptBuilder()
    
    async def process_user_turn(
        self,
        session_id: int,
        turn_data: TurnCreate,
    ) -> TurnResponse:
        """Process user's turn and generate response."""
        # Get session and case
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session {session_id} not found")
        
        case = self.case_repo.get_by_id(session.case_id)
        if not case:
            raise NotFoundError(f"Case {session.case_id} not found")
        
        # Get turn number
        turn_number = self.turn_repo.get_next_turn_number(session_id)

        # Initialize in-memory dialogue state for this turn
        state = DialogueState(session)

        # Build legacy-compatible metrics and spans from analysis
        user_metrics, user_spans = await analyze_user_input(
            self.nlu_pipeline,
            turn_data.text,
            voice_tone=turn_data.voice_tone,
        )

        # Track question type and emotion spans in state
        # (analysis already computed inside analyze_user_input)
        # For now we only keep state for patient model context; metrics/spans live on turns.

        # Detect and update SPIKES stage via StageTracker before LLM generation
        stage = self.stage_tracker.detect_stage(turn_data.text, session)
        self.stage_tracker.update_session_stage(session, stage)
        turn_spikes_stage = stage
        
        # Create user turn
        user_turn = Turn(
            session_id=session_id,
            turn_number=turn_number,
            role="user",
            text=turn_data.text,
            audio_url=turn_data.audio_url,
            metrics_json=json.dumps(user_metrics),  # kept for backward compatibility
            spans_json=json.dumps(user_spans) if user_spans else None,
            spikes_stage=turn_spikes_stage,
        )
        self.turn_repo.create(user_turn)
        
        # Generate patient response with latency tracking via PatientModel plugin
        conversation_history = self._get_conversation_history(session_id)

        # Enrich dialogue state with additional context expected by PatientModel plugins
        state.case = case
        state.session = session
        state.conversation_history = conversation_history

        patient_model = self._instantiate_patient_model(session)

        # Track latency for patient model call
        start_time = time.time()
        patient_response = await patient_model.generate_response(
            state=state,
            clinician_input=turn_data.text,
        )
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Analyze assistant (patient) response (EO detection)
        assistant_metrics, assistant_spans = await analyze_assistant_response(
            self.nlu_adapter,
            patient_response,
            user_turn,
            latency_ms,
        )

        assistant_audio_url = None
        assistant_audio_expires_at = None
        if turn_data.enable_tts and self.tts_adapter is not None and self.storage_adapter is not None:
            assistant_audio_url, assistant_audio_expires_at = await self._create_assistant_audio(
                session_id=session_id,
                response_text=patient_response,
                case=case,
            )
        
        # Create assistant turn
        assistant_turn = Turn(
            session_id=session_id,
            turn_number=turn_number + 1,
            role="assistant",
            text=patient_response,
            audio_url=assistant_audio_url,
            audio_expires_at=assistant_audio_expires_at,
            metrics_json=json.dumps(assistant_metrics),  # kept for backward compatibility
            spans_json=json.dumps(assistant_spans) if assistant_spans else None,
            spikes_stage=session.current_spikes_stage,
        )
        created_turn = self.turn_repo.create(assistant_turn)
        
        return TurnResponse.model_validate(created_turn)

    def _instantiate_patient_model(self, session) -> PatientModel:
        """Resolve PatientModel from session freeze, then settings; register on demand."""
        plugin_key: str | None = getattr(session, "patient_model_plugin", None)
        if not plugin_key:
            plugin_key = getattr(self.settings, "patient_model_plugin", None)
        if not plugin_key:
            raise RuntimeError(
                "No patient model plugin configured (session.patient_model_plugin and "
                "settings.patient_model_plugin are both empty)."
            )
        try:
            plugin_cls = PluginRegistry.get_patient_model(plugin_key)
        except ValueError:
            plugin_cls = _load_class_from_path(plugin_key)
            PluginRegistry.register_patient_model(plugin_key, plugin_cls)
        return plugin_cls()  # type: ignore[return-value]

    def _get_conversation_history(self, session_id: int) -> list[dict[str, str]]:
        """Get conversation history for context."""
        turns = self.turn_repo.get_by_session(session_id)
        return [
            {"role": turn.role, "content": turn.text}
            for turn in turns
        ]

    async def _create_assistant_audio(
        self,
        session_id: int,
        response_text: str,
        case,
    ) -> tuple[str | None, datetime | None]:
        """Synthesize assistant speech and persist it, without blocking text replies on failure."""
        try:
            voice_profile = infer_patient_voice_profile(
                case,
                base_instructions=self.settings.openai_tts_instructions,
            )
            tts_result = await self.tts_adapter.synthesize_speech(
                response_text,
                voice_id=voice_profile.voice_id,
                instructions=voice_profile.instructions,
            )
            if not tts_result.audio_data:
                logger.warning("TTS returned empty audio payload for session %s", session_id)
                return None, None

            object_key = f"sessions/{session_id}/assistant/{uuid4().hex}.{tts_result.file_extension}"
            stored_key = await self.storage_adapter.put_file(
                tts_result.audio_data,
                object_key,
                content_type=tts_result.content_type,
            )
            expires_at = utc_now() + timedelta(seconds=self.settings.assistant_audio_ttl_seconds)
            return stored_key, expires_at
        except Exception as exc:
            logger.warning("Skipping assistant TTS for session %s: %s", session_id, exc)
            return None, None
    
    async def _update_spikes_stage(
        self,
        session,
        conversation_history: list[dict[str, str]],
    ) -> None:
        """Update SPIKES stage based on conversation content."""
        # Get the last user (clinician) turn to detect stage from content
        last_user_turn = None
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                last_user_turn = msg.get("content", "")
                break
        
        if last_user_turn:
            # Analyze the last user turn for SPIKES stage
            elicitation_spans = await self.nlu_adapter.detect_elicitation_spans(last_user_turn)
            response_spans = await self.nlu_adapter.detect_response_spans(last_user_turn)
            
            # Use span detector to detect SPIKES stage
            from adapters.nlu.span_detector import SpanDetector
            span_detector = SpanDetector()
            detected_stage = span_detector.detect_spikes_stage(
                last_user_turn,
                has_elicitations=len(elicitation_spans) > 0,
                has_responses=len(response_spans) > 0,
            )
            
            if detected_stage:
                # Only update if we detected a clear stage
                # Also check progression: don't go backwards unless it's empathy (can occur multiple times)
                current_index = self.SPIKES_STAGES.index(session.current_spikes_stage) if session.current_spikes_stage in self.SPIKES_STAGES else 0
                detected_index = self.SPIKES_STAGES.index(detected_stage) if detected_stage in self.SPIKES_STAGES else current_index
                
                # Allow progression forward or staying at empathy/summary
                if detected_index >= current_index or detected_stage in ["empathy", "summary"]:
                    session.current_spikes_stage = detected_stage
                    self.session_repo.update(session)
                    logger.info(f"Session {session.id} updated to stage: {detected_stage} (detected from content)")
                    return
        
        # Fallback: simple rule-based progression if no content-based detection
        turn_count = len(conversation_history)
        stage_index = min(turn_count // 6, len(self.SPIKES_STAGES) - 1)
        new_stage = self.SPIKES_STAGES[stage_index]
        if session.current_spikes_stage != new_stage:
            session.current_spikes_stage = new_stage
            self.session_repo.update(session)
            logger.info(f"Session {session.id} advanced to stage: {new_stage} (fallback rule)")

