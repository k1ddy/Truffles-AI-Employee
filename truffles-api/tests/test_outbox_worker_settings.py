from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core import consultant_runtime
from app.core.consultant_runtime import ConsultantRuntime, PreparedConversation
from app.models import Conversation, OutboxMessage
from app.schemas.webhook import WebhookRequest
from app.services import outbox_runtime_service as outbox_runtime
from app.workers import outbox


def test_outbox_worker_settings_parses_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "12")
    _, settings = outbox._get_outbox_worker_settings()
    assert settings.max_wait_seconds == 12


def test_outbox_worker_settings_clamps_negative_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "-5")
    _, settings = outbox._get_outbox_worker_settings()
    assert settings.max_wait_seconds == 0


def test_scoped_outbox_process_request_defaults_from_runtime_settings(monkeypatch):
    settings = outbox_runtime.OutboxProcessSettings(
        limit=9,
        idle_seconds=7,
        max_wait_seconds=11,
        max_attempts=5,
        retry_backoff_seconds=2.0,
        stale_seconds=120,
    )
    monkeypatch.setattr(outbox_runtime, "load_outbox_process_settings", lambda: settings)

    request = outbox_runtime.ScopedOutboxProcessRequest.from_optional(
        client_id="client-1",
        allowed_branch_ids=["branch-a", "branch-b"],
        archive_pending_older_than_hours=24,
    )

    assert request.limit == 9
    assert request.idle_seconds == 7
    assert request.max_wait_seconds == 11
    assert request.include_without_conversation is True
    assert request.archive_pending_limit == 9
    assert request.allowed_branch_ids == ("branch-a", "branch-b")


def _prepared_conversation(*, user_message=None) -> PreparedConversation:
    client_id = uuid4()
    branch_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        branch_id=branch_id,
        state="bot_active",
        context={},
    )
    return PreparedConversation(
        client=SimpleNamespace(id=client_id, name="demo_salon"),
        user=SimpleNamespace(id=uuid4()),
        conversation=conversation,
        user_message=user_message,
        remote_jid="77015705555@s.whatsapp.net",
        branch_id=branch_id,
        tenant_context={
            "client_id": str(client_id),
            "branch_id": str(branch_id),
            "client_slug": "demo_salon",
            "source": "webhook",
        },
        instance_id="instance-1",
        source="webhook",
    )


def _webhook_request(message_id: str = "msg-1") -> WebhookRequest:
    return WebhookRequest.model_validate(
        {
            "client_slug": "demo_salon",
            "body": {
                "message": "Хочу записаться",
                "messageType": "text",
                "metadata": {
                    "messageId": message_id,
                    "remoteJid": "77015705555@s.whatsapp.net",
                    "timestamp": 1777470000,
                    "instanceId": "instance-1",
                },
            },
        }
    )


