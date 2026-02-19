"""Research controller/router — read-only, admin-only, anonymized data."""

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from config.logging import get_logger
from core.deps import get_db, require_admin
from domain.entities.user import User
from services.research_service import ResearchService

logger = get_logger(__name__)
router = APIRouter(prefix="/research", tags=["research"])


@router.get("/sessions")
async def get_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Return list of anonymized sessions (no PII, admin only)."""
    service = ResearchService(db)
    sessions = service.get_all_sessions(skip=skip, limit=limit)
    return {"sessions": sessions, "total": len(sessions), "skip": skip, "limit": limit}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Return anonymized session details (no PII, admin only)."""
    service = ResearchService(db)
    try:
        session_data = service.get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_data


@router.get("/export")
async def export_research_data(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Return downloadable JSON export of anonymized research data (admin only)."""
    service = ResearchService(db)
    json_content = service.get_export_json_content()
    record_count = len(json.loads(json_content))
    logger.info(
        "Research export triggered admin_user_id=%s timestamp=%s sessions_exported=%s",
        current_user.id,
        datetime.now(timezone.utc).isoformat(),
        record_count,
    )
    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="research_export.json"',
        },
    )
