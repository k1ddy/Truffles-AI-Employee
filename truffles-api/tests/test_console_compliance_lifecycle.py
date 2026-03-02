from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleComplianceLifecycleRunRequest
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", client_id=None, company_id=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), name="Agent"),
        client=SimpleNamespace(
            id=client_id or uuid4(),
            company_id=company_id or uuid4(),
        ),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
    )


def _run_record(*, client_id=None, branch_id=None, agent_id=None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        scope="client" if branch_id is None else "branch",
        data_class="learned_responses",
        operation="retention_scan",
        run_mode="preview",
        status="completed",
        client_id=client_id or uuid4(),
        branch_id=branch_id,
        policy_version_id=None,
        policy_scope="client",
        summary_json={"candidate_count": 1},
        error_message=None,
        started_at=now,
        finished_at=now,
        triggered_by=agent_id or uuid4(),
        created_at=now,
        updated_at=now,
    )


def _record_item(*, run_id):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        run_id=run_id,
        entity_type="learned_response",
        entity_id=str(uuid4()),
        action="retention_scan",
        result="candidate",
        payload_json={"retention_expires_at": now.isoformat()},
        occurred_at=now,
    )


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()
    body = ConsoleComplianceLifecycleRunRequest(
        scope="client",
        operation="retention_scan",
        reason="run retention preview",
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_compliance_lifecycle(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_branch_scope_requires_branch_id(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsoleComplianceLifecycleRunRequest(
        scope="branch",
        operation="retention_scan",
        reason="run retention preview",
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_compliance_lifecycle(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_success(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    context = _mock_context(role="platform_admin", client_id=client_id, agent_id=agent_id)
    db = Mock()
    body = ConsoleComplianceLifecycleRunRequest(
        scope="client",
        operation="destruction_preview",
        reason="preview",
        max_items=5,
    )
    run = _run_record(client_id=client_id, agent_id=agent_id)
    records = [_record_item(run_id=run.id)]

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_policy_registry_scope", lambda *args, **kwargs: ("client", None))
    monkeypatch.setattr(
        console_router,
        "_execute_compliance_lifecycle_preview_run",
        lambda *args, **kwargs: (run, records),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.run_compliance_lifecycle(
        request=Mock(),
        body=body,
        db=db,
    )

    assert response.success is True
    assert response.run.id == run.id
    assert len(response.records) == 1
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_compliance_lifecycle_run_returns_not_found(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_policy_registry_scope", lambda *args, **kwargs: ("client", None))
    monkeypatch.setattr(console_router, "get_lifecycle_run", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_compliance_lifecycle_run(
            run_id=uuid4(),
            request=Mock(),
            scope="client",
            branch_id=None,
            records_limit=10,
            db=db,
        )

    assert exc_info.value.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_compliance_lifecycle_runs_returns_items(monkeypatch):
    client_id = uuid4()
    context = _mock_context(role="platform_admin", client_id=client_id)
    db = Mock()
    run = _run_record(client_id=client_id)

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_policy_registry_scope", lambda *args, **kwargs: ("client", None))
    monkeypatch.setattr(console_router, "list_lifecycle_runs", lambda *args, **kwargs: [run])

    response = await console_router.list_compliance_lifecycle_runs(
        request=Mock(),
        scope="client",
        branch_id=None,
        data_class=None,
        operation=None,
        limit=20,
        db=db,
    )

    assert len(response.items) == 1
    assert response.items[0].id == run.id


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_job_returns_preview_summary(monkeypatch):
    client_id = uuid4()
    context = _mock_context(role="platform_admin", client_id=client_id)
    db = Mock()
    run = _run_record(client_id=client_id)
    records = [_record_item(run_id=run.id), _record_item(run_id=run.id)]
    captured: dict[str, object] = {}

    monkeypatch.setattr(console_router, "_resolve_policy_registry_scope", lambda *args, **kwargs: ("client", None))

    def _fake_execute(*args, **kwargs):
        captured["run_mode"] = kwargs["run_mode"]
        captured["operation"] = kwargs["operation"]
        captured["max_items"] = kwargs["max_items"]
        return run, records

    monkeypatch.setattr(console_router, "_execute_compliance_lifecycle_preview_run", _fake_execute)

    result = await console_router._run_compliance_lifecycle_job(
        db,
        context=context,
        mode="execute",
        params={"operation": "destruction_preview", "max_items": 12},
    )

    assert result["mode"] == "execute"
    assert result["status"] == "completed"
    assert result["records_count"] == 2
    assert result["lane"] == "manual"
    assert result["skipped"] is False
    assert captured["run_mode"] == "manual"
    assert captured["operation"] == "destruction_preview"
    assert captured["max_items"] == 12


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_job_rejects_invalid_scope():
    db = Mock()
    context = _mock_context(role="platform_admin")

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router._run_compliance_lifecycle_job(
            db,
            context=context,
            mode="dry_run",
            params={"scope": "fleet"},
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_job_auto_lane_skips_when_not_due(monkeypatch):
    db = Mock()
    context = _mock_context(role="platform_admin")
    recent_job = SimpleNamespace(
        id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr(console_router, "_resolve_policy_registry_scope", lambda *args, **kwargs: ("client", None))
    monkeypatch.setattr(
        console_router,
        "_find_recent_compliance_lifecycle_ops_job",
        lambda *args, **kwargs: recent_job,
    )
    monkeypatch.setattr(
        console_router,
        "_execute_compliance_lifecycle_preview_run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not execute")),
    )

    result = await console_router._run_compliance_lifecycle_job(
        db,
        context=context,
        mode="execute",
        params={
            "lane": "auto",
            "operation": "retention_scan",
            "cadence_minutes": 60,
        },
    )

    assert result["skipped"] is True
    assert result["skip_reason"] == "cadence_not_due"
    assert result["last_run_job_id"] == str(recent_job.id)


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_job_auto_lane_dry_run_ignores_cadence(monkeypatch):
    db = Mock()
    context = _mock_context(role="platform_admin")
    run = _run_record(client_id=context.client.id, agent_id=context.agent.id)
    records = [_record_item(run_id=run.id)]
    captured: dict[str, object] = {}

    monkeypatch.setattr(console_router, "_resolve_policy_registry_scope", lambda *args, **kwargs: ("client", None))
    monkeypatch.setattr(
        console_router,
        "_find_recent_compliance_lifecycle_ops_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("cadence lookup must be execute-only")),
    )

    def _fake_execute(*args, **kwargs):
        captured["run_mode"] = kwargs["run_mode"]
        captured["operation"] = kwargs["operation"]
        return run, records

    monkeypatch.setattr(console_router, "_execute_compliance_lifecycle_preview_run", _fake_execute)

    result = await console_router._run_compliance_lifecycle_job(
        db,
        context=context,
        mode="dry_run",
        params={
            "lane": "auto",
            "operation": "retention_scan",
            "cadence_minutes": 60,
        },
    )

    assert result["mode"] == "dry_run"
    assert result["skipped"] is False
    assert result["lane"] == "auto"
    assert captured["operation"] == "retention_scan"
    assert captured["run_mode"] == "preview"


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_job_auto_lane_runs_when_due(monkeypatch):
    db = Mock()
    context = _mock_context(role="platform_admin")
    run = _run_record(client_id=context.client.id, agent_id=context.agent.id)
    records = [_record_item(run_id=run.id)]
    old_job = SimpleNamespace(
        id=uuid4(),
        created_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(console_router, "_resolve_policy_registry_scope", lambda *args, **kwargs: ("client", None))
    monkeypatch.setattr(
        console_router,
        "_find_recent_compliance_lifecycle_ops_job",
        lambda *args, **kwargs: old_job,
    )

    def _fake_execute(*args, **kwargs):
        captured["operation"] = kwargs["operation"]
        captured["run_mode"] = kwargs["run_mode"]
        return run, records

    monkeypatch.setattr(console_router, "_execute_compliance_lifecycle_preview_run", _fake_execute)

    result = await console_router._run_compliance_lifecycle_job(
        db,
        context=context,
        mode="execute",
        params={
            "lane": "auto",
            "profile": "destruction_daily",
            "cadence_minutes": 60,
        },
    )

    assert result["skipped"] is False
    assert result["lane"] == "auto"
    assert result["profile"] == "destruction_daily"
    assert captured["operation"] == "destruction_preview"
    assert captured["run_mode"] == "manual"


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_job_rejects_invalid_profile():
    db = Mock()
    context = _mock_context(role="platform_admin")

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router._run_compliance_lifecycle_job(
            db,
            context=context,
            mode="dry_run",
            params={"profile": "weekly_cleanup"},
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert "profile must be" in exc_info.value.message


@pytest.mark.asyncio
async def test_run_compliance_lifecycle_job_rejects_profile_operation_mismatch():
    db = Mock()
    context = _mock_context(role="platform_admin")

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router._run_compliance_lifecycle_job(
            db,
            context=context,
            mode="execute",
            params={
                "profile": "destruction_daily",
                "operation": "retention_scan",
            },
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert "operation must match selected profile" in exc_info.value.message
