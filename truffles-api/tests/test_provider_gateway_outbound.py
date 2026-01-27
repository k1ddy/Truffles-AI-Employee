from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services.provider_gateway_service import build_provider_outbound_payload


@pytest.fixture
def client():
    return TestClient(app)


def _tenant_context():
    return {
        "client_id": str(uuid4()),
        "client_slug": "demo_salon",
        "instance_id": "demo-instance",
    }


def test_build_provider_outbound_payload_ok():
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context=_tenant_context(),
        remote_jid="77770000000@s.whatsapp.net",
        text="Hello",
        idempotency_key="idem-1",
        callback_url="https://example.com/provider/status",
        metadata={"event_type": "whatsapp.send_text"},
    )

    assert error is None
    assert payload is not None
    assert payload["provider"] == "chatflow"
    assert payload["channel"] == "whatsapp"
    assert payload["content"]["text"] == "Hello"
    assert payload["to"]["jid"] == "77770000000@s.whatsapp.net"
    assert payload["idempotency_key"] == "idem-1"


def test_build_provider_outbound_payload_media_ok():
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context=_tenant_context(),
        remote_jid="77770000000@s.whatsapp.net",
        text=None,
        media={
            "media_type": "image",
            "signed_url": "https://example.com/media.jpg",
            "caption": "Caption",
        },
        idempotency_key="idem-2",
        callback_url="https://example.com/provider/status",
        metadata={"event_type": "whatsapp.send_media"},
    )

    assert error is None
    assert payload is not None
    assert payload["content"]["media"]["media_type"] == "image"
    assert payload["content"]["media"]["signed_url"] == "https://example.com/media.jpg"


def test_build_provider_outbound_payload_missing_tenant():
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context=None,
        remote_jid="77770000000@s.whatsapp.net",
        text="Hello",
        idempotency_key="idem-1",
        callback_url=None,
    )

    assert payload is None
    assert error == "missing_tenant_context"


def test_provider_status_disabled_returns_404(client, monkeypatch):
    monkeypatch.delenv("PROVIDER_GATEWAY_STATUS_ENABLED", raising=False)
    response = client.post("/provider/status", json={})
    assert response.status_code == 404


def test_provider_status_calls_update(client, monkeypatch):
    monkeypatch.setenv("PROVIDER_GATEWAY_STATUS_ENABLED", "1")
    monkeypatch.delenv("PROVIDER_GATEWAY_TOKEN", raising=False)

    db = Mock()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        payload = {
            "provider": "chatflow",
            "channel": "whatsapp",
            "provider_message_id": "msg-1",
            "tenant_context": _tenant_context(),
            "status": "sent",
            "status_at": datetime.now(timezone.utc).isoformat(),
            "outbox_id": str(uuid4()),
        }
        with patch(
            "app.routers.provider_gateway.update_outbox_status_from_provider",
            return_value=(True, "ok"),
        ) as mock_update:
            response = client.post("/provider/status", json=payload)
            assert response.status_code == 200
            assert response.json()["success"] is True
            mock_update.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_db, None)