def test_consultant_runtime_enqueue_only_writes_outbox(monkeypatch):
    captured: dict[str, object] = {}
    prepared = _prepared_conversation(
        user_message=SimpleNamespace(message_metadata={}),
    )

    def _enqueue_outbox_message(_db, **kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(
        consultant_runtime,
        "enqueue_outbox_message",
        _enqueue_outbox_message,
    )
    db = SimpleNamespace(commit=lambda: captured.setdefault("committed", True))

    response = ConsultantRuntime()._enqueue_inbound_for_outbox(
        db,
        payload=_webhook_request(),
        prepared=prepared,
    )

    assert response.success is True
    assert response.message == "Accepted"
    assert response.bot_response is None
    assert captured["client_id"] == prepared.client.id
    assert captured["conversation_id"] == prepared.conversation.id
    assert captured["branch_id"] == prepared.branch_id
    assert captured["inbound_message_id"] == "msg-1"
    assert captured["payload_json"]["tenant_context"]["client_id"] == str(prepared.client.id)
    assert captured["payload_json"]["tenant_context"]["branch_id"] == str(prepared.branch_id)
    assert prepared.user_message.message_metadata["decision_meta"]["outbox_enqueue"] == "enqueued"
    assert prepared.conversation.context["decision_trace"][-1]["stage"] == "outbox"


def test_consultant_runtime_skip_persist_persists_before_transport_failure_raise(monkeypatch):
    saved_messages: list[SimpleNamespace] = []
    prepared = _prepared_conversation()

    def _save_message(_db, conversation_id, client_id, role, content, *, message_metadata):
        message = SimpleNamespace(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=dict(message_metadata),
        )
        saved_messages.append(message)
        return message

    class _FailedResult:
        error = RuntimeError("provider unavailable")

        @staticmethod
        def is_ok():
            return False

    monkeypatch.setattr(consultant_runtime, "save_message", _save_message)
    monkeypatch.setattr(consultant_runtime, "send_message_safe", lambda *_args, **_kwargs: _FailedResult())

    runtime = ConsultantRuntime()
    bot_response = runtime._send_and_persist_reply(
        object(),
        prepared=prepared,
        reply=SimpleNamespace(reply_kind="fact", text="Ответ"),
        payload=_webhook_request(),
        enqueue_only=False,
        skip_persist=True,
    )

    assert saved_messages
    assert saved_messages[0].message_metadata["transport_status"] == "failed"
    assert bot_response is saved_messages[0]
    with pytest.raises(RuntimeError, match="ChatFlow delivery failed"):
        runtime._raise_delivery_failure_after_commit(
            skip_persist=True,
            bot_response=bot_response,
        )


@pytest.mark.asyncio
async def test_outbox_webhook_delivery_failure_marks_failed_without_retry(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    conversation_id = uuid4()
    outbox_id = uuid4()
    outbox_row = SimpleNamespace(id=outbox_id, meta={})
    conversation = SimpleNamespace(
        id=conversation_id,
        branch_id=branch_id,
        context={},
        state="bot_active",
    )

    class _Query:
        def __init__(self, result):
            self._result = result

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self._result

    class _Db:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        def query(self, model):
            if model is OutboxMessage:
                return _Query(outbox_row)
            if model is Conversation:
                return _Query(conversation)
            return _Query(None)

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    async def _delivery_failed(*_args, **_kwargs):
        raise RuntimeError(
            "ChatFlow delivery failed: [CHATFLOW_ERROR] Outbound blocked by transport mode guard"
        )

    statuses: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.core.consultant_core_v2.handle_webhook_payload",
        _delivery_failed,
    )
    monkeypatch.setattr(
        outbox_runtime,
        "mark_outbox_status",
        lambda _db, *, outbox_id, status, last_error=None, next_attempt_at=None: statuses.append(
            {
                "outbox_id": outbox_id,
                "status": status,
                "last_error": last_error,
                "next_attempt_at": next_attempt_at,
            }
        ),
    )
    monkeypatch.setattr(outbox_runtime, "record_outbox_latency", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outbox_runtime, "record_delivery_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outbox_runtime, "alert_error", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outbox_runtime, "_find_message_by_message_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        outbox_runtime,
        "_find_message_by_conversation_created_at",
        lambda *_args, **_kwargs: None,
    )

    db = _Db()
    results = await outbox_runtime.process_claimed_outbox_rows(
        db,
        [
            {
                "id": outbox_id,
                "payload_json": {
                    "client_slug": "demo_salon",
                    "body": {
                        "messageType": "text",
                        "message": "Хочу записаться",
                        "metadata": {
                            "remoteJid": "79990000000@s.whatsapp.net",
                            "messageId": "msg-1",
                        },
                    },
                    "tenant_context": {
                        "client_id": str(client_id),
                        "client_slug": "demo_salon",
                        "branch_id": str(branch_id),
                        "source": "webhook",
                    },
                },
                "attempts": 1,
                "conversation_id": conversation_id,
                "client_id": client_id,
                "branch_id": branch_id,
                "inbound_message_id": "msg-1",
                "created_at": datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
            }
        ],
        settings=outbox_runtime.OutboxProcessSettings(
            limit=10,
            idle_seconds=1,
            max_wait_seconds=1,
            max_attempts=5,
            retry_backoff_seconds=2.0,
            stale_seconds=120,
        ),
    )

    assert results == {"claimed": 1, "sent": 0, "failed": 1, "retry_scheduled": 0}
    assert db.rollbacks == 0
    assert statuses == [
        {
            "outbox_id": outbox_id,
            "status": "FAILED",
            "last_error": "ChatFlow delivery failed: [CHATFLOW_ERROR] Outbound blocked by transport mode guard",
            "next_attempt_at": None,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "handler_name"),
    [
        (outbox_runtime.OUTBOX_EVENT_CALENDAR_SYNC_OUTBOUND, "process_outbound_sync_event"),
        (outbox_runtime.OUTBOX_EVENT_KNOWLEDGE_SYNC, "process_knowledge_sync_event"),
    ],
)
async def test_process_claimed_outbox_rows_marks_sent_for_internal_outbox_events(
    monkeypatch,
    event_type,
    handler_name,
):
    marked: list[dict[str, object]] = []
    client_id = "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(outbox_runtime, handler_name, lambda **_kwargs: (True, None))
    monkeypatch.setattr(
        outbox_runtime,
        "mark_outbox_status",
        lambda _db, *, outbox_id, status, last_error=None, next_attempt_at=None: marked.append(
            {
                "outbox_id": outbox_id,
                "status": status,
                "last_error": last_error,
                "next_attempt_at": next_attempt_at,
            }
        ),
    )

    results = await outbox_runtime.process_claimed_outbox_rows(
        object(),
        [
            {
                "id": "row-1",
                "payload_json": {
                    "schema_version": "outbox.v1",
                    "event_type": event_type,
                    "client_id": client_id,
                    "tenant_context": {
                        "client_id": client_id,
                        "source": "system",
                    },
                },
                "attempts": 1,
                "conversation_id": None,
                "client_id": client_id,
                "branch_id": None,
                "inbound_message_id": None,
                "created_at": datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc),
            }
        ],
        settings=outbox_runtime.OutboxProcessSettings(
            limit=10,
            idle_seconds=8,
            max_wait_seconds=10,
            max_attempts=5,
            retry_backoff_seconds=2.0,
            stale_seconds=120,
        ),
    )

    assert results == {"claimed": 1, "sent": 1, "failed": 0, "retry_scheduled": 0}
    assert marked == [
        {
            "outbox_id": "row-1",
            "status": "SENT",
            "last_error": None,
            "next_attempt_at": None,
        }
    ]


