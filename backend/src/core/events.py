"""Application startup and shutdown event handlers."""

from fastapi import FastAPI

from config.logging import get_logger, setup_logging
from db.base import engine

logger = get_logger(__name__)


def create_start_app_handler(app: FastAPI):
    """Create application startup handler."""
    
    async def start_app() -> None:
        """Execute startup tasks."""
        logger.info("Starting application...")
        
        # Setup logging
        setup_logging()
        logger.info("Logging configured")
        
        # Test database connection
        try:
            with engine.connect() as conn:
                logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
        
        logger.info("Application startup complete")
    
    return start_app


def create_stop_app_handler(app: FastAPI):
    """Create application shutdown handler."""
    
    async def stop_app() -> None:
        """Execute shutdown tasks."""
        logger.info("Shutting down application...")
        
        # Close database connections
        engine.dispose()
        logger.info("Database connections closed")
        
        logger.info("Application shutdown complete")
    
    return stop_app

