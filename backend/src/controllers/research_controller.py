"""Research controller/router — read-only, admin-only, anonymized data."""

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from config.logging import get_logger
from core.deps import get_db, require_admin
from domain.entities.user import User
from domain.models.admin import ResearchSessionsEnvelope
from services.research_service import ResearchService

logger = get_logger(__name__)
router = APIRouter(prefix="/research", tags=["research"])


@router.get("/sessions", response_model=ResearchSessionsEnvelope)
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


@router.get("/sessions/{anon_session_id}")
async def get_session(
    anon_session_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Return anonymized session details by anon_session_id (no PII, admin only)."""
    service = ResearchService(db)
    try:
        session_data = service.get_session_by_anon(anon_session_id)
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


@router.get("/export/metrics.csv")
async def export_metrics_csv(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Stream metrics CSV: one row per session (admin only)."""
    service = ResearchService(db)
    logger.info(
        "Research metrics CSV export admin_user_id=%s timestamp=%s",
        current_user.id,
        datetime.now(timezone.utc).isoformat(),
    )
    return StreamingResponse(
        service.stream_metrics_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="session_metrics.csv"',
        },
    )


@router.get("/export/transcripts.csv")
async def export_transcripts_csv(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Stream all transcripts CSV: flattened rows with anonymized text (admin only)."""
    service = ResearchService(db)
    logger.info(
        "Research transcripts CSV export admin_user_id=%s timestamp=%s",
        current_user.id,
        datetime.now(timezone.utc).isoformat(),
    )
    return StreamingResponse(
        service.stream_transcripts_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="all_transcripts.csv"',
        },
    )


@router.get("/export/session/{anon_session_id}.csv")
async def export_session_transcript_csv(
    anon_session_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Stream single session transcript CSV by anon_session_id (admin only)."""
    service = ResearchService(db)
    try:
        stream = service.stream_session_transcript_csv(anon_session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    safe_anon = "".join(c if c.isalnum() or c == "_" else "_" for c in anon_session_id)[:32]
    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="session_{safe_anon}.csv"',
        },
    )


@router.get("/export.csv")
async def export_research_csv(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Return downloadable CSV export of anonymized flattened session+turns (admin only)."""
    service = ResearchService(db)
    csv_content = service.get_export_csv_content()
    logger.info(
        "Research CSV export triggered admin_user_id=%s timestamp=%s",
        current_user.id,
        datetime.now(timezone.utc).isoformat(),
    )
    return StreamingResponse(
        iter([csv_content.encode("utf-8")]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="research_export.csv"',
        },
    )
