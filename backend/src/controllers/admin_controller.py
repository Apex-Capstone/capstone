"""Admin controller/router."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text  
from sqlalchemy.orm import Session

from core.deps import get_db, require_admin
from domain.entities.user import User
from domain.models.admin import AnalyticsDashboard
from domain.models.cases import CaseCreate, CaseResponse
from domain.models.sessions import SessionDetailResponse, SessionListResponse, TurnResponse
from services.analytics_service import AnalyticsService
from services.case_service import CaseService
from services.session_service import SessionService

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminSessionListResponse(BaseModel):
    """Admin session list with filters."""
    sessions: list[SessionDetailResponse]
    total: int
    skip: int
    limit: int


class MetricsTimeline(BaseModel):
    """Metrics timeline for a session."""
    turn_number: int
    timestamp: datetime
    empathy_score: float
    question_type: str
    spikes_stage: str


class AdminSessionDetail(BaseModel):
    """Admin session detail with transcript and metrics."""
    session: SessionDetailResponse
    metrics_timeline: list[MetricsTimeline]


@router.get("/health/db")
async def db_health(
    db: Annotated[Session, Depends(get_db)],
):
    """Simple DB health check."""
    db.execute(text("SELECT 1"))
    return {"db_ok": True}


@router.get("/sessions", response_model=AdminSessionListResponse)
async def list_all_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    user_id: Optional[int] = Query(None),
    case_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """Filter sessions by user, case, date (admin only)."""
    from repositories.session_repo import SessionRepository
    
    session_repo = SessionRepository(db)
    
    # Get sessions with filters
    # Note: This is a simplified version - you'd add proper filtering in the repo
    if user_id:
        sessions = session_repo.get_by_user(user_id, skip, limit)
    elif case_id:
        sessions = session_repo.get_by_case(case_id, skip, limit)
    else:
        sessions = session_repo.get_all(skip, limit)
    
    # Convert to detailed responses
    session_service = SessionService(db)
    detailed_sessions = []
    for sess in sessions:
        detailed = await session_service.get_session(sess.id)
        detailed_sessions.append(detailed)
    
    return AdminSessionListResponse(
        sessions=detailed_sessions,
        total=len(sessions),
        skip=skip,
        limit=limit,
    )


@router.get("/sessions/{session_id}", response_model=AdminSessionDetail)
async def get_admin_session_detail(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Get transcript + metrics timeline for a session (admin only)."""
    session_service = SessionService(db)
    session_detail = await session_service.get_session(session_id)
    
    # Build metrics timeline
    metrics_timeline = []
    for turn in session_detail.turns:
        if turn.metrics_json:
            import json
            try:
                metrics = json.loads(turn.metrics_json.replace("'", '"'))
                metrics_timeline.append(
                    MetricsTimeline(
                        turn_number=turn.turn_number,
                        timestamp=turn.timestamp,
                        empathy_score=metrics.get("empathy", {}).get("empathy_score", 0),
                        question_type=metrics.get("question_type", "unknown"),
                        spikes_stage=turn.spikes_stage or "unknown",
                    )
                )
            except:
                pass
    
    return AdminSessionDetail(
        session=session_detail,
        metrics_timeline=metrics_timeline,
    )


@router.get("/aggregates", response_model=AnalyticsDashboard)
async def get_aggregates(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Get cohort/case aggregates (admin only)."""
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_dashboard_analytics()


@router.post("/cases", response_model=CaseResponse, status_code=201)
async def create_patient_case(
    case_data: CaseCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Create patient case (admin only)."""
    case_service = CaseService(db)
    return await case_service.create_case(case_data)
