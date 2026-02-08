from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services import integration_guardrails_service as guardrails


def _branch(*, state: str = "ok", reason: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        slug="main",
        is_active=True,
        instance_id="inst-1",
        webhook_secret="secret",
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        integration_state=state,
        integration_reason=reason,
        integration_checked_at=None,
        integration_degraded_at=None,
        integration_recovered_at=None,
    )


def test_degrade_and_recover_branch_transition(monkeypatch):
    events: list[str] = []
    error_alerts: list[dict] = []
    warning_alerts: list[dict] = []

    monkeypatch.setattr(
        guardrails,
        "record_audit_event",
        lambda *_args, **kwargs: events.append(kwargs.get("event_type", "")),
    )
    monkeypatch.setattr(
        guardrails,
        "alert_error",
        lambda _message, context=None: error_alerts.append(context or {}),
    )
    monkeypatch.setattr(
        guardrails,
        "alert_warning",
        lambda _message, context=None: warning_alerts.append(context or {}),
    )

    branch = _branch()
    db = Mock()

    changed = guardrails.degrade_branch_integration(
        db,
        branch=branch,
        reason=guardrails.REASON_INVALID_WEBHOOK_SECRET,
        source="unit_test",
    )

    assert changed is True
    assert branch.integration_state == "degraded"
    assert branch.integration_reason == guardrails.REASON_INVALID_WEBHOOK_SECRET
    assert branch.integration_degraded_at is not None
    assert "integration_degraded" in events
    assert len(error_alerts) == 1

    changed = guardrails.degrade_branch_integration(
        db,
        branch=branch,
        reason=guardrails.REASON_INVALID_WEBHOOK_SECRET,
        source="unit_test",
    )

    assert changed is False

    changed = guardrails.recover_branch_integration(
        db,
        branch=branch,
        source="unit_test",
    )

    assert changed is True
    assert branch.integration_state == "ok"
    assert branch.integration_reason is None
    assert branch.integration_recovered_at is not None
    assert "integration_recovered" in events
    assert len(warning_alerts) == 1


def test_report_integration_incident_without_branch(monkeypatch):
    events: list[str] = []
    error_alerts: list[dict] = []

    monkeypatch.setattr(
        guardrails,
        "record_audit_event",
        lambda *_args, **kwargs: events.append(kwargs.get("event_type", "")),
    )
    monkeypatch.setattr(
        guardrails,
        "alert_error",
        lambda _message, context=None: error_alerts.append(context or {}),
    )

    client = SimpleNamespace(id=uuid4(), name="demo")
    db = Mock()

    changed = guardrails.report_integration_incident(
        db,
        client=client,
        reason=guardrails.REASON_UNKNOWN_INSTANCE_ID,
        source="unit_test",
        context={"instance_id": "unknown"},
    )

    assert changed is False
    assert events == ["integration_incident"]
    assert len(error_alerts) == 1


def test_run_watchdog_applies_degrade_recover_and_commit(monkeypatch):
    monkeypatch.setattr(guardrails, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(guardrails, "alert_error", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(guardrails, "alert_warning", lambda *_args, **_kwargs: True)

    branch_degrade = _branch(state="ok")
    branch_recover = _branch(state="degraded", reason=guardrails.REASON_INSTANCE_ID_MISMATCH)

    branch_query = Mock()
    branch_query.filter.return_value.order_by.return_value.all.return_value = [branch_degrade, branch_recover]

    db = Mock()
    db.query.return_value = branch_query

    def _fake_evaluate(*_args, branch, **_kwargs):
        if branch.id == branch_degrade.id:
            return guardrails.REASON_INSTANCE_ID_MISMATCH, {"check": "mismatch"}, False
        return None, {"check": "ok"}, True

    monkeypatch.setattr(guardrails, "_evaluate_branch_watchdog_reason", _fake_evaluate)

    result = guardrails.run_integration_watchdog(db)

    assert result["checked"] == 2
    assert result["degraded"] == 1
    assert result["recovered"] == 1
    assert result["remediated"] == 1
    db.commit.assert_called_once()
