"""Analytics service for admin dashboard."""

from datetime import datetime

from sqlalchemy.orm import Session

from domain.models.admin import (
    AnalyticsDashboard,
    CaseStats,
    PerformanceStats,
    SessionStats,
    UserStats,
)
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from repositories.user_repo import UserRepository
from repositories.case_repo import CaseRepository


class AnalyticsService:
    """Service for analytics and reporting."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)
        self.feedback_repo = FeedbackRepository(db)
        self.case_repo = CaseRepository(db)
    
    async def get_dashboard_analytics(self) -> AnalyticsDashboard:
        """Get comprehensive analytics for admin dashboard."""
        user_stats = await self._get_user_stats()
        session_stats = await self._get_session_stats()
        case_stats = await self._get_case_stats()
        performance_stats = await self._get_performance_stats()
        
        return AnalyticsDashboard(
            user_stats=user_stats,
            session_stats=session_stats,
            performance_stats=performance_stats,
            case_stats=case_stats,
            generated_at=datetime.utcnow(),
        )
    
    async def _get_user_stats(self) -> UserStats:
        """Get user statistics."""
        total_users = self.user_repo.count()
        users_by_role = self.user_repo.count_by_role()
        active_users = self.session_repo.count_active_in_period(days=30)
        
        return UserStats(
            total_users=total_users,
            users_by_role=users_by_role,
            active_users_last_30_days=active_users,
        )
    
    async def _get_session_stats(self) -> SessionStats:
        """Get session statistics."""
        total_sessions = self.session_repo.count()
        sessions_by_state = self.session_repo.count_by_state()
        avg_duration = self.session_repo.get_average_duration()
        sessions_by_case = self.session_repo.count_by_case()

        return SessionStats(
            total_sessions=total_sessions,
            completed_sessions=sessions_by_state.get("completed", 0),
            active_sessions=sessions_by_state.get("active", 0),
            average_duration_seconds=avg_duration,
            sessions_by_case=sessions_by_case,
        )
    
    async def _get_performance_stats(self) -> PerformanceStats:
        """Get performance statistics."""
        avg_scores = self.feedback_repo.get_average_scores()
        
        return PerformanceStats(
            average_empathy_score=avg_scores["empathy"],
            average_communication_score=avg_scores["communication"],
            average_spikes_completion=avg_scores["spikes"],
            average_overall_score=avg_scores["overall"],
        )

    async def _get_case_stats(self) -> CaseStats:
        """Get high-level case statistics."""
        total_cases = self.case_repo.count()
        cases_by_category = self.case_repo.count_by_category()
        return CaseStats(
            total_cases=total_cases,
            cases_by_category=cases_by_category,
        )

