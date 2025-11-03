"""Dialogue management service with SPIKES state machine."""

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
        
        # Analyze user input
        metrics = await self._analyze_user_input(turn_data.text)
        
        # Create user turn
        user_turn = Turn(
            session_id=session_id,
            turn_number=turn_number,
            role="user",
            text=turn_data.text,
            audio_url=turn_data.audio_url,
            metrics_json=str(metrics),
            spikes_stage=session.current_spikes_stage,
        )
        self.turn_repo.create(user_turn)
        
        # Generate patient response
        conversation_history = self._get_conversation_history(session_id)
        patient_response = await self.llm_adapter.generate_patient_response(
            case_script=case.script,
            conversation_history=conversation_history,
            current_spikes_stage=session.current_spikes_stage or "setting",
        )
        
        # Create assistant turn
        assistant_turn = Turn(
            session_id=session_id,
            turn_number=turn_number + 1,
            role="assistant",
            text=patient_response,
            spikes_stage=session.current_spikes_stage,
        )
        created_turn = self.turn_repo.create(assistant_turn)
        
        # Update SPIKES stage if needed
        await self._update_spikes_stage(session, conversation_history)
        
        return TurnResponse.model_validate(created_turn)
    
    async def _analyze_user_input(self, text: str) -> dict:
        """Analyze user input for metrics."""
        empathy = await self.nlu_adapter.detect_empathy_cues(text)
        question_type = await self.nlu_adapter.classify_question_type(text)
        
        return {
            "empathy": empathy,
            "question_type": question_type,
        }
    
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
        """Update SPIKES stage based on conversation progress."""
        # Simple rule: advance stage after 3-4 exchanges per stage
        turn_count = len(conversation_history)
        stage_index = min(turn_count // 6, len(self.SPIKES_STAGES) - 1)
        
        new_stage = self.SPIKES_STAGES[stage_index]
        if session.current_spikes_stage != new_stage:
            session.current_spikes_stage = new_stage
            self.session_repo.update(session)
            logger.info(f"Session {session.id} advanced to stage: {new_stage}")

