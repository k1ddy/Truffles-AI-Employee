from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.schemas.provider_gateway import ProviderInbound
from app.schemas.webhook import WebhookResponse
from app.services.provider_gateway_service import translate_provider_inbound


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
        "message": {"type": "text", "text": "Привет"},
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_provider_inbound_disabled_returns_404(client, monkeypatch):
    monkeypatch.delenv("PROVIDER_GATEWAY_INBOUND_ENABLED", raising=False)
    response = client.post("/provider/inbound", json=_build_payload())
    assert response.status_code == 404


def test_provider_inbound_token_required(client, monkeypatch):
    monkeypatch.setenv("PROVIDER_GATEWAY_INBOUND_ENABLED", "1")
    monkeypatch.setenv("PROVIDER_GATEWAY_TOKEN", "secret")
    response = client.post("/provider/inbound", json=_build_payload())
    assert response.status_code == 401


def test_provider_inbound_routes_to_webhook(client, monkeypatch):
    monkeypatch.setenv("PROVIDER_GATEWAY_INBOUND_ENABLED", "1")
    monkeypatch.delenv("PROVIDER_GATEWAY_TOKEN", raising=False)

    db = Mock()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with patch(
            "app.routers.provider_gateway.legacy._handle_webhook_payload",
            new_callable=AsyncMock,
        ) as mock_handle:
            mock_handle.return_value = WebhookResponse(
                success=True,
                message="ok",
                conversation_id=uuid4(),
                bot_response="reply",
            )

            payload = _build_payload()
            response = client.post("/provider/inbound", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            webhook_request = mock_handle.call_args.args[0]
            assert webhook_request.client_slug == "demo_salon"
            assert webhook_request.body.message == "Привет"
            assert webhook_request.body.metadata.remoteJid == "77770000000@s.whatsapp.net"
            assert webhook_request.body.metadata.messageId == "msg-123"
            assert webhook_request.body.metadata.instanceId == "demo-instance"
            assert isinstance(webhook_request.body.metadata.timestamp, int)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_translate_provider_inbound_requires_client_slug():
    payload = _build_payload({"tenant_context": {"client_id": str(uuid4())}})
    inbound = ProviderInbound.model_validate(payload)
    request, error = translate_provider_inbound(inbound)
    assert request is None
    assert error == "client_slug_required"
