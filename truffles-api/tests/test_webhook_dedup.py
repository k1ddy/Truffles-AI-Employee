from unittest.mock import Mock

import pytest

from app.routers import webhook


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
async def test_is_duplicate_message_id_reports_db_fallback_on_redis_error():
    db = Mock()
    insert_result = Mock()
    insert_result.rowcount = 1
    db.execute.return_value = insert_result
    query = Mock()
    filtered = Mock()
    filtered.first.return_value = None
    query.filter.return_value = filtered
    db.query.return_value = query
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
