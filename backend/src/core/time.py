"""Shared UTC datetime helpers for persistence and API serialization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import BeforeValidator, PlainSerializer


UTC = timezone.utc


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)


def ensure_utc_datetime(value: datetime) -> datetime:
    """Normalize a datetime to an aware UTC instant.

    Naive datetimes are interpreted as already being UTC.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_utc_datetime(value: Any) -> Any:
    """Parse incoming datetimes/strings and normalize them to UTC."""
    if value is None or isinstance(value, datetime):
        return None if value is None else ensure_utc_datetime(value)

    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        parsed = datetime.fromisoformat(normalized)
        return ensure_utc_datetime(parsed)

    return value


def serialize_utc_datetime(value: datetime) -> str:
    """Serialize a datetime as an ISO-8601 UTC string with a `Z` suffix."""
    return ensure_utc_datetime(value).isoformat().replace("+00:00", "Z")


def json_utc_default(value: Any) -> str:
    """JSON serializer for values that may contain datetimes."""
    if isinstance(value, datetime):
        return serialize_utc_datetime(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


UTCDateTime = Annotated[
    datetime,
    BeforeValidator(parse_utc_datetime),
    PlainSerializer(serialize_utc_datetime, return_type=str, when_used="json"),
]
