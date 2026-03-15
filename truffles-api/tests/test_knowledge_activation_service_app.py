from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app import knowledge_activation_service_app as service_app
from app.routers import knowledge_activation_service as service_router


@pytest.mark.asyncio
async def test_knowledge_activation_service_health(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_ACTIVATION_SERVICE_ENABLED", raising=False)
    data = await service_app.health(SimpleNamespace())
    assert data["status"] == "ok"
    assert data["service"] == "knowledge_activation_service"
    assert data["knowledge_activation_enabled"] is False


@pytest.mark.asyncio
async def test_knowledge_activation_service_disabled_returns_404(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_ACTIVATION_SERVICE_ENABLED", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        await service_router.process_knowledge_activation(SimpleNamespace(headers={}), db=Mock())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_knowledge_activation_service_token_required(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_ACTIVATION_SERVICE_ENABLED", "1")
    monkeypatch.setenv("KNOWLEDGE_ACTIVATION_SERVICE_TOKEN", "secret")
    with pytest.raises(HTTPException) as exc_info:
        await service_router.process_knowledge_activation(SimpleNamespace(headers={}), db=Mock())
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_knowledge_activation_service_processes_jobs(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_ACTIVATION_SERVICE_ENABLED", "1")
    monkeypatch.setenv("KNOWLEDGE_ACTIVATION_PROCESS_LIMIT", "7")
    monkeypatch.setenv("KNOWLEDGE_ACTIVATION_STUCK_AFTER_SECONDS", "33")
    monkeypatch.delenv("KNOWLEDGE_ACTIVATION_SERVICE_TOKEN", raising=False)

    db = Mock()
    with patch(
        "app.routers.knowledge_activation_service.process_queued_knowledge_activation_jobs",
        return_value={"claimed": 2, "succeeded": 2, "failed": 0, "stuck": 1},
    ) as mock_process:
        data = await service_router.process_knowledge_activation(SimpleNamespace(headers={}), db=db)

    assert data == {"claimed": 2, "succeeded": 2, "failed": 0, "stuck": 1}
    mock_process.assert_called_once_with(
        db,
        limit=7,
        stuck_after_seconds=33,
    )
