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


class _BranchQueryMock(_QueryMock):
    def filter(self, *args, **_kwargs):
        filtered = list(self._rows)
        for expr in args:
            expr_text = str(expr)
            try:
                value = expr.right.value
            except Exception:
                value = None
            if "branches.client_id IN" in expr_text and value is not None:
                allowed = set(value)
                filtered = [row for row in filtered if row.client_id in allowed]
            if "branches.id =" in expr_text and value is not None:
                filtered = [row for row in filtered if row.id == value]
        self._rows = filtered
        return self


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
            owner="platform-admin",
            next_renewal_at="2030-01-01",
            last_rebind_at="2026-02-01",
            rebind_required=False,
            alert_state="warn",
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
    assert result.provider_binding_owner == "platform-admin"
    assert result.provider_binding_next_renewal_at == "2030-01-01"
    assert result.provider_binding_last_rebind_at == "2026-02-01"
    assert result.provider_binding_rebind_required is False
    assert result.provider_binding_alert_state == "warn"
    assert result.provider_binding_notes == "manual renewal"
    assert result.provider_binding_payment_status == "confirmed"
    assert result.provider_binding_payment_confirmed_at == now.isoformat()
    assert result.provider_binding_expiry_status == "ok"
    assert result.provider_binding_days_until_expiry == 120


def test_build_branch_integration_status_rebind_required_forces_error():
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
            webhook_status="rebind_required",
            paid_until="2030-01-01",
            owner="platform-admin",
            next_renewal_at="2030-01-01",
            rebind_required=True,
            alert_state="critical",
        ),
    )

    assert result.status == "error"
    assert result.provider_binding_rebind_required is True
    assert "provider_binding_rebind_required" in result.drift_issues


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
    assert response.action == "integration_reconcile"
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
    assert response.action == "integration_reconcile"
    assert response.mode == "execute"
    assert response.result["degraded"] == 1
    assert marked == ["used"]
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_list_integrations_builds_provider_ops_queue(monkeypatch):
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
            whatsapp_status="instance_id_mismatch",
            telegram_status="ok",
            provider_binding_rebind_required=True,
            provider_binding_alert_state="critical",
            provider_binding_expiry_status="expired",
            drift_issues=["instance_id_mismatch", "provider_binding_rebind_required", "provider_binding_expired"],
            status="error",
        ),
    )

    response = await console_router.list_integrations(
        request=request,
        stale_after_minutes=60,
        db=db,
    )

    assert len(response.provider_ops_queue) == 1
    queue_item = response.provider_ops_queue[0]
    assert queue_item.branch_id == branch_id
    assert queue_item.priority == "p0"
    assert queue_item.recommended_action == "provider_complete_rebind"
    assert "provider_binding_rebind_required" in queue_item.reasons


