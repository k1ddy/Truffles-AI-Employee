import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleKnowledgeActivationRetryRequest, ConsoleReminderRetryRequest
from app.services.console_errors import ConsoleAPIError


def test_parse_outbox_status_param_defaults_to_failed():
    assert console_router._parse_outbox_status_param(None) == ["FAILED"]
    assert console_router._parse_outbox_status_param("") == ["FAILED"]


def test_parse_outbox_status_param_all():
    assert console_router._parse_outbox_status_param("all") is None


def test_parse_outbox_status_param_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_outbox_status_param("oops")


def test_parse_knowledge_activation_status_param_defaults_to_failed():
    assert console_router._parse_knowledge_activation_status_param(None) == ["failed"]
    assert console_router._parse_knowledge_activation_status_param("") == ["failed"]


def test_parse_knowledge_activation_status_param_all():
    assert console_router._parse_knowledge_activation_status_param("all") is None


def test_parse_knowledge_activation_status_param_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_knowledge_activation_status_param("oops")


def test_summarize_outbox_payload_contract():
    payload = {
        "client_slug": "demo_salon",
        "tenant_context": {
            "client_id": str(uuid4()),
            "branch_id": str(uuid4()),
        },
        "body": {
            "messageType": "text",
            "message": "Hello there",
            "metadata": {
                "remoteJid": "77000000000@s.whatsapp.net",
                "instanceId": "demo",
                "forwarded_to_telegram": True,
            },
        },
    }
    summary = console_router._summarize_outbox_payload(payload)
    assert summary["message_type"] == "text"
    assert summary["message_preview"] == "Hello there"
    assert summary["remote_jid"] == "77000000000@s.whatsapp.net"
    assert summary["instance_id"] == "demo"
    assert summary["forwarded_to_telegram"] is True
    assert summary["channel"] == "whatsapp"


def test_summarize_outbox_payload_fallback():
    payload = {
        "body": {
            "message": "Fallback message",
            "metadata": {"remoteJid": "77000000000@s.whatsapp.net"},
        }
    }
    summary = console_router._summarize_outbox_payload(payload)
    assert summary["message_preview"] == "Fallback message"
    assert summary["remote_jid"] == "77000000000@s.whatsapp.net"
    assert summary["channel"] == "whatsapp"


def test_parse_reminder_status_param_default_all():
    assert console_router._parse_reminder_status_param(None) is None
    assert console_router._parse_reminder_status_param("") is None
    assert console_router._parse_reminder_status_param("all") is None


def test_parse_reminder_status_param_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_reminder_status_param("oops")


def test_parse_reminder_retry_status_param():
    assert console_router._parse_reminder_retry_status_param("failed") == ["FAILED"]
    assert console_router._parse_reminder_retry_status_param("pending") == ["PENDING"]
    assert console_router._parse_reminder_retry_status_param("all") == ["PENDING", "FAILED"]

    with pytest.raises(ConsoleAPIError):
        console_router._parse_reminder_retry_status_param("sent")


