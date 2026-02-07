from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker, RefResolver

from app.adapters.provider_gateway import ProviderGatewayAdapter
from app.database import get_db
from app.main import app
from app.ports.messaging import MessageOptions
from app.services.provider_gateway_service import build_provider_outbound_payload


@pytest.fixture
def client():
    return TestClient(app)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_schema(relative_path: str) -> Draft202012Validator:
    schema_path = _repo_root() / relative_path
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    store = _schema_store(schema)
    resolver = RefResolver(base_uri=schema_path.resolve().as_uri(), referrer=schema, store=store)
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _validate_schema(relative_path: str, payload: dict) -> None:
    _load_schema(relative_path).validate(payload)


def _schema_store(schema: dict) -> dict[str, dict]:
    store: dict[str, dict] = {}
    schema_id = schema.get("$id")
    if isinstance(schema_id, str):
        store[schema_id] = schema

    tenant_path = _repo_root() / "contracts/tenancy/tenant_context.v1.jsonschema"
    tenant_schema = json.loads(tenant_path.read_text(encoding="utf-8"))
    tenant_id = tenant_schema.get("$id")
    if isinstance(tenant_id, str):
        store[tenant_id] = tenant_schema
    store[tenant_path.resolve().as_uri()] = tenant_schema
    return store


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
    signed_url = "https://example.com/media.jpg?expires=1700000000&sig=abc"
    expected_expires_at = datetime.fromtimestamp(1700000000, tz=timezone.utc).isoformat()
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context=_tenant_context(),
        remote_jid="77770000000@s.whatsapp.net",
        text=None,
        media={
            "media_type": "image",
            "signed_url": signed_url,
            "caption": "Caption",
        },
        idempotency_key="idem-2",
        callback_url="https://example.com/provider/status",
        metadata={"event_type": "whatsapp.send_media"},
    )

    assert error is None
    assert payload is not None
    assert payload["content"]["media"]["media_type"] == "image"
    assert payload["content"]["media"]["signed_url"] == signed_url
    assert payload["content"]["media"]["expires_at"] == expected_expires_at


def test_build_provider_outbound_payload_media_missing_signed_url():
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context=_tenant_context(),
        remote_jid="77770000000@s.whatsapp.net",
        text=None,
        media={
            "media_type": "image",
            "source_url": "https://example.com/media.jpg",
        },
        idempotency_key="idem-2",
        callback_url="https://example.com/provider/status",
        metadata={"event_type": "whatsapp.send_media"},
    )

    assert payload is None
    assert error == "missing_media_signed_url"


def test_build_provider_outbound_payload_media_missing_expires():
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
        },
        idempotency_key="idem-2",
        callback_url="https://example.com/provider/status",
        metadata={"event_type": "whatsapp.send_media"},
    )

    assert payload is None
    assert error == "missing_media_expires_at"


def test_provider_gateway_adapter_send_media_adds_ttl(monkeypatch):
    signed_url = "https://example.com/media.jpg?expires=1700000000&sig=abc"
    expected_expires_at = datetime.fromtimestamp(1700000000, tz=timezone.utc).isoformat()
    captured: dict = {}

    def _fake_post(url, json, headers=None, timeout=None):
        captured["payload"] = json
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"provider_message_id": "msg-1"}
        return response

    monkeypatch.setenv("PROVIDER_GATEWAY_OUTBOUND_URL", "https://example.com/outbound")
    monkeypatch.setenv("PROVIDER_GATEWAY_TOKEN", "test-token")
    monkeypatch.setenv("PROVIDER_GATEWAY_STATUS_CALLBACK_URL", "https://example.com/status")

    with patch("app.adapters.provider_gateway.httpx.post", side_effect=_fake_post):
        adapter = ProviderGatewayAdapter()
        options = MessageOptions(
            idempotency_key="idem-3",
            extra={
                "outbox_id": str(uuid4()),
                "tenant_context": _tenant_context(),
                "provider": "chatflow",
                "channel": "whatsapp",
            },
        )
        result = adapter.send_media(
            "77770000000@s.whatsapp.net",
            signed_url,
            "image",
            options,
        )

    assert result.is_ok()
    payload = captured["payload"]
    assert payload["content"]["media"]["signed_url"] == signed_url
    assert payload["content"]["media"]["expires_at"] == expected_expires_at


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


def test_build_provider_outbound_payload_rejects_invalid_tenant_context_contract():
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context={
            **_tenant_context(),
            "source": "provider_gateway",
        },
        remote_jid="77770000000@s.whatsapp.net",
        text="Hello",
        idempotency_key="idem-1",
        callback_url=None,
    )

    assert payload is None
    assert error == "invalid_tenant_context_contract"


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


