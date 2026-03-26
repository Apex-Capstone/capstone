"""SQLAlchemy base configuration and session management."""

from typing import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config.settings import get_settings

settings = get_settings()

# All tables default to the "core" schema
metadata = MetaData(schema="core")
Base = declarative_base(metadata=metadata)

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=0,
    pool_timeout=30,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db() -> None:
    """Initialize database tables."""
    # Import all models so they register with Base.metadata
    from domain.entities import case, feedback, session, turn, user  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Usage:
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
