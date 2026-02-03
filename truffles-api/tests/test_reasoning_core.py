from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

import pytest

from app.routers.webhook import decision as decision_router
from app.routers.webhook import trace as trace_router
from app.contracts.result import Ok
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest, WebhookResponse
from app.services import reasoning_core


def test_reasoning_core_stage_snapshot_matches_trace():
    assert reasoning_core.STAGE_ORDER_SNAPSHOT == trace_router.DECISION_STAGE_ORDER_SNAPSHOT


@pytest.mark.asyncio
async def test_reasoning_core_delegates_to_decision(monkeypatch):
    payload = WebhookRequest(body=WebhookBody(message="hi"))
    db = object()
    conversation_id = UUID("00000000-0000-0000-0000-000000000000")
    outbox_created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    captured: dict[str, object] = {}

    async def fake_handle(payload, db, **kwargs):
        captured["payload"] = payload
        captured["db"] = db
        captured["kwargs"] = kwargs
        return WebhookResponse(success=True, message="ok")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", fake_handle)

    request = reasoning_core.ReasoningCoreRequest(
        payload=payload,
        db=db,
        provided_secret="secret",
        enforce_secret=True,
        enqueue_only=True,
        skip_persist=True,
        conversation_id=conversation_id,
        batch_messages=["a", "b"],
        outbox_ids=["o1"],
        outbox_created_at=outbox_created_at,
    )

    response = await reasoning_core.run_reasoning_core(request)

    assert response.success is True
    assert captured["payload"] is payload
    assert captured["db"] is db
    assert captured["kwargs"]["provided_secret"] == "secret"
    assert captured["kwargs"]["enforce_secret"] is True
    assert captured["kwargs"]["enqueue_only"] is True
    assert captured["kwargs"]["skip_persist"] is True
    assert captured["kwargs"]["conversation_id"] == conversation_id
    assert captured["kwargs"]["batch_messages"] == ["a", "b"]
    assert captured["kwargs"]["outbox_ids"] == ["o1"]
    assert captured["kwargs"]["outbox_created_at"] == outbox_created_at


@pytest.mark.asyncio
async def test_reasoning_core_fallback_on_exception(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hi",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                instanceId="inst-1",
                messageId="msg-1",
            ),
        ),
    )
    db = Mock()

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    send_calls: dict[str, object] = {}

    def fake_send_message_safe(*args, **kwargs):
        send_calls["called"] = True
        return Ok("ok")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", boom)
    monkeypatch.setattr(reasoning_core, "send_message_safe", fake_send_message_safe)
    monkeypatch.setattr(reasoning_core, "alert_error", lambda *args, **kwargs: None)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        enqueue_only=False,
        skip_persist=False,
        conversation_id=None,
        batch_messages=None,
        outbox_ids=None,
        outbox_created_at=None,
    )

    assert response.success is True
    assert response.bot_response == decision_router.MSG_DELIVERY_FAILED
    assert send_calls.get("called") is True
    db.rollback.assert_called_once()
