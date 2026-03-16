from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.scoring_service import ScoringService


class ApexMetrics:
    """
    Default MetricsPlugin implementation that reuses ScoringService's
    span- and SPIKES-based metric helpers to expose research metrics.
    """

    def compute(self, db: Session, session_id: int) -> dict[str, Any]:
        service = ScoringService(db)

        # Load turns for the session using the same repositories as scoring.
        session = service.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found for metrics computation.")

        turns = service.turn_repo.get_by_session(session_id)

        # Extract spans and derive AFCE-aligned metrics
        all_spans = service._extract_spans_from_turns(turns)
        eo_counts_by_dimension = service._calculate_eo_counts_by_dimension(all_spans)
        response_counts_by_type = service._calculate_response_counts_by_type(all_spans)

        # SPIKES coverage over the conversation
        spikes_coverage = service._analyze_spikes_coverage(turns)

        return {
            "eo_counts_by_dimension": eo_counts_by_dimension,
            "response_counts_by_type": response_counts_by_type,
            "spikes_coverage": spikes_coverage,
        }

