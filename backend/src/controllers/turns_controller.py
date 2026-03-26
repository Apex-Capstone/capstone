"""Turn media controller/router."""

import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from adapters.storage import get_storage_adapter
from core.deps import get_current_user, get_db, verify_session_access
from core.errors import NotFoundError
from core.time import utc_now
from domain.entities.user import User
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository
from services.audio_cache_service import AudioCacheService

router = APIRouter(prefix="/turns", tags=["turns"])


@router.get("/{turn_id}/audio")
async def get_turn_audio(
    turn_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Serve assistant audio from cache or remote storage."""
    turn_repo = TurnRepository(db)
    turn = turn_repo.get_by_id(turn_id)
    if not turn or not turn.audio_url or turn.role != "assistant":
        raise NotFoundError(f"Audio not found for turn {turn_id}")

    if turn.audio_expires_at and turn.audio_expires_at <= utc_now():
        raise NotFoundError(f"Audio expired for turn {turn_id}")

    session = SessionRepository(db).get_by_id(turn.session_id)
    if not session:
        raise NotFoundError(f"Session {turn.session_id} not found")
    verify_session_access(session, current_user)

    cache_service = AudioCacheService()
    cached_path = cache_service.get_cached_path(turn.audio_url)
    if cached_path is None:
        file_data = await get_storage_adapter().get_file(turn.audio_url)
        cached_path = cache_service.cache_file(turn.audio_url, file_data)

    media_type = mimetypes.guess_type(str(Path(turn.audio_url)))[0] or "application/octet-stream"
    return FileResponse(
        path=str(cached_path),
        media_type=media_type,
        filename=Path(turn.audio_url).name,
    )
