"""Security utilities for JWT and password hashing."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import get_settings

# Password hashing context (portable, no 72-byte limit like bcrypt)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Notes:
    - Forces `sub` to string to avoid downstream validators rejecting int subjects.
    - Adds `iat` and `nbf` claims.
    """
    settings = get_settings()
    to_encode = data.copy()

    # Ensure subject is a string (important for some validators)
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))

    to_encode.update({
        "iat": now,
        "nbf": now,
        "exp": expire,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,          # ensure this is FIXED via .env
        algorithm=settings.algorithm, # e.g., "HS256"
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode a JWT access token.

    Returns the payload dict on success, or None on any JWT error.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_aud": False},  # set True and pass 'audience' if you use aud
        )
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
