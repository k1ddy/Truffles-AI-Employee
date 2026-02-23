from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import ProgrammingError
from starlette.requests import Request

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


def test_select_reference_active_branches_filters_to_reference_subset() -> None:
    selected_id = uuid4()
    ignored_id = uuid4()
    inactive_id = uuid4()
    branches = [
        SimpleNamespace(id=selected_id, is_active=True),
        SimpleNamespace(id=ignored_id, is_active=True),
        SimpleNamespace(id=inactive_id, is_active=False),
    ]

    scoped = console_router._select_reference_active_branches(
        branches,
        reference_branch_ids=(selected_id,),
    )

    assert [branch.id for branch in scoped] == [selected_id]


def test_select_reference_active_branches_falls_back_to_all_active() -> None:
    first = uuid4()
    second = uuid4()
    branches = [
        SimpleNamespace(id=first, is_active=True),
        SimpleNamespace(id=second, is_active=True),
    ]

    scoped = console_router._select_reference_active_branches(
        branches,
        reference_branch_ids=(uuid4(),),
    )

    assert [branch.id for branch in scoped] == [first, second]


def _build_list_query_mock() -> Mock:
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    return query


def _build_request(query: str = "") -> Request:
    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": query.encode("utf-8"),
            "headers": [],
        },
        receive=_receive,
    )


def test_request_with_query_params_rewrites_query_string() -> None:
    request = _build_request("foo=bar")

    derived = console_router._request_with_query_params(
        request,
        {"limit": 10, "cursor": None, "lifecycle": "active"},
    )

    assert dict(derived.query_params) == {"limit": "10", "lifecycle": "active"}


@pytest.mark.asyncio
async def test_get_tenants_portfolio_composes_clients_and_attention(monkeypatch) -> None:
    clients_response = console_router.ConsoleClientListResponse(items=[], cursor=None, has_more=False, summary=None)
    attention_response = console_router.ConsoleFleetAttentionResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        stale_after_minutes=120,
        summary=console_router.ConsoleFleetAttentionSummary(
            active_clients_total=0,
            clients_with_attention=0,
            high_risk_clients=0,
            medium_risk_clients=0,
            low_risk_clients=0,
            stale_branches_total=0,
            integration_error_branches_total=0,
            integration_warn_branches_total=0,
            outbox_failed_24h_total=0,
            pending_handovers_total=0,
        ),
        items=[],
    )
    captured: dict[str, dict[str, object]] = {}
    latency_calls: list[tuple[str, float | None]] = []

    async def _fake_list_clients(**kwargs):
        captured["clients"] = kwargs
        return clients_response

    async def _fake_list_fleet_attention(**kwargs):
        captured["attention"] = kwargs
        return attention_response

    monkeypatch.setattr(console_router, "list_clients", _fake_list_clients)
    monkeypatch.setattr(console_router, "list_fleet_attention", _fake_list_fleet_attention)
    monkeypatch.setattr(
        console_router,
        "record_tenants_endpoint_latency",
        lambda endpoint, elapsed_ms: latency_calls.append((endpoint, elapsed_ms)),
    )

    response = await console_router.get_tenants_portfolio(
        request=_build_request(),
        limit=5,
        attention_limit=3,
        lifecycle="active",
        db=Mock(),
    )

    assert response.clients == clients_response
    assert response.fleet_attention == attention_response
    assert captured["clients"]["limit"] == 5
    assert captured["clients"]["include_fleet"] == "true"
    assert captured["clients"]["include_summary"] == "true"
    assert captured["attention"]["limit"] == 3
    assert latency_calls
    assert latency_calls[0][0] == "portfolio"
    assert latency_calls[0][1] is not None
    assert latency_calls[0][1] >= 0


