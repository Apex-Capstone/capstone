"""Authentication controller/router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db
from domain.entities.user import User
from domain.models.auth import UserResponse
from repositories.user_repo import UserRepository

router = APIRouter(prefix="/auth", tags=["authentication"])


class EmailExistsResponse(BaseModel):
    """Response model for email-availability checks."""

    exists: bool


@router.get("/email-exists", response_model=EmailExistsResponse)
async def email_exists(
    db: Annotated[Session, Depends(get_db)],
    email: EmailStr = Query(...),
):
    """Check whether an account already exists for the given email."""
    user = UserRepository(db).get_by_email(str(email).lower())
    return EmailExistsResponse(exists=user is not None)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)
