"""Authentication request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """Base user schema."""
    
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "student"


class UserCreate(UserBase):
    """User creation schema."""
    
    password: str


class UserUpdate(BaseModel):
    """User update schema."""
    
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """User response schema."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, extra="ignore")



class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response schema."""
    
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    
    sub: int  # user_id
    exp: datetime
    role: str

