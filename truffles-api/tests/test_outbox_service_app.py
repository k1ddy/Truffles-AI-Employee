from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.outbox_service_app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_outbox_service_health(client, monkeypatch):
    monkeypatch.delenv("OUTBOX_SERVICE_ENABLED", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "outbox_service"
    assert data["outbox_enabled"] is False


def test_outbox_service_disabled_returns_404(client, monkeypatch):
    monkeypatch.delenv("OUTBOX_SERVICE_ENABLED", raising=False)
    response = client.post("/outbox/process")
    assert response.status_code == 404


def test_outbox_service_token_required(client, monkeypatch):
    monkeypatch.setenv("OUTBOX_SERVICE_ENABLED", "1")
    monkeypatch.setenv("OUTBOX_SERVICE_TOKEN", "secret")
    response = client.post("/outbox/process")
    assert response.status_code == 401


def test_outbox_service_processes(client, monkeypatch):
    monkeypatch.setenv("OUTBOX_SERVICE_ENABLED", "1")
    monkeypatch.delenv("OUTBOX_SERVICE_TOKEN", raising=False)

    db = Mock()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with patch(
            "app.routers.outbox_service.release_stale_processing",
            return_value={"released": 1, "failed": 0},
        ) as mock_release, patch(
            "app.routers.outbox_service.claim_pending_outbox_batches",
            return_value=[{"id": "row-1"}],
        ) as mock_claim, patch(
            "app.routers.outbox_service.schedule_inbound_syncs",
            return_value={"scheduled": 0, "errors": 0},
        ) as mock_inbound, patch(
            "app.routers.outbox_service.process_reminder_jobs",
            return_value={"total": 0, "sent": 0, "failed": 0},
        ) as mock_reminders, patch(
            "app.routers.webhook._process_outbox_rows",
            new=AsyncMock(return_value={"sent": 1, "failed": 0}),
        ) as mock_process:
            response = client.post("/outbox/process")
            assert response.status_code == 200
            data = response.json()
            assert data["sent"] == 1
            assert data["failed"] == 0
            assert data["released_stale"] == 1
            assert data["failed_stale"] == 0
            mock_release.assert_called_once()
            mock_claim.assert_called_once_with(
                db,
                limit=10,
                idle_seconds=8,
                max_wait_seconds=10,
                include_without_conversation=True,
            )
            mock_inbound.assert_called_once()
            mock_reminders.assert_called_once()
            mock_process.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(get_db, None)
