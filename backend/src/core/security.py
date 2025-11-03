"""Security utilities for JWT and password hashing."""

from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import get_settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode a JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


# Role-based access control scopes
class RoleScopes:
    """Define role-based access scopes."""
    
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"
    RESEARCHER = "researcher"
    
    @classmethod
    def get_all_scopes(cls) -> list[str]:
        """Get all available role scopes."""
        return [cls.STUDENT, cls.INSTRUCTOR, cls.ADMIN, cls.RESEARCHER]
    
    @classmethod
    def has_permission(cls, user_role: str, required_role: str) -> bool:
        """Check if user role has permission for required role."""
        role_hierarchy = {
            cls.ADMIN: [cls.ADMIN, cls.INSTRUCTOR, cls.RESEARCHER, cls.STUDENT],
            cls.INSTRUCTOR: [cls.INSTRUCTOR, cls.STUDENT],
            cls.RESEARCHER: [cls.RESEARCHER],
            cls.STUDENT: [cls.STUDENT],
        }
        return required_role in role_hierarchy.get(user_role, [])

