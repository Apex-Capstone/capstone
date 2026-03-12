"""Dialogue management service with SPIKES state machine."""

import json
import time
from sqlalchemy.orm import Session

from adapters.llm import LLMAdapter
from adapters.nlu import NLUAdapter
from config.logging import get_logger
from config.settings import get_settings
from core.errors import NotFoundError
from domain.entities.turn import Turn
from domain.models.sessions import TurnCreate, TurnResponse
from repositories.case_repo import CaseRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository
from services.stage_tracker import StageTracker
from services.nlu_pipeline import NLUPipeline
from services.dialogue_state import DialogueState
from services.patient_prompt_builder import PatientPromptBuilder

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
    ):
        self.db = db
        self.llm_adapter = llm_adapter
        self.nlu_adapter = nlu_adapter
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

        # Run NLU analysis through the unified pipeline
        analysis = await self.nlu_pipeline.analyze(turn_data.text)

        # Track question type and emotion spans in state
        state.add_question_type(analysis["question_type"])
        if analysis.get("emotion_spans"):
            state.add_emotion_spans(analysis["emotion_spans"])

        # Build legacy-compatible metrics and spans from analysis
        user_metrics, user_spans = await self._analyze_user_input(turn_data.text, analysis)

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
        
        # Generate patient response with latency tracking
        conversation_history = self._get_conversation_history(session_id)

        # Build patient prompt from case metadata and current SPIKES stage
        patient_context = self.patient_prompt_builder.build_prompt(
            case=case,
            stage=session.current_spikes_stage,
        )

        # Track latency for LLM call
        start_time = time.time()
        patient_response = await self.llm_adapter.generate_patient_response(
            case_script=patient_context,
            conversation_history=conversation_history,
            current_spikes_stage=session.current_spikes_stage or "setting",
        )
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Analyze assistant (patient) response (EO detection)
        assistant_metrics, assistant_spans = await self._analyze_assistant_response(
            patient_response,
            user_turn,
            latency_ms,
        )
        
        # Create assistant turn
        assistant_turn = Turn(
            session_id=session_id,
            turn_number=turn_number + 1,
            role="assistant",
            text=patient_response,
            metrics_json=json.dumps(assistant_metrics),  # kept for backward compatibility
            spans_json=json.dumps(assistant_spans) if assistant_spans else None,
            spikes_stage=session.current_spikes_stage,
        )
        created_turn = self.turn_repo.create(assistant_turn)
        
        return TurnResponse.model_validate(created_turn)
    
    async def _analyze_user_input(self, text: str, analysis: dict) -> tuple[dict, list]:
        """Analyze user input for metrics and spans.
        
        Returns:
            Tuple of (metrics_dict, spans_list) where spans_list contains elicitation and response spans.
        """
        empathy = analysis["empathy"]
        question_type = analysis["question_type"]
        tone = analysis["tone"]
        empathy_response = empathy.get("has_empathy", False)
        empathy_response_type = analysis["empathy_response_type"]

        # Combine elicitation and response spans for backward compatibility
        all_spans: list[dict] = []
        for span in analysis.get("elicitation_spans", []):
            span["span_type"] = "elicitation"
            all_spans.append(span)
        for span in analysis.get("response_spans", []):
            span["span_type"] = "response"
            all_spans.append(span)

        metrics = {
            "empathy": empathy,
            "question_type": question_type,
            "tone": tone,
            "empathy_response": empathy_response,
            "empathy_response_type": empathy_response_type,
        }

        return metrics, all_spans
    
    async def _analyze_assistant_response(
        self,
        text: str,
        previous_user_turn: Turn,
        latency_ms: float,
    ) -> tuple[dict, list]:
        """Analyze assistant (patient) response for metrics and spans.
        
        Returns:
            Tuple of (metrics_dict, spans_list) where spans_list contains EO spans
        """
        # Legacy EO detection for backward compatibility
        eo_analysis = await self.nlu_adapter.detect_empathy_opportunity(text)
        
        # AFCE-aligned EO span detection
        eo_spans = await self.nlu_adapter.detect_eo_spans(text)
        
        # Add span_type to each EO span
        all_spans = []
        for span in eo_spans:
            span["span_type"] = "eo"
            all_spans.append(span)
        
        # Note: Missed opportunity detection will be handled retrospectively in scoring_service (Part 2)
        # based on whether the next user turn shows empathy after this assistant turn presents an EO
        
        metrics = {
            "empathy_opportunity_type": eo_analysis.get("empathy_opportunity_type"),
            "empathy_opportunity": eo_analysis.get("empathy_opportunity", False),
            "latency_ms": latency_ms,
        }
        
        return metrics, all_spans
    
    def _get_conversation_history(self, session_id: int) -> list[dict[str, str]]:
        """Get conversation history for context."""
        turns = self.turn_repo.get_by_session(session_id)
        return [
            {"role": turn.role, "content": turn.text}
            for turn in turns
        ]
    
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