@pytest.mark.asyncio
async def test_get_tenants_company_cockpit_uses_company_scope_when_client_not_selected(monkeypatch) -> None:
    company_id = uuid4()
    first_client_id = uuid4()
    clients_response = console_router.ConsoleClientListResponse(
        items=[
            console_router.ConsoleClient(
                id=first_client_id,
                slug="alpha",
                status="active",
                company_id=company_id,
            )
        ],
        cursor=None,
        has_more=False,
        summary=None,
    )
    branches_response = console_router.ConsoleBranchListResponse(
        items=[
            console_router.ConsoleBranch(
                id=uuid4(),
                slug="branch-1",
                name="Branch 1",
                is_active=True,
            )
        ],
        cursor=None,
        has_more=False,
    )
    captured: dict[str, dict[str, object]] = {}
    latency_calls: list[tuple[str, float | None]] = []

    async def _fake_list_clients(**kwargs):
        captured["clients"] = kwargs
        return clients_response

    async def _fake_list_branches(**kwargs):
        captured["branches"] = kwargs
        return branches_response

    monkeypatch.setattr(console_router, "list_clients", _fake_list_clients)
    monkeypatch.setattr(console_router, "list_branches", _fake_list_branches)
    monkeypatch.setattr(
        console_router,
        "record_tenants_endpoint_latency",
        lambda endpoint, elapsed_ms: latency_calls.append((endpoint, elapsed_ms)),
    )

    response = await console_router.get_tenants_company_cockpit(
        request=_build_request(),
        company_id=str(company_id),
        lifecycle="active",
        db=Mock(),
    )

    assert response.company_id == company_id
    assert response.selected_client_id is None
    assert response.clients == clients_response
    assert response.branches == branches_response
    assert captured["clients"]["company_id"] == str(company_id)
    assert captured["branches"]["company_id"] == str(company_id)
    assert captured["branches"]["client_id"] is None
    assert latency_calls
    assert latency_calls[0][0] == "company_cockpit"
    assert latency_calls[0][1] is not None
    assert latency_calls[0][1] >= 0


@pytest.mark.asyncio
async def test_get_tenants_company_cockpit_uses_selected_client_scope_when_requested(monkeypatch) -> None:
    company_id = uuid4()
    selected_client_id = uuid4()
    clients_response = console_router.ConsoleClientListResponse(
        items=[
            console_router.ConsoleClient(
                id=selected_client_id,
                slug="alpha",
                status="active",
                company_id=company_id,
            )
        ],
        cursor=None,
        has_more=False,
        summary=None,
    )
    branches_response = console_router.ConsoleBranchListResponse(items=[], cursor=None, has_more=False)
    captured: dict[str, dict[str, object]] = {}

    async def _fake_list_clients(**kwargs):
        captured["clients"] = kwargs
        return clients_response

    async def _fake_list_branches(**kwargs):
        captured["branches"] = kwargs
        return branches_response

    monkeypatch.setattr(console_router, "list_clients", _fake_list_clients)
    monkeypatch.setattr(console_router, "list_branches", _fake_list_branches)

    response = await console_router.get_tenants_company_cockpit(
        request=_build_request(),
        company_id=str(company_id),
        client_id=str(selected_client_id),
        lifecycle="active",
        db=Mock(),
    )

    assert response.selected_client_id == selected_client_id
    assert captured["branches"]["company_id"] == str(company_id)
    assert captured["branches"]["client_id"] == str(selected_client_id)

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
    monkeypatch.setattr(
        console_router,
        "_build_onboarding_throughput_metrics",
        lambda *_args, **_kwargs: console_router.ConsoleOnboardingThroughputMetrics(
            window_hours=720,
            approved_branches_total=1,
            first_pass_approved_branches=1,
            time_to_go_live_median_hours=12.0,
            blocker_age_p95_hours=4.0,
            first_pass_go_live_rate_pct=100.0,
            incident_reopen_rate_24h_pct=0.0,
        ),
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
        return SimpleNamespace(
            role="platform_admin",
            client=None,
            accessible_clients=[SimpleNamespace(id=uuid4(), company_id=uuid4())],
        )

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        db=db,
    )

    assert captured["include_inactive_tenants"] is False
    filters = [str(call.args[0]) for call in query.filter.call_args_list]
    assert "branches.is_active IS true" in filters


@pytest.mark.asyncio
async def test_list_branches_archived_lifecycle_filters_inactive(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={"lifecycle": "archived"})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            role="platform_admin",
            client=None,
            accessible_clients=[SimpleNamespace(id=uuid4(), company_id=uuid4())],
        )

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        lifecycle="archived",
        db=db,
    )

    assert captured["include_inactive_tenants"] is True
    filters = [str(call.args[0]) for call in query.filter.call_args_list]
    assert "branches.is_active IS false" in filters


