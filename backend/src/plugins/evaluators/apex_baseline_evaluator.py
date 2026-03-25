from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models.sessions import FeedbackResponse
from plugins.registry import PluginRegistry
from services.scoring_service import ScoringService


class ApexBaselineEvaluator:
    """Rule-only evaluator: delegates to ScoringService.generate_feedback_rule_only (no LLM)."""

    name: str = "plugins.evaluators.apex_baseline_evaluator:ApexBaselineEvaluator"
    version: str = "1.0"

    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        service = ScoringService(db)
        return await service.generate_feedback_rule_only(session_id)


PluginRegistry.register_evaluator(ApexBaselineEvaluator.name, ApexBaselineEvaluator)
