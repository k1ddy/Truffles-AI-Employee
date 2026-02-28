from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.contracts import Err, ErrorCodes, IntegrationError, Ok
from app.models import Conversation, OutboxMessage
from app.ports.messaging import MessageSent
from app.routers.webhook import _legacy as legacy
from app.routers.webhook import outbox as outbox_router
from app.schemas.provider_gateway import ProviderStatus
from app.services.provider_gateway_service import update_outbox_status_from_provider


class _Query:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


def _make_db(outbox: OutboxMessage | None = None, conversation: Conversation | None = None):
    db = Mock()

    def _query(model):
        if model is OutboxMessage:
            return _Query(outbox)
        if model is Conversation:
            return _Query(conversation)
        return _Query(None)

    db.query.side_effect = _query
    return db


def _make_status(*, outbox_id: str, client_id: str, branch_id: str | None = None) -> ProviderStatus:
    return ProviderStatus.model_validate(
        {
            "provider": "chatflow",
            "channel": "whatsapp",
            "provider_message_id": "msg-1",
            "tenant_context": {
                "client_id": client_id,
                "client_slug": "demo_salon",
                "instance_id": "demo-instance",
                "branch_id": branch_id,
            },
            "status": "sent",
            "status_at": datetime.now(timezone.utc).isoformat(),
            "outbox_id": outbox_id,
        }
    )


def test_provider_status_updates_outbox():
    client_id = uuid4()
    outbox = OutboxMessage(
        id=uuid4(),
        client_id=client_id,
        inbound_message_id="msg-1",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox)
    status = _make_status(outbox_id=str(outbox.id), client_id=str(client_id))

    ok, message = update_outbox_status_from_provider(db, status=status)

    assert ok is True
    assert message == "ok"
    assert outbox.status == "SENT"
    assert outbox.meta["provider_status"]["status"] == "sent"
    assert outbox.meta["provider_status"]["provider_message_id"] == "msg-1"


def test_provider_status_rejects_tenant_mismatch():
    outbox = OutboxMessage(
        id=uuid4(),
        client_id=uuid4(),
        inbound_message_id="msg-1",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox)
    status = _make_status(outbox_id=str(outbox.id), client_id=str(uuid4()))

    ok, message = update_outbox_status_from_provider(db, status=status)

    assert ok is False
    assert message == "tenant_mismatch"
    assert "provider_status" not in outbox.meta


def test_provider_status_rejects_branch_tenant_mismatch():
    branch_id = uuid4()
    outbox = OutboxMessage(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=branch_id,
        inbound_message_id="msg-1",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox)
    status = _make_status(
        outbox_id=str(outbox.id),
        client_id=str(outbox.client_id),
        branch_id=str(uuid4()),
    )

    ok, message = update_outbox_status_from_provider(db, status=status)

    assert ok is False
    assert message == "tenant_mismatch"
    assert "provider_status" not in outbox.meta


@pytest.mark.asyncio
async def test_outbox_gateway_uses_provider_from_payload(monkeypatch):
    monkeypatch.setenv("PROVIDER_GATEWAY_OUTBOUND_ENABLED", "1")

    client_id = uuid4()
    outbox_id = uuid4()
    outbox_row = OutboxMessage(
        id=outbox_id,
        client_id=client_id,
        inbound_message_id="msg-1",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox_row)

    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "client_slug": "demo_salon",
        "provider": "mockflow",
        "channel": "whatsapp",
        "tenant_context": {
            "client_id": str(client_id),
            "client_slug": "demo_salon",
            "instance_id": "demo-instance",
        },
        "payload": {
            "remote_jid": "77770000000@s.whatsapp.net",
            "instance_id": "demo-instance",
            "text": "Hello",
            "idempotency_key": "idem-1",
        },
    }
    row = {
        "id": outbox_id,
        "payload_json": payload_json,
        "conversation_id": None,
        "client_id": client_id,
        "inbound_message_id": "msg-1",
        "created_at": datetime.now(timezone.utc),
    }

    captured = {}

    def _send_text(self, to, text, options):
        captured["provider"] = options.extra.get("provider")
        captured["channel"] = options.extra.get("channel")
        return Ok(MessageSent(remote_jid=to, message_id="mock-1", provider_response={"ok": True}))

    monkeypatch.setattr(outbox_router.ProviderGatewayAdapter, "send_text", _send_text)
    monkeypatch.setattr(outbox_router, "mark_outbox_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(outbox_router, "record_outbox_latency", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_message_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_conversation_created_at", lambda *args, **kwargs: None)

    results = await outbox_router._process_outbox_rows(db, [row], max_attempts=3, retry_backoff_seconds=1.0)

    assert results["sent"] == 1
    assert captured["provider"] == "mockflow"
    assert captured["channel"] == "whatsapp"


