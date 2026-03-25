"""Trainee analytics controller/router."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db
from domain.entities.user import User
from domain.models.analytics import TraineeSessionAnalytics
from services.trainee_analytics_service import TraineeAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/my-sessions", response_model=list[TraineeSessionAnalytics])
async def get_my_session_analytics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return session analytics for the authenticated user."""
    service = TraineeAnalyticsService(db)
    return service.get_user_session_analytics(current_user.id)

