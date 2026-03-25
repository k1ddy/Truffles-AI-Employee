from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

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

    def with_for_update(self):
        return self

    def order_by(self, *_args, **_kwargs):
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

    def flush(self):
        for item in self._added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            if getattr(item, "created_at", None) is None:
                item.created_at = datetime.now(timezone.utc)

    def commit(self):
        self.commits += 1
        for item in self._added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            if getattr(item, "created_at", None) is None:
                item.created_at = datetime.now(timezone.utc)

    def refresh(self, _item):
        return None


def test_bootstrap_outreach_conversation_case_creates_active_case(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    user = SimpleNamespace(id=uuid4(), phone=None, last_active_at=None)
    conversation = SimpleNamespace(id=uuid4(), branch_id=branch_id, last_message_at=None)
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
    )
    db = _FakeDb(case=None)

    monkeypatch.setattr(console_router, "get_or_create_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(
        console_router,
        "get_or_create_conversation",
        lambda *_args, **_kwargs: conversation,
    )

    resolved_conversation, auto_case, created = console_router._bootstrap_outreach_conversation_case(
        db,
        context=context,
        remote_jid="77771234567@s.whatsapp.net",
        branch_id=branch_id,
        content="Здравствуйте",
    )

    assert resolved_conversation is conversation
    assert created is True
    assert auto_case.conversation_id == conversation.id
    assert auto_case.status == "active"
    assert auto_case.trigger_type == "manual"
    assert auto_case.trigger_value == "console_outreach_no_case"
    assert auto_case.channel == "whatsapp"
    assert auto_case.channel_ref == "77771234567@s.whatsapp.net"
    assert auto_case.meta["outreach_bootstrap_reason"] == "new_case_created"
    assert auto_case.meta["outreach_dedupe_key"].startswith("outreach-no-case:")
    assert user.phone == "77771234567"
    assert user.last_active_at is not None
    assert conversation.last_message_at is not None
    trace = conversation.context["decision_trace"]
    assert trace[-1]["stage"] == "outreach_auto_case_bootstrap"
    assert trace[-1]["decision"] == "case_created"


