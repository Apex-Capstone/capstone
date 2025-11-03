"""Authentication service."""

from typing import Optional

from sqlalchemy.orm import Session

from core.errors import AuthenticationError, ConflictError
from core.security import create_access_token, get_password_hash, verify_password
from domain.entities.user import User
from domain.models.auth import LoginRequest, LoginResponse, UserCreate, UserResponse
from repositories.user_repo import UserRepository


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register a new user."""
        # Check if user already exists
        existing_user = self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise ConflictError("User with this email already exists")
        
        # Create user entity
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
        )
        
        # Save to database
        created_user = self.user_repo.create(user)
        
        return UserResponse.model_validate(created_user)
    
    async def login(self, login_data: LoginRequest) -> LoginResponse:
        """Authenticate user and return access token."""
        # Get user by email
        user = self.user_repo.get_by_email(login_data.email)
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        
        # Create access token
        token_data = {"sub": user.id, "role": user.role}
        access_token = create_access_token(token_data)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    
    async def get_user_by_id(self, user_id: int) -> Optional[UserResponse]:
        """Get user by ID."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return None
        return UserResponse.model_validate(user)