@pytest.mark.asyncio
async def test_list_branches_rejects_client_from_other_company(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={})

    company_id = uuid4()
    company_client_id = uuid4()
    foreign_client_id = uuid4()

    def _fake_context(_request, _db, **_kwargs):
        return SimpleNamespace(
            role="platform_admin",
            client=None,
            accessible_clients=[
                SimpleNamespace(id=company_client_id, company_id=company_id),
                SimpleNamespace(id=foreign_client_id, company_id=uuid4()),
            ],
        )

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_branches(
            request=request,
            company_id=str(company_id),
            client_id=str(foreign_client_id),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_list_branches_accepts_branch_id_filter(monkeypatch) -> None:
    branch_id = uuid4()
    client_id = uuid4()
    query = _build_list_query_mock()
    branch_lookup_query = Mock()
    branch_lookup_query.filter.return_value = branch_lookup_query
    branch_lookup_query.first.return_value = SimpleNamespace(
        id=branch_id,
        client_id=client_id,
    )
    db = Mock()
    db.query.side_effect = [query, branch_lookup_query]
    request = SimpleNamespace(query_params={})

    def _fake_context(_request, _db, **_kwargs):
        return SimpleNamespace(
            role="platform_admin",
            client=None,
            accessible_clients=[SimpleNamespace(id=client_id, company_id=uuid4())],
        )

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        client_id=str(client_id),
        branch_id=str(branch_id),
        db=db,
    )

    filters = [str(call.args[0]) for call in query.filter.call_args_list]
    assert any("branches.id =" in item for item in filters)


