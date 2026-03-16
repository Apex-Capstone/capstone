from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models.sessions import FeedbackResponse
from services.scoring_service import ScoringService


class ApexHybridEvaluator:
    """
    Default Evaluator plugin that delegates to the existing ScoringService.

    This preserves current scoring behavior while exposing it through the
    Evaluator interface so it can be swapped via the plugin manager.
    """

    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        service = ScoringService(db)
        return await service.generate_feedback(session_id)

