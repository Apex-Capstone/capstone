"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    # Can be used to set test-specific configurations
    pass

