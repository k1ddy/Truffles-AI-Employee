from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import (
    ConsoleHumanLockPauseRequest,
    ConsoleManagerMessageRequest,
    ConsoleOutreachMessageRequest,
)


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result


class _FakeDb:
    def __init__(self, conversation=None, case=None):
        self._conversation = conversation
        self._case = case
        self._added = []
        self.commits = 0

    def query(self, model):
        if model is console_router.Conversation:
            return _FakeQuery(self._conversation)
        if model is console_router.Handover:
            return _FakeQuery(self._case)
        return _FakeQuery(None)

    def add(self, item):
        self._added.append(item)

    def commit(self):
        self.commits += 1
        for item in self._added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            if getattr(item, "created_at", None) is None:
                item.created_at = datetime.now(timezone.utc)

    def refresh(self, _item):
        return None


@pytest.mark.asyncio
async def test_send_outreach_message_enqueues_outbox_and_sets_pause(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        user_id=uuid4(),
    )
    context = SimpleNamespace(
        role="support",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        branches=[SimpleNamespace(id=branch_id)],
        effective_branch_id=branch_id,
    )
    db = _FakeDb(conversation=conversation)
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "get_instance_id", lambda *_args, **_kwargs: "instance-1")
    monkeypatch.setattr(console_router, "_is_env_enabled", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(console_router, "start_idempotency", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    def _fake_enqueue(*_args, **kwargs):
        captured["payload_json"] = kwargs.get("payload_json")
        return True

    monkeypatch.setattr(console_router, "enqueue_outbox_message", _fake_enqueue)
    monkeypatch.setattr(
        console_router,
        "upsert_human_lock",
        lambda *_args, **_kwargs: SimpleNamespace(
            lock_until=datetime.now(timezone.utc) + timedelta(minutes=30),
            active=True,
            source="console_outreach",
            reason="manual_pause",
        ),
    )

    response = await console_router.send_outreach_message(
        body=ConsoleOutreachMessageRequest(
            destination="+7 (777) 123-45-67",
            content="Здравствуйте",
            conversation_id=conversation.id,
            branch_id=branch_id,
            pause_bot_minutes=30,
            pause_reason="manual_pause",
        ),
        request=Mock(headers={"Idempotency-Key": "idem"}),
        db=db,
    )

    assert response.success is True
    assert response.delivery_status == "queued"
    assert response.remote_jid == "77771234567@s.whatsapp.net"
    assert response.outbox_enqueued is True
    assert response.lock_until is not None
    assert captured["payload_json"]["event_type"] == "whatsapp.send_text"
    assert captured["payload_json"]["payload"]["text"] == "Здравствуйте"
    assert captured["payload_json"]["tenant_context"]["source"] == "system"
    assert captured["payload_json"]["tenant_context"]["origin_source"] == "console_outreach"


@pytest.mark.asyncio
async def test_send_manager_message_enqueues_outbox_when_worker_enabled(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        user_id=uuid4(),
        telegram_topic_id=None,
    )
    agent_id = uuid4()
    case = SimpleNamespace(
        id=uuid4(),
        status="active",
        assigned_to=str(agent_id),
        assigned_to_name="Agent",
        manager_response=None,
        first_response_at=None,
    )
    context = SimpleNamespace(
        role="manager",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=agent_id, name="Agent"),
        branches=[SimpleNamespace(id=branch_id)],
        effective_branch_id=branch_id,
    )
    db = _FakeDb(case=case)
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_resolve_console_conversation_or_404",
        lambda *_args, **_kwargs: conversation,
    )
    monkeypatch.setattr(console_router, "start_idempotency", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "resolve_conversation_remote_jid",
        lambda *_args, **_kwargs: "77771234567@s.whatsapp.net",
    )
    monkeypatch.setattr(console_router, "get_instance_id", lambda *_args, **_kwargs: "instance-1")
    monkeypatch.setattr(console_router, "_is_env_enabled", lambda *_args, **_kwargs: True)

    def _fake_enqueue(*_args, **kwargs):
        captured["payload_json"] = kwargs.get("payload_json")
        return True

    monkeypatch.setattr(console_router, "enqueue_outbox_message", _fake_enqueue)
    monkeypatch.setattr(console_router, "upsert_human_lock", lambda *_args, **_kwargs: SimpleNamespace())

    response = await console_router.send_manager_message(
        conversation_id=conversation.id,
        body=ConsoleManagerMessageRequest(content="Здравствуйте"),
        request=Mock(headers={"Idempotency-Key": "idem"}),
        db=db,
    )

    assert response.success is True
    assert response.message.content == "Здравствуйте"
    assert case.manager_response == "Здравствуйте"
    assert case.first_response_at is not None
    assert captured["payload_json"]["event_type"] == "whatsapp.send_text"
    assert captured["payload_json"]["payload"]["text"] == "Здравствуйте"
    assert captured["payload_json"]["tenant_context"]["source"] == "system"
    assert captured["payload_json"]["tenant_context"]["origin_source"] == "console_message"