@pytest.mark.asyncio
async def test_preview_scoped_outbox_process_summarizes_shared_runtime_scope(monkeypatch):
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    pending_rows = [
        type("Row", (), {"conversation_id": "conv-1", "created_at": now - timedelta(days=8)})(),
        type("Row", (), {"conversation_id": None, "created_at": now - timedelta(days=1)})(),
    ]
    processing_rows = [type("Row", (), {"conversation_id": "conv-2", "created_at": now})()]
    failed_rows = [type("Row", (), {"conversation_id": None, "created_at": now})()]

    def _query_rows(_db, *, request, status):
        assert request.client_id == "client-1"
        if status == "PENDING":
            return pending_rows
        if status == "PROCESSING":
            return processing_rows
        if status == "FAILED":
            return failed_rows
        return []

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(outbox_runtime, "_query_scoped_outbox_message_rows", _query_rows)
    monkeypatch.setattr(outbox_runtime, "datetime", _FrozenDateTime)

    result = await outbox_runtime.preview_scoped_outbox_process(
        object(),
        request=outbox_runtime.ScopedOutboxProcessRequest.from_optional(
            client_id="client-1",
            allowed_branch_ids=["branch-a"],
            limit=5,
            idle_seconds=12,
            max_wait_seconds=34,
            include_without_conversation=False,
        ),
    )

    assert result["mode"] == "dry_run"
    assert result["scope"] == {"client_id": "client-1", "branch_ids": ["branch-a"]}
    assert result["config"] == {
        "limit": 5,
        "idle_seconds": 12,
        "max_wait_seconds": 34,
        "include_without_conversation": False,
    }
    assert result["counts"] == {
        "pending": 2,
        "processing": 1,
        "failed": 1,
        "pending_with_conversation": 1,
        "pending_without_conversation": 1,
        "pending_older_than_7d": 1,
    }
    assert result["archive_preview"] == {"enabled": False}


