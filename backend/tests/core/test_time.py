from datetime import datetime, timedelta, timezone

from core.time import ensure_utc_datetime, parse_utc_datetime, serialize_utc_datetime


def test_ensure_utc_datetime_treats_naive_values_as_utc():
    value = datetime(2026, 1, 2, 3, 4, 5)

    normalized = ensure_utc_datetime(value)

    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 3
    assert normalized.minute == 4


def test_ensure_utc_datetime_converts_aware_values_to_utc():
    value = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=-5)))

    normalized = ensure_utc_datetime(value)

    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 8


def test_parse_and_serialize_utc_datetime_round_trip_with_z_suffix():
    parsed = parse_utc_datetime("2026-01-02T03:04:05")

    assert parsed.tzinfo == timezone.utc
    assert serialize_utc_datetime(parsed) == "2026-01-02T03:04:05Z"
