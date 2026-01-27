from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.inbox_service_app import app


@pytest.fixture
def client():
    return TestClient(app)


def _build_payload(overrides: dict | None = None) -> dict:
    payload = {
        "provider": "chatflow",
        "channel": "whatsapp",
        "provider_message_id": "msg-123",
        "tenant_context": {
            "client_id": str(uuid4()),
            "client_slug": "demo_salon",
            "instance_id": "demo-instance",
        },
        "received_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sender": {
            "id": "77770000000",
            "phone": "77770000000",
            "jid": "77770000000@s.whatsapp.net",
            "display_name": "Tester",
        },
        "receiver": {"id": "salon-number", "phone": "77778889999"},
        "message": {"type": "text", "text": "Hi"},
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_inbox_service_disabled_returns_404(client, monkeypatch):
    monkeypatch.delenv("INBOX_SERVICE_ENABLED", raising=False)
    response = client.post("/inbox/event", json=_build_payload())
    assert response.status_code == 404


def test_inbox_service_token_required(client, monkeypatch):
    monkeypatch.setenv("INBOX_SERVICE_ENABLED", "1")
    monkeypatch.setenv("INBOX_SERVICE_TOKEN", "secret")
    response = client.post("/inbox/event", json=_build_payload())
    assert response.status_code == 401


def test_inbox_event_records_event(client, monkeypatch):
    monkeypatch.setenv("INBOX_SERVICE_ENABLED", "1")
    monkeypatch.delenv("INBOX_SERVICE_TOKEN", raising=False)

    db = Mock()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with patch(
            "app.routers.inbox_service.record_inbox_event",
            return_value=(True, "event-123"),
        ) as mock_record:
            payload = _build_payload()
            response = client.post("/inbox/event", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["event_id"] == "event-123"
            mock_record.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_db, None)
