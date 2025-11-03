"""Tests for authentication functionality."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.errors import AuthenticationError, ConflictError
from db.base import Base
from domain.models.auth import LoginRequest, UserCreate
from services.auth_service import AuthService


@pytest.fixture
def test_db():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.mark.asyncio
async def test_register_user(test_db):
    """Test user registration."""
    auth_service = AuthService(test_db)
    user_data = UserCreate(
        email="newuser@example.com",
        password="password123",
        full_name="New User",
        role="student",
    )
    
    user = await auth_service.register_user(user_data)
    
    assert user.email == "newuser@example.com"
    assert user.role == "student"
    assert user.id is not None


@pytest.mark.asyncio
async def test_register_duplicate_user(test_db):
    """Test registering duplicate user raises error."""
    auth_service = AuthService(test_db)
    user_data = UserCreate(
        email="duplicate@example.com",
        password="password123",
        role="student",
    )
    
    # First registration
    await auth_service.register_user(user_data)
    
    # Second registration should fail
    with pytest.raises(ConflictError):
        await auth_service.register_user(user_data)


@pytest.mark.asyncio
async def test_login_success(test_db):
    """Test successful login."""
    auth_service = AuthService(test_db)
    
    # Register user
    user_data = UserCreate(
        email="login@example.com",
        password="password123",
        role="student",
    )
    await auth_service.register_user(user_data)
    
    # Login
    login_data = LoginRequest(
        email="login@example.com",
        password="password123",
    )
    result = await auth_service.login(login_data)
    
    assert result.access_token is not None
    assert result.user.email == "login@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(test_db):
    """Test login with invalid password."""
    auth_service = AuthService(test_db)
    
    # Register user
    user_data = UserCreate(
        email="test@example.com",
        password="correctpassword",
        role="student",
    )
    await auth_service.register_user(user_data)
    
    # Login with wrong password
    login_data = LoginRequest(
        email="test@example.com",
        password="wrongpassword",
    )
    
    with pytest.raises(AuthenticationError):
        await auth_service.login(login_data)

