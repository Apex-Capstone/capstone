"""Authentication controller/router."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db
from core.security import create_access_token, decode_access_token
from domain.entities.user import User
from domain.models.auth import LoginRequest, LoginResponse, UserCreate, UserResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response."""
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """Register a new user."""
    auth_service = AuthService(db)
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Login user and return JWT tokens."""
    auth_service = AuthService(db)
    return await auth_service.login(login_data)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
):
    """Refresh access token."""
    payload = decode_access_token(refresh_data.refresh_token)
    if not payload:
        from core.errors import AuthenticationError
        raise AuthenticationError("Invalid refresh token")
    
    # Create new access token
    token_data = {"sub": payload.get("sub"), "role": payload.get("role")}
    access_token = create_access_token(token_data)
    
    return RefreshTokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user information."""
    return UserResponse.model_validate(current_user)

