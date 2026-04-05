"""Unit tests for Supabase JWT decoding and role scopes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from jose import jwt

from core.security import RoleScopes, decode_supabase_token

JWT_SECRET = "unit-test-supabase-jwt-secret-key"


@pytest.fixture
def jwt_secret() -> str:
    return JWT_SECRET


@patch("core.security.get_settings")
def test_decode_supabase_token_valid(mock_get_settings, jwt_secret: str) -> None:
    mock_get_settings.return_value.supabase_jwt_secret = jwt_secret
    sub = str(uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "exp": now + timedelta(hours=1),
        "iat": now,
    }
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    decoded = decode_supabase_token(token)
    assert decoded is not None
    assert decoded["sub"] == sub


@patch("core.security.get_settings")
def test_decode_supabase_token_expired(mock_get_settings, jwt_secret: str) -> None:
    mock_get_settings.return_value.supabase_jwt_secret = jwt_secret
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid4()),
        "exp": now - timedelta(hours=1),
        "iat": now - timedelta(hours=2),
    }
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    assert decode_supabase_token(token) is None


@patch("core.security.get_settings")
def test_decode_supabase_token_wrong_secret(mock_get_settings, jwt_secret: str) -> None:
    mock_get_settings.return_value.supabase_jwt_secret = jwt_secret
    token = jwt.encode({"sub": str(uuid4())}, "different-secret", algorithm="HS256")
    assert decode_supabase_token(token) is None


@patch("core.security.get_settings")
def test_decode_supabase_token_malformed(mock_get_settings, jwt_secret: str) -> None:
    mock_get_settings.return_value.supabase_jwt_secret = jwt_secret
    assert decode_supabase_token("not-a-jwt") is None


@pytest.mark.parametrize(
    ("user_role", "required", "expected"),
    [
        ("admin", "admin", True),
        ("admin", "trainee", True),
        ("trainee", "trainee", True),
        ("trainee", "admin", False),
        ("guest", "trainee", False),
    ],
)
def test_role_scopes_has_permission(
    user_role: str, required: str, expected: bool
) -> None:
    assert RoleScopes.has_permission(user_role, required) is expected


def test_role_scopes_get_all_scopes() -> None:
    scopes = RoleScopes.get_all_scopes()
    assert RoleScopes.TRAINEE in scopes
    assert RoleScopes.ADMIN in scopes
