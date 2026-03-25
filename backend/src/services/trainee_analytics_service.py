"""Service for trainee-facing analytics views."""

import json
from typing import Any

from sqlalchemy.orm import Session

from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.models.analytics import TraineeSessionAnalytics


class TraineeAnalyticsService:
    """Service for personal session analytics."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _parse_json(value: Any) -> dict[str, Any] | None:
        """Parse JSON-ish text safely into a dict."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return None
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except (TypeError, json.JSONDecodeError):
            return None

    def get_user_session_analytics(self, user_id: int) -> list[TraineeSessionAnalytics]:
        """Return completed sessions plus feedback metrics for one user."""
        rows = (
            self.db.query(SessionEntity, Feedback)
            .join(Feedback, Feedback.session_id == SessionEntity.id)
            .filter(SessionEntity.user_id == user_id, SessionEntity.state == "completed")
            .all()
        )

        out: list[TraineeSessionAnalytics] = []
        for session, feedback in rows:
            spikes_coverage = self._parse_json(feedback.spikes_coverage)
            linkage_stats = self._parse_json(feedback.linkage_stats)

            spikes_percent_raw = 0.0
            if spikes_coverage:
                spikes_percent_raw = float(spikes_coverage.get("percent") or 0.0)
            spikes_coverage_percent = max(0.0, min(100.0, spikes_percent_raw * 100.0))

            spikes_stages_covered: list[str] | None = None
            if spikes_coverage:
                raw_covered = spikes_coverage.get("covered")
                if isinstance(raw_covered, list) and raw_covered:
                    spikes_stages_covered = [str(x) for x in raw_covered if x is not None]

            eo_addressed_rate: float | None = None
            if linkage_stats and linkage_stats.get("addressed_rate") is not None:
                eo_addressed_rate = max(
                    0.0,
                    min(100.0, float(linkage_stats.get("addressed_rate") or 0.0) * 100.0),
                )

            out.append(
                TraineeSessionAnalytics(
                    session_id=session.id,
                    case_id=session.case_id,
                    case_title=session.case.title if session.case and session.case.title else f"Case #{session.case_id}",
                    empathy_score=float(feedback.empathy_score or 0.0),
                    communication_score=float(feedback.communication_score or 0.0),
                    clinical_score=float(feedback.clinical_reasoning_score or 0.0),
                    spikes_completion_score=float(feedback.spikes_completion_score or 0.0),
                    spikes_coverage_percent=spikes_coverage_percent,
                    duration_seconds=int(session.duration_seconds or 0),
                    created_at=feedback.created_at or session.started_at,
                    eo_addressed_rate=eo_addressed_rate,
                    spikes_stages_covered=spikes_stages_covered,
                )
            )

        out.sort(key=lambda row: row.created_at)
        return out

