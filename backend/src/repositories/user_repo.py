"""User repository for database operations."""

from typing import Any, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User


class UserRepository:
    """Repository for User entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def create(self, user: User) -> User:
        """Create a new user."""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update(self, user: User) -> User:
        """Update an existing user."""
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user_id: int) -> bool:
        """Delete a user by ID."""
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
    
    def count(self) -> int:
        """Count total users."""
        return self.db.query(User).count()
    
    def count_by_role(self) -> dict[str, int]:
        """Count users by role."""
        from sqlalchemy import func
        
        results = self.db.query(
            User.role,
            func.count(User.id)
        ).group_by(User.role).all()
        
        return {role: count for role, count in results}

    def _apply_user_overview_filters(self, stmt: Any, role: Optional[str], q: Optional[str]) -> Any:
        if role:
            stmt = stmt.where(User.role == role)
        if q and q.strip():
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(term),
                    User.full_name.ilike(term),
                )
            )
        return stmt

    def count_for_overview(self, role: Optional[str], q: Optional[str]) -> int:
        """Count users matching overview filters (pagination total)."""
        stmt = select(func.count(User.id))
        stmt = self._apply_user_overview_filters(stmt, role, q)
        result = self.db.execute(stmt).scalar_one()
        return int(result)

    def list_admin_overview(
        self,
        skip: int,
        limit: int,
        sort: str,
        role: Optional[str],
        q: Optional[str],
    ) -> tuple[list[dict[str, Any]], int]:
        """Paginated user rows with session and feedback aggregates (admin)."""
        session_agg = (
            select(
                SessionEntity.user_id.label("uid"),
                func.count(SessionEntity.id).label("session_count"),
                func.coalesce(
                    func.sum(case((SessionEntity.state == "completed", 1), else_=0)),
                    0,
                ).label("completed_session_count"),
                func.max(SessionEntity.started_at).label("last_session_at"),
            )
            .group_by(SessionEntity.user_id)
            .subquery()
        )

        feedback_agg = (
            select(
                SessionEntity.user_id.label("uid"),
                func.avg(Feedback.overall_score).label("avg_overall"),
                func.avg(Feedback.empathy_score).label("avg_empathy"),
            )
            .select_from(SessionEntity)
            .join(Feedback, Feedback.session_id == SessionEntity.id)
            .group_by(SessionEntity.user_id)
            .subquery()
        )

        stmt = (
            select(
                User.id,
                User.email,
                User.full_name,
                User.role,
                User.created_at,
                func.coalesce(session_agg.c.session_count, 0).label("session_count"),
                func.coalesce(session_agg.c.completed_session_count, 0).label(
                    "completed_session_count"
                ),
                session_agg.c.last_session_at,
                feedback_agg.c.avg_overall,
                feedback_agg.c.avg_empathy,
            )
            .select_from(User)
            .outerjoin(session_agg, User.id == session_agg.c.uid)
            .outerjoin(feedback_agg, User.id == feedback_agg.c.uid)
        )
        stmt = self._apply_user_overview_filters(stmt, role, q)

        if sort == "email_asc":
            stmt = stmt.order_by(User.email.asc())
        elif sort == "avg_score_desc":
            stmt = stmt.order_by(feedback_agg.c.avg_overall.desc().nulls_last(), User.id.asc())
        else:
            # last_active_desc (default)
            stmt = stmt.order_by(session_agg.c.last_session_at.desc().nulls_last(), User.id.asc())

        stmt = stmt.offset(skip).limit(limit)
        rows = self.db.execute(stmt).all()
        total = self.count_for_overview(role, q)

        out: list[dict[str, Any]] = []
        for row in rows:
            avg_overall = row.avg_overall
            avg_empathy = row.avg_empathy
            out.append(
                {
                    "id": row.id,
                    "email": row.email,
                    "full_name": row.full_name,
                    "role": row.role,
                    "created_at": row.created_at,
                    "session_count": int(row.session_count),
                    "completed_session_count": int(row.completed_session_count),
                    "last_session_at": row.last_session_at,
                    "average_overall_score": float(avg_overall) if avg_overall is not None else None,
                    "average_empathy_score": float(avg_empathy) if avg_empathy is not None else None,
                }
            )
        return out, total

