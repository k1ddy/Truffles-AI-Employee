from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.routers import webhook
from app.routers.webhook import decision as decision_router
from app.routers.webhook import dedup as dedup_module
from app.routers.webhook import guards as guards_module


class FakeRedisBuffer:
    def __init__(self):
        self.data = {}

    async def rpush(self, key, value):
        self.data.setdefault(key, []).append(value)

    async def ltrim(self, key, start, end):
        values = self.data.get(key, [])
        if start < 0:
            start = max(len(values) + start, 0)
        if end < 0:
            end = len(values) + end
        self.data[key] = values[start : end + 1]

    async def expire(self, key, ttl):
        return None

    async def lrange(self, key, start, end):
        values = self.data.get(key, [])
        if start < 0:
            start = max(len(values) + start, 0)
        if end < 0:
            end = len(values) + end
        return values[start : end + 1]

    async def delete(self, key):
        self.data.pop(key, None)


class FakeRedisDedup:
    async def set(self, key, value, ex=None, nx=None):
        return False


class FakeRedisError:
    async def set(self, key, value, ex=None, nx=None):
        raise RuntimeError("redis unavailable")


@pytest.mark.asyncio
async def test_buffer_user_message_trims_and_drains():
    redis_client = FakeRedisBuffer()
    await webhook._buffer_user_message(
        redis_client=redis_client,
        client_id="client",
        remote_jid="jid",
        message_text="first",
        ttl_seconds=10,
        max_messages=2,
    )
    await webhook._buffer_user_message(
        redis_client=redis_client,
        client_id="client",
        remote_jid="jid",
        message_text="second",
        ttl_seconds=10,
        max_messages=2,
    )
    await webhook._buffer_user_message(
        redis_client=redis_client,
        client_id="client",
        remote_jid="jid",
        message_text="third",
        ttl_seconds=10,
        max_messages=2,
    )

    drained = await webhook._drain_buffered_messages(
        redis_client=redis_client,
        client_id="client",
        remote_jid="jid",
    )

    assert drained == ["second", "third"]
    assert redis_client.data == {}


@pytest.mark.asyncio
async def test_drain_buffered_messages_strips_empty_values():
    redis_client = FakeRedisBuffer()
    key = "truffles:buffer:client:jid"
    redis_client.data[key] = ["  ", "hello", None, "world "]

    drained = await webhook._drain_buffered_messages(
        redis_client=redis_client,
        client_id="client",
        remote_jid="jid",
    )

    assert drained == ["hello", "world"]


