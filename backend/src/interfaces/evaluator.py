from __future__ import annotations

from typing import Protocol

from domain.models.sessions import FeedbackResponse


class Evaluator(Protocol):
    async def evaluate(self, db, session_id: int) -> FeedbackResponse:
        """Evaluate a completed session and return a FeedbackResponse."""
        ...

