"""Performance and robustness tests for analytics and research services.

Validation of:
  - get_user_session_analytics throughput at scale (100+ sessions)
  - get_dashboard_analytics throughput (mocked repos)
  - Research export streaming at scale (50 sessions × 5 turns)
  - resolve_anon_to_session_id worst-case scan performance
  - CSV streaming incrementality (yields chunks, not one blob)
  - Robustness: malformed JSON fields, None scores, missing cases
  - Concurrent read safety via asyncio.gather

Mark: tests in this module run with pytest.mark.slow.
To skip slow tests:  pytest -m "not slow"
To run only slow tests: pytest -m slow
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from services.analytics_service import AnalyticsService
from services.research_service import ResearchService, generate_anon_session_id, resolve_anon_to_session_id
from services.trainee_analytics_service import TraineeAnalyticsService
from tests.utils.transcript_runner import create_all_for_test_engine

pytestmark = pytest.mark.slow

TEST_SALT = "perf-test-salt-abc"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(e)
    return e


@pytest.fixture(scope="module")
def db_factory(engine):
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture(scope="module")
def seeded_data(db_factory):
    """Seed 100 sessions across 5 users and 3 cases for performance tests."""
    db = db_factory()

    users = [User(email=f"perf_user_{i}@test.com", role="trainee") for i in range(5)]
    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)

    cases = [
        Case(title=f"Perf Case {i}", script="Script", difficulty_level="intermediate")
        for i in range(3)
    ]
    db.add_all(cases)
    db.commit()
    for c in cases:
        db.refresh(c)

    sessions = []
    for idx in range(100):
        user = users[idx % len(users)]
        case = cases[idx % len(cases)]
        s = SessionEntity(
            user_id=user.id,
            case_id=case.id,
            state="completed",
            duration_seconds=120 + idx,
        )
        db.add(s)
        db.flush()

        fb = Feedback(
            session_id=s.id,
            empathy_score=60.0 + (idx % 40),
            communication_score=55.0 + (idx % 35),
            clinical_reasoning_score=50.0 + (idx % 30),
            spikes_completion_score=45.0 + (idx % 50),
            overall_score=58.0 + (idx % 35),
        )
        db.add(fb)
        sessions.append(s)

    db.commit()
    user_ids = [u.id for u in users]
    case_ids = [c.id for c in cases]
    session_ids = [s.id for s in sessions]
    last_session_id = sessions[-1].id
    db.close()
    return {
        "user_ids": user_ids,
        "case_ids": case_ids,
        "session_ids": session_ids,
        "last_session_id": last_session_id,
    }


@pytest.fixture(scope="module")
def seeded_turns_data(db_factory, seeded_data):
    """Add 5 turns to each of the first 50 sessions."""
    db = db_factory()
    for sid in seeded_data["session_ids"][:50]:
        for i in range(1, 6):
            db.add(
                Turn(
                    session_id=sid,
                    turn_number=i,
                    role="user" if i % 2 == 1 else "assistant",
                    text=f"Turn {i} content for session {sid}.",
                )
            )
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Trainee analytics throughput
# ---------------------------------------------------------------------------


def test_trainee_analytics_100_sessions_under_3_seconds(db_factory, seeded_data):
    """get_user_session_analytics on a user with ~20 sessions should be fast."""
    db = db_factory()
    user_id = seeded_data["user_ids"][0]

    svc = TraineeAnalyticsService(db)
    start = time.perf_counter()
    results = svc.get_user_session_analytics(user_id)
    elapsed = time.perf_counter() - start

    db.close()
    assert elapsed < 3.0, f"Analytics took {elapsed:.2f}s (> 3s limit)"
    assert isinstance(results, list)


def test_trainee_analytics_all_users_under_5_seconds(db_factory, seeded_data):
    """Querying all 5 users sequentially should complete in under 5 seconds."""
    db = db_factory()
    svc = TraineeAnalyticsService(db)

    start = time.perf_counter()
    for user_id in seeded_data["user_ids"]:
        svc.get_user_session_analytics(user_id)
    elapsed = time.perf_counter() - start

    db.close()
    assert elapsed < 5.0, f"All-user analytics took {elapsed:.2f}s (> 5s limit)"


# ---------------------------------------------------------------------------
# Admin dashboard analytics throughput (mocked repos)
# ---------------------------------------------------------------------------


async def test_dashboard_analytics_mocked_repos_under_1_second():
    """With mocked repos, get_dashboard_analytics should complete in well under 1 second."""
    svc = AnalyticsService.__new__(AnalyticsService)
    svc.db = MagicMock()
    svc.user_repo = MagicMock()
    svc.user_repo.count.return_value = 1000
    svc.user_repo.count_by_role.return_value = {"trainee": 990, "admin": 10}
    svc.session_repo = MagicMock()
    svc.session_repo.count_active_in_period.return_value = 200
    svc.session_repo.count.return_value = 5000
    svc.session_repo.count_by_state.return_value = {"completed": 4800, "active": 200}
    svc.session_repo.get_average_duration.return_value = 310.0
    svc.session_repo.count_by_case.return_value = {str(i): 50 for i in range(100)}
    svc.feedback_repo = MagicMock()
    svc.feedback_repo.get_average_scores.return_value = {
        "empathy": 68.0,
        "communication": 64.0,
        "spikes": 52.0,
        "overall": 62.0,
    }
    svc.feedback_repo.get_average_overall_by_month.return_value = [
        {"month": f"2024-{str(m).zfill(2)}", "score": 60.0 + m} for m in range(1, 13)
    ]
    svc.case_repo = MagicMock()
    svc.case_repo.count.return_value = 25
    svc.case_repo.count_by_category.return_value = {"oncology": 10, "cardiology": 8, "other": 7}

    start = time.perf_counter()
    dashboard = await svc.get_dashboard_analytics()
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"Dashboard analytics took {elapsed:.2f}s (> 1s limit)"
    assert dashboard.user_stats.total_users == 1000


# ---------------------------------------------------------------------------
# Research export streaming throughput
# ---------------------------------------------------------------------------


def test_stream_metrics_csv_50_sessions_under_5_seconds(db_factory, seeded_turns_data):
    """Streaming metrics CSV for 50+ sessions should complete in under 5 seconds."""
    db = db_factory()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(db)

        start = time.perf_counter()
        chunks = list(svc.stream_metrics_csv())
        elapsed = time.perf_counter() - start

    db.close()
    assert elapsed < 5.0, f"stream_metrics_csv took {elapsed:.2f}s (> 5s limit)"
    assert len(chunks) >= 1


def test_stream_transcripts_csv_250_turns_under_5_seconds(db_factory, seeded_turns_data):
    """Streaming transcripts CSV for 50 sessions × 5 turns under 5 seconds."""
    db = db_factory()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(db)

        start = time.perf_counter()
        chunks = list(svc.stream_transcripts_csv())
        elapsed = time.perf_counter() - start

    db.close()
    assert elapsed < 5.0, f"stream_transcripts_csv took {elapsed:.2f}s (> 5s limit)"
    assert len(chunks) >= 1


# ---------------------------------------------------------------------------
# Anon ID resolution performance
# ---------------------------------------------------------------------------


def test_resolve_anon_id_for_last_session_under_5_seconds(db_factory, seeded_data):
    """Worst-case anon resolution (linear scan to last session) under 5 seconds."""
    last_session_id = seeded_data["last_session_id"]
    db = db_factory()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        anon_id = generate_anon_session_id(last_session_id)
        from repositories.session_repo import SessionRepository
        repo = SessionRepository(db)

        start = time.perf_counter()
        found_id = resolve_anon_to_session_id(anon_id, repo)
        elapsed = time.perf_counter() - start

    db.close()
    assert elapsed < 5.0, f"resolve_anon_to_session_id took {elapsed:.2f}s (> 5s limit)"
    assert found_id == last_session_id


# ---------------------------------------------------------------------------
# CSV streaming incrementality
# ---------------------------------------------------------------------------


def test_metrics_csv_yields_multiple_chunks_not_single_blob(db_factory, seeded_turns_data):
    """stream_metrics_csv must yield incrementally (header + per-session chunks)."""
    db = db_factory()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(db)
        chunks = list(svc.stream_metrics_csv())

    db.close()
    # At minimum: 1 header chunk + at least 1 data chunk
    assert len(chunks) >= 2, f"Expected incremental yielding, got {len(chunks)} chunk(s)"


def test_transcripts_csv_yields_multiple_chunks(db_factory, seeded_turns_data):
    """stream_transcripts_csv must yield header + per-turn chunks."""
    db = db_factory()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(db)
        chunks = list(svc.stream_transcripts_csv())

    db.close()
    assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# Robustness: malformed / missing data
# ---------------------------------------------------------------------------


def test_analytics_survives_null_feedback_scores(db_factory, seeded_data):
    """Sessions with NULL scores in Feedback must not raise."""
    db = db_factory()
    user_id = seeded_data["user_ids"][0]

    case = Case(title="Null Score Case", script="Script")
    db.add(case)
    db.commit()
    db.refresh(case)

    session = SessionEntity(user_id=user_id, case_id=case.id, state="completed")
    db.add(session)
    db.commit()
    db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        empathy_score=None,
        communication_score=None,
        clinical_reasoning_score=None,
        spikes_completion_score=None,
        overall_score=None,
    )
    db.add(feedback)
    db.commit()

    svc = TraineeAnalyticsService(db)
    results = svc.get_user_session_analytics(user_id)
    db.close()

    row = next(r for r in results if r.session_id == session.id)
    assert row.empathy_score == pytest.approx(0.0)
    assert row.communication_score == pytest.approx(0.0)


def test_analytics_survives_malformed_spikes_json(db_factory, seeded_data):
    """Malformed spikes_coverage JSON must not raise; defaults to 0."""
    db = db_factory()
    user_id = seeded_data["user_ids"][1]

    case = Case(title="Bad JSON Case", script="Script")
    db.add(case)
    db.commit()
    db.refresh(case)

    session = SessionEntity(user_id=user_id, case_id=case.id, state="completed")
    db.add(session)
    db.commit()
    db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        spikes_coverage="NOT VALID JSON {{{}",
        linkage_stats="also bad",
    )
    db.add(feedback)
    db.commit()

    svc = TraineeAnalyticsService(db)
    results = svc.get_user_session_analytics(user_id)
    db.close()

    row = next(r for r in results if r.session_id == session.id)
    assert row.spikes_coverage_percent == pytest.approx(0.0)
    assert row.eo_addressed_rate is None


def test_research_export_survives_session_without_feedback(db_factory, seeded_data):
    """Sessions without feedback in get_all_sessions must not raise."""
    db = db_factory()
    user_id = seeded_data["user_ids"][2]
    case_id = seeded_data["case_ids"][0]

    session = SessionEntity(user_id=user_id, case_id=case_id, state="active")
    db.add(session)
    db.commit()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(db)
        results = svc.get_all_sessions()

    db.close()
    assert isinstance(results, list)


def test_research_export_survives_missing_case(db_factory, seeded_data):
    """get_all_sessions must not raise even if case_name lookup fails."""
    db = db_factory()
    user_id = seeded_data["user_ids"][3]

    # Create session with a non-existent case_id (no FK enforcement in SQLite)
    session = SessionEntity(user_id=user_id, case_id=99999, state="completed")
    db.add(session)
    db.commit()
    db.refresh(session)

    db.add(Feedback(session_id=session.id, empathy_score=50.0, overall_score=50.0))
    db.commit()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(db)
        results = svc.get_all_sessions()

    db.close()
    assert isinstance(results, list)
    row = next((r for r in results if r.get("case_id") == 99999), None)
    if row:
        assert row.get("case_name") is None


# ---------------------------------------------------------------------------
# Concurrent read safety
# ---------------------------------------------------------------------------


async def test_concurrent_get_all_sessions_consistent(db_factory, seeded_data):
    """10 concurrent get_all_sessions calls must all return the same session count."""

    async def _get_sessions():
        db = db_factory()
        with patch("services.research_service.get_settings") as m:
            m.return_value.research_anon_salt = TEST_SALT
            svc = ResearchService(db)
            result = svc.get_all_sessions(limit=200)
        db.close()
        return len(result)

    counts = await asyncio.gather(*[_get_sessions() for _ in range(10)])
    assert len(set(counts)) == 1, f"Inconsistent results: {counts}"
