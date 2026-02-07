from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.routers import console as console_router
from app.schemas.console import ConsoleBranchIntegrationStatus


def _make_branch(
    *,
    is_active: bool = True,
    instance_id: str | None = "instance-1",
    telegram_chat_id: str | None = "12345",
    webhook_secret: str | None = "whs_v1_secret",
):
    return SimpleNamespace(
        id=uuid4(),
        slug="branch-a",
        name="Branch A",
        is_active=is_active,
        instance_id=instance_id,
        telegram_chat_id=telegram_chat_id,
        webhook_secret=webhook_secret,
    )


def test_build_branch_integration_status_missing_instance():
    branch = _make_branch(instance_id=None)
    result = console_router._build_branch_integration_status(
        client_slug="demo",
        branch=branch,
        has_telegram_bot_token=True,
        stale_after_minutes=60,
        last_inbound_at=None,
        last_inbound_instance_id=None,
        now=datetime.now(timezone.utc),
    )

    assert result.whatsapp_status == "missing_instance_id"
    assert result.status == "error"
    assert "missing_instance_id" in result.drift_issues


def test_build_branch_integration_status_instance_mismatch():
    branch = _make_branch(instance_id="expected-instance")
    result = console_router._build_branch_integration_status(
        client_slug="demo",
        branch=branch,
        has_telegram_bot_token=True,
        stale_after_minutes=60,
        last_inbound_at=datetime.now(timezone.utc),
        last_inbound_instance_id="other-instance",
        now=datetime.now(timezone.utc),
    )

    assert result.whatsapp_status == "instance_id_mismatch"
    assert result.status == "error"
    assert "instance_id_mismatch" in result.drift_issues


def test_build_branch_integration_status_no_recent_inbound():
    branch = _make_branch(instance_id="instance-1")
    now = datetime.now(timezone.utc)
    result = console_router._build_branch_integration_status(
        client_slug="demo",
        branch=branch,
        has_telegram_bot_token=True,
        stale_after_minutes=30,
        last_inbound_at=now - timedelta(minutes=31),
        last_inbound_instance_id="instance-1",
        now=now,
    )

    assert result.whatsapp_status == "no_recent_inbound"
    assert result.status == "warn"
    assert "no_recent_inbound" in result.drift_issues


def test_build_branch_integration_status_ok():
    branch = _make_branch(instance_id="instance-1")
    now = datetime.now(timezone.utc)
    result = console_router._build_branch_integration_status(
        client_slug="demo",
        branch=branch,
        has_telegram_bot_token=True,
        stale_after_minutes=30,
        last_inbound_at=now - timedelta(minutes=5),
        last_inbound_instance_id="instance-1",
        now=now,
    )

    assert result.whatsapp_status == "ok"
    assert result.telegram_status == "ok"
    assert result.status == "ok"
    assert result.drift_issues == []


def test_emit_integration_drift_signals_detect_and_clear(monkeypatch):
    with console_router._INTEGRATION_DRIFT_LOCK:
        console_router._INTEGRATION_DRIFT_STATE.clear()

    events = []
    alerts = []
    db = SimpleNamespace(commit=lambda: events.append("commit"))
    context = SimpleNamespace(
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        client=SimpleNamespace(id=uuid4()),
    )

    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: events.append(kwargs["event_type"]))
    monkeypatch.setattr(console_router, "alert_warning", lambda *args, **kwargs: alerts.append("alert"))

    branch_id = uuid4()
    detected = ConsoleBranchIntegrationStatus(
        branch_id=branch_id,
        branch_slug="branch-a",
        branch_name="Branch A",
        is_active=True,
        instance_id="instance-1",
        telegram_chat_id="12345",
        webhook_url="https://api.truffles.kz/webhook/demo?webhook_secret=abc",
        webhook_url_valid=True,
        whatsapp_status="instance_id_mismatch",
        telegram_status="ok",
        last_inbound_at=datetime.now(timezone.utc).isoformat(),
        last_inbound_instance_id="other-instance",
        drift_issues=["instance_id_mismatch"],
        status="error",
    )
    cleared = ConsoleBranchIntegrationStatus(
        branch_id=branch_id,
        branch_slug="branch-a",
        branch_name="Branch A",
        is_active=True,
        instance_id="instance-1",
        telegram_chat_id="12345",
        webhook_url="https://api.truffles.kz/webhook/demo?webhook_secret=abc",
        webhook_url_valid=True,
        whatsapp_status="ok",
        telegram_status="ok",
        last_inbound_at=datetime.now(timezone.utc).isoformat(),
        last_inbound_instance_id="instance-1",
        drift_issues=[],
        status="ok",
    )

    console_router._emit_integration_drift_signals(db, context=context, statuses=[detected])
    console_router._emit_integration_drift_signals(db, context=context, statuses=[detected])
    console_router._emit_integration_drift_signals(db, context=context, statuses=[cleared])

    assert events.count("integration_drift_detected") == 1
    assert events.count("integration_drift_cleared") == 1
    assert events.count("commit") == 2
    assert len(alerts) == 1
