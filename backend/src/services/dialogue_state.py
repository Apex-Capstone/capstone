from typing import Any, List


class DialogueState:
    """In-memory dialogue state for a single session turn."""

    def __init__(self, session: Any) -> None:
        self.session_id = session.id

        self.current_stage = session.current_spikes_stage
        self.stage_history: List[str] = []

        self.emotion_spans: List[dict] = []
        self.empathy_opportunities: List[dict] = []
        self.addressed_opportunities: List[dict] = []

        self.question_types: List[str] = []

    def update_stage(self, stage: str) -> None:
        if stage and stage != self.current_stage:
            self.stage_history.append(stage)
            self.current_stage = stage

    def add_emotion_spans(self, spans: List[dict]) -> None:
        if not spans:
            return
        self.emotion_spans.extend(spans)

    def add_empathy_opportunity(self, span: dict) -> None:
        if not span:
            return
        self.empathy_opportunities.append(span)

    def add_question_type(self, question_type: str) -> None:
        if not question_type:
            return
        self.question_types.append(question_type)