@pytest.mark.asyncio
async def test_list_branches_rejects_branch_from_other_client(monkeypatch) -> None:
    branch_id = uuid4()
    selected_client_id = uuid4()
    foreign_client_id = uuid4()
    query = _build_list_query_mock()
    branch_lookup_query = Mock()
    branch_lookup_query.filter.return_value = branch_lookup_query
    branch_lookup_query.first.return_value = SimpleNamespace(
        id=branch_id,
        client_id=foreign_client_id,
    )
    db = Mock()
    db.query.side_effect = [query, branch_lookup_query]
    request = SimpleNamespace(query_params={})

    def _fake_context(_request, _db, **_kwargs):
        return SimpleNamespace(
            role="platform_admin",
            client=None,
            accessible_clients=[
                SimpleNamespace(id=selected_client_id, company_id=uuid4()),
                SimpleNamespace(id=foreign_client_id, company_id=uuid4()),
            ],
        )

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_branches(
            request=request,
            client_id=str(selected_client_id),
            branch_id=str(branch_id),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_list_branches_rejects_branch_from_other_company(monkeypatch) -> None:
    branch_id = uuid4()
    scoped_company_id = uuid4()
    scoped_client_id = uuid4()
    foreign_company_id = uuid4()
    foreign_client_id = uuid4()
    query = _build_list_query_mock()
    branch_lookup_query = Mock()
    branch_lookup_query.filter.return_value = branch_lookup_query
    branch_lookup_query.first.return_value = SimpleNamespace(
        id=branch_id,
        client_id=foreign_client_id,
    )
    db = Mock()
    db.query.side_effect = [query, branch_lookup_query]
    request = SimpleNamespace(query_params={})

    def _fake_context(_request, _db, **_kwargs):
        return SimpleNamespace(
            role="platform_admin",
            client=None,
            accessible_clients=[
                SimpleNamespace(id=scoped_client_id, company_id=scoped_company_id),
                SimpleNamespace(id=foreign_client_id, company_id=foreign_company_id),
            ],
        )

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_branches(
            request=request,
            company_id=str(scoped_company_id),
            branch_id=str(branch_id),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


class _RowsQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


def test_build_onboarding_throughput_metrics_computes_expected_values() -> None:
    now = datetime.now(timezone.utc)
    client_id = uuid4()
    branch_a_id = uuid4()
    branch_b_id = uuid4()

    branch_rows = [
        SimpleNamespace(
            id=branch_a_id,
            client_id=client_id,
            go_live_state="approved",
            go_live_reviewed_at=now - timedelta(hours=24),
            created_at=now - timedelta(hours=48),
            is_active=True,
            onboarding_updated_at=now - timedelta(hours=48),
            go_live_waiver_until=None,
        ),
        SimpleNamespace(
            id=branch_b_id,
            client_id=client_id,
            go_live_state="approved",
            go_live_reviewed_at=now - timedelta(hours=12),
            created_at=now - timedelta(hours=72),
            is_active=True,
            onboarding_updated_at=now - timedelta(hours=72),
            go_live_waiver_until=None,
        ),
        SimpleNamespace(
            id=uuid4(),
            client_id=client_id,
            go_live_state="pending",
            go_live_reviewed_at=None,
            created_at=now - timedelta(hours=50),
            is_active=True,
            onboarding_updated_at=now - timedelta(hours=50),
            go_live_waiver_until=None,
        ),
        SimpleNamespace(
            id=uuid4(),
            client_id=client_id,
            go_live_state="pending",
            go_live_reviewed_at=None,
            created_at=now - timedelta(hours=10),
            is_active=True,
            onboarding_updated_at=now - timedelta(hours=10),
            go_live_waiver_until=None,
        ),
    ]
    audit_rows = [
        SimpleNamespace(branch_id=branch_b_id, event_type="branch_go_live_rejected", created_at=now - timedelta(hours=36)),
        SimpleNamespace(branch_id=branch_a_id, event_type="branch_go_live_approved", created_at=now - timedelta(hours=24)),
        SimpleNamespace(branch_id=branch_b_id, event_type="branch_go_live_approved", created_at=now - timedelta(hours=12)),
    ]
    incident_rows = [
        SimpleNamespace(
            client_id=client_id,
            alert_metadata={"incident_id": "inc-a", "incident_state": "resolved"},
            created_at=now - timedelta(hours=8),
            id=uuid4(),
        ),
        SimpleNamespace(
            client_id=client_id,
            alert_metadata={"incident_id": "inc-a", "incident_state": "open"},
            created_at=now - timedelta(hours=4),
            id=uuid4(),
        ),
        SimpleNamespace(
            client_id=client_id,
            alert_metadata={"incident_id": "inc-b", "incident_state": "resolved"},
            created_at=now - timedelta(hours=6),
            id=uuid4(),
        ),
    ]

    db = Mock()
    queries = [
        _RowsQuery(branch_rows),
        _RowsQuery(audit_rows),
        _RowsQuery(incident_rows),
    ]

    def _query_side_effect(*_entities):
        assert queries, "unexpected extra db.query call"
        return queries.pop(0)

    db.query.side_effect = _query_side_effect

    metrics = console_router._build_onboarding_throughput_metrics(
        db,
        client_ids={client_id},
        window_hours=72,
    )

    assert metrics.approved_branches_total == 2
    assert metrics.first_pass_approved_branches == 1
    assert metrics.first_pass_go_live_rate_pct == 50.0
    assert metrics.incident_reopen_rate_24h_pct == 50.0
    assert metrics.time_to_go_live_median_hours == 42.0
    assert metrics.blocker_age_p95_hours == 48.0


def test_build_onboarding_throughput_metrics_empty_scope_returns_defaults() -> None:
    db = Mock()

    metrics = console_router._build_onboarding_throughput_metrics(
        db,
        client_ids=set(),
    )

    assert metrics.window_hours == console_router._ONBOARDING_THROUGHPUT_WINDOW_HOURS
    assert metrics.approved_branches_total == 0
    assert metrics.first_pass_approved_branches == 0
    assert metrics.time_to_go_live_median_hours is None
    assert metrics.blocker_age_p95_hours is None
    assert metrics.first_pass_go_live_rate_pct is None
    assert metrics.incident_reopen_rate_24h_pct is None
    db.query.assert_not_called()


def test_normalize_tenants_weekly_snapshot_week_key_accepts_valid_format() -> None:
    assert console_router._normalize_tenants_weekly_snapshot_week_key("2026-W08") == "2026-W08"


@pytest.mark.parametrize("value", ["", "2026-08", "2026-W8", "2026-W54", "bad-value"])
def test_normalize_tenants_weekly_snapshot_week_key_rejects_invalid(value: str) -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._normalize_tenants_weekly_snapshot_week_key(value)

    assert exc_info.value.code == "INVALID_PARAM"


def test_normalize_tenants_weekly_snapshot_payload_rejects_non_object() -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._normalize_tenants_weekly_snapshot_payload(None)

    assert exc_info.value.code == "INVALID_PARAM"


def _sample_weekly_snapshot(now: datetime, blocked_signals: int = 1) -> dict:
    return {
        "generatedAt": now.isoformat(),
        "sourceWindow": 12,
        "workspaceMode": "portfolio",
        "lifecycleMode": "active",
        "kpi": {
            "onboardingCoverage": 88,
            "goLiveReadiness": 76,
            "serviceStability": 97,
            "decommissionShare": 6,
            "changeFailure": 3,
            "rollbackShare": 4,
            "blockedSignals": blocked_signals,
        },
        "drilldown": [
            {
                "id": "blockedSignals",
                "status": "warn",
                "value": blocked_signals,
                "reason": "blocked signal detected",
            }
        ],
        "attentionSummary": {
            "activeClientsTotal": 10,
            "highRiskClients": 1,
            "mediumRiskClients": 2,
            "outboxFailed24hTotal": 0,
            "pendingHandoversTotal": 1,
        },
    }


def test_normalize_tenants_weekly_snapshot_payload_rejects_invalid_schema() -> None:
    now = datetime.now(timezone.utc)
    invalid_payload = _sample_weekly_snapshot(now)
    invalid_payload["kpi"] = {"blockedSignals": 1}

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._normalize_tenants_weekly_snapshot_payload(invalid_payload)

    assert exc_info.value.code == "INVALID_PARAM"


def test_serialize_tenants_weekly_snapshot_record_maps_payload() -> None:
    now = datetime.now(timezone.utc)
    event = SimpleNamespace(
        id=uuid4(),
        created_at=now,
        client_id=uuid4(),
        actor_name="Platform Admin",
        payload={
            "week_key": "2026-W08",
            "snapshot": _sample_weekly_snapshot(now, blocked_signals=1),
        },
    )

    record = console_router._serialize_tenants_weekly_snapshot_record(event)

    assert record.week_key == "2026-W08"
    assert record.snapshot.kpi.blockedSignals == 1
    assert record.snapshot_schema_version == "v1"
    assert record.actor_name == "Platform Admin"


def test_serialize_tenants_weekly_snapshot_record_falls_back_for_legacy_payload() -> None:
    now = datetime.now(timezone.utc)
    event = SimpleNamespace(
        id=uuid4(),
        created_at=now,
        client_id=uuid4(),
        actor_name="Platform Admin",
        payload={
            "week_key": "2026-W08",
            "snapshot": {"generatedAt": now.isoformat()},
        },
    )

    record = console_router._serialize_tenants_weekly_snapshot_record(event)

    assert record.week_key == "2026-W08"
    assert record.snapshot.kpi.blockedSignals == 0
    assert record.snapshot.workspaceMode == "portfolio"
    assert record.snapshot_schema_version == "v1"


def test_build_weekly_snapshot_schema_versions_groups_items() -> None:
    now = datetime.now(timezone.utc)
    snapshot_model = console_router.ConsoleTenantsWeeklySnapshotPayload.model_validate(
        _sample_weekly_snapshot(now, blocked_signals=1),
    )
    items = [
        console_router.ConsoleTenantsWeeklySnapshotRecord(
            id=uuid4(),
            created_at=now.isoformat(),
            client_id=uuid4(),
            week_key="2026-W08",
            snapshot=snapshot_model,
            snapshot_schema_version="v1",
        ),
        console_router.ConsoleTenantsWeeklySnapshotRecord(
            id=uuid4(),
            created_at=now.isoformat(),
            client_id=uuid4(),
            week_key="2026-W09",
            snapshot=snapshot_model,
            snapshot_schema_version="v2",
        ),
        console_router.ConsoleTenantsWeeklySnapshotRecord(
            id=uuid4(),
            created_at=now.isoformat(),
            client_id=uuid4(),
            week_key="2026-W10",
            snapshot=snapshot_model,
            snapshot_schema_version="v1",
        ),
    ]

    versions = console_router._build_weekly_snapshot_schema_versions(items)

    assert versions == {"v1": 2, "v2": 1}


class _ClientQuery:
    def __init__(self, client):
        self._client = client

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._client


class _SnapshotSaveQuery:
    def __init__(self, item):
        self._item = item

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._item


@pytest.mark.asyncio
async def test_save_tenants_weekly_snapshot_updates_existing_week(monkeypatch) -> None:
    client_id = uuid4()
    event_id = uuid4()
    now = datetime.now(timezone.utc)
    existing_snapshot = SimpleNamespace(
        id=event_id,
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
        client_id=client_id,
        actor_id=None,
        actor_name=None,
        week_key="2026-W08",
        snapshot=_sample_weekly_snapshot(now, blocked_signals=3),
        snapshot_schema_version="v1",
    )
    request = SimpleNamespace(query_params={})
    context = SimpleNamespace(
        role="platform_admin",
        agent=SimpleNamespace(id=uuid4(), name="Platform Admin"),
    )
    db = Mock()
    db.query.side_effect = lambda model: (
        _ClientQuery(SimpleNamespace(id=client_id))
        if model is console_router.Client
        else _SnapshotSaveQuery(existing_snapshot)
    )
    db.refresh = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    response = await console_router.save_tenants_weekly_snapshot(
        request=request,
        payload=console_router.ConsoleTenantsWeeklySnapshotCreateRequest(
            client_id=client_id,
            week_key="2026-W08",
            snapshot=console_router.ConsoleTenantsWeeklySnapshotPayload.model_validate(
                _sample_weekly_snapshot(now, blocked_signals=1),
            ),
        ),
        db=db,
    )

    assert response.item.id == event_id
    assert response.item.week_key == "2026-W08"
    assert response.item.snapshot.kpi.blockedSignals == 1
    assert response.item.snapshot_schema_version == "v1"
    assert existing_snapshot.actor_name == "Platform Admin"
    assert existing_snapshot.snapshot_schema_version == "v1"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_tenants_weekly_snapshot_returns_read_only_error_when_table_missing(monkeypatch) -> None:
    client_id = uuid4()
    now = datetime.now(timezone.utc)
    request = SimpleNamespace(query_params={})
    context = SimpleNamespace(
        role="platform_admin",
        agent=SimpleNamespace(id=uuid4(), name="Platform Admin"),
    )

    class _BrokenSnapshotSaveQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            raise ProgrammingError(
                "SELECT",
                {},
                Exception('relation "tenants_weekly_snapshots" does not exist'),
            )

    db = Mock()
    db.query.side_effect = lambda model: (
        _ClientQuery(SimpleNamespace(id=client_id))
        if model is console_router.Client
        else _BrokenSnapshotSaveQuery()
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.save_tenants_weekly_snapshot(
            request=request,
            payload=console_router.ConsoleTenantsWeeklySnapshotCreateRequest(
                client_id=client_id,
                week_key="2026-W08",
                snapshot=console_router.ConsoleTenantsWeeklySnapshotPayload.model_validate(
                    _sample_weekly_snapshot(now, blocked_signals=2),
                ),
            ),
            db=db,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "TENANTS_WEEKLY_SNAPSHOT_STORAGE_UNAVAILABLE"
    db.rollback.assert_called_once()


def test_normalize_tenants_sensitive_access_field_accepts_instance_id() -> None:
    assert console_router._normalize_tenants_sensitive_access_field("instance_id") == "instance_id"


@pytest.mark.parametrize("value", ["", "phone", "telegram_chat_id"])
def test_normalize_tenants_sensitive_access_field_rejects_unsupported(value: str) -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._normalize_tenants_sensitive_access_field(value)

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.parametrize("value", ["reveal", "copy"])
def test_normalize_tenants_sensitive_access_action_accepts_allowed(value: str) -> None:
    assert console_router._normalize_tenants_sensitive_access_action(value) == value


@pytest.mark.parametrize("value", ["", "download", "open"])
def test_normalize_tenants_sensitive_access_action_rejects_invalid(value: str) -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._normalize_tenants_sensitive_access_action(value)

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_audit_tenants_sensitive_access_records_event(monkeypatch) -> None:
    branch_id = uuid4()
    client_id = uuid4()
    request = SimpleNamespace(query_params={})
    context = SimpleNamespace(
        role="platform_admin",
        agent=SimpleNamespace(id=uuid4(), name="Platform Admin"),
    )
    branch = SimpleNamespace(id=branch_id, client_id=client_id)
    db = Mock()
    db.query.side_effect = lambda model: (
        _ClientQuery(branch)
        if model is console_router.Branch
        else AssertionError(f"Unexpected model: {model}")
    )
    db.refresh = Mock()

    event = SimpleNamespace(id=uuid4())
    record_audit_mock = Mock(return_value=event)
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(console_router, "record_audit_event", record_audit_mock)

    response = await console_router.audit_tenants_sensitive_access(
        request=request,
        payload=console_router.ConsoleTenantsSensitiveAccessAuditRequest(
            branch_id=branch_id,
            field="instance_id",
            action="copy",
            context="changes",
        ),
        db=db,
    )

    assert response.ok is True
    assert response.audit_id == event.id
    assert record_audit_mock.call_count == 1
    assert record_audit_mock.call_args.kwargs["event_type"] == "tenants_sensitive_id_accessed"
    assert record_audit_mock.call_args.kwargs["client_id"] == client_id
    assert record_audit_mock.call_args.kwargs["branch_id"] == branch_id
    assert record_audit_mock.call_args.kwargs["payload"]["field"] == "instance_id"
    assert record_audit_mock.call_args.kwargs["payload"]["action"] == "copy"
    db.commit.assert_called_once()
