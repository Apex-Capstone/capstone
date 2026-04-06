"""Unit tests for TraineeAnalyticsService.

Verification of:
  - _parse_json static helper (pure function)
  - get_user_session_analytics: query filtering, score derivation, sorting
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from services.trainee_analytics_service import TraineeAnalyticsService
from tests.utils.transcript_runner import create_all_for_test_engine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(e)
    return e


@pytest.fixture
def test_db(engine):
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_user(test_db):
    user = User(
        email=f"trainee_{uuid.uuid4().hex[:12]}@test.com",
        role="trainee",
        full_name="Test Trainee",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(title="Oncology Case", script="Test script", difficulty_level="intermediate")
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


# ---------------------------------------------------------------------------
# _parse_json — pure function, no DB
# ---------------------------------------------------------------------------


def test_parse_json_none_returns_none():
    assert TraineeAnalyticsService._parse_json(None) is None


def test_parse_json_dict_passed_through():
    d = {"key": "value", "nested": {"x": 1}}
    result = TraineeAnalyticsService._parse_json(d)
    assert result is d


def test_parse_json_valid_json_string():
    result = TraineeAnalyticsService._parse_json('{"a": 1, "b": "hello"}')
    assert result == {"a": 1, "b": "hello"}


def test_parse_json_nested_json_string():
    payload = json.dumps({"covered": ["S", "P"], "percent": 0.5})
    result = TraineeAnalyticsService._parse_json(payload)
    assert result == {"covered": ["S", "P"], "percent": 0.5}


def test_parse_json_json_list_returns_none():
    """JSON array is not a dict — must return None."""
    assert TraineeAnalyticsService._parse_json('[1, 2, 3]') is None


def test_parse_json_json_scalar_returns_none():
    """JSON number/bool is not a dict — must return None."""
    assert TraineeAnalyticsService._parse_json("42") is None
    assert TraineeAnalyticsService._parse_json("true") is None


def test_parse_json_invalid_json_string_returns_none():
    assert TraineeAnalyticsService._parse_json("not-json{{") is None


def test_parse_json_non_string_non_dict_returns_none():
    assert TraineeAnalyticsService._parse_json(42) is None
    assert TraineeAnalyticsService._parse_json(3.14) is None
    assert TraineeAnalyticsService._parse_json(True) is None
    assert TraineeAnalyticsService._parse_json([1, 2]) is None


# ---------------------------------------------------------------------------
# get_user_session_analytics
# ---------------------------------------------------------------------------


def test_empty_list_for_user_with_no_sessions(test_db, test_user):
    svc = TraineeAnalyticsService(test_db)
    assert svc.get_user_session_analytics(test_user.id) == []


def test_empty_list_for_user_with_only_active_sessions(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="active")
    test_db.add(session)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    assert svc.get_user_session_analytics(test_user.id) == []


def test_sessions_without_feedback_excluded(test_db, test_user, test_case):
    """Completed sessions with no Feedback row are excluded by the inner join."""
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    assert svc.get_user_session_analytics(test_user.id) == []


def test_single_completed_session_basic_fields(test_db, test_user, test_case):
    session = SessionEntity(
        user_id=test_user.id,
        case_id=test_case.id,
        state="completed",
        duration_seconds=180,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        empathy_score=75.0,
        communication_score=80.0,
        clinical_reasoning_score=60.0,
        spikes_completion_score=50.0,
        overall_score=68.0,
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    results = svc.get_user_session_analytics(test_user.id)

    assert len(results) == 1
    row = results[0]
    assert row.session_id == session.id
    assert row.case_id == test_case.id
    assert row.case_title == "Oncology Case"
    assert row.empathy_score == pytest.approx(75.0)
    assert row.communication_score == pytest.approx(80.0)
    assert row.clinical_score == pytest.approx(60.0)
    assert row.spikes_completion_score == pytest.approx(50.0)
    assert row.duration_seconds == 180


def test_spikes_coverage_percent_scaled_from_fraction(test_db, test_user, test_case):
    """spikes_coverage 'percent' field is a fraction (0–1); service multiplies by 100."""
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        spikes_coverage=json.dumps({"percent": 0.5, "covered": ["S", "P", "I"]}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.spikes_coverage_percent == pytest.approx(50.0)


def test_spikes_coverage_percent_clamped_at_100(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        spikes_coverage=json.dumps({"percent": 2.0, "covered": ["S"]}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.spikes_coverage_percent == pytest.approx(100.0)


def test_spikes_coverage_percent_clamped_at_zero(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        spikes_coverage=json.dumps({"percent": -0.5, "covered": []}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.spikes_coverage_percent == pytest.approx(0.0)


def test_spikes_coverage_percent_zero_when_missing(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(session_id=session.id)
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.spikes_coverage_percent == pytest.approx(0.0)


def test_spikes_stages_covered_populated(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        spikes_coverage=json.dumps({"percent": 0.67, "covered": ["S", "P", "I", "K"]}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.spikes_stages_covered == ["S", "P", "I", "K"]


def test_spikes_stages_covered_none_entries_filtered(test_db, test_user, test_case):
    """None entries in the covered list must be skipped."""
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        spikes_coverage=json.dumps({"percent": 0.33, "covered": ["S", None, "P"]}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.spikes_stages_covered == ["S", "P"]


def test_spikes_stages_covered_empty_list_yields_none(test_db, test_user, test_case):
    """Empty covered list -> spikes_stages_covered stays None."""
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        spikes_coverage=json.dumps({"percent": 0.0, "covered": []}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.spikes_stages_covered is None


def test_eo_addressed_rate_scaled_from_fraction(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        linkage_stats=json.dumps({"addressed_rate": 0.8, "total_eos": 5}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.eo_addressed_rate == pytest.approx(80.0)


def test_eo_addressed_rate_clamped_at_100(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        linkage_stats=json.dumps({"addressed_rate": 1.5}),
    )
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.eo_addressed_rate == pytest.approx(100.0)


def test_eo_addressed_rate_none_when_linkage_missing(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(session_id=session.id)
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.eo_addressed_rate is None


def test_null_feedback_scores_default_to_zero(test_db, test_user, test_case):
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(session_id=session.id)
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.empathy_score == pytest.approx(0.0)
    assert result.communication_score == pytest.approx(0.0)
    assert result.clinical_score == pytest.approx(0.0)
    assert result.spikes_completion_score == pytest.approx(0.0)


def test_case_title_fallback_when_title_is_empty(test_db, test_user):
    """Empty string title triggers the 'Case #<id>' fallback."""
    case = Case(title="", script="Script")
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    session = SessionEntity(user_id=test_user.id, case_id=case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(session_id=session.id)
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.case_title == f"Case #{case.id}"


def test_multiple_sessions_sorted_by_created_at(test_db, test_user, test_case):
    """Results are sorted by created_at ascending."""
    earlier = datetime(2024, 1, 1, tzinfo=timezone.utc)
    later = datetime(2024, 6, 1, tzinfo=timezone.utc)

    s1 = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    s2 = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add_all([s1, s2])
    test_db.commit()
    test_db.refresh(s1)
    test_db.refresh(s2)

    fb1 = Feedback(session_id=s1.id, empathy_score=70.0, created_at=later)
    fb2 = Feedback(session_id=s2.id, empathy_score=80.0, created_at=earlier)
    test_db.add_all([fb1, fb2])
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    results = svc.get_user_session_analytics(test_user.id)
    assert len(results) == 2
    assert results[0].created_at <= results[1].created_at
    # The session with earlier feedback comes first
    assert results[0].session_id == s2.id
    assert results[1].session_id == s1.id


def test_only_own_sessions_returned(test_db, test_case):
    """Trainee A must not see sessions belonging to Trainee B."""
    user_a = User(email="a@test.com", role="trainee")
    user_b = User(email="b@test.com", role="trainee")
    test_db.add_all([user_a, user_b])
    test_db.commit()
    test_db.refresh(user_a)
    test_db.refresh(user_b)

    session_b = SessionEntity(user_id=user_b.id, case_id=test_case.id, state="completed")
    test_db.add(session_b)
    test_db.commit()
    test_db.refresh(session_b)

    test_db.add(Feedback(session_id=session_b.id, empathy_score=90.0))
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    assert svc.get_user_session_analytics(user_a.id) == []


def test_duration_seconds_zero_when_null(test_db, test_user, test_case):
    session = SessionEntity(
        user_id=test_user.id, case_id=test_case.id, state="completed", duration_seconds=None
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(session_id=session.id)
    test_db.add(feedback)
    test_db.commit()

    svc = TraineeAnalyticsService(test_db)
    result = svc.get_user_session_analytics(test_user.id)[0]
    assert result.duration_seconds == 0
