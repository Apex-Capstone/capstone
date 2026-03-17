from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models.sessions import FeedbackResponse
from plugins.registry import PluginRegistry
from services.scoring_service import ScoringService


class ApexHybridEvaluator:
    """
    Default Evaluator plugin that delegates to ScoringService's
    internal scoring implementation.
    """

    # Registry key is intentionally the same as the default settings path
    # so that settings.evaluator_plugin can be used directly as a lookup key.
    name: str = "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator"
    version: str = "1.0"

    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        service = ScoringService(db)
        # Call the internal implementation directly to avoid plugin recursion.
        return await service._generate_feedback_impl(session_id)


# Register with the global plugin registry on import so that lookups are
# deterministic and do not rely on dynamic discovery.
PluginRegistry.register_evaluator(ApexHybridEvaluator.name, ApexHybridEvaluator)