@pytest.mark.asyncio
async def test_list_integrations_rejects_unavailable_company_scope(monkeypatch):
    request = SimpleNamespace(query_params={"company_id": str(uuid4())})
    db = Mock()

    context = SimpleNamespace(
        role="platform_admin",
        accessible_clients=[SimpleNamespace(id=uuid4(), name="demo", status="active", company_id=uuid4())],
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_integrations(
            request=request,
            stale_after_minutes=60,
            company_id=str(request.query_params["company_id"]),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_list_integrations_rejects_client_company_mismatch(monkeypatch):
    request = SimpleNamespace(query_params={})
    company_a = uuid4()
    company_b = uuid4()
    client_a = uuid4()
    client_b = uuid4()
    db = Mock()

    context = SimpleNamespace(
        role="platform_admin",
        client=None,
        accessible_clients=[
            SimpleNamespace(id=client_a, name="client-a", status="active", company_id=company_a),
            SimpleNamespace(id=client_b, name="client-b", status="active", company_id=company_b),
        ],
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_integrations(
            request=request,
            stale_after_minutes=60,
            company_id=str(company_a),
            client_id=str(client_b),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"
    assert exc_info.value.message == "client_id does not belong to company_id"


@pytest.mark.asyncio
async def test_list_integrations_rejects_branch_client_mismatch(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_a = uuid4()
    client_b = uuid4()
    branch_id = uuid4()
    db = Mock()
    branch = SimpleNamespace(id=branch_id, client_id=client_a)
    db.query.return_value = _QueryMock([branch])

    context = SimpleNamespace(
        role="platform_admin",
        client=None,
        accessible_clients=[
            SimpleNamespace(id=client_a, name="client-a", status="active", company_id=uuid4()),
            SimpleNamespace(id=client_b, name="client-b", status="active", company_id=uuid4()),
        ],
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_integrations(
            request=request,
            stale_after_minutes=60,
            client_id=str(client_b),
            branch_id=str(branch_id),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"
    assert exc_info.value.message == "branch_id does not belong to client_id"


@pytest.mark.asyncio
async def test_list_integrations_applies_scope_filters(monkeypatch):
    request = SimpleNamespace(query_params={})
    company_a = uuid4()
    company_b = uuid4()
    client_a = uuid4()
    client_b = uuid4()
    branch_a = uuid4()
    branch_b = uuid4()
    db = Mock()
    loader_client_ids: list[list] = []

    context = SimpleNamespace(
        role="platform_admin",
        client=None,
        accessible_clients=[
            SimpleNamespace(id=client_a, name="client-a", status="active", company_id=company_a),
            SimpleNamespace(id=client_b, name="client-b", status="active", company_id=company_b),
        ],
    )
    branch_rows = [
        SimpleNamespace(
            id=branch_a,
            client_id=client_a,
            slug="branch-a",
            name="Branch A",
            is_active=True,
            instance_id="instance-a",
            telegram_chat_id="111",
            webhook_secret="secret-a",
        ),
        SimpleNamespace(
            id=branch_b,
            client_id=client_b,
            slug="branch-b",
            name="Branch B",
            is_active=True,
            instance_id="instance-b",
            telegram_chat_id="222",
            webhook_secret="secret-b",
        ),
    ]
    branch_query = _BranchQueryMock(branch_rows)

    def _query_side_effect(*entities):
        if len(entities) == 1 and entities[0] is console_router.Branch:
            return branch_query
        if len(entities) == 2:
            return _QueryMock([(client_a, "token-a"), (client_b, "token-b")])
        raise AssertionError(f"unexpected query entities: {entities}")

    db.query.side_effect = _query_side_effect
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    def _capture_inbound_loader(_db, *, client_ids):
        loader_client_ids.append(list(client_ids))
        return {}

    monkeypatch.setattr(console_router, "_load_latest_branch_inbound_observations_for_clients", _capture_inbound_loader)
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
            instance_id=kwargs["branch"].instance_id,
            telegram_chat_id=kwargs["branch"].telegram_chat_id,
            webhook_url="https://api.truffles.kz/webhook/demo?webhook_secret=abc",
            webhook_url_valid=True,
            whatsapp_status="ok",
            telegram_status="ok",
            drift_issues=[],
            status="ok",
        ),
    )

    response = await console_router.list_integrations(
        request=request,
        stale_after_minutes=60,
        company_id=str(company_a),
        client_id=str(client_a),
        branch_id=str(branch_a),
        db=db,
    )

    assert len(response.items) == 1
    assert response.items[0].client_id == client_a
    assert response.items[0].branch_id == branch_a
    assert loader_client_ids == [[client_a]]


@pytest.mark.asyncio
async def test_run_provider_ops_action_dry_run(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id, is_active=True, instance_id="instance-1")
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
        "_build_provider_binding_lifecycle_map",
        lambda *_args, **_kwargs: {
            branch_id: console_router._ProviderBindingLifecycle(
                provider="chatflow",
                instance_id="instance-1",
                webhook_status="pending",
                owner="platform-admin",
                next_renewal_at="2030-01-01",
            )
        },
    )

    response = await console_router.run_integration_reconcile_for_branch(
        branch_id=branch_id,
        body=ConsoleIntegrationBranchActionRequest(action="provider_start_rebind", mode="dry_run"),
        request=request,
        db=db,
    )

    assert response.branch_id == branch_id
    assert response.action == "provider_start_rebind"
    assert response.mode == "dry_run"
    assert response.result["dry_run"] is True
    assert response.result["binding_patch"]["webhook_status"] == "rebind_required"
    assert response.result["binding_patch"]["rebind_required"] is True


@pytest.mark.asyncio
async def test_run_provider_ops_action_execute_requires_confirmation(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id, is_active=True, instance_id="instance-1")
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
        "_build_provider_binding_lifecycle_map",
        lambda *_args, **_kwargs: {branch_id: console_router._ProviderBindingLifecycle()},
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
            body=ConsoleIntegrationBranchActionRequest(action="provider_send_reminder", mode="execute"),
            request=request,
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_run_provider_ops_reminder_execute_marks_confirmation(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    actor_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id, is_active=True, instance_id="instance-1")
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
    require_calls: list[dict] = []

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_provider_binding_lifecycle_map",
        lambda *_args, **_kwargs: {branch_id: console_router._ProviderBindingLifecycle()},
    )

    def _fake_require_confirmation(*_args, **kwargs):
        require_calls.append(kwargs)
        return confirmation

    monkeypatch.setattr(console_router, "require_confirmation", _fake_require_confirmation)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "mark_confirmation_used",
        lambda *_args, **_kwargs: marked.append("used"),
    )

    response = await console_router.run_integration_reconcile_for_branch(
        branch_id=branch_id,
        body=ConsoleIntegrationBranchActionRequest(
            action="provider_send_reminder",
            mode="execute",
            confirmation_id=uuid4(),
            notes="manual provider reminder",
        ),
        request=request,
        db=db,
    )

    assert response.branch_id == branch_id
    assert response.action == "provider_send_reminder"
    assert response.mode == "execute"
    assert require_calls and require_calls[0]["action"] == "provider_ops_execute"
    assert marked == ["used"]
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_provider_start_rebind_execute_handles_legacy_contract_extras(monkeypatch):
    request = SimpleNamespace(query_params={})
    client_id = uuid4()
    branch_id = uuid4()
    actor_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id, is_active=True, instance_id="instance-1")
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
    require_calls: list[dict] = []
    contract_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        scope="branch",
        status="active",
        schema_version="v1",
        payment_status="pending",
        payment_confirmed_at=None,
        payment_confirmed_by=None,
        payload_json={
            "domain_slug": "beauty",
            "purchased": {},
            "provider_binding": {"whatsapp": {"provider": "chatflow", "instance_id": "instance-1"}},
            "legacy_extra": {"source": "old-migration"},
        },
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_provider_binding_lifecycle_map",
        lambda *_args, **_kwargs: {branch_id: console_router._ProviderBindingLifecycle()},
    )

    def _fake_require_confirmation(*_args, **kwargs):
        require_calls.append(kwargs)
        return confirmation

    monkeypatch.setattr(console_router, "require_confirmation", _fake_require_confirmation)
    monkeypatch.setattr(
        console_router,
        "_get_latest_onboarding_contract",
        lambda *_args, **kwargs: contract_record
        if kwargs.get("scope") == "branch" and kwargs.get("branch_id") == branch_id
        else None,
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "mark_confirmation_used",
        lambda *_args, **_kwargs: marked.append("used"),
    )

    response = await console_router.run_integration_reconcile_for_branch(
        branch_id=branch_id,
        body=ConsoleIntegrationBranchActionRequest(
            action="provider_start_rebind",
            mode="execute",
            confirmation_id=uuid4(),
            notes="manual start rebind",
        ),
        request=request,
        db=db,
    )

    assert response.branch_id == branch_id
    assert response.action == "provider_start_rebind"
    assert response.mode == "execute"
    assert response.result["binding_after"]["webhook_status"] == "rebind_required"
    assert response.result["binding_after"]["rebind_required"] is True
    assert response.result["payment_status_after"] == "pending"
    assert require_calls and require_calls[0]["action"] == "provider_ops_execute"
    assert marked == ["used"]
    assert "legacy_extra" not in contract_record.payload_json
    db.commit.assert_called_once()