@pytest.mark.asyncio
async def test_outbox_rows_skip_conversation_fallback_when_inbound_id_present(monkeypatch):
    monkeypatch.setenv("PROVIDER_GATEWAY_OUTBOUND_ENABLED", "1")

    client_id = uuid4()
    outbox_id = uuid4()
    conversation_id = uuid4()
    outbox_row = OutboxMessage(
        id=outbox_id,
        client_id=client_id,
        inbound_message_id="calendar:123:1:update",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox_row)

    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "client_slug": "demo_salon",
        "provider": "mockflow",
        "channel": "whatsapp",
        "tenant_context": {
            "client_id": str(client_id),
            "client_slug": "demo_salon",
            "instance_id": "demo-instance",
        },
        "payload": {
            "remote_jid": "77770000000@s.whatsapp.net",
            "instance_id": "demo-instance",
            "text": "Hello",
            "idempotency_key": "idem-calendar-fallback",
        },
    }
    row = {
        "id": outbox_id,
        "payload_json": payload_json,
        "conversation_id": conversation_id,
        "client_id": client_id,
        "inbound_message_id": "calendar:123:1:update",
        "created_at": datetime.now(timezone.utc),
    }

    fallback_calls: list[object] = []

    def _send_text(self, to, text, options):
        return Ok(MessageSent(remote_jid=to, message_id="mock-2", provider_response={"ok": True}))

    monkeypatch.setattr(outbox_router.ProviderGatewayAdapter, "send_text", _send_text)
    monkeypatch.setattr(outbox_router, "mark_outbox_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(outbox_router, "record_outbox_latency", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_message_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        legacy,
        "_find_message_by_conversation_created_at",
        lambda *args, **kwargs: fallback_calls.append((args, kwargs)) or None,
    )

    results = await outbox_router._process_outbox_rows(db, [row], max_attempts=3, retry_backoff_seconds=1.0)

    assert results["sent"] == 1
    assert not fallback_calls


@pytest.mark.asyncio
@pytest.mark.parametrize("client_slug", ["demo_salon", "generic"])
async def test_outbox_rows_reject_tenant_context_client_mismatch(monkeypatch, client_slug: str):
    client_id = uuid4()
    outbox_id = uuid4()
    outbox_row = OutboxMessage(
        id=outbox_id,
        client_id=client_id,
        branch_id=None,
        inbound_message_id="msg-tenant-client",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox_row)

    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "client_slug": client_slug,
        "provider": "mockflow",
        "channel": "whatsapp",
        "tenant_context": {
            "client_id": str(uuid4()),
            "client_slug": client_slug,
            "instance_id": f"{client_slug}-instance",
        },
        "payload": {
            "remote_jid": "77770000000@s.whatsapp.net",
            "instance_id": f"{client_slug}-instance",
            "text": "Hello",
            "idempotency_key": "idem-tenant-client",
        },
    }
    row = {
        "id": outbox_id,
        "payload_json": payload_json,
        "conversation_id": None,
        "client_id": client_id,
        "branch_id": None,
        "inbound_message_id": "msg-tenant-client",
        "created_at": datetime.now(timezone.utc),
        "attempts": 1,
    }

    statuses = []

    monkeypatch.setattr(outbox_router, "mark_outbox_status", lambda *_args, **kwargs: statuses.append(kwargs["status"]))
    monkeypatch.setattr(outbox_router, "record_delivery_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outbox_router, "alert_error", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_message_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_conversation_created_at", lambda *args, **kwargs: None)

    results = await outbox_router._process_outbox_rows(db, [row], max_attempts=3, retry_backoff_seconds=1.0)

    assert results["sent"] == 0
    assert results["failed"] == 1
    assert statuses == ["FAILED"]
    assert outbox_row.meta["contract_error"] == "event:tenant_context_client_mismatch"


