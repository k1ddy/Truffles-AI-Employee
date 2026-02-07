import json
from uuid import uuid4

import pytest
from starlette.requests import Request

from app.routers.webhook.parsing import _normalize_chatflow_payload, _parse_webhook_request
from app.schemas.webhook import WebhookRequest


def _build_json_request(payload: dict, *, query_string: str = "") -> Request:
    body = json.dumps(payload).encode("utf-8")
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/webhook",
        "query_string": query_string.encode("utf-8"),
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope, receive)


def test_normalize_chatflow_payload_extracts_tenant_context():
    tenant_context = {
        "client_id": str(uuid4()),
        "client_slug": "demo_salon",
        "source": "system",
    }
    payload = {
        "body": {
            "message": "hello",
            "metadata": {"remoteJid": "77000000000@s.whatsapp.net"},
            "tenant_context": tenant_context,
        }
    }

    body, slug, normalized_tenant_context = _normalize_chatflow_payload(payload, None)

    assert slug == "truffles"
    assert body["message"] == "hello"
    assert normalized_tenant_context == tenant_context


@pytest.mark.asyncio
async def test_parse_webhook_request_sets_tenant_context_instance_from_query():
    tenant_context = {
        "client_id": str(uuid4()),
        "client_slug": "demo_salon",
        "source": "system",
    }
    payload = {
        "body": {
            "message": "hello",
            "metadata": {"remoteJid": "77000000000@s.whatsapp.net"},
            "tenant_context": tenant_context,
        }
    }
    request = _build_json_request(payload, query_string="instanceId=inst-query")

    parsed = await _parse_webhook_request(request, client_slug="demo_salon")

    assert isinstance(parsed, WebhookRequest)
    assert parsed.client_slug == "demo_salon"
    assert parsed.body.metadata is not None
    assert parsed.body.metadata.instanceId == "inst-query"
    assert parsed.tenant_context is not None
    assert parsed.tenant_context.instance_id == "inst-query"


@pytest.mark.asyncio
async def test_parse_webhook_request_backfills_tenant_context_when_missing():
    payload = {
        "body": {
            "message": "hello",
            "metadata": {"remoteJid": "77000000000@s.whatsapp.net", "instanceId": "inst-body"},
        }
    }
    request = _build_json_request(payload)

    parsed = await _parse_webhook_request(request, client_slug="generic")

    assert isinstance(parsed, WebhookRequest)
    assert parsed.tenant_context is not None
    assert parsed.tenant_context.client_slug == "generic"
    assert parsed.tenant_context.instance_id == "inst-body"
    assert parsed.tenant_context.source == "webhook"
