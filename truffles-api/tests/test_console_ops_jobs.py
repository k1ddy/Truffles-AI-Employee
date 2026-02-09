from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleOpsJobRunRequest
from app.services.console_errors import ConsoleAPIError


def _build_context():
    return SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        agent=SimpleNamespace(id=uuid4(), role="platform_admin"),
        role="platform_admin",
    )


def _build_db_with_job_identity():
    db = Mock()
    captured: dict[str, object] = {}

    def _capture_job(job):
        captured["job"] = job

    def _hydrate_job():
        job = captured["job"]
        job.id = uuid4()
        job.created_at = datetime.now(timezone.utc)

    db.add.side_effect = _capture_job
    db.flush.side_effect = _hydrate_job
    db.refresh.side_effect = lambda _job: None
    return db


def test_parse_ops_job_params_rejects_non_object():
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._parse_ops_job_params(["bad"])

    assert exc_info.value.code == "INVALID_PARAM"


def test_parse_ops_job_int_param_validates_bounds():
    params = {"limit": "5"}
    assert console_router._parse_ops_job_int_param(params, name="limit", default=1, min_value=1, max_value=10) == 5

    with pytest.raises(ConsoleAPIError):
        console_router._parse_ops_job_int_param({"limit": 0}, name="limit", default=1, min_value=1, max_value=10)


@pytest.mark.asyncio
async def test_run_ops_job_success(monkeypatch):
    request = SimpleNamespace(query_params={})
    db = _build_db_with_job_identity()
    context = _build_context()
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    async def _fake_runner(_db, *, context, mode, params):
        assert mode == "dry_run"
        assert params == {"limit": 7}
        assert context.client.id
        return {"mode": "dry_run", "ok": True}

    monkeypatch.setattr(console_router, "_run_outbox_process_job", _fake_runner)

    response = await console_router.run_ops_job(
        body=ConsoleOpsJobRunRequest(job_type="outbox_process", mode="dry_run", params={"limit": 7}),
        request=request,
        db=db,
    )

    assert response.job.status == "success"
    assert response.job.result_payload["mode"] == "dry_run"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_ops_job_records_failed_status_on_console_error(monkeypatch):
    request = SimpleNamespace(query_params={})
    db = _build_db_with_job_identity()
    context = _build_context()
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    async def _fake_runner(_db, *, context, mode, params):
        _ = (context, mode, params)
        raise ConsoleAPIError(400, "INVALID_PARAM", "heal execute is not available in this slice")

    monkeypatch.setattr(console_router, "_run_heal_job", _fake_runner)

    response = await console_router.run_ops_job(
        body=ConsoleOpsJobRunRequest(job_type="heal", mode="execute", params={}),
        request=request,
        db=db,
    )

    assert response.job.status == "failed"
    assert response.job.error_message == "heal execute is not available in this slice"
    assert response.job.result_payload["error"]["code"] == "INVALID_PARAM"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_ops_job_integration_reconcile_success(monkeypatch):
    request = SimpleNamespace(query_params={})
    db = _build_db_with_job_identity()
    context = _build_context()
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    async def _fake_runner(_db, *, context, mode, params):
        assert mode == "dry_run"
        assert params == {"limit": 5}
        assert context.client.id
        return {"mode": "dry_run", "checked": 2}

    monkeypatch.setattr(console_router, "_run_integration_reconcile_job", _fake_runner)

    response = await console_router.run_ops_job(
        body=ConsoleOpsJobRunRequest(job_type="integration_reconcile", mode="dry_run", params={"limit": 5}),
        request=request,
        db=db,
    )

    assert response.job.status == "success"
    assert response.job.result_payload["checked"] == 2
    assert response.job.result_payload["artifact"]["artifact_type"] == "integration_reconcile_report"
    db.commit.assert_called_once()
