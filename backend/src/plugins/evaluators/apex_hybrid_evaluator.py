from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models.sessions import FeedbackResponse
from services.scoring_service import ScoringService


class ApexHybridEvaluator:
    """
    Default Evaluator plugin that delegates to ScoringService's
    internal scoring implementation.
    """

    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        service = ScoringService(db)
        # Call the internal implementation directly to avoid plugin recursion.
        return await service._generate_feedback_impl(session_id)

