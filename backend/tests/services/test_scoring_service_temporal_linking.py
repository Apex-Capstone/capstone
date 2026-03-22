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


def test_eo_immediate_empathic_response_is_valid_link(scoring_service: ScoringService) -> None:
    turns = [
        SimpleNamespace(turn_number=1, role="assistant"),
        SimpleNamespace(turn_number=2, role="user"),
    ]
    eo_spans = [{"turn_number": 1, "span_type": "eo", "text": "I am scared"}]
    response_spans = [{"turn_number": 2, "span_type": "response", "text": "I hear you"}]

    links, missed, stats, _ = scoring_service._compute_eo_linking(
        eo_spans=eo_spans,
        response_spans=response_spans,
        elicitation_spans=[],
        turns=turns,
    )

    assert stats["addressed_count"] == 1
    assert stats["missed_count"] == 0
    assert "eo_1" in links
    assert len(links["eo_1"]) == 1
    assert missed == []


def test_eo_later_empathy_after_missed_turn_is_invalid_link(scoring_service: ScoringService) -> None:
    turns = [
        SimpleNamespace(turn_number=1, role="assistant"),
        SimpleNamespace(turn_number=2, role="user"),  # immediate clinician turn, no response span
        SimpleNamespace(turn_number=3, role="assistant"),
        SimpleNamespace(turn_number=4, role="user"),  # later empathic response appears here
    ]
    eo_spans = [{"turn_number": 1, "span_type": "eo", "text": "This feels overwhelming"}]
    response_spans = [{"turn_number": 4, "span_type": "response", "text": "That sounds hard"}]

    links, missed, stats, _ = scoring_service._compute_eo_linking(
        eo_spans=eo_spans,
        response_spans=response_spans,
        elicitation_spans=[],
        turns=turns,
    )

    assert stats["addressed_count"] == 0
    assert stats["missed_count"] == 1
    assert links == {}
    assert len(missed) == 1
    assert missed[0]["turn_number"] == 1


def test_multiple_eos_do_not_all_link_to_one_late_response(scoring_service: ScoringService) -> None:
    turns = [
        SimpleNamespace(turn_number=1, role="assistant"),  # eo_1
        SimpleNamespace(turn_number=2, role="user"),  # no empathy response
        SimpleNamespace(turn_number=3, role="assistant"),  # eo_2
        SimpleNamespace(turn_number=4, role="user"),  # one empathy response here
    ]
    eo_spans = [
        {"turn_number": 1, "span_type": "eo", "text": "I don't know what to do"},
        {"turn_number": 3, "span_type": "eo", "text": "I am still anxious"},
    ]
    response_spans = [{"turn_number": 4, "span_type": "response", "text": "I can see this is difficult"}]

    links, missed, stats, _ = scoring_service._compute_eo_linking(
        eo_spans=eo_spans,
        response_spans=response_spans,
        elicitation_spans=[],
        turns=turns,
    )

    assert stats["addressed_count"] == 1
    assert stats["missed_count"] == 1
    assert "eo_1" not in links
    assert "eo_2" in links
    assert len(links["eo_2"]) == 1
    assert len(missed) == 1
    assert missed[0]["span_id"] == "eo_1"