@pytest.mark.asyncio
async def test_run_outbox_worker_cycle_uses_shared_runtime_helpers(monkeypatch):
    settings = outbox_runtime.OutboxProcessSettings(
        limit=2,
        idle_seconds=8,
        max_wait_seconds=10,
        max_attempts=5,
        retry_backoff_seconds=2.0,
        stale_seconds=120,
    )
    db = object()
    now = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
    claim_calls: list[dict[str, object]] = []
    process_calls: list[list[dict[str, object]]] = []

    monkeypatch.setattr(
        outbox_runtime,
        "release_stale_processing",
        lambda *_args, **_kwargs: {"released": 1, "failed": 0},
    )
    monkeypatch.setattr(
        outbox_runtime,
        "schedule_inbound_syncs",
        lambda *_args, **_kwargs: {"interval_seconds": 120, "scheduled": 1, "errors": 0},
    )

    rows_queue = [
        [{"id": "row-1"}],
        [],
    ]

    def _claim_rows(*_args, **kwargs):
        claim_calls.append(kwargs)
        return rows_queue.pop(0)

    async def _process_rows(_db, rows, *, settings):
        process_calls.append(rows)
        assert settings.limit == 2
        return {"sent": len(rows), "failed": 0}

    monkeypatch.setattr(outbox_runtime, "claim_pending_outbox_batches", _claim_rows)
    monkeypatch.setattr(outbox_runtime, "process_claimed_outbox_rows", _process_rows)
    monkeypatch.setattr(outbox_runtime.time, "monotonic", lambda: 0.05)

    result = await outbox_runtime.run_outbox_worker_cycle(
        db,
        settings=settings,
        interval_seconds=1.0,
        next_inbound_schedule_at=None,
        now=now,
        loop_started_at=0.0,
    )

    assert result.next_inbound_schedule_at == now + timedelta(seconds=120)
    assert result.released_stale == {"released": 1, "failed": 0}
    assert result.inbound_results == {"interval_seconds": 120, "scheduled": 1, "errors": 0}
    assert result.processed_batches == 1
    assert process_calls == [[{"id": "row-1"}]]
    assert claim_calls == [
        {
            "limit": 2,
            "idle_seconds": 8,
            "max_wait_seconds": 10,
            "include_without_conversation": True,
        },
        {
            "limit": 2,
            "idle_seconds": 8,
            "max_wait_seconds": 10,
            "include_without_conversation": True,
        },
    ]


