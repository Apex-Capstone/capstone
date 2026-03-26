"""Authentication request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """Base user schema."""
    
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "trainee"


class UserUpdate(BaseModel):
    """User update schema."""
    
    full_name: Optional[str] = None
    role: Optional[str] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    year_of_study: Optional[str] = None


class UserResponse(UserBase):
    """User response schema returned by /auth/me and admin endpoints."""
    
    id: int
    gender: Optional[str] = None
    race: Optional[str] = None
    year_of_study: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, extra="ignore")
