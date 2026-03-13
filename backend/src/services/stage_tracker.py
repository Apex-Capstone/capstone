from typing import Optional

from config.logging import get_logger
from repositories.session_repo import SessionRepository


logger = get_logger(__name__)


class StageTracker:
    """Track and update SPIKES stages for a dialogue session."""

    STAGES = [
        "setting",    # Setting up the interview
        "perception", # Assessing patient's perception
        "invitation", # Obtaining invitation to share information
        "knowledge",  # Giving knowledge and information
        "emotion",    # Addressing emotions with empathy
        "strategy",   # Strategy, planning, and summary
    ]

    def __init__(self, session_repo: Optional[SessionRepository] = None) -> None:
        self.session_repo = session_repo

    def detect_stage(self, text: str, session) -> Optional[str]:
        """Detect the SPIKES stage for the given text and session.

        Uses simple keyword-based heuristics for v1 and enforces
        monotonic progression through the stage sequence.
        """
        text_lower = text.lower()
        current_stage = session.current_spikes_stage if session else None
        detected_stage: Optional[str] = None

        # Define phrase buckets per stage
        setting_cues = [
            "hello", "hi ", "hi,", "good morning", "good afternoon",
            "i'm dr", "i am dr",
            "is this still a good time", "is this a good time",
            "a good time to talk",
            "comfortable here", "would you prefer a quieter room", "can we talk here",
        ]
        perception_cues = [
            "what do you know", "what do you think", "how much do you know",
            "what have you been thinking", "what have you been thinking about",
            "what have you heard so far", "what have you been told",
            "how are you feeling about",
            "can you tell me what has been getting worse",
            "can you tell me what part feels the hardest",
            "can you tell me what", "tell me what symptoms",
        ]
        invitation_cues = [
            "would you like", "would you like more details",
            "would you like me to explain",
            "should i explain",
            "is it ok if i explain", "is it okay if i explain",
            "would it be alright if i explain", "would it be all right if i explain",
            "before we move on, is there anything else",
            "anything else you're hoping to understand",
            "anything important you haven't shared",
            "do you have any other questions",
        ]
        knowledge_cues = [
            "diagnosis", "results show", "the results show", "the scan shows",
            "let me walk through what we know so far",
            "let me walk through what we know",
            "i'll explain what tests can help",
            "i'll explain what tests", "what tests can help us understand",
        ]
        emotion_cues = [
            "i hear you",
            "i understand", "i understand how", "i understand that",
            "that sounds difficult",
            "it makes sense you'd feel", "it makes sense that you'd feel",
            "it makes sense that", "anyone would feel",
            "i'm sorry", "sorry that", "sorry it's been stressful",
        ]
        strategy_cues = [
            "here's our plan", "here is our plan",
            "next steps", "from here on", "going forward",
            "we'll check", "we will check",
            "we'll review", "we will review",
            "we'll support you", "i'll support you",
            "let's schedule", "let us schedule",
        ]

        # Collect all candidate stages with simple matching
        candidates: set[str] = set()
        if any(p in text_lower for p in setting_cues):
            candidates.add("setting")
        if any(p in text_lower for p in perception_cues):
            candidates.add("perception")
        if any(p in text_lower for p in invitation_cues):
            candidates.add("invitation")
        if any(p in text_lower for p in knowledge_cues):
            candidates.add("knowledge")
        if any(p in text_lower for p in emotion_cues):
            candidates.add("emotion")
        if any(p in text_lower for p in strategy_cues):
            candidates.add("strategy")

        # If we found any candidates, select one using precedence:
        # strategy > knowledge > invitation > emotion > perception > setting
        precedence = ["strategy", "knowledge", "invitation", "emotion", "perception", "setting"]
        for stage in precedence:
            if stage in candidates:
                detected_stage = stage
                break

        # If no explicit detection, fall back to current stage (if any), else None.
        if not detected_stage:
            detected_stage = current_stage

        new_stage = self.enforce_progression(current_stage, detected_stage) if detected_stage else detected_stage
        logger.info(f"SPIKES stage detected: {new_stage}")
        return new_stage

    def enforce_progression(self, current_stage: Optional[str], detected_stage: str) -> str:
        """Enforce monotonic progression through stages.

        Never regress to an earlier stage; if a lower stage is detected,
        keep the current stage.
        """
        if not current_stage:
            return detected_stage

        if current_stage not in self.STAGES or detected_stage not in self.STAGES:
            return detected_stage

        current_index = self.STAGES.index(current_stage)
        detected_index = self.STAGES.index(detected_stage)

        if detected_index < current_index:
            return current_stage

        return detected_stage

    def update_session_stage(self, session, stage: Optional[str]) -> None:
        """Persist the SPIKES stage on the session if it changed."""
        if not stage or stage == session.current_spikes_stage:
            return

        session.current_spikes_stage = stage

        # When used without a repository (e.g., in unit tests), skip persistence.
        if self.session_repo:
            self.session_repo.update(session)