@pytest.mark.asyncio
@pytest.mark.parametrize("client_slug", ["demo_salon", "generic"])
async def test_outbox_rows_reject_tenant_context_branch_mismatch(monkeypatch, client_slug: str):
    client_id = uuid4()
    branch_id = uuid4()
    outbox_id = uuid4()
    outbox_row = OutboxMessage(
        id=outbox_id,
        client_id=client_id,
        branch_id=branch_id,
        inbound_message_id="msg-tenant-branch",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox_row)

    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "client_slug": client_slug,
        "provider": "mockflow",
        "channel": "whatsapp",
        "tenant_context": {
            "client_id": str(client_id),
            "branch_id": str(uuid4()),
            "client_slug": client_slug,
            "instance_id": f"{client_slug}-instance",
        },
        "payload": {
            "remote_jid": "77770000000@s.whatsapp.net",
            "instance_id": f"{client_slug}-instance",
            "text": "Hello",
            "idempotency_key": "idem-tenant-branch",
        },
    }
    row = {
        "id": outbox_id,
        "payload_json": payload_json,
        "conversation_id": None,
        "client_id": client_id,
        "branch_id": branch_id,
        "inbound_message_id": "msg-tenant-branch",
        "created_at": datetime.now(timezone.utc),
        "attempts": 1,
    }

    statuses = []

    monkeypatch.setattr(outbox_router, "mark_outbox_status", lambda *_args, **kwargs: statuses.append(kwargs["status"]))
    monkeypatch.setattr(outbox_router, "record_delivery_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outbox_router, "alert_error", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_message_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_conversation_created_at", lambda *args, **kwargs: None)

    results = await outbox_router._process_outbox_rows(db, [row], max_attempts=3, retry_backoff_seconds=1.0)

    assert results["sent"] == 0
    assert results["failed"] == 1
    assert statuses == ["FAILED"]
    assert outbox_row.meta["contract_error"] == "event:tenant_context_branch_mismatch"


@pytest.mark.asyncio
async def test_outbox_rows_reject_missing_tenant_context(monkeypatch):
    client_id = uuid4()
    outbox_id = uuid4()
    outbox_row = OutboxMessage(
        id=outbox_id,
        client_id=client_id,
        branch_id=None,
        inbound_message_id="msg-missing-tenant-context",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox_row)

    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "client_slug": "generic",
        "provider": "mockflow",
        "channel": "whatsapp",
        "payload": {
            "remote_jid": "77770000000@s.whatsapp.net",
            "instance_id": "generic-instance",
            "text": "Hello",
            "idempotency_key": "idem-missing-tenant-context",
        },
    }
    row = {
        "id": outbox_id,
        "payload_json": payload_json,
        "conversation_id": None,
        "client_id": client_id,
        "branch_id": None,
        "inbound_message_id": "msg-missing-tenant-context",
        "created_at": datetime.now(timezone.utc),
        "attempts": 1,
    }

    statuses = []

    monkeypatch.setattr(outbox_router, "mark_outbox_status", lambda *_args, **kwargs: statuses.append(kwargs["status"]))
    monkeypatch.setattr(outbox_router, "record_delivery_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outbox_router, "alert_error", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_message_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_conversation_created_at", lambda *args, **kwargs: None)

    results = await outbox_router._process_outbox_rows(db, [row], max_attempts=3, retry_backoff_seconds=1.0)

    assert results["sent"] == 0
    assert results["failed"] == 1
    assert statuses == ["FAILED"]
    assert outbox_row.meta["contract_error"] == "event:missing_tenant_context"