@pytest.mark.asyncio
async def test_run_default_outbox_process_uses_canonical_runtime_helper(monkeypatch):
    settings = outbox_runtime.OutboxProcessSettings(
        limit=10,
        idle_seconds=8,
        max_wait_seconds=10,
        max_attempts=5,
        retry_backoff_seconds=2.0,
        stale_seconds=120,
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(outbox_runtime, "load_outbox_process_settings", lambda: settings)
    monkeypatch.setattr(
        outbox_runtime,
        "release_stale_processing",
        lambda *_args, **_kwargs: {"released": 1, "failed": 0},
    )
    monkeypatch.setattr(
        outbox_runtime,
        "schedule_inbound_syncs",
        lambda *_args, **_kwargs: {"scheduled": 1, "errors": 0},
    )
    monkeypatch.setattr(
        outbox_runtime,
        "process_reminder_jobs",
        lambda *_args, **_kwargs: {"total": 1, "processed": 1},
    )

    async def _fake_run_canonical(_db, *, settings, claim_rows):
        captured["settings"] = settings
        captured["rows"] = claim_rows()
        return captured["rows"], {"sent": 1, "failed": 0}

    monkeypatch.setattr(outbox_runtime, "run_canonical_outbox_process", _fake_run_canonical)
    monkeypatch.setattr(
        outbox_runtime,
        "claim_pending_outbox_batches",
        lambda *_args, **kwargs: [kwargs],
    )

    result = await outbox_runtime.run_default_outbox_process(object(), include_reminders=True)

    assert captured["settings"] is settings
    assert captured["rows"] == [
        {
            "limit": 10,
            "idle_seconds": 8,
            "max_wait_seconds": 10,
            "include_without_conversation": True,
        }
    ]
    assert result["sent"] == 1
    assert result["calendar_inbound"] == {"scheduled": 1, "errors": 0}
    assert result["reminder_jobs"] == {"total": 1, "processed": 1}
    assert result["released_stale"] == 1
    assert result["failed_stale"] == 0


@pytest.mark.asyncio
async def test_run_scoped_outbox_process_uses_shared_runtime_helpers(monkeypatch):
    client_id = object()
    allowed_branch_ids = [object()]
    settings = outbox_runtime.OutboxProcessSettings(
        limit=10,
        idle_seconds=8,
        max_wait_seconds=10,
        max_attempts=5,
        retry_backoff_seconds=2.0,
        stale_seconds=120,
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(outbox_runtime, "load_outbox_process_settings", lambda: settings)

    def _fake_archive(*_args, **kwargs):
        captured["archive"] = kwargs
        return {"matched": 2, "archived": 2}

    async def _fake_run_canonical(_db, *, settings, claim_rows):
        captured["settings"] = settings
        captured["rows"] = claim_rows()
        return captured["rows"], {"sent": 1, "failed": 0}

    monkeypatch.setattr(outbox_runtime, "archive_pending_outbox", _fake_archive)
    monkeypatch.setattr(outbox_runtime, "run_canonical_outbox_process", _fake_run_canonical)
    monkeypatch.setattr(
        outbox_runtime,
        "claim_scoped_outbox_rows",
        lambda *_args, **kwargs: [{**kwargs, "id": "row-1"}],
    )

    result = await outbox_runtime.run_scoped_outbox_process(
        object(),
        request=outbox_runtime.ScopedOutboxProcessRequest.from_optional(
            client_id=client_id,
            allowed_branch_ids=allowed_branch_ids,
            limit=5,
            idle_seconds=12,
            max_wait_seconds=34,
            include_without_conversation=False,
            archive_pending_older_than_hours=24,
            archive_pending_limit=7,
            archive_pending_without_conversation_only=True,
            settings=settings,
        ),
    )

    assert result["processed"] == 1
    assert result["results"] == {"sent": 1, "failed": 0}
    assert result["archive"] == {"matched": 2, "archived": 2}
    assert captured["archive"]["client_id"] is client_id
    assert captured["archive"]["older_than_seconds"] == 24 * 3600
    assert captured["archive"]["limit"] == 7
    assert captured["archive"]["branch_ids"] == allowed_branch_ids
    assert captured["archive"]["only_without_conversation"] is True
    assert captured["rows"] == [
        {
            "client_id": client_id,
            "allowed_branch_ids": allowed_branch_ids,
            "limit": 5,
            "idle_seconds": 12,
            "max_wait_seconds": 34,
            "include_without_conversation": False,
            "id": "row-1",
        }
    ]
    assert captured["settings"] is settings


def test_outbox_worker_startup_guard_blocks_unsafe_mode(monkeypatch):
    monkeypatch.setenv("OUTBOX_WORKER_ENABLED", "1")
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@prod-db.internal:5432/chatbot")
    monkeypatch.delenv("OUTBOUND_ALLOWLIST_JIDS", raising=False)
    monkeypatch.delenv("OUTBOX_WORKER_UNSAFE_ALLOW", raising=False)

    with pytest.raises(RuntimeError):
        outbox.assert_outbox_worker_startup_safe()


def test_outbox_worker_startup_guard_can_be_overridden(monkeypatch):
    monkeypatch.setenv("OUTBOX_WORKER_ENABLED", "1")
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@prod-db.internal:5432/chatbot")
    monkeypatch.delenv("OUTBOUND_ALLOWLIST_JIDS", raising=False)
    monkeypatch.setenv("OUTBOX_WORKER_UNSAFE_ALLOW", "1")

    snapshot = outbox.assert_outbox_worker_startup_safe()

    assert "test_mode_outbox_worker_on_nonlocal_db" in snapshot.danger_flags
