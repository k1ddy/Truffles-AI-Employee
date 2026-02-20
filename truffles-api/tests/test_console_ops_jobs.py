from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models import AlertEvent
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


@pytest.mark.asyncio
async def test_run_ops_job_incident_state_success(monkeypatch):
    request = SimpleNamespace(query_params={})
    db = _build_db_with_job_identity()
    context = _build_context()
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_require_ops_access", lambda _context, action="read": None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    async def _fake_runner(_db, *, context, mode, params):
        assert mode == "execute"
        assert params["incident_id"] == "outbox-demo"
        assert params["incident_state"] == "resolved"
        assert context.client.id
        return {"mode": "execute", "incident_id": "outbox-demo", "incident_state": "resolved"}

    monkeypatch.setattr(console_router, "_run_incident_state_job", _fake_runner)

    response = await console_router.run_ops_job(
        body=ConsoleOpsJobRunRequest(
            job_type="incident_state",
            mode="execute",
            params={"incident_id": "outbox-demo", "incident_state": "resolved"},
        ),
        request=request,
        db=db,
    )

    assert response.job.status == "success"
    assert response.job.result_payload["incident_state"] == "resolved"
    assert response.job.result_payload["artifact"]["artifact_type"] == "incident_state_report"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_incident_state_job_execute_adds_alert_event():
    db = Mock()
    captured: dict[str, object] = {}

    def _capture_add(obj):
        captured["obj"] = obj

    db.add.side_effect = _capture_add
    context = _build_context()

    result = await console_router._run_incident_state_job(
        db,
        context=context,
        mode="execute",
        params={
            "incident_id": "outbox-demo",
            "incident_state": "in_progress",
            "owner": "ops@truffles",
            "note": "working on provider binding",
            "reason_code": "provider_billing_blocked",
            "due_at": "2026-02-21T10:00:00+00:00",
        },
    )

    assert result["incident_state"] == "in_progress"
    assert result["incident_id"] == "outbox-demo"
    event = captured.get("obj")
    assert isinstance(event, AlertEvent)
    assert event.alert_type == "console_incident_state"
    assert event.alert_metadata["incident_id"] == "outbox-demo"
    assert event.alert_metadata["incident_state"] == "in_progress"
    assert event.alert_metadata["owner"] == "ops@truffles"


@pytest.mark.asyncio
async def test_run_incident_state_job_resolved_requires_evidence_payload():
    db = Mock()
    context = _build_context()

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router._run_incident_state_job(
            db,
            context=context,
            mode="execute",
            params={
                "incident_id": "outbox-demo",
                "incident_state": "resolved",
                "reason_code": "provider_billing_blocked",
            },
        )

    assert exc_info.value.code == "INCIDENT_EVIDENCE_REQUIRED"


@pytest.mark.asyncio
async def test_run_incident_state_job_resolved_with_evidence_adds_metadata():
    db = Mock()
    captured: dict[str, object] = {}

    def _capture_add(obj):
        captured["obj"] = obj

    db.add.side_effect = _capture_add
    context = _build_context()

    result = await console_router._run_incident_state_job(
        db,
        context=context,
        mode="execute",
        params={
            "incident_id": "outbox-demo",
            "incident_state": "resolved",
            "reason_code": "provider_billing_blocked",
            "note": "Ops executed remediation and validated post-check.",
            "evidence_confirmed": True,
            "evidence_summary": "checklist=all_passed | delta_failed_24h=-4",
        },
    )

    assert result["incident_state"] == "resolved"
    assert result["evidence_confirmed"] is True
    assert result["evidence_summary"] == "checklist=all_passed | delta_failed_24h=-4"
    event = captured.get("obj")
    assert isinstance(event, AlertEvent)
    assert event.alert_metadata["incident_state"] == "resolved"
    assert event.alert_metadata["evidence_confirmed"] is True
    assert event.alert_metadata["evidence_summary"] == "checklist=all_passed | delta_failed_24h=-4"


@pytest.mark.asyncio
async def test_run_outbox_process_job_execute_supports_archive_and_single_message_flag(monkeypatch):
    db = Mock()
    context = _build_context()
    captured: dict[str, object] = {}

    def _fake_archive(
        _db,
        *,
        client_id,
        older_than_seconds,
        limit,
        reason,
        branch_ids,
        only_without_conversation,
    ):
        captured["archive"] = {
            "client_id": client_id,
            "older_than_seconds": older_than_seconds,
            "limit": limit,
            "reason": reason,
            "branch_ids": branch_ids,
            "only_without_conversation": only_without_conversation,
        }
        return {"matched": 3, "archived": 3}

    def _fake_claim(
        _db,
        *,
        context,
        limit,
        idle_seconds,
        max_wait_seconds,
        include_without_conversation,
    ):
        captured["claim"] = {
            "context_client_id": context.client.id,
            "limit": limit,
            "idle_seconds": idle_seconds,
            "max_wait_seconds": max_wait_seconds,
            "include_without_conversation": include_without_conversation,
        }
        return []

    monkeypatch.setattr(console_router, "archive_pending_outbox", _fake_archive)
    monkeypatch.setattr(console_router, "_claim_scoped_outbox_rows", _fake_claim)

    result = await console_router._run_outbox_process_job(
        db,
        context=context,
        mode="execute",
        params={
            "limit": 5,
            "idle_seconds": 12,
            "max_wait_seconds": 34,
            "include_without_conversation": False,
            "archive_pending_older_than_hours": 24,
            "archive_pending_limit": 7,
            "archive_pending_without_conversation_only": True,
        },
    )

    assert result["processed"] == 0
    assert result["results"]["processed"] == 0
    assert result["archive"] == {"matched": 3, "archived": 3}
    assert captured["claim"]["include_without_conversation"] is False
    assert captured["archive"]["older_than_seconds"] == 24 * 3600
    assert captured["archive"]["limit"] == 7
    assert captured["archive"]["only_without_conversation"] is True
