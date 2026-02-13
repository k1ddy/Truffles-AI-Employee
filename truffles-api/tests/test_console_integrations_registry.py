from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleBranchIntegrationStatus, ConsoleIntegrationBranchActionRequest
from app.services.console_errors import ConsoleAPIError


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


class _QueryMock:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


def test_build_branch_integration_status_missing_instance():
    branch = _make_branch(instance_id=None)
    client_id = uuid4()
    result = console_router._build_branch_integration_status(
        client_id=client_id,
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
    client_id = uuid4()
    result = console_router._build_branch_integration_status(
        client_id=client_id,
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
    client_id = uuid4()
    now = datetime.now(timezone.utc)
    result = console_router._build_branch_integration_status(
        client_id=client_id,
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
    client_id = uuid4()
    now = datetime.now(timezone.utc)
    result = console_router._build_branch_integration_status(
        client_id=client_id,
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


def test_build_branch_integration_status_exposes_provider_binding_lifecycle():
    branch = _make_branch(instance_id="instance-1")
    client_id = uuid4()
    now = datetime.now(timezone.utc)
    result = console_router._build_branch_integration_status(
        client_id=client_id,
        client_slug="demo",
        branch=branch,
        has_telegram_bot_token=True,
        stale_after_minutes=30,
        last_inbound_at=now - timedelta(minutes=1),
        last_inbound_instance_id="instance-1",
        now=now,
        provider_binding=console_router._ProviderBindingLifecycle(
            provider="chatflow",
            instance_id="instance-1",
            webhook_status="configured",
            paid_until="2030-01-01",
            notes="manual renewal",
            payment_status="confirmed",
            payment_confirmed_at=now.isoformat(),
            expiry_status="ok",
            days_until_expiry=120,
        ),
    )

    assert result.provider_binding_provider == "chatflow"
    assert result.provider_binding_instance_id == "instance-1"
    assert result.provider_binding_webhook_status == "configured"
    assert result.provider_binding_paid_until == "2030-01-01"
    assert result.provider_binding_notes == "manual renewal"
    assert result.provider_binding_payment_status == "confirmed"
    assert result.provider_binding_payment_confirmed_at == now.isoformat()
    assert result.provider_binding_expiry_status == "ok"
    assert result.provider_binding_days_until_expiry == 120


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
        client_id=context.client.id,
        client_slug="demo",
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
        client_id=context.client.id,
        client_slug="demo",
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


@pytest.mark.asyncio
async def test_list_integrations_requires_platform_admin(monkeypatch):
    request = SimpleNamespace(query_params={})
    db = Mock()
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="owner",
            accessible_clients=[],
        ),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_integrations(request=request, db=db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_list_integrations_is_read_only_without_drift_side_effects(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    db = Mock()

    context = SimpleNamespace(
        role="platform_admin",
        accessible_clients=[SimpleNamespace(id=client_id, name="demo", status="active")],
    )

    branch_rows = [
        SimpleNamespace(
            id=branch_id,
            client_id=client_id,
            slug="branch-a",
            name="Branch A",
            is_active=True,
            instance_id="instance-1",
            telegram_chat_id="12345",
            webhook_secret="secret",
        )
    ]

    def _query_side_effect(*entities):
        if len(entities) == 1 and entities[0] is console_router.Branch:
            return _QueryMock(branch_rows)
        if len(entities) == 2:
            return _QueryMock([(client_id, "token-a")])
        raise AssertionError(f"unexpected query entities: {entities}")

    db.query.side_effect = _query_side_effect
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_load_latest_branch_inbound_observations_for_clients",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        console_router,
        "_build_provider_binding_lifecycle_map",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        console_router,
        "_build_branch_integration_status",
        lambda **kwargs: ConsoleBranchIntegrationStatus(
            client_id=kwargs["client_id"],
            client_slug=kwargs["client_slug"],
            branch_id=kwargs["branch"].id,
            branch_slug=kwargs["branch"].slug,
            branch_name=kwargs["branch"].name,
            is_active=True,
            instance_id="instance-1",
            telegram_chat_id="12345",
            webhook_url="https://api.truffles.kz/webhook/demo?webhook_secret=abc",
            webhook_url_valid=True,
            whatsapp_status="ok",
            telegram_status="ok",
            last_inbound_at=None,
            last_inbound_instance_id=None,
            integration_state="ok",
            integration_reason=None,
            integration_checked_at=None,
            integration_degraded_at=None,
            integration_recovered_at=None,
            drift_issues=[],
            status="ok",
        ),
    )
    monkeypatch.setattr(
        console_router,
        "_emit_integration_drift_signals",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("read path must not emit drift signals")),
    )

    response = await console_router.list_integrations(
        request=request,
        stale_after_minutes=60,
        db=db,
    )

    assert response.stale_after_minutes == 60
    assert len(response.items) == 1
    assert response.items[0].client_id == client_id
    assert response.items[0].client_slug == "demo"


@pytest.mark.asyncio
async def test_run_integration_reconcile_for_branch_dry_run(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id, is_active=True)
    db = Mock()
    db.query.return_value = _QueryMock([branch])

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="platform_admin",
            client=SimpleNamespace(id=client_id),
            accessible_clients=[SimpleNamespace(id=client_id, status="active")],
        ),
    )
    monkeypatch.setattr(
        console_router,
        "run_integration_watchdog_scoped",
        lambda *_args, **_kwargs: {"mode": "dry_run", "checked": 1, "degraded": 0, "recovered": 0, "remediated": 0},
    )

    response = await console_router.run_integration_reconcile_for_branch(
        branch_id=branch_id,
        body=ConsoleIntegrationBranchActionRequest(mode="dry_run"),
        request=request,
        db=db,
    )

    assert response.branch_id == branch_id
    assert response.mode == "dry_run"
    assert response.result["checked"] == 1
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_integration_reconcile_for_branch_execute_requires_confirmation(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id, is_active=True)
    db = Mock()
    db.query.return_value = _QueryMock([branch])

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="platform_admin",
            client=SimpleNamespace(id=client_id),
            accessible_clients=[SimpleNamespace(id=client_id, status="active")],
            agent=SimpleNamespace(id=uuid4()),
            effective_branch_id=None,
        ),
    )
    monkeypatch.setattr(
        console_router,
        "require_confirmation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation required")
        ),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_integration_reconcile_for_branch(
            branch_id=branch_id,
            body=ConsoleIntegrationBranchActionRequest(mode="execute"),
            request=request,
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_run_integration_reconcile_for_branch_execute_marks_confirmation(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    actor_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id, is_active=True)
    db = Mock()
    db.query.return_value = _QueryMock([branch])

    context = SimpleNamespace(
        role="platform_admin",
        client=SimpleNamespace(id=client_id),
        accessible_clients=[SimpleNamespace(id=client_id, status="active")],
        agent=SimpleNamespace(id=actor_id),
        effective_branch_id=None,
    )
    confirmation = SimpleNamespace(id=uuid4())
    marked: list[str] = []

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(console_router, "require_confirmation", lambda *_args, **_kwargs: confirmation)
    monkeypatch.setattr(
        console_router,
        "run_integration_watchdog_scoped",
        lambda *_args, **_kwargs: {"mode": "execute", "checked": 1, "degraded": 1, "recovered": 0, "remediated": 0},
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "mark_confirmation_used",
        lambda *_args, **_kwargs: marked.append("used"),
    )

    response = await console_router.run_integration_reconcile_for_branch(
        branch_id=branch_id,
        body=ConsoleIntegrationBranchActionRequest(mode="execute", confirmation_id=uuid4()),
        request=request,
        db=db,
    )

    assert response.branch_id == branch_id
    assert response.mode == "execute"
    assert response.result["degraded"] == 1
    assert marked == ["used"]
    db.commit.assert_called_once()
