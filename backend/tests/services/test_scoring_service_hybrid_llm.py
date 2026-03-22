"""Hybrid merge: 70/30 component blend and overall from merged components."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from schemas.llm_reviewer import LLMMissedOpportunityItem, LLMReviewerOutput
from services.scoring_service import ScoringService, _compact_llm_output_for_evaluator_meta
from tests.utils.transcript_runner import create_all_for_test_engine


@pytest.fixture
def scoring_service() -> ScoringService:
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    testing_session_local = sessionmaker(bind=engine)
    db = testing_session_local()
    try:
        yield ScoringService(db)
    finally:
        db.close()


def test_merge_rule_and_llm_component_scores(scoring_service: ScoringService) -> None:
    e, c, s, o = scoring_service._merge_rule_and_llm_component_scores(
        70.0,
        80.0,
        90.0,
        50.0,
        50.0,
        50.0,
    )
    assert e == pytest.approx(0.7 * 70.0 + 0.3 * 50.0)
    assert c == pytest.approx(0.7 * 80.0 + 0.3 * 50.0)
    assert s == pytest.approx(0.7 * 90.0 + 0.3 * 50.0)
    # Displayed overall is always recomputed from merged components (not blended from LLM overall_score).
    assert o == pytest.approx(0.5 * e + 0.2 * c + 0.3 * s)


def test_compact_llm_output_for_evaluator_meta_caps_list_length() -> None:
    mos = [
        LLMMissedOpportunityItem(
            turn_number=i,
            patient_emotional_cue="cue",
            why_missed_or_weak="why",
        )
        for i in range(1, 50)
    ]
    out = LLMReviewerOutput(
        empathy_score=50.0,
        communication_score=50.0,
        spikes_completion_score=50.0,
        overall_score=50.0,
        missed_opportunities=mos,
        spikes_annotations=[],
        strengths=["ok"],
        areas_for_improvement=["ok"],
    )
    d = _compact_llm_output_for_evaluator_meta(out)
    assert len(d["missed_opportunities"]) == 40
    assert d.get("_meta_truncated") is True