@pytest.mark.asyncio
async def test_send_manager_message_skips_pause_when_disabled(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        user_id=uuid4(),
        telegram_topic_id=None,
    )
    agent_id = uuid4()
    case = SimpleNamespace(
        id=uuid4(),
        status="active",
        assigned_to=str(agent_id),
        assigned_to_name="Agent",
        manager_response=None,
        first_response_at=None,
    )
    context = SimpleNamespace(
        role="manager",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=agent_id, name="Agent"),
        branches=[SimpleNamespace(id=branch_id)],
        effective_branch_id=branch_id,
    )
    db = _FakeDb(case=case)
    captured = {"pause_called": False}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_resolve_console_conversation_or_404",
        lambda *_args, **_kwargs: conversation,
    )
    monkeypatch.setattr(console_router, "start_idempotency", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "resolve_conversation_remote_jid",
        lambda *_args, **_kwargs: "77771234567@s.whatsapp.net",
    )
    monkeypatch.setattr(console_router, "get_instance_id", lambda *_args, **_kwargs: "instance-1")
    monkeypatch.setattr(console_router, "_is_env_enabled", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(console_router, "enqueue_outbox_message", lambda *_args, **_kwargs: True)

    def _fake_upsert(*_args, **_kwargs):
        captured["pause_called"] = True
        return SimpleNamespace()

    monkeypatch.setattr(console_router, "upsert_human_lock", _fake_upsert)

    response = await console_router.send_manager_message(
        conversation_id=conversation.id,
        body=ConsoleManagerMessageRequest(content="Здравствуйте", pause_enabled=False),
        request=Mock(headers={"Idempotency-Key": "idem"}),
        db=db,
    )

    assert response.success is True
    assert captured["pause_called"] is False

@pytest.mark.asyncio
async def test_pause_conversation_human_lock_returns_active_status(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        user_id=uuid4(),
    )
    context = SimpleNamespace(
        role="manager",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        branches=[SimpleNamespace(id=branch_id)],
        effective_branch_id=branch_id,
    )
    db = _FakeDb(conversation=conversation)

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "resolve_conversation_remote_jid",
        lambda *_args, **_kwargs: "77771234567@s.whatsapp.net",
    )
    monkeypatch.setattr(
        console_router,
        "upsert_human_lock",
        lambda *_args, **_kwargs: SimpleNamespace(
            lock_until=datetime.now(timezone.utc) + timedelta(minutes=15),
            active=True,
            source="console_pause",
            reason="manual",
        ),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    response = await console_router.pause_conversation_human_lock(
        conversation_id=conversation.id,
        body=ConsoleHumanLockPauseRequest(minutes=15, reason="manual"),
        request=Mock(),
        db=db,
    )

    assert response.success is True
    assert response.status.active is True
    assert response.status.remote_jid == "77771234567@s.whatsapp.net"
    assert response.status.remaining_seconds is not None
    assert response.status.remaining_seconds > 0
    assert response.status.reason == "manual"


@pytest.mark.asyncio
async def test_get_conversation_human_lock_status_returns_inactive_when_missing(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        user_id=uuid4(),
    )
    context = SimpleNamespace(
        role="viewer",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        branches=[SimpleNamespace(id=branch_id)],
        effective_branch_id=branch_id,
    )
    db = _FakeDb(conversation=conversation)

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "resolve_conversation_remote_jid",
        lambda *_args, **_kwargs: "77771234567@s.whatsapp.net",
    )
    monkeypatch.setattr(console_router, "get_active_human_lock", lambda *_args, **_kwargs: None)

    response = await console_router.get_conversation_human_lock_status(
        conversation_id=conversation.id,
        request=Mock(),
        db=db,
    )

    assert response.success is True
    assert response.status.active is False
    assert response.status.remote_jid == "77771234567@s.whatsapp.net"