def test_bootstrap_outreach_conversation_case_reuses_existing_case(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    existing_case = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    user = SimpleNamespace(id=uuid4(), phone="77771234567", last_active_at=None)
    conversation = SimpleNamespace(id=existing_case.conversation_id, branch_id=branch_id, last_message_at=None)
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
    )
    db = _FakeDb(case=existing_case)

    monkeypatch.setattr(console_router, "get_or_create_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(
        console_router,
        "get_or_create_conversation",
        lambda *_args, **_kwargs: conversation,
    )

    resolved_conversation, auto_case, created = console_router._bootstrap_outreach_conversation_case(
        db,
        context=context,
        remote_jid="77771234567@s.whatsapp.net",
        branch_id=branch_id,
        content="Здравствуйте",
    )

    assert resolved_conversation is conversation
    assert auto_case is existing_case
    assert created is False
    assert len(db._added) == 0
    assert auto_case.meta["outreach_bootstrap_reason"] == "active_case_reused"
    trace = conversation.context["decision_trace"]
    assert trace[-1]["stage"] == "outreach_auto_case_bootstrap"
    assert trace[-1]["reason"] == "active_case_reused"


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
async def test_send_outreach_message_without_branch_uses_context_branch(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    boot_conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        user_id=uuid4(),
    )
    boot_case = SimpleNamespace(
        id=uuid4(),
        conversation_id=boot_conversation.id,
        status="active",
        trigger_message_id=None,
    )
    context = SimpleNamespace(
        role="manager",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        branches=[SimpleNamespace(id=branch_id)],
        effective_branch_id=branch_id,
    )
    db = _FakeDb()
    captured = {"instance_branch_id": None}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_resolve_branch_from_context",
        lambda _context: SimpleNamespace(id=branch_id),
    )
    monkeypatch.setattr(console_router, "_is_env_enabled", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(console_router, "start_idempotency", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "enqueue_outbox_message", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        console_router,
        "_bootstrap_outreach_conversation_case",
        lambda *_args, **_kwargs: (boot_conversation, boot_case, True),
    )
    monkeypatch.setattr(
        console_router,
        "upsert_human_lock",
        lambda *_args, **_kwargs: SimpleNamespace(lock_until=datetime.now(timezone.utc) + timedelta(minutes=30)),
    )

    def _fake_get_instance_id(_db, _client_id, *, branch_id: UUID, remote_jid: str):
        captured["instance_branch_id"] = branch_id
        return "instance-1"

    monkeypatch.setattr(console_router, "get_instance_id", _fake_get_instance_id)

    response = await console_router.send_outreach_message(
        body=ConsoleOutreachMessageRequest(
            destination="+7 (777) 123-45-67",
            content="Здравствуйте",
            pause_bot_minutes=30,
        ),
        request=Mock(headers={"Idempotency-Key": "idem"}),
        db=db,
    )

    assert response.success is True
    assert captured["instance_branch_id"] == branch_id
    assert response.conversation_id == boot_conversation.id
    assert response.case_id == boot_case.id
    assert response.case_created is True


@pytest.mark.asyncio
async def test_send_outreach_message_rejects_branch_mismatch(monkeypatch):
    client_id = uuid4()
    conversation_branch_id = uuid4()
    request_branch_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=conversation_branch_id,
        user_id=uuid4(),
    )
    context = SimpleNamespace(
        role="manager",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        branches=[SimpleNamespace(id=conversation_branch_id), SimpleNamespace(id=request_branch_id)],
        effective_branch_id=None,
    )
    db = _FakeDb()

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_resolve_console_conversation_or_404",
        lambda *_args, **_kwargs: conversation,
    )

    with pytest.raises(console_router.ConsoleAPIError) as exc_info:
        await console_router.send_outreach_message(
            body=ConsoleOutreachMessageRequest(
                destination="+7 (777) 123-45-67",
                content="Здравствуйте",
                conversation_id=conversation.id,
                branch_id=request_branch_id,
                pause_bot_minutes=30,
            ),
            request=Mock(headers={"Idempotency-Key": "idem"}),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert "branch_id must match conversation branch" in exc_info.value.message


@pytest.mark.asyncio
async def test_send_outreach_message_no_case_reuses_existing_case(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    existing_conversation = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        user_id=uuid4(),
    )
    existing_case = SimpleNamespace(
        id=uuid4(),
        conversation_id=existing_conversation.id,
        status="active",
        trigger_message_id=uuid4(),
    )
    context = SimpleNamespace(
        role="manager",
        client=SimpleNamespace(id=client_id, name="demo"),
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        branches=[SimpleNamespace(id=branch_id)],
        effective_branch_id=branch_id,
    )
    db = _FakeDb()

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_resolve_branch_from_context",
        lambda _context: SimpleNamespace(id=branch_id),
    )
    monkeypatch.setattr(console_router, "get_instance_id", lambda *_args, **_kwargs: "instance-1")
    monkeypatch.setattr(console_router, "_is_env_enabled", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(console_router, "start_idempotency", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "enqueue_outbox_message", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        console_router,
        "_bootstrap_outreach_conversation_case",
        lambda *_args, **_kwargs: (existing_conversation, existing_case, False),
    )
    monkeypatch.setattr(
        console_router,
        "upsert_human_lock",
        lambda *_args, **_kwargs: SimpleNamespace(lock_until=datetime.now(timezone.utc) + timedelta(minutes=30)),
    )

    response = await console_router.send_outreach_message(
        body=ConsoleOutreachMessageRequest(
            destination="+7 (777) 123-45-67",
            content="Здравствуйте",
            pause_bot_minutes=30,
        ),
        request=Mock(headers={"Idempotency-Key": "idem"}),
        db=db,
    )

    assert response.success is True
    assert response.conversation_id == existing_conversation.id
    assert response.case_id == existing_case.id
    assert response.case_created is False


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
