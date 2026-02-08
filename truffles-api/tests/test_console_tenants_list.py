from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from datetime import datetime, timezone

from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


def test_parse_uuid_param_accepts_valid() -> None:
    value = str(uuid4())

    parsed = console_router._parse_uuid_param("company_id", value)

    assert parsed == UUID(value)


def test_parse_uuid_param_rejects_invalid() -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._parse_uuid_param("company_id", "not-a-uuid")

    assert exc_info.value.code == "INVALID_PARAM"


def test_parse_tenant_lifecycle_param_defaults_to_active() -> None:
    assert console_router._parse_tenant_lifecycle_param(None) == "active"


@pytest.mark.parametrize("value", ["active", "archived", "all"])
def test_parse_tenant_lifecycle_param_accepts_allowed_values(value: str) -> None:
    assert console_router._parse_tenant_lifecycle_param(value) == value


def test_parse_tenant_lifecycle_param_rejects_invalid() -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._parse_tenant_lifecycle_param("inactive")

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("all", None),
        ("active", "active"),
        ("onboarding", "onboarding"),
    ],
)
def test_parse_fleet_lifecycle_param(value: str | None, expected: str | None) -> None:
    assert console_router._parse_fleet_lifecycle_param(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("all", None),
        ("pending", "pending"),
        ("confirmed", "confirmed"),
    ],
)
def test_parse_fleet_payment_param(value: str | None, expected: str | None) -> None:
    assert console_router._parse_fleet_payment_param(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("all", None),
        ("ok", "ok"),
        ("degraded", "degraded"),
    ],
)
def test_parse_fleet_service_param(value: str | None, expected: str | None) -> None:
    assert console_router._parse_fleet_service_param(value) == expected


def test_parse_fleet_params_reject_invalid_values() -> None:
    with pytest.raises(ConsoleAPIError):
        console_router._parse_fleet_lifecycle_param("invalid")
    with pytest.raises(ConsoleAPIError):
        console_router._parse_fleet_payment_param("paid")
    with pytest.raises(ConsoleAPIError):
        console_router._parse_fleet_service_param("bad")


def _build_list_query_mock() -> Mock:
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    return query


@pytest.mark.asyncio
async def test_list_clients_defaults_to_active_lifecycle(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_clients(
        request=request,
        db=db,
    )

    assert captured["require_selection"] is False
    assert captured["include_inactive_tenants"] is False
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "clients.status = :status_1"


@pytest.mark.asyncio
async def test_list_clients_archived_lifecycle_enables_inactive_scope(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={"lifecycle": "archived"})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_clients(
        request=request,
        lifecycle="archived",
        db=db,
    )

    assert captured["include_inactive_tenants"] is True
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "clients.status != :status_1"


@pytest.mark.asyncio
async def test_list_clients_include_fleet_enriches_items_and_summary(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    client_id = uuid4()
    company_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        name="alpha",
        status="active",
        company_id=company_id,
        created_at=now,
    )
    company = SimpleNamespace(id=company_id, name="Acme Group")
    client_query = _build_list_query_mock()
    client_query.all.return_value = [client]
    company_query = _build_list_query_mock()
    company_query.all.return_value = [company]

    db = Mock()

    def _query_side_effect(model):
        if model is console_router.Client:
            return client_query
        if model is console_router.Company:
            return company_query
        raise AssertionError(f"Unexpected model: {model}")

    db.query.side_effect = _query_side_effect
    request = SimpleNamespace(query_params={"include_fleet": "true", "include_summary": "true"})

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(role="platform_admin"),
    )
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: {
            client_id: console_router._FleetClientDetails(
                lifecycle_state="active",
                payment_status="confirmed",
                commercial_state="payment_confirmed",
                service_state="ok",
                owner_name="Owner",
                next_action="monitor_sla_and_quality",
                total_branches=2,
                active_branches=2,
                degraded_branches=0,
                go_live_ready_branches=2,
            )
        },
    )

    response = await console_router.list_clients(
        request=request,
        include_fleet="true",
        include_summary="true",
        db=db,
    )

    assert len(response.items) == 1
    assert response.items[0].status == "active"
    assert response.items[0].lifecycle_state == "active"
    assert response.items[0].payment_status == "confirmed"
    assert response.items[0].commercial_state == "payment_confirmed"
    assert response.items[0].service_state == "ok"
    assert response.summary is not None
    assert response.summary.total_clients == 1
    assert response.summary.active_clients == 1
    assert response.summary.payment_confirmed_clients == 1


@pytest.mark.asyncio
async def test_list_clients_filters_by_fleet_payment(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    company_id = uuid4()
    client_a = SimpleNamespace(
        id=uuid4(),
        name="alpha",
        status="active",
        company_id=company_id,
        created_at=now,
    )
    client_b = SimpleNamespace(
        id=uuid4(),
        name="beta",
        status="active",
        company_id=company_id,
        created_at=now,
    )
    client_query = _build_list_query_mock()
    client_query.all.return_value = [client_a, client_b]
    company_query = _build_list_query_mock()
    company_query.all.return_value = [SimpleNamespace(id=company_id, name="Acme Group")]

    db = Mock()

    def _query_side_effect(model):
        if model is console_router.Client:
            return client_query
        if model is console_router.Company:
            return company_query
        raise AssertionError(f"Unexpected model: {model}")

    db.query.side_effect = _query_side_effect
    request = SimpleNamespace(query_params={"payment_status": "confirmed"})

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(role="platform_admin"),
    )

    def _details_map(_db, *, clients, **_kwargs):
        base_map = {
            client_a.id: console_router._FleetClientDetails(
                lifecycle_state="active",
                payment_status="confirmed",
                commercial_state="payment_confirmed",
                service_state="ok",
                owner_name=None,
                next_action="monitor_sla_and_quality",
                total_branches=1,
                active_branches=1,
                degraded_branches=0,
                go_live_ready_branches=1,
            ),
            client_b.id: console_router._FleetClientDetails(
                lifecycle_state="go_live_ready",
                payment_status="pending",
                commercial_state="payment_pending",
                service_state="attention",
                owner_name=None,
                next_action="confirm_payment_and_approve_go_live",
                total_branches=1,
                active_branches=1,
                degraded_branches=0,
                go_live_ready_branches=1,
            ),
        }
        return {client.id: base_map[client.id] for client in clients}

    monkeypatch.setattr(console_router, "_build_fleet_client_details_map", _details_map)

    response = await console_router.list_clients(
        request=request,
        payment_status="confirmed",
        db=db,
    )

    assert len(response.items) == 1
    assert response.items[0].id == client_a.id
    assert response.items[0].payment_status == "confirmed"


@pytest.mark.asyncio
async def test_list_branches_defaults_to_active_lifecycle(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        db=db,
    )

    assert captured["include_inactive_tenants"] is False
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "branches.is_active IS true"


@pytest.mark.asyncio
async def test_list_branches_archived_lifecycle_filters_inactive(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={"lifecycle": "archived"})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        lifecycle="archived",
        db=db,
    )

    assert captured["include_inactive_tenants"] is True
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "branches.is_active IS false"
