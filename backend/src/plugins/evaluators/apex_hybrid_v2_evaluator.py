from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models.sessions import FeedbackResponse
from plugins.registry import PluginRegistry
from services.scoring_service import ScoringService


class ApexHybridV2Evaluator:
    """
    Hybrid evaluator v2: rule-based core + three focused LLM reviews + 70/30 merge
    (ScoringService.generate_feedback_hybrid_v2).
    """

    name: str = "plugins.evaluators.apex_hybrid_v2_evaluator:ApexHybridV2Evaluator"
    version: str = "2.0"

    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        service = ScoringService(db)
        return await service.generate_feedback_hybrid_v2(session_id)


PluginRegistry.register_evaluator(ApexHybridV2Evaluator.name, ApexHybridV2Evaluator)
