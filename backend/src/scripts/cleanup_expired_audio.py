"""Delete expired assistant audio from storage, cache, and DB."""

import argparse
import asyncio

from adapters.storage import get_storage_adapter
from db.base import SessionLocal
from services.audio_cleanup_service import AudioCleanupService


async def amain(limit: int | None) -> None:
    db = SessionLocal()
    try:
        service = AudioCleanupService(
            db=db,
            storage_adapter=get_storage_adapter(),
        )
        cleaned_count = await service.cleanup_expired_audio(limit=limit)
        print(f"Cleaned {cleaned_count} expired assistant audio objects.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean expired assistant audio.")
    parser.add_argument("--limit", type=int, default=None, help="Max expired audio rows to process")
    args = parser.parse_args()
    asyncio.run(amain(limit=args.limit))


if __name__ == "__main__":
    main()
