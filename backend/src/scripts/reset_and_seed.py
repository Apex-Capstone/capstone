"""
Dev-only script to hard reset the `core` schema and seed users + cases.

Do not run this as a Render (or other production) pre-deploy hook: it executes
`DROP SCHEMA IF EXISTS core CASCADE`, which deletes all application data on every run.

Usage (from backend/):
  poetry run python -m src.scripts.reset_and_seed
"""

import asyncio

from sqlalchemy import text

from db.base import engine, init_db, SessionLocal
from scripts.seed import seed  # reuse existing seed(db, do_reset=False)


async def reset_and_seed() -> None:
    # 1) Drop & recreate the core schema
    print("Dropping and recreating core schema...")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS core CASCADE;"))
        conn.execute(text("CREATE SCHEMA core;"))

    # 2) Recreate tables from SQLAlchemy models
    print("Running init_db() to create tables...")
    init_db()

    # 3) Seed users + cases
    print("Seeding dev data (admin, trainees, cases)...")
    db = SessionLocal()
    try:
        await seed(db, do_reset=False)
    finally:
        db.close()

    print("Reset + seed complete.")


def main() -> None:
    asyncio.run(reset_and_seed())


if __name__ == "__main__":
    main()
