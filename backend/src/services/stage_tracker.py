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

        # setting: greetings or introductions
        if any(
            phrase in text_lower
            for phrase in ["hello", "hi ", "hi,", "good morning", "good afternoon", "i'm dr", "i am dr"]
        ):
            detected_stage = "setting"

        # perception: questions about patient's understanding and perspective
        elif any(
            phrase in text_lower
            for phrase in [
                "understand",
                "what do you know",
                "what do you think",
                "how much do you know",
                # additional perception / understanding probes
                "what have you been thinking",
                "what have you been thinking about",
                "what have you heard so far",
                "what have you been told",
                "how are you feeling about",
            ]
        ):
            detected_stage = "perception"

        # invitation: asking permission to explain
        elif any(
            phrase in text_lower
            for phrase in [
                "would you like",
                "should i explain",
                "is it ok if i explain",
                "can i tell you more",
                # additional invitation cues
                "would it be alright if i explain",
                "would it be all right if i explain",
                "would it be okay if i explain",
                "would you like me to explain",
                "would you like more details",
            ]
        ):
            detected_stage = "invitation"

        # knowledge: explanation statements
        elif any(
            phrase in text_lower
            for phrase in ["diagnosis", "results show", "the results show", "the scan shows"]
        ):
            detected_stage = "knowledge"

        # emotion: empathy statements
        elif any(
            phrase in text_lower
            for phrase in [
                "sorry",
                "i understand",
                "that must be difficult",
                "i can imagine this is hard",
                # additional emotion / empathy cues
                "i can see this is difficult",
                "this must be overwhelming",
                "i understand this is hard",
                "i know this is difficult",
            ]
        ):
            detected_stage = "emotion"

        # strategy: treatment planning
        elif any(
            phrase in text_lower
            for phrase in ["next steps", "treatment plan", "from here on", "going forward"]
        ):
            detected_stage = "strategy"

        # If no explicit detection, default to current or initial stage
        if not detected_stage:
            detected_stage = current_stage or "setting"

        new_stage = self.enforce_progression(current_stage, detected_stage)
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