def test_provider_status_rejects_invalid_tenant_context_source(client, monkeypatch):
    monkeypatch.setenv("PROVIDER_GATEWAY_STATUS_ENABLED", "1")
    monkeypatch.delenv("PROVIDER_GATEWAY_TOKEN", raising=False)

    payload = {
        "provider": "chatflow",
        "channel": "whatsapp",
        "provider_message_id": "msg-1",
        "tenant_context": {
            **_tenant_context(),
            "source": "provider_gateway",
        },
        "status": "sent",
        "status_at": datetime.now(timezone.utc).isoformat(),
        "outbox_id": str(uuid4()),
    }
    with patch("app.routers.provider_gateway.update_outbox_status_from_provider") as mock_update:
        response = client.post("/provider/status", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Invalid tenant_context contract"
    mock_update.assert_not_called()


def test_provider_outbound_contract_text():
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context=_tenant_context(),
        remote_jid="77770000000@s.whatsapp.net",
        text="Hello",
        idempotency_key="idem-10",
        callback_url="https://example.com/provider/status",
    )

    assert error is None
    assert payload is not None
    _validate_schema("contracts/integrations/provider_outbound.v1.jsonschema", payload)


def test_provider_outbound_contract_media():
    signed_url = "https://example.com/media.jpg?expires=1700000000&sig=abc"
    payload, error = build_provider_outbound_payload(
        outbox_id=str(uuid4()),
        provider="chatflow",
        channel="whatsapp",
        tenant_context=_tenant_context(),
        remote_jid="77770000000@s.whatsapp.net",
        text=None,
        media={
            "media_type": "image",
            "signed_url": signed_url,
            "caption": "Caption",
        },
        idempotency_key="idem-11",
        callback_url="https://example.com/provider/status",
    )

    assert error is None
    assert payload is not None
    _validate_schema("contracts/integrations/provider_outbound.v1.jsonschema", payload)


def test_provider_status_contract_valid():
    payload = {
        "provider": "chatflow",
        "channel": "whatsapp",
        "provider_message_id": "msg-1",
        "tenant_context": _tenant_context(),
        "status": "sent",
        "status_at": datetime.now(timezone.utc).isoformat(),
        "outbox_id": str(uuid4()),
    }

    _validate_schema("contracts/events/provider_status.v1.jsonschema", payload)


def test_media_send_contract_valid():
    payload = {
        "media_id": "media-1",
        "tenant_context": _tenant_context(),
        "media_type": "image",
        "signed_url": "https://example.com/media.jpg?sig=abc",
        "expires_at": datetime.now(timezone.utc).isoformat(),
        "caption": "Hello",
    }

    _validate_schema("contracts/integrations/media_send.v1.jsonschema", payload)


def test_mock_provider_validates_outbound_text(monkeypatch):
    outbound_url = "https://mock-provider.local/outbound"

    def _fake_post(url, json, headers=None, timeout=None):
        _validate_schema("contracts/integrations/provider_outbound.v1.jsonschema", json)
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"provider_message_id": "mock-1"}
        return response

    with patch("app.adapters.provider_gateway.httpx.post", side_effect=_fake_post):
        adapter = ProviderGatewayAdapter(base_url=outbound_url, token="token")
        options = MessageOptions(
            idempotency_key="idem-12",
            extra={
                "outbox_id": str(uuid4()),
                "tenant_context": _tenant_context(),
                "provider": "chatflow",
                "channel": "whatsapp",
            },
        )
        result = adapter.send_text("77770000000@s.whatsapp.net", "Hello", options)

    assert result.is_ok()


def test_mock_provider_validates_outbound_media():
    outbound_url = "https://mock-provider.local/outbound"

    def _fake_post(url, json, headers=None, timeout=None):
        _validate_schema("contracts/integrations/provider_outbound.v1.jsonschema", json)
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"provider_message_id": "mock-2"}
        return response

    with patch("app.adapters.provider_gateway.httpx.post", side_effect=_fake_post):
        adapter = ProviderGatewayAdapter(base_url=outbound_url, token="token")
        options = MessageOptions(
            idempotency_key="idem-13",
            extra={
                "outbox_id": str(uuid4()),
                "tenant_context": _tenant_context(),
                "provider": "chatflow",
                "channel": "whatsapp",
            },
        )
        result = adapter.send_media(
            "77770000000@s.whatsapp.net",
            "https://example.com/media.jpg?expires=1700000000&sig=abc",
            "image",
            options,
        )

    assert result.is_ok()
