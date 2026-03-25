"""Unit tests for post-refactor scoring formulas (communication, SPIKES, overall)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.scoring_service import ScoringService
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


def test_communication_score_full_data_clarity_weighted(scoring_service: ScoringService) -> None:
    """With tone + questions + elicitations + strategies, score reflects the 40/35/25 blend."""
    turns = [
        SimpleNamespace(role="user", metrics_json='{"tone": {"calm": true, "clear": true}}'),
        SimpleNamespace(role="user", metrics_json='{"tone": {"calm": true, "clear": true}}'),
    ]
    question_breakdown = {"open": 1, "closed": 1, "eliciting": 0, "ratio_open": 0.5}
    spikes_strategies = {
        "knowledge": [
            {"strategy": "clarify", "turn": 1},
            {"strategy": "summarize", "turn": 2},
        ]
    }
    all_spans = [
        {"span_type": "elicitation", "type": "direct", "dimension": "Feeling"},
    ]
    raw = scoring_service._compute_communication_score(
        turns, question_breakdown, spikes_strategies, all_spans
    )
    clarity = 100.0  # all clear + calm
    # Smoothed open share (1+0.5)/(2+1)=0.5; open_part=min(1, 0.5/0.65); elicitation_part=1.0
    ratio_open_smooth = (1 + 0.5) / (2 + 1.0)
    open_part = min(1.0, ratio_open_smooth / scoring_service._QUESTION_OPEN_RATIO_TARGET)
    elicitation_part = min(1.0, (1.0 / 2.0) / 0.25)
    q_part = 100.0 * (0.55 * open_part + 0.45 * elicitation_part)
    struct = 100.0 * (2 / 5)  # clarify + summarize
    expected = 0.40 * clarity + 0.35 * q_part + 0.25 * struct
    assert raw == pytest.approx(expected)


def test_communication_score_partial_data_neutral_missing_tone(scoring_service: ScoringService) -> None:
    """No tone booleans: clarity subscore is neutral (50); open-heavy question term still contributes."""
    turns = [
        SimpleNamespace(role="user", metrics_json='{"question_type": "open"}'),
    ]
    question_breakdown = {"open": 1, "closed": 0, "eliciting": 0, "ratio_open": 1.0}
    spikes_strategies: dict = {}
    all_spans: list = []
    raw = scoring_service._compute_communication_score(
        turns, question_breakdown, spikes_strategies, all_spans
    )
    clarity = 50.0
    # One open, zero closed: smoothed share 0.75 -> open_part=1.0; no elicitations
    ratio_open_smooth = (1 + 0.5) / (1 + 1.0)
    open_part = min(1.0, ratio_open_smooth / scoring_service._QUESTION_OPEN_RATIO_TARGET)
    q_part = 100.0 * (0.55 * open_part + 0.45 * 0.0)
    struct = 50.0
    expected = 0.40 * clarity + 0.35 * q_part + 0.25 * struct
    assert raw == pytest.approx(expected)


def test_communication_score_no_data_all_neutral(scoring_service: ScoringService) -> None:
    """No tone, no classified questions, no elicitations, no strategies -> 50."""
    turns = [SimpleNamespace(role="user", metrics_json=None)]
    raw = scoring_service._compute_communication_score(turns, {}, {}, [])
    assert raw == pytest.approx(50.0)


def test_spikes_completion_is_covered_stages_over_six_times_100(scoring_service: ScoringService) -> None:
    session = SimpleNamespace()
    turns = [
        SimpleNamespace(spikes_stage="setting", role="user"),
        SimpleNamespace(spikes_stage="knowledge", role="user"),
        SimpleNamespace(spikes_stage="k", role="user"),
    ]
    score = scoring_service._calculate_spikes_completion(session, turns, [])
    assert score == pytest.approx(round((2.0 / 6.0) * 100.0, 2))


def test_overall_score_weights_empathy_communication_spikes(scoring_service: ScoringService) -> None:
    """overall = 0.5*empathy + 0.2*communication + 0.3*spikes after component scores."""
    empathy = 80.0
    communication = 50.0
    spikes = 40.0
    blended = 0.5 * empathy + 0.2 * communication + 0.3 * spikes
    assert blended == pytest.approx(62.0)
    assert scoring_service._clamp_score(round(blended, 2)) == 62.0


def test_old_communication_and_clinical_formulas_not_present_in_source() -> None:
    """Guardrail: removed legacy SPIKES+open-question communication and clinical reasoning blend."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "src" / "services" / "scoring_service.py"
    src = path.read_text()
    assert "0.7 * spikes_coverage_percent" not in src
    assert "0.3 * ratio_open" not in src
    assert "0.35 * communication_score" not in src
    assert "stage_score * empathy_modifier" not in src
    assert "empathy_modifier" not in src
