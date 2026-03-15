from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from app import outbox_service_app as service_app
from app.routers import outbox_service as service_router


@pytest.mark.asyncio
async def test_outbox_service_health(monkeypatch):
    monkeypatch.delenv("OUTBOX_SERVICE_ENABLED", raising=False)
    data = await service_app.health(SimpleNamespace())
    assert data["status"] == "ok"
    assert data["service"] == "outbox_service"
    assert data["outbox_enabled"] is False


@pytest.mark.asyncio
async def test_outbox_service_disabled_returns_404(monkeypatch):
    monkeypatch.delenv("OUTBOX_SERVICE_ENABLED", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        await service_router.process_outbox(SimpleNamespace(headers={}), db=Mock())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_outbox_service_token_required(monkeypatch):
    monkeypatch.setenv("OUTBOX_SERVICE_ENABLED", "1")
    monkeypatch.setenv("OUTBOX_SERVICE_TOKEN", "secret")
    with pytest.raises(HTTPException) as exc_info:
        await service_router.process_outbox(SimpleNamespace(headers={}), db=Mock())
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_outbox_service_processes(monkeypatch):
    monkeypatch.setenv("OUTBOX_SERVICE_ENABLED", "1")
    monkeypatch.setenv("OUTBOX_COALESCE_SECONDS", "8")
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "10")
    monkeypatch.delenv("OUTBOX_SERVICE_TOKEN", raising=False)

    db = Mock()
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
        data = await service_router.process_outbox(SimpleNamespace(headers={}), db=db)

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
