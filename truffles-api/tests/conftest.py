from unittest.mock import Mock

import pytest


@pytest.fixture
def db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_env(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("QDRANT_API_KEY", "test-key")
