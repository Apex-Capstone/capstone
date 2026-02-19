"""FastAPI dependencies for database sessions and authentication."""

from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from config.logging import get_logger
from core.errors import AuthenticationError, AuthorizationError
from core.security import RoleScopes, decode_access_token
from db.base import SessionLocal
from domain.entities.user import User
from repositories.user_repo import UserRepository

logger = get_logger(__name__)
security = HTTPBearer()


# Database dependency
def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Authentication dependency
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise AuthenticationError("Invalid or expired token")
    
    user_id: int = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise AuthenticationError("User not found")
    
    return user


# Role-based dependencies
def require_role(required_role: str):
    """Dependency factory for role-based access control."""
    
    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        """Check if user has required role."""
        if not RoleScopes.has_permission(current_user.role, required_role):
            raise AuthorizationError(
                f"Access denied. Required role: {required_role}",
                details={"user_role": current_user.role, "required_role": required_role}
            )
        return current_user
    
    return role_checker


# Convenience role dependencies
def require_trainee(
    current_user: Annotated[User, Depends(require_role(RoleScopes.TRAINEE))]
) -> User:
    """Ensure current user has at least trainee permissions."""
    return current_user


def require_admin(
    current_user: Annotated[User, Depends(require_role(RoleScopes.ADMIN))]
) -> User:
    """Ensure current user is an admin."""
    return current_user


def verify_session_access(session, current_user: User) -> None:
    """
    Verify the current user has access to the session.
    - Admin: allow access to any session.
    - Trainee: only allow if session.user_id == current_user.id.
    - Otherwise: raise AuthorizationError (403).
    """
    if current_user.role == "admin":
        return
    if current_user.role == "trainee" and getattr(session, "user_id", None) == current_user.id:
        return
    raise AuthorizationError("Not authorized to access this session")

