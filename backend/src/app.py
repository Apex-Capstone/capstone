"""FastAPI application instance and router mounting."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.logging import setup_logging
from config.settings import get_settings
from controllers import (
    admin_controller,
    auth_controller,
    cases_controller,
    research_controller,
    sessions_controller,
    ws_controller,
)
from core.errors import (
    AppError,
    app_error_handler,
    general_exception_handler,
    http_exception_handler,
)
from core.events import create_start_app_handler, create_stop_app_handler

# Get settings
settings = get_settings()

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Medical Case Simulation API",
    description="AI-powered medical case simulation with SPIKES protocol",
    version="1.0.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register event handlers
app.add_event_handler("startup", create_start_app_handler(app))
app.add_event_handler("shutdown", create_stop_app_handler(app))

# Register error handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register routers with /v1 prefix
app.include_router(auth_controller.router, prefix="/v1")
app.include_router(cases_controller.router, prefix="/v1")
app.include_router(sessions_controller.router, prefix="/v1")
app.include_router(admin_controller.router, prefix="/v1")
app.include_router(research_controller.router, prefix="/v1")
app.include_router(ws_controller.router, prefix="/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Medical Case Simulation API",
        "version": "0.1.0",
        "docs": "/api/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

