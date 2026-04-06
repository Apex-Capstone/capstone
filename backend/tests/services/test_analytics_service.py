"""Unit tests for AnalyticsService (admin dashboard aggregates).

Uses mocked repositories so no real database I/O is required.
Verification of:
  - get_dashboard_analytics: full pipeline returns a valid AnalyticsDashboard
  - _get_user_stats: correct mapping from repo counts
  - _get_session_stats: completed/active derived from count_by_state dict
  - _get_performance_stats: score keys and MonthScoreAverage wrapping
  - _get_case_stats: count and category breakdown
  - Edge case: all-zero / empty data still produces a valid response
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from domain.models.admin import (
    AnalyticsDashboard,
    CaseStats,
    MonthScoreAverage,
    PerformanceStats,
    SessionStats,
    UserStats,
)
from services.analytics_service import AnalyticsService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_service(
    *,
    total_users: int = 10,
    users_by_role: dict | None = None,
    active_users: int = 3,
    total_sessions: int = 20,
    sessions_by_state: dict | None = None,
    avg_duration: float = 300.0,
    sessions_by_case: dict | None = None,
    avg_scores: dict | None = None,
    by_month: list | None = None,
    total_cases: int = 5,
    cases_by_category: dict | None = None,
) -> AnalyticsService:
    """Create an AnalyticsService with fully mocked repositories."""
    if users_by_role is None:
        users_by_role = {"trainee": 8, "admin": 2}
    if sessions_by_state is None:
        sessions_by_state = {"completed": 15, "active": 5}
    if sessions_by_case is None:
        sessions_by_case = {"1": 10, "2": 10}
    if avg_scores is None:
        avg_scores = {
            "empathy": 72.5,
            "communication": 68.0,
            "spikes": 55.0,
            "overall": 65.0,
        }
    if by_month is None:
        by_month = [
            {"month": "2024-01", "score": 60.0},
            {"month": "2024-02", "score": 65.5},
        ]
    if cases_by_category is None:
        cases_by_category = {"oncology": 3, "pediatrics": 2}

    svc = AnalyticsService.__new__(AnalyticsService)
    svc.db = MagicMock()

    svc.user_repo = MagicMock()
    svc.user_repo.count.return_value = total_users
    svc.user_repo.count_by_role.return_value = users_by_role
    svc.session_repo = MagicMock()
    svc.session_repo.count_active_in_period.return_value = active_users
    svc.session_repo.count.return_value = total_sessions
    svc.session_repo.count_by_state.return_value = sessions_by_state
    svc.session_repo.get_average_duration.return_value = avg_duration
    svc.session_repo.count_by_case.return_value = sessions_by_case

    svc.feedback_repo = MagicMock()
    svc.feedback_repo.get_average_scores.return_value = avg_scores
    svc.feedback_repo.get_average_overall_by_month.return_value = by_month

    svc.case_repo = MagicMock()
    svc.case_repo.count.return_value = total_cases
    svc.case_repo.count_by_category.return_value = cases_by_category

    return svc


# ---------------------------------------------------------------------------
# get_dashboard_analytics
# ---------------------------------------------------------------------------


async def test_get_dashboard_analytics_returns_valid_model():
    svc = _build_service()
    dashboard = await svc.get_dashboard_analytics()

    assert isinstance(dashboard, AnalyticsDashboard)
    assert dashboard.generated_at is not None


async def test_get_dashboard_analytics_contains_all_sub_stats():
    svc = _build_service()
    dashboard = await svc.get_dashboard_analytics()

    assert isinstance(dashboard.user_stats, UserStats)
    assert isinstance(dashboard.session_stats, SessionStats)
    assert isinstance(dashboard.performance_stats, PerformanceStats)
    assert isinstance(dashboard.case_stats, CaseStats)


# ---------------------------------------------------------------------------
# _get_user_stats
# ---------------------------------------------------------------------------


async def test_get_user_stats_maps_counts():
    svc = _build_service(total_users=15, active_users=7)
    stats = await svc._get_user_stats()

    assert stats.total_users == 15
    assert stats.active_users_last_30_days == 7


async def test_get_user_stats_maps_role_breakdown():
    svc = _build_service(users_by_role={"trainee": 12, "admin": 3})
    stats = await svc._get_user_stats()

    assert stats.users_by_role == {"trainee": 12, "admin": 3}


async def test_get_user_stats_empty_role_dict():
    svc = _build_service(total_users=0, users_by_role={}, active_users=0)
    stats = await svc._get_user_stats()

    assert stats.total_users == 0
    assert stats.users_by_role == {}
    assert stats.active_users_last_30_days == 0


# ---------------------------------------------------------------------------
# _get_session_stats
# ---------------------------------------------------------------------------


async def test_get_session_stats_completed_and_active():
    svc = _build_service(
        total_sessions=25,
        sessions_by_state={"completed": 20, "active": 5},
        avg_duration=420.0,
    )
    stats = await svc._get_session_stats()

    assert stats.total_sessions == 25
    assert stats.completed_sessions == 20
    assert stats.active_sessions == 5
    assert stats.average_duration_seconds == pytest.approx(420.0)


async def test_get_session_stats_missing_keys_default_to_zero():
    """count_by_state may return a dict without 'completed' or 'active' keys."""
    svc = _build_service(sessions_by_state={})
    stats = await svc._get_session_stats()

    assert stats.completed_sessions == 0
    assert stats.active_sessions == 0


async def test_get_session_stats_sessions_by_case():
    svc = _build_service(sessions_by_case={"case_1": 7, "case_2": 3})
    stats = await svc._get_session_stats()

    assert stats.sessions_by_case == {"case_1": 7, "case_2": 3}


async def test_get_session_stats_zero_sessions():
    svc = _build_service(total_sessions=0, sessions_by_state={}, avg_duration=0.0)
    stats = await svc._get_session_stats()

    assert stats.total_sessions == 0
    assert stats.average_duration_seconds == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _get_performance_stats
# ---------------------------------------------------------------------------


async def test_get_performance_stats_score_keys():
    svc = _build_service(
        avg_scores={
            "empathy": 80.0,
            "communication": 75.0,
            "spikes": 60.0,
            "overall": 71.7,
        }
    )
    stats = await svc._get_performance_stats()

    assert stats.average_empathy_score == pytest.approx(80.0)
    assert stats.average_communication_score == pytest.approx(75.0)
    assert stats.average_spikes_completion == pytest.approx(60.0)
    assert stats.average_overall_score == pytest.approx(71.7)


async def test_get_performance_stats_month_averages_wrapped():
    svc = _build_service(
        by_month=[
            {"month": "2024-03", "score": 70.0},
            {"month": "2024-04", "score": 72.5},
            {"month": "2024-05", "score": 75.0},
        ]
    )
    stats = await svc._get_performance_stats()

    assert len(stats.average_score_by_month) == 3
    assert all(isinstance(m, MonthScoreAverage) for m in stats.average_score_by_month)
    assert stats.average_score_by_month[0].month == "2024-03"
    assert stats.average_score_by_month[0].score == pytest.approx(70.0)
    assert stats.average_score_by_month[2].score == pytest.approx(75.0)


async def test_get_performance_stats_empty_month_list():
    svc = _build_service(by_month=[])
    stats = await svc._get_performance_stats()

    assert stats.average_score_by_month == []


# ---------------------------------------------------------------------------
# _get_case_stats
# ---------------------------------------------------------------------------


async def test_get_case_stats_counts_and_categories():
    svc = _build_service(total_cases=8, cases_by_category={"oncology": 4, "cardiology": 4})
    stats = await svc._get_case_stats()

    assert stats.total_cases == 8
    assert stats.cases_by_category == {"oncology": 4, "cardiology": 4}


async def test_get_case_stats_empty():
    svc = _build_service(total_cases=0, cases_by_category={})
    stats = await svc._get_case_stats()

    assert stats.total_cases == 0
    assert stats.cases_by_category == {}


# ---------------------------------------------------------------------------
# Edge case: all zeros / empty data
# ---------------------------------------------------------------------------


async def test_dashboard_all_zeros_is_valid():
    svc = _build_service(
        total_users=0,
        users_by_role={},
        active_users=0,
        total_sessions=0,
        sessions_by_state={},
        avg_duration=0.0,
        sessions_by_case={},
        avg_scores={"empathy": 0.0, "communication": 0.0, "spikes": 0.0, "overall": 0.0},
        by_month=[],
        total_cases=0,
        cases_by_category={},
    )
    dashboard = await svc.get_dashboard_analytics()

    assert isinstance(dashboard, AnalyticsDashboard)
    assert dashboard.user_stats.total_users == 0
    assert dashboard.session_stats.total_sessions == 0
    assert dashboard.performance_stats.average_overall_score == pytest.approx(0.0)
    assert dashboard.case_stats.total_cases == 0
    assert dashboard.performance_stats.average_score_by_month == []