@pytest.mark.asyncio
async def test_outbox_rows_reject_invalid_tenant_context_contract(monkeypatch):
    client_id = uuid4()
    outbox_id = uuid4()
    outbox_row = OutboxMessage(
        id=outbox_id,
        client_id=client_id,
        branch_id=None,
        inbound_message_id="msg-invalid-tenant-context",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox_row)

    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "client_slug": "generic",
        "provider": "mockflow",
        "channel": "whatsapp",
        "tenant_context": {
            "client_id": str(client_id),
            "client_slug": "generic",
            "source": "provider_gateway",
        },
        "payload": {
            "remote_jid": "77770000000@s.whatsapp.net",
            "instance_id": "generic-instance",
            "text": "Hello",
            "idempotency_key": "idem-invalid-tenant-context",
        },
    }
    row = {
        "id": outbox_id,
        "payload_json": payload_json,
        "conversation_id": None,
        "client_id": client_id,
        "branch_id": None,
        "inbound_message_id": "msg-invalid-tenant-context",
        "created_at": datetime.now(timezone.utc),
        "attempts": 1,
    }

    statuses = []

    monkeypatch.setattr(outbox_router, "mark_outbox_status", lambda *_args, **kwargs: statuses.append(kwargs["status"]))
    monkeypatch.setattr(outbox_router, "record_delivery_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outbox_router, "alert_error", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_message_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_conversation_created_at", lambda *args, **kwargs: None)

    results = await outbox_router._process_outbox_rows(db, [row], max_attempts=3, retry_backoff_seconds=1.0)

    assert results["sent"] == 0
    assert results["failed"] == 1
    assert statuses == ["FAILED"]
    assert outbox_row.meta["contract_error"] == "event:invalid_tenant_context_contract"


@pytest.mark.asyncio
async def test_outbox_rows_fail_fast_on_chatflow_billing_blocked(monkeypatch):
    monkeypatch.delenv("PROVIDER_GATEWAY_OUTBOUND_ENABLED", raising=False)

    client_id = uuid4()
    outbox_id = uuid4()
    outbox_row = OutboxMessage(
        id=outbox_id,
        client_id=client_id,
        branch_id=None,
        inbound_message_id="msg-billing-blocked",
        payload_json={},
        status="PENDING",
        meta={},
    )
    db = _make_db(outbox=outbox_row)

    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "client_slug": "demo_salon",
        "provider": "chatflow",
        "channel": "whatsapp",
        "tenant_context": {
            "client_id": str(client_id),
            "client_slug": "demo_salon",
            "instance_id": "demo-instance",
        },
        "payload": {
            "remote_jid": "77770000000@s.whatsapp.net",
            "instance_id": "demo-instance",
            "text": "Hello",
            "idempotency_key": "idem-billing-blocked",
        },
    }
    row = {
        "id": outbox_id,
        "payload_json": payload_json,
        "conversation_id": None,
        "client_id": client_id,
        "branch_id": None,
        "inbound_message_id": "msg-billing-blocked",
        "created_at": datetime.now(timezone.utc),
        "attempts": 1,
    }

    statuses: list[str] = []
    def _billing_blocked_send_text(self, to, text, options):
        return Err(
            IntegrationError(
                code=ErrorCodes.CHATFLOW_BILLING_BLOCKED,
                message="ChatFlow billing blocked: plan renewal required",
                service="chatflow",
                context={"reason": "billing_blocked", "retryable": False},
            )
        )

    monkeypatch.setattr(outbox_router.ChatFlowAdapter, "send_text", _billing_blocked_send_text)
    monkeypatch.setattr(outbox_router, "mark_outbox_status", lambda *_args, **kwargs: statuses.append(kwargs["status"]))
    monkeypatch.setattr(outbox_router, "record_outbox_latency", lambda *args, **kwargs: None)
    monkeypatch.setattr(outbox_router, "record_delivery_failure", lambda *args, **kwargs: None)
    monkeypatch.setattr(outbox_router, "alert_error", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_message_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(legacy, "_find_message_by_conversation_created_at", lambda *args, **kwargs: None)

    results = await outbox_router._process_outbox_rows(db, [row], max_attempts=5, retry_backoff_seconds=1.0)

    assert results["sent"] == 0
    assert results["failed"] == 1
    assert results["retry_scheduled"] == 0
    assert statuses == ["FAILED"]
