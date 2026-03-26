"""Cleanup service for expired assistant audio."""

from datetime import datetime

from sqlalchemy.orm import Session

from adapters.storage.base import StorageAdapter
from config.logging import get_logger
from core.time import ensure_utc_datetime, utc_now
from repositories.turn_repo import TurnRepository
from services.audio_cache_service import AudioCacheService

logger = get_logger(__name__)


class AudioCleanupService:
    """Delete expired assistant audio from remote storage, cache, and DB."""

    def __init__(
        self,
        db: Session,
        storage_adapter: StorageAdapter,
        cache_service: AudioCacheService | None = None,
    ) -> None:
        self.db = db
        self.storage_adapter = storage_adapter
        self.cache_service = cache_service or AudioCacheService()
        self.turn_repo = TurnRepository(db)

    async def cleanup_expired_audio(
        self,
        now: datetime | None = None,
        limit: int | None = None,
    ) -> int:
        """Clean expired assistant audio and return the number of cleared turns."""
        cutoff = utc_now() if now is None else ensure_utc_datetime(now)
        expired_turns = self.turn_repo.get_expired_assistant_audio(cutoff, limit=limit)
        cleaned_count = 0

        for turn in expired_turns:
            object_key = turn.audio_url
            if not object_key:
                continue

            try:
                await self.storage_adapter.delete_file(object_key)
            except Exception as exc:
                logger.warning(
                    "Failed deleting expired audio for turn %s (%s): %s",
                    turn.id,
                    object_key,
                    exc,
                )
                continue

            self.cache_service.delete_cached_file(object_key)
            turn.audio_url = None
            turn.audio_expires_at = None
            cleaned_count += 1

        if cleaned_count:
            self.db.commit()

        return cleaned_count
