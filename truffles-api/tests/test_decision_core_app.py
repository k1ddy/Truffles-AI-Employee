from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.decision_core_app import app
from app.schemas.webhook import WebhookResponse


@pytest.fixture
def client():
    return TestClient(app)


def _build_payload(overrides: dict | None = None) -> dict:
    payload = {
        "body": {
            "messageType": "text",
            "message": "Hello",
            "metadata": {
                "remoteJid": "77770000000@s.whatsapp.net",
                "messageId": "msg-123",
                "timestamp": int(time.time()),
            },
        },
        "client_slug": "demo_salon",
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_decision_core_health(client, monkeypatch):
    monkeypatch.delenv("DECISION_CORE_ENABLED", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "decision_core"
    assert data["decision_enabled"] is False


def test_decision_core_disabled_returns_404(client, monkeypatch):
    monkeypatch.delenv("DECISION_CORE_ENABLED", raising=False)
    response = client.post("/decision/handle", json=_build_payload())
    assert response.status_code == 404


def test_decision_core_token_required(client, monkeypatch):
    monkeypatch.setenv("DECISION_CORE_ENABLED", "1")
    monkeypatch.setenv("DECISION_CORE_TOKEN", "secret")
    response = client.post("/decision/handle", json=_build_payload())
    assert response.status_code == 401


def test_decision_core_accepts_payload(client, monkeypatch):
    monkeypatch.setenv("DECISION_CORE_ENABLED", "1")
    monkeypatch.delenv("DECISION_CORE_TOKEN", raising=False)
    with patch(
        "app.routers.decision_core.reasoning_core.handle_webhook_payload",
        new=AsyncMock(return_value=WebhookResponse(success=True, message="ok")),
    ) as mock_handle:
        response = client.post("/decision/handle", json=_build_payload())
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "ok"
        mock_handle.assert_awaited_once()
