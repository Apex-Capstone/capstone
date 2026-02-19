"""Core module for security, errors, dependencies, and events."""

from core.deps import (
    get_current_user,
    get_db,
    require_role,
    require_trainee,
    require_admin,
    verify_session_access,
)
from core.errors import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
    app_error_handler,
    general_exception_handler,
    http_exception_handler,
)
from core.events import create_start_app_handler, create_stop_app_handler
from core.security import (
    RoleScopes,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

__all__ = [
    # Dependencies
    "get_db",
    "get_current_user",
    "require_trainee",
    "require_admin",
    "require_role",
    "verify_session_access",
    # Errors
    "AppError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "ExternalServiceError",
    "app_error_handler",
    "http_exception_handler",
    "general_exception_handler",
    # Security
    "RoleScopes",
    "create_access_token",
    "decode_access_token",
    "verify_password",
    "get_password_hash",
    # Events
    "create_start_app_handler",
    "create_stop_app_handler",
]

