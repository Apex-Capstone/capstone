"""SQLAlchemy base configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings

settings = get_settings()

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Create declarative base for models
Base = declarative_base()


def init_db() -> None:
    """Initialize database tables."""
    # Import all models here to ensure they are registered with Base
    from domain.entities import case, feedback, session, turn, user  # noqa: F401
    
    Base.metadata.create_all(bind=engine)