@pytest.mark.asyncio
async def test_is_duplicate_message_id_short_circuits_on_redis():
    db = Mock()
    diagnostics = {}

    result = await webhook.is_duplicate_message_id(
        db=db,
        client_id="client",
        message_id="message-1",
        redis_client=FakeRedisDedup(),
        diagnostics=diagnostics,
    )

    assert result is True
    assert diagnostics["dedup_backend"] == "redis"
    assert diagnostics["dedup_fallback_reason"] is None
    assert diagnostics["dedup_duplicate"] is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_is_duplicate_message_id_reports_db_fallback_on_redis_error(monkeypatch):
    db = Mock()
    insert_result = Mock()
    insert_result.rowcount = 1
    db.execute.return_value = insert_result
    monkeypatch.setattr(
        dedup_module,
        "_lookup_duplicate_message_in_messages_table",
        lambda *args, **kwargs: None,
    )
    diagnostics = {}

    result = await webhook.is_duplicate_message_id(
        db=db,
        client_id="client",
        message_id="message-2",
        redis_client=FakeRedisError(),
        diagnostics=diagnostics,
    )

    assert result is False
    assert diagnostics["dedup_backend"] == "db_fallback"
    assert diagnostics["dedup_fallback_reason"] == "redis_error"
    assert diagnostics["dedup_duplicate"] is False
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_is_duplicate_message_id_reports_db_duplicate_without_redis():
    db = Mock()
    insert_result = Mock()
    insert_result.rowcount = 0
    db.execute.return_value = insert_result
    diagnostics = {}

    result = await webhook.is_duplicate_message_id(
        db=db,
        client_id="client",
        message_id="message-3",
        redis_client=False,
        diagnostics=diagnostics,
    )

    assert result is True
    assert diagnostics["dedup_backend"] == "db_fallback"
    assert diagnostics["dedup_fallback_reason"] == "redis_unavailable"
    assert diagnostics["dedup_duplicate"] is True
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_dedup_gate_fast_test_bypass(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("LLM_QUALITY_FAST_DEDUP", "1")

    called = {"duplicate_check": False}

    async def _fake_is_duplicate_message_id(*_args, **_kwargs):
        called["duplicate_check"] = True
        return True

    monkeypatch.setattr(dedup_module, "is_duplicate_message_id", _fake_is_duplicate_message_id)

    diagnostics = {}
    response, resolved_message_id = await dedup_module._handle_dedup_gate(
        db=Mock(),
        client=SimpleNamespace(id="client-1"),
        message_id="msg-fast-1",
        remote_jid="77000000000@s.whatsapp.net",
        metadata=SimpleNamespace(timestamp=1234567890, messageId="msg-fast-1"),
        message_text="test",
        conversation_id=None,
        resolve_trace_conversation=lambda **_kwargs: None,
        record_early_trace=lambda *_args, **_kwargs: False,
        dedup_diagnostics=diagnostics,
    )

    assert response is None
    assert resolved_message_id == "msg-fast-1"
    assert called["duplicate_check"] is False
    assert diagnostics["dedup_backend"] == "fast_test_bypass"
    assert diagnostics["dedup_fallback_reason"] == "test_mode_fast_dedup"
    assert diagnostics["dedup_duplicate"] is False


def test_lookup_preexisting_duplicate_message_falls_back_to_messages_table_on_owner_db_error(
    monkeypatch,
):
    db = Mock()
    db.execute.side_effect = RuntimeError("message_dedup unavailable")
    duplicate_row = Mock()

    monkeypatch.setattr(
        dedup_module,
        "_lookup_duplicate_message_in_messages_table",
        lambda *args, **kwargs: duplicate_row,
    )

    probe = dedup_module._lookup_preexisting_duplicate_message(
        db,
        client_id="client-1",
        message_id="msg-fallback-1",
    )

    assert probe == dedup_module.DuplicateMessageProbe(
        duplicate=True,
        backend="messages_table",
        fallback_reason="message_dedup_lookup_error",
    )
    db.rollback.assert_called_once()


def test_handle_post_debounce_muted_state_gate_skips_muted_without_booking_signal(monkeypatch):
    captured_trace: dict[str, object] = {}

    monkeypatch.setattr(decision_router, "_coerce_batch_messages", lambda text, batch: [text])
    monkeypatch.setattr(guards_module, "is_opt_out_message", lambda _text: False)
    monkeypatch.setattr(guards_module, "_get_conversation_context", lambda conversation: {})
    monkeypatch.setattr(guards_module, "_get_booking_context", lambda context: {})
    monkeypatch.setattr(guards_module, "_get_reengage_confirmation", lambda context: None)
    monkeypatch.setattr(
        guards_module,
        "_record_decision_trace",
        lambda conversation, payload: captured_trace.update(payload),
    )

    conversation = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000031",
        state="bot_active",
        bot_status="muted",
        bot_muted_until=None,
        no_count=3,
        telegram_topic_id=None,
    )

    response = guards_module._handle_post_debounce_muted_state_gate(
        conversation=conversation,
        message_text="просто спасибо",
        batch_messages=None,
        client_slug="demo_salon",
        now=datetime(2026, 3, 18, tzinfo=timezone.utc),
    )

    assert response is not None
    assert response.success is True
    assert response.message == "Bot muted (after debounce)"
    assert str(response.conversation_id) == "00000000-0000-0000-0000-000000000031"
    assert captured_trace["decision"] == "muted_skip_after_debounce"
    assert captured_trace["booking_signal"] is False
    assert captured_trace["booking_active"] is False


def test_handle_post_debounce_muted_state_gate_unmutes_for_active_booking(monkeypatch):
    monkeypatch.setattr(decision_router, "_coerce_batch_messages", lambda text, batch: [text])
    monkeypatch.setattr(guards_module, "is_opt_out_message", lambda _text: False)
    monkeypatch.setattr(guards_module, "_get_conversation_context", lambda conversation: {"booking": {"active": True}})
    monkeypatch.setattr(guards_module, "_get_booking_context", lambda context: {"active": True})
    monkeypatch.setattr(guards_module, "_get_reengage_confirmation", lambda context: None)

    conversation = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000032",
        state="bot_active",
        bot_status="muted",
        bot_muted_until=None,
        no_count=3,
        telegram_topic_id=None,
    )

    response = guards_module._handle_post_debounce_muted_state_gate(
        conversation=conversation,
        message_text="продолжаем запись",
        batch_messages=None,
        client_slug="demo_salon",
        now=datetime(2026, 3, 18, tzinfo=timezone.utc),
    )

    assert response is None
    assert conversation.bot_status == "active"
    assert conversation.bot_muted_until is None
    assert conversation.no_count == 0
