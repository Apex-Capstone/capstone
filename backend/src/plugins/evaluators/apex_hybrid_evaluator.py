from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models.sessions import FeedbackResponse
from plugins.registry import PluginRegistry
from services.scoring_service import ScoringService


class ApexHybridEvaluator:
    """
    Hybrid evaluator: rule-based core + optional LLM merge (ScoringService.generate_feedback_hybrid).
    """

    # Registry key is intentionally the same as the default settings path
    # so that settings.evaluator_plugin can be used directly as a lookup key.
    name: str = "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator"
    version: str = "1.0"

    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        service = ScoringService(db)
        return await service.generate_feedback_hybrid(session_id)


# Register with the global plugin registry on import so that lookups are
# deterministic and do not rely on dynamic discovery.
PluginRegistry.register_evaluator(ApexHybridEvaluator.name, ApexHybridEvaluator)

