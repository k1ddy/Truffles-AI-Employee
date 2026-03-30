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
    monkeypatch.delenv("OUTBOX_SERVICE_TOKEN", raising=False)

    db = Mock()
    with patch(
        "app.routers.outbox_service.run_default_outbox_process",
        new=AsyncMock(return_value={"sent": 1, "failed": 0, "released_stale": 1, "failed_stale": 0}),
    ) as mock_run:
        data = await service_router.process_outbox(SimpleNamespace(headers={}), db=db)

    assert data["sent"] == 1
    assert data["failed"] == 0
    assert data["released_stale"] == 1
    assert data["failed_stale"] == 0
    mock_run.assert_awaited_once_with(db, include_reminders=True)
