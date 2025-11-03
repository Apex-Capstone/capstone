"""Analytics service for admin dashboard."""

from datetime import datetime

from sqlalchemy.orm import Session

from domain.models.admin import (
    AnalyticsDashboard,
    PerformanceStats,
    SessionStats,
    UserStats,
)
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from repositories.user_repo import UserRepository


class AnalyticsService:
    """Service for analytics and reporting."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)
        self.feedback_repo = FeedbackRepository(db)
    
    async def get_dashboard_analytics(self) -> AnalyticsDashboard:
        """Get comprehensive analytics for admin dashboard."""
        user_stats = await self._get_user_stats()
        session_stats = await self._get_session_stats()
        performance_stats = await self._get_performance_stats()
        
        return AnalyticsDashboard(
            user_stats=user_stats,
            session_stats=session_stats,
            performance_stats=performance_stats,
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
        
        return SessionStats(
            total_sessions=total_sessions,
            completed_sessions=sessions_by_state.get("completed", 0),
            active_sessions=sessions_by_state.get("active", 0),
            average_duration_seconds=avg_duration,
            sessions_by_case={},  # Would need additional query
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