@pytest.mark.asyncio
async def test_retry_reminders_requires_confirm_for_bulk(monkeypatch):
    request = SimpleNamespace(query_params={})
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        agent=SimpleNamespace(id=uuid4(), role="platform_admin"),
        role="platform_admin",
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)

    now = datetime.now(timezone.utc)
    row_a = SimpleNamespace(
        id=uuid4(),
        status="FAILED",
        next_attempt_at=now,
        last_error="outbox_duplicate",
        updated_at=now,
        run_at=now,
    )
    row_b = SimpleNamespace(
        id=uuid4(),
        status="FAILED",
        next_attempt_at=now,
        last_error="outbox_duplicate",
        updated_at=now,
        run_at=now,
    )

    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = [row_a, row_b]
    db.query.return_value = query

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.retry_reminders(
            body=ConsoleReminderRetryRequest(limit=10, status="failed", confirm=False),
            request=request,
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_retry_reminders_sets_pending_and_commits(monkeypatch):
    request = SimpleNamespace(query_params={})
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        agent=SimpleNamespace(id=uuid4(), role="platform_admin"),
        role="platform_admin",
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    now = datetime.now(timezone.utc)
    row_a = SimpleNamespace(
        id=uuid4(),
        status="FAILED",
        next_attempt_at=now,
        last_error="remote_jid_missing",
        updated_at=now,
        run_at=now,
    )
    row_b = SimpleNamespace(
        id=uuid4(),
        status="PENDING",
        next_attempt_at=now,
        last_error=None,
        updated_at=now,
        run_at=now,
    )

    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = [row_a, row_b]
    db.query.return_value = query

    response = await console_router.retry_reminders(
        body=ConsoleReminderRetryRequest(limit=10, status="all", confirm=True),
        request=request,
        db=db,
    )

    assert response.success is True
    assert response.retried == 2
    assert row_a.status == "PENDING"
    assert row_b.status == "PENDING"
    assert row_a.last_error is None
    assert row_a.next_attempt_at is None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_console_health_uses_runtime_redis_fallback_when_url_missing(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    captured: dict[str, object] = {}

    class _RedisClient:
        def ping(self):
            return True

    class _RedisFactory:
        @staticmethod
        def from_url(url: str, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return _RedisClient()

    monkeypatch.setitem(sys.modules, "redis", SimpleNamespace(Redis=_RedisFactory))

    db = Mock()
    db.execute.return_value = None
    outbox_query = Mock()
    outbox_query.filter.return_value = outbox_query
    outbox_query.count.return_value = 0
    db.query.return_value = outbox_query

    response = await console_router.get_health(db=db)

    assert response.database == "connected"
    assert response.redis == "connected"
    assert response.status == "ok"
    assert captured["url"] == console_router._DEFAULT_RUNTIME_REDIS_URL


@pytest.mark.asyncio
async def test_console_health_sets_unhealthy_when_database_is_unavailable(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://unit-test:6379/0")

    class _RedisClient:
        def ping(self):
            return True

    class _RedisFactory:
        @staticmethod
        def from_url(_url: str, **_kwargs):
            return _RedisClient()

    monkeypatch.setitem(sys.modules, "redis", SimpleNamespace(Redis=_RedisFactory))

    db = Mock()
    db.execute.side_effect = RuntimeError("db down")
    outbox_query = Mock()
    outbox_query.filter.return_value = outbox_query
    outbox_query.count.return_value = 0
    db.query.return_value = outbox_query

    response = await console_router.get_health(db=db)

    assert response.database == "error"
    assert response.status == "unhealthy"


@pytest.mark.asyncio
async def test_console_health_includes_knowledge_activation_summary(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://unit-test:6379/0")

    class _RedisClient:
        def ping(self):
            return True

    class _RedisFactory:
        @staticmethod
        def from_url(_url: str, **_kwargs):
            return _RedisClient()

    monkeypatch.setitem(sys.modules, "redis", SimpleNamespace(Redis=_RedisFactory))
    monkeypatch.setattr(
        console_router,
        "build_knowledge_activation_health_snapshot",
        lambda _db: {
            "status": "warning",
            "metric_basis": "latest_activation_job_per_version",
            "counts": {"queued": 2, "running": 1, "ready": 0, "failed": 1, "stuck": 0},
            "failed_24h": 1,
            "stale_running": 0,
            "oldest_queued_age_seconds": 1200,
            "oldest_running_heartbeat_age_seconds": 90,
            "thresholds": {
                "queued_warning": 1,
                "queued_critical": 5,
                "failed_24h_warning": 1,
                "failed_24h_critical": 3,
                "stuck_warning": 1,
                "stuck_critical": 2,
                "oldest_queued_warning_seconds": 600,
                "oldest_queued_critical_seconds": 1800,
                "stale_running_critical": 1,
            },
        },
    )

    db = Mock()
    db.execute.return_value = None
    outbox_query = Mock()
    outbox_query.filter.return_value = outbox_query
    outbox_query.count.return_value = 0
    db.query.return_value = outbox_query

    response = await console_router.get_health(db=db)

    assert response.status == "degraded"
    assert response.knowledge_activation is not None
    assert response.knowledge_activation.status == "warning"
    assert response.knowledge_activation.counts.queued == 2


@pytest.mark.asyncio
async def test_list_knowledge_activation_jobs_returns_latest_items(monkeypatch):
    request = SimpleNamespace(query_params={})
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        agent=SimpleNamespace(id=uuid4(), role="platform_admin"),
        role="platform_admin",
    )
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(
        id=uuid4(),
        branch_id=uuid4(),
        version_id=uuid4(),
        state="FAILED",
        current_stage="failed",
        source="knowledge_publish",
        attempt_count=2,
        queued_at=now,
        started_at=now,
        heartbeat_at=now,
        finished_at=now,
        last_error="boom",
        error_code="activation_failed",
        created_at=now,
        updated_at=now,
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)
    monkeypatch.setattr(
        console_router,
        "build_knowledge_activation_health_snapshot",
        lambda _db, **_kwargs: {
            "counts": {"queued": 0, "running": 0, "ready": 0, "failed": 1, "stuck": 0},
        },
    )
    monkeypatch.setattr(
        console_router,
        "list_latest_knowledge_activation_jobs",
        lambda _db, **_kwargs: [job],
    )

    response = await console_router.list_knowledge_activation_jobs(
        request=request,
        status="failed",
        db=Mock(),
    )

    assert response.counts.failed == 1
    assert response.counts.total == 1
    assert len(response.items) == 1
    assert response.items[0].state == "failed"
    assert response.items[0].stage == "failed"
    assert response.items[0].attempt_count == 2


@pytest.mark.asyncio
async def test_retry_knowledge_activation_jobs_creates_new_attempt(monkeypatch):
    request = SimpleNamespace(query_params={})
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        agent=SimpleNamespace(id=uuid4(), role="platform_admin"),
        role="platform_admin",
    )
    job = SimpleNamespace(
        id=uuid4(),
        branch_id=uuid4(),
        version_id=uuid4(),
        state="FAILED",
        current_stage="failed",
    )
    branch = SimpleNamespace(id=job.branch_id, client_id=context.client.id)
    version = SimpleNamespace(id=job.version_id, client_id=context.client.id)
    created: list[dict] = []

    class _BranchQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return [branch]

    class _VersionQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return [version]

    db = Mock()
    db.query.side_effect = lambda model: _BranchQuery() if model is console_router.Branch else _VersionQuery()

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "list_latest_knowledge_activation_jobs", lambda _db, **_kwargs: [job])
    monkeypatch.setattr(
        console_router,
        "create_knowledge_activation_job",
        lambda _db, **kwargs: created.append(kwargs),
    )

    response = await console_router.retry_knowledge_activation_jobs(
        body=ConsoleKnowledgeActivationRetryRequest(ids=[job.id], status="all"),
        request=request,
        db=db,
    )

    assert response.success is True
    assert response.retried == 1
    assert response.skipped == 0
    assert created[0]["branch"] is branch
    assert created[0]["version"] is version
    assert created[0]["source"] == "console_ops_retry"
    db.commit.assert_called_once()
