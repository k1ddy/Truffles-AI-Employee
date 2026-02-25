from contextlib import nullcontext
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


def test_build_fleet_client_details_from_projection_accepts_valid_row() -> None:
    branch_id = uuid4()
    row = SimpleNamespace(
        lifecycle_state="active",
        payment_status="confirmed",
        commercial_state="payment_confirmed",
        service_state="ok",
        owner_name="Owner",
        next_action="monitor_sla_and_quality",
        total_branches=3,
        active_branches=3,
        degraded_branches=0,
        go_live_ready_branches=2,
        reference_branch_ids=[str(branch_id)],
        reference_branch_reason="selected_active_branch",
    )

    details = console_router._build_fleet_client_details_from_projection(row)

    assert details is not None
    assert details.lifecycle_state == "active"
    assert details.payment_status == "confirmed"
    assert details.reference_branch_ids == (branch_id,)


def test_load_materialized_fleet_client_details_map_returns_max_freshness_lag() -> None:
    client_id = uuid4()
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        client_id=client_id,
        lifecycle_state="active",
        payment_status="confirmed",
        commercial_state="payment_confirmed",
        service_state="ok",
        owner_name="Owner",
        next_action="monitor_sla_and_quality",
        total_branches=3,
        active_branches=2,
        degraded_branches=1,
        go_live_ready_branches=1,
        reference_branch_ids=[],
        reference_branch_reason="selected_active_branch",
        refreshed_at=now - timedelta(seconds=90),
    )
    query_result = Mock()
    query_result.all.return_value = [row]
    query = Mock()
    query.filter.return_value = query_result
    db = Mock()
    db.query.return_value = query

    details_map, freshness_lag = console_router._load_materialized_fleet_client_details_map(
        db,
        client_ids={client_id},
    )

    assert client_id in details_map
    assert freshness_lag is not None
    assert freshness_lag >= 30.0


def test_compact_stale_materialized_fleet_projection_rows_deletes_stale_ids(monkeypatch) -> None:
    stale_one = uuid4()
    stale_two = uuid4()
    company_one = uuid4()
    company_two = uuid4()
    stale_rows_query = Mock()
    stale_rows_query.filter.return_value = stale_rows_query
    stale_rows_query.order_by.return_value = stale_rows_query
    stale_rows_query.limit.return_value = stale_rows_query
    stale_rows_query.all.return_value = [
        (stale_one, company_one),
        (stale_two, company_two),
    ]
    delete_query = Mock()
    delete_query.filter.return_value = delete_query
    delete_query.delete.return_value = 2
    db = Mock()
    query_calls = {"count": 0}

    def _query_side_effect(*_args):
        query_calls["count"] += 1
        if query_calls["count"] == 1:
            return stale_rows_query
        return delete_query

    db.query.side_effect = _query_side_effect
    compaction_events: list[dict[str, object]] = []
    prewarm_calls: list[list[UUID]] = []

    monkeypatch.setattr(console_router, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        console_router,
        "record_tenants_fleet_projection_compaction",
        lambda **kwargs: compaction_events.append(kwargs),
    )
    monkeypatch.setattr(
        console_router,
        "_maybe_enqueue_projection_fallback_prewarm_for_company_ids",
        lambda **kwargs: prewarm_calls.append(kwargs.get("company_ids") or []),
    )

    deleted = console_router._compact_stale_materialized_fleet_projection_rows()

    assert deleted == 2
    assert db.commit.call_count == 1
    assert db.close.call_count == 1
    assert len(prewarm_calls) == 1
    assert set(prewarm_calls[0]) == {company_one, company_two}
    assert compaction_events == [{"outcome": "success", "deleted_rows": 2}]


def test_compact_stale_materialized_fleet_projection_rows_skips_prewarm_without_company_scope(
    monkeypatch,
) -> None:
    stale_id = uuid4()
    stale_rows_query = Mock()
    stale_rows_query.filter.return_value = stale_rows_query
    stale_rows_query.order_by.return_value = stale_rows_query
    stale_rows_query.limit.return_value = stale_rows_query
    stale_rows_query.all.return_value = [(stale_id, None)]
    delete_query = Mock()
    delete_query.filter.return_value = delete_query
    delete_query.delete.return_value = 1
    db = Mock()
    query_calls = {"count": 0}

    def _query_side_effect(*_args):
        query_calls["count"] += 1
        if query_calls["count"] == 1:
            return stale_rows_query
        return delete_query

    db.query.side_effect = _query_side_effect
    prewarm_calls: list[list[UUID]] = []

    monkeypatch.setattr(console_router, "SessionLocal", lambda: db)
    monkeypatch.setattr(console_router, "record_tenants_fleet_projection_compaction", lambda **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_maybe_enqueue_projection_fallback_prewarm_for_company_ids",
        lambda **kwargs: prewarm_calls.append(kwargs.get("company_ids") or []),
    )

    deleted = console_router._compact_stale_materialized_fleet_projection_rows()

    assert deleted == 1
    assert prewarm_calls == []
    assert db.commit.call_count == 1
    assert db.close.call_count == 1


def test_maybe_run_fleet_projection_maintenance_respects_interval(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        console_router,
        "_compact_stale_materialized_fleet_projection_rows",
        lambda: calls.append(1) or 0,
    )
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_ENABLED", True)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_ENABLED", True)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_INTERVAL_SECONDS", 60)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_NEXT_ALLOWED_AT", 0.0)

    console_router._maybe_run_fleet_projection_maintenance(now_mono=100.0)
    console_router._maybe_run_fleet_projection_maintenance(now_mono=120.0)
    console_router._maybe_run_fleet_projection_maintenance(now_mono=161.0)

    assert len(calls) == 2


def test_build_fleet_attention_response_requests_projection_persist(monkeypatch) -> None:
    client_id = uuid4()
    company_id = uuid4()
    now = datetime.now(timezone.utc)
    active_client = SimpleNamespace(
        id=client_id,
        name="alpha",
        company_id=company_id,
    )
    details = console_router._FleetClientDetails(
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
    )
    captured_load_calls: list[dict[str, object]] = []

    def _load_details(*_args, **kwargs):
        captured_load_calls.append(kwargs)
        return {client_id: details}

    empty_query = Mock()
    empty_query.filter.return_value = empty_query
    empty_query.all.return_value = []
    db = Mock()
    db.query.return_value = empty_query

    monkeypatch.setattr(console_router, "_load_or_build_fleet_client_details_map", _load_details)
    monkeypatch.setattr(
        console_router,
        "_load_latest_branch_inbound_observations_for_clients",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        console_router,
        "_query_outbox_failed_24h_map",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        console_router,
        "_query_pending_handovers_map",
        lambda *_args, **_kwargs: {},
    )

    response = console_router._build_fleet_attention_response_for_clients(
        db,
        active_clients=[active_client],
        companies_by_id={},
        stale_after_minutes=120,
        include_low_mode=True,
        limit=20,
        now=now,
    )

    assert response.summary.active_clients_total == 1
    assert len(captured_load_calls) == 1
    assert captured_load_calls[0]["persist_missing"] is True
    assert captured_load_calls[0]["persist_missing_max_clients"] == (
        console_router._TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS
    )


def test_load_or_build_fleet_client_details_map_uses_materialized_when_complete(monkeypatch) -> None:
    client_id = uuid4()
    company_id = uuid4()
    client = SimpleNamespace(id=client_id, company_id=company_id)
    company = SimpleNamespace(id=company_id, name="Acme")
    expected = console_router._FleetClientDetails(
        lifecycle_state="active",
        payment_status="confirmed",
        commercial_state="payment_confirmed",
        service_state="ok",
        owner_name="Owner",
        next_action="monitor_sla_and_quality",
        total_branches=1,
        active_branches=1,
        degraded_branches=0,
        go_live_ready_branches=1,
    )
    db = Mock()
    observation_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        console_router,
        "_load_materialized_fleet_client_details_map",
        lambda *_args, **_kwargs: ({client_id: expected}, 42.0),
    )
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not rebuild details on full materialized hit")),
    )
    monkeypatch.setattr(
        console_router,
        "record_tenants_fleet_projection_observation",
        lambda **kwargs: observation_calls.append(kwargs),
    )

    result = console_router._load_or_build_fleet_client_details_map(
        db,
        clients=[client],
        companies_by_id={company_id: company},
    )

    assert result == {client_id: expected}
    assert observation_calls == [
        {
            "total_clients": 1,
            "materialized_clients": 1,
            "fallback_clients": 0,
            "max_freshness_lag_seconds": 42.0,
        }
    ]


def test_load_or_build_fleet_client_details_map_rebuilds_missing_and_upserts(monkeypatch) -> None:
    hit_client_id = uuid4()
    miss_client_id = uuid4()
    company_id = uuid4()
    hit_client = SimpleNamespace(id=hit_client_id, company_id=company_id)
    miss_client = SimpleNamespace(id=miss_client_id, company_id=company_id)
    company = SimpleNamespace(id=company_id, name="Acme")
    materialized_hit = console_router._FleetClientDetails(
        lifecycle_state="active",
        payment_status="confirmed",
        commercial_state="payment_confirmed",
        service_state="ok",
        owner_name="Owner",
        next_action="monitor_sla_and_quality",
        total_branches=1,
        active_branches=1,
        degraded_branches=0,
        go_live_ready_branches=1,
    )
    rebuilt_miss = console_router._FleetClientDetails(
        lifecycle_state="onboarding",
        payment_status="pending",
        commercial_state="payment_pending",
        service_state="attention",
        owner_name=None,
        next_action="complete_onboarding_steps",
        total_branches=2,
        active_branches=1,
        degraded_branches=1,
        go_live_ready_branches=0,
    )
    upsert_calls: list[dict[str, object]] = []
    db = Mock()
    observation_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        console_router,
        "_load_materialized_fleet_client_details_map",
        lambda *_args, **_kwargs: ({hit_client_id: materialized_hit}, 75.0),
    )
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: {miss_client_id: rebuilt_miss},
    )
    monkeypatch.setattr(
        console_router,
        "_upsert_materialized_fleet_client_details",
        lambda _db, **kwargs: upsert_calls.append(kwargs) or True,
    )
    monkeypatch.setattr(
        console_router,
        "record_tenants_fleet_projection_observation",
        lambda **kwargs: observation_calls.append(kwargs),
    )

    result = console_router._load_or_build_fleet_client_details_map(
        db,
        clients=[hit_client, miss_client],
        companies_by_id={company_id: company},
        persist_missing=True,
    )

    assert result[hit_client_id] == materialized_hit
    assert result[miss_client_id] == rebuilt_miss
    assert len(upsert_calls) == 1
    assert upsert_calls[0]["details_by_client_id"] == {miss_client_id: rebuilt_miss}
    assert observation_calls == [
        {
            "total_clients": 2,
            "materialized_clients": 1,
            "fallback_clients": 1,
            "max_freshness_lag_seconds": 75.0,
        }
    ]


def test_load_or_build_fleet_client_details_map_respects_persist_limit(monkeypatch) -> None:
    company_id = uuid4()
    clients = [
        SimpleNamespace(id=uuid4(), company_id=company_id),
        SimpleNamespace(id=uuid4(), company_id=company_id),
        SimpleNamespace(id=uuid4(), company_id=company_id),
    ]
    rebuilt_details = {
        clients[0].id: console_router._FleetClientDetails(
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
        clients[1].id: console_router._FleetClientDetails(
            lifecycle_state="onboarding",
            payment_status="pending",
            commercial_state="payment_pending",
            service_state="attention",
            owner_name=None,
            next_action="confirm_payment_and_approve_go_live",
            total_branches=2,
            active_branches=1,
            degraded_branches=0,
            go_live_ready_branches=1,
        ),
        clients[2].id: console_router._FleetClientDetails(
            lifecycle_state="active",
            payment_status="confirmed",
            commercial_state="payment_confirmed",
            service_state="degraded",
            owner_name=None,
            next_action="resolve_service_degradation",
            total_branches=3,
            active_branches=2,
            degraded_branches=1,
            go_live_ready_branches=2,
        ),
    }
    upsert_calls: list[dict[str, object]] = []
    observation_calls: list[dict[str, object]] = []
    db = Mock()

    monkeypatch.setattr(
        console_router,
        "_load_materialized_fleet_client_details_map",
        lambda *_args, **_kwargs: ({}, None),
    )
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: rebuilt_details,
    )
    monkeypatch.setattr(
        console_router,
        "_upsert_materialized_fleet_client_details",
        lambda _db, **kwargs: upsert_calls.append(kwargs) or True,
    )
    monkeypatch.setattr(
        console_router,
        "record_tenants_fleet_projection_observation",
        lambda **kwargs: observation_calls.append(kwargs),
    )

    result = console_router._load_or_build_fleet_client_details_map(
        db,
        clients=clients,
        companies_by_id={company_id: SimpleNamespace(id=company_id)},
        persist_missing=True,
        persist_missing_max_clients=2,
    )

    assert result == rebuilt_details
    assert len(upsert_calls) == 1
    persisted_details = upsert_calls[0]["details_by_client_id"]
    assert isinstance(persisted_details, dict)
    assert list(persisted_details.keys()) == [clients[0].id, clients[1].id]
    assert observation_calls == [
        {
            "total_clients": 3,
            "materialized_clients": 0,
            "fallback_clients": 3,
            "max_freshness_lag_seconds": None,
        }
    ]


def test_load_or_build_fleet_client_details_map_enqueues_projection_fallback_prewarm_for_unpersisted_clients(
    monkeypatch,
) -> None:
    company_a = uuid4()
    company_b = uuid4()
    clients = [
        SimpleNamespace(id=uuid4(), company_id=company_a),
        SimpleNamespace(id=uuid4(), company_id=company_a),
        SimpleNamespace(id=uuid4(), company_id=company_b),
    ]
    rebuilt_details = {
        client.id: console_router._FleetClientDetails(
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
        )
        for client in clients
    }
    enqueue_calls: list[dict[str, object]] = []
    db = Mock()

    monkeypatch.setattr(
        console_router,
        "_load_materialized_fleet_client_details_map",
        lambda *_args, **_kwargs: ({}, None),
    )
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: rebuilt_details,
    )
    monkeypatch.setattr(
        console_router,
        "_upsert_materialized_fleet_client_details",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueue_calls.append(kwargs),
    )
    monkeypatch.setattr(console_router, "record_tenants_fleet_projection_observation", lambda **_kwargs: None)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED", True)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES", 10)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MIN_INTERVAL_SECONDS", 0)

    result = console_router._load_or_build_fleet_client_details_map(
        db,
        clients=clients,
        companies_by_id={
            company_a: SimpleNamespace(id=company_a),
            company_b: SimpleNamespace(id=company_b),
        },
        persist_missing=True,
        persist_missing_max_clients=1,
    )

    assert result == rebuilt_details
    assert len(enqueue_calls) == 1
    assert enqueue_calls[0]["company_ids"] == {company_a, company_b}
    assert enqueue_calls[0]["global_prewarm_required"] is False


def test_load_or_build_fleet_client_details_map_skips_projection_fallback_prewarm_when_all_fallback_clients_persisted(
    monkeypatch,
) -> None:
    company_id = uuid4()
    clients = [
        SimpleNamespace(id=uuid4(), company_id=company_id),
        SimpleNamespace(id=uuid4(), company_id=company_id),
    ]
    rebuilt_details = {
        client.id: console_router._FleetClientDetails(
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
        )
        for client in clients
    }
    enqueue_calls: list[dict[str, object]] = []
    db = Mock()

    monkeypatch.setattr(
        console_router,
        "_load_materialized_fleet_client_details_map",
        lambda *_args, **_kwargs: ({}, None),
    )
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: rebuilt_details,
    )
    monkeypatch.setattr(
        console_router,
        "_upsert_materialized_fleet_client_details",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueue_calls.append(kwargs),
    )
    monkeypatch.setattr(console_router, "record_tenants_fleet_projection_observation", lambda **_kwargs: None)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED", True)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES", 10)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MIN_INTERVAL_SECONDS", 0)

    result = console_router._load_or_build_fleet_client_details_map(
        db,
        clients=clients,
        companies_by_id={company_id: SimpleNamespace(id=company_id)},
        persist_missing=True,
        persist_missing_max_clients=10,
    )

    assert result == rebuilt_details
    assert enqueue_calls == []


def test_throttle_projection_fallback_prewarm_company_ids_respects_interval(monkeypatch) -> None:
    company_id = uuid4()
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MIN_INTERVAL_SECONDS", 60)
    monkeypatch.setattr(
        console_router,
        "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY",
        {},
    )

    first = console_router._throttle_projection_fallback_prewarm_company_ids(
        company_ids=[company_id],
        now_mono=100.0,
    )
    second = console_router._throttle_projection_fallback_prewarm_company_ids(
        company_ids=[company_id],
        now_mono=120.0,
    )
    third = console_router._throttle_projection_fallback_prewarm_company_ids(
        company_ids=[company_id],
        now_mono=161.0,
    )

    assert first == {company_id}
    assert second == set()
    assert third == {company_id}


def test_select_projection_fallback_prewarm_company_ids_rotates_overflow_scope() -> None:
    company_a = uuid4()
    company_b = uuid4()
    company_c = uuid4()
    company_d = uuid4()
    company_e = uuid4()

    first_batch, first_offset = console_router._select_projection_fallback_prewarm_company_ids(
        company_ids=[company_a, company_b, company_c, company_d, company_e],
        max_company_scopes=2,
        rotation_offset=0,
    )
    second_batch, second_offset = console_router._select_projection_fallback_prewarm_company_ids(
        company_ids=[company_a, company_b, company_c, company_d, company_e],
        max_company_scopes=2,
        rotation_offset=first_offset,
    )
    third_batch, third_offset = console_router._select_projection_fallback_prewarm_company_ids(
        company_ids=[company_a, company_b, company_c, company_d, company_e],
        max_company_scopes=2,
        rotation_offset=second_offset,
    )

    assert first_batch == [company_a, company_b]
    assert second_batch == [company_c, company_d]
    assert third_batch == [company_e, company_a]
    assert first_offset == 2
    assert second_offset == 4
    assert third_offset == 1


def test_maybe_enqueue_projection_fallback_prewarm_for_company_ids_rotates_batches(monkeypatch) -> None:
    company_a = uuid4()
    company_b = uuid4()
    company_c = uuid4()
    company_d = uuid4()
    throttled_batches: list[list[UUID]] = []
    enqueue_calls: list[dict[str, object]] = []

    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_ENABLED", True)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED", True)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES", 2)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_SELECTION_OFFSET", 0)

    def _record_throttle(**kwargs):
        company_ids = list(kwargs["company_ids"])
        throttled_batches.append(company_ids)
        return set(company_ids)

    monkeypatch.setattr(
        console_router,
        "_throttle_projection_fallback_prewarm_company_ids",
        _record_throttle,
    )
    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueue_calls.append(kwargs),
    )

    company_scope = [company_a, company_b, company_c, company_d]
    console_router._maybe_enqueue_projection_fallback_prewarm_for_company_ids(company_ids=company_scope)
    console_router._maybe_enqueue_projection_fallback_prewarm_for_company_ids(company_ids=company_scope)

    assert throttled_batches == [[company_a, company_b], [company_c, company_d]]
    assert enqueue_calls == [
        {"company_ids": {company_a, company_b}, "global_prewarm_required": False},
        {"company_ids": {company_c, company_d}, "global_prewarm_required": False},
    ]


def test_maybe_enqueue_projection_fallback_prewarm_for_client_ids_enqueues_company_scopes(monkeypatch) -> None:
    first_client_id = uuid4()
    second_client_id = uuid4()
    company_a = uuid4()
    company_b = uuid4()
    enqueue_calls: list[dict[str, object]] = []

    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED", True)
    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES", 10)
    monkeypatch.setattr(
        console_router,
        "_load_company_ids_for_client_ids",
        lambda **_kwargs: {company_a, company_b},
    )
    monkeypatch.setattr(
        console_router,
        "_throttle_projection_fallback_prewarm_company_ids",
        lambda **_kwargs: {company_b},
    )
    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueue_calls.append(kwargs),
    )

    console_router._maybe_enqueue_projection_fallback_prewarm_for_client_ids(
        client_ids={first_client_id, second_client_id},
    )

    assert enqueue_calls == [
        {
            "company_ids": {company_b},
            "global_prewarm_required": False,
        }
    ]


def test_maybe_enqueue_projection_fallback_prewarm_for_client_ids_skips_without_company_map(monkeypatch) -> None:
    client_id = uuid4()
    enqueue_calls: list[dict[str, object]] = []

    monkeypatch.setattr(console_router, "_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED", True)
    monkeypatch.setattr(
        console_router,
        "_load_company_ids_for_client_ids",
        lambda **_kwargs: set(),
    )
    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueue_calls.append(kwargs),
    )

    console_router._maybe_enqueue_projection_fallback_prewarm_for_client_ids(
        client_ids={client_id},
    )

    assert enqueue_calls == []


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
    query.join.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    return query


def _collect_filter_predicates(query: Mock) -> list[str]:
    predicates: list[str] = []
    for call in query.filter.call_args_list:
        predicates.extend(str(predicate) for predicate in call.args)
    return predicates


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


def _build_fleet_summary() -> console_router.ConsoleFleetSummary:
    return console_router.ConsoleFleetSummary(
        total_companies=1,
        total_clients=1,
        active_clients=1,
        onboarding_clients=0,
        archived_clients=0,
        paused_clients=0,
        go_live_ready_clients=0,
        degraded_clients=0,
        payment_pending_clients=0,
        payment_confirmed_clients=1,
        lifecycle_counts={
            "lead": 0,
            "contracting": 0,
            "onboarding": 0,
            "go_live_ready": 0,
            "active": 1,
            "paused": 0,
            "archived": 0,
        },
        payment_counts={"pending": 0, "confirmed": 1, "rejected": 0, "unknown": 0},
        service_counts={"ok": 1, "degraded": 0, "attention": 0},
        onboarding_throughput=None,
    )


def test_request_with_query_params_rewrites_query_string() -> None:
    request = _build_request("foo=bar")

    derived = console_router._request_with_query_params(
        request,
        {"limit": 10, "cursor": None, "lifecycle": "active"},
    )

    assert dict(derived.query_params) == {"limit": "10", "lifecycle": "active"}


def test_invalidate_tenants_fleet_cache_scope_queues_company_prewarm(monkeypatch) -> None:
    company_id = uuid4()
    db = Mock()
    db.begin_nested.return_value = nullcontext()
    db.info = {}
    queued_company_ids: list[set[UUID]] = []

    monkeypatch.setattr(
        console_router,
        "_queue_fleet_summary_prewarm_company_ids",
        lambda *_args, **kwargs: queued_company_ids.append(kwargs.get("company_ids") or set()),
    )

    console_router._invalidate_tenants_fleet_cache_scope(
        db,
        reason="test_invalidate",
        company_ids={company_id},
    )

    assert queued_company_ids == [{company_id}]
    db.execute.assert_called_once()
    assert db.info[console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY] is True


def test_invalidate_tenants_fleet_cache_scope_marks_global_prewarm(monkeypatch) -> None:
    db = Mock()
    db.begin_nested.return_value = nullcontext()
    db.info = {}

    monkeypatch.setattr(console_router, "_queue_fleet_summary_prewarm_company_ids", lambda *_args, **_kwargs: None)

    console_router._invalidate_tenants_fleet_cache_scope(
        db,
        reason="test_invalidate_global",
        company_ids=None,
    )

    assert db.info[console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY] is True


def test_invalidate_tenants_fleet_cache_scope_records_incremental_event(monkeypatch) -> None:
    company_id = uuid4()
    db = Mock()
    db.begin_nested.return_value = nullcontext()
    db.info = {}

    monkeypatch.setattr(console_router, "_queue_fleet_summary_prewarm_company_ids", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_queue_fleet_global_prewarm", lambda *_args, **_kwargs: None)

    console_router._invalidate_tenants_fleet_cache_scope(
        db,
        reason="integration_reconcile.execute",
        company_ids={company_id},
    )

    assert db.info[console_router._TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY] == [
        {
            "reason": "integration_reconcile.execute",
            "company_ids": [str(company_id)],
        }
    ]


def test_on_console_session_after_commit_enqueues_company_prewarm(monkeypatch) -> None:
    company_id = uuid4()
    enqueued: list[tuple[set[UUID], bool]] = []
    session = SimpleNamespace(
        info={
            console_router._TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY: {company_id},
        }
    )

    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueued.append(
            (kwargs.get("company_ids") or set(), bool(kwargs.get("global_prewarm_required")))
        ),
    )

    console_router._on_console_session_after_commit(session)

    assert enqueued == [({company_id}, False)]
    assert console_router._TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY not in session.info


def test_on_console_session_after_commit_enqueues_from_incremental_events(monkeypatch) -> None:
    company_id = uuid4()
    enqueued: list[tuple[set[UUID], bool]] = []
    session = SimpleNamespace(
        info={
            console_router._TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY: [
                {
                    "reason": "update_client",
                    "company_ids": [str(company_id)],
                }
            ],
            console_router._TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY: {company_id},
            console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY: True,
        }
    )

    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueued.append(
            (kwargs.get("company_ids") or set(), bool(kwargs.get("global_prewarm_required")))
        ),
    )

    console_router._on_console_session_after_commit(session)

    assert enqueued == [({company_id}, True)]
    assert console_router._TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY not in session.info
    assert console_router._TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY not in session.info
    assert console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY not in session.info


def test_on_console_session_after_commit_enqueues_global_prewarm(monkeypatch) -> None:
    session = SimpleNamespace(
        info={
            console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY: True,
        }
    )
    enqueued: list[tuple[set[UUID], bool]] = []

    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch",
        lambda **kwargs: enqueued.append(
            (kwargs.get("company_ids") or set(), bool(kwargs.get("global_prewarm_required")))
        ),
    )

    console_router._on_console_session_after_commit(session)

    assert enqueued == [(set(), True)]
    assert console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY not in session.info


def test_on_console_session_after_rollback_clears_incremental_events() -> None:
    session = SimpleNamespace(
        info={
            console_router._TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY: [
                {"reason": "x", "company_ids": []}
            ],
            console_router._TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY: {uuid4()},
            console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY: True,
        }
    )

    console_router._on_console_session_after_rollback(session)

    assert session.info == {}


def test_drain_fleet_incremental_prewarm_dispatch_queue_once_schedules_coalesced_batch(monkeypatch) -> None:
    first_company_id = uuid4()
    second_company_id = uuid4()
    summary_calls: list[set[UUID]] = []
    attention_calls: list[set[UUID]] = []
    global_calls: list[bool] = []

    monkeypatch.setattr(
        console_router,
        "_claim_fleet_incremental_prewarm_dispatch_batch",
        lambda: [],
    )

    with console_router._TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
        console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.clear()
        console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.append(
            {
                "company_ids": [str(first_company_id)],
                "global_required": False,
            }
        )
        console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.append(
            {
                "company_ids": [str(second_company_id)],
                "global_required": True,
            }
        )

    monkeypatch.setattr(
        console_router,
        "_schedule_fleet_summary_prewarm_for_company_ids",
        lambda **kwargs: summary_calls.append(kwargs.get("company_ids") or set()),
    )
    monkeypatch.setattr(
        console_router,
        "_schedule_fleet_attention_prewarm_for_company_ids",
        lambda **kwargs: attention_calls.append(kwargs.get("company_ids") or set()),
    )
    monkeypatch.setattr(
        console_router,
        "_schedule_fleet_global_prewarm",
        lambda: global_calls.append(True),
    )

    drained = console_router._drain_fleet_incremental_prewarm_dispatch_queue_once()

    assert drained is True
    assert summary_calls == [{first_company_id, second_company_id}]
    assert attention_calls == [{first_company_id, second_company_id}]
    assert global_calls == [True]
    with console_router._TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
        assert not console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE


def test_enqueue_fleet_incremental_prewarm_dispatch_overflow_collapses_to_global(monkeypatch) -> None:
    first_company_id = uuid4()
    second_company_id = uuid4()

    with console_router._TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
        console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.clear()
        console_router._TENANTS_FLEET_PREWARM_DISPATCH_WORKER = None

    monkeypatch.setattr(console_router, "_TENANTS_FLEET_PREWARM_DISPATCH_QUEUE_MAX", 1)
    monkeypatch.setattr(
        console_router,
        "_enqueue_fleet_incremental_prewarm_dispatch_durable",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(console_router, "_ensure_fleet_incremental_prewarm_dispatch_worker", lambda: None)

    console_router._enqueue_fleet_incremental_prewarm_dispatch(
        company_ids={first_company_id},
        global_prewarm_required=False,
    )
    console_router._enqueue_fleet_incremental_prewarm_dispatch(
        company_ids={second_company_id},
        global_prewarm_required=False,
    )

    with console_router._TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
        assert len(console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE) == 1
        payload = console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE[0]
        assert payload["global_required"] is True
        assert payload["company_ids"] == [str(second_company_id)]
        console_router._TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.clear()
        console_router._TENANTS_FLEET_PREWARM_DISPATCH_WORKER = None


def test_enqueue_fleet_incremental_prewarm_dispatch_durable_persists_job(monkeypatch) -> None:
    company_id = uuid4()
    db = Mock()
    count_query = Mock()
    count_query.filter.return_value = count_query
    count_query.scalar.return_value = 0
    db.query.return_value = count_query
    captured_jobs: list[object] = []
    db.add.side_effect = lambda job: captured_jobs.append(job)

    monkeypatch.setattr(console_router, "SessionLocal", lambda: db)

    persisted = console_router._enqueue_fleet_incremental_prewarm_dispatch_durable(
        company_ids={company_id},
        global_prewarm_required=False,
    )

    assert persisted is True
    assert len(captured_jobs) == 1
    job = captured_jobs[0]
    assert job.company_ids == [str(company_id)]
    assert job.global_required is False
    db.commit.assert_called_once()
    db.close.assert_called_once()


def test_claim_fleet_incremental_prewarm_dispatch_batch_marks_rows_processing(monkeypatch) -> None:
    company_id = uuid4()
    job_id = uuid4()
    row = SimpleNamespace(
        id=job_id,
        company_ids=[str(company_id)],
        global_required=True,
        status=console_router._TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING,
        locked_at=None,
        updated_at=None,
        attempt_count=0,
    )
    stale_query = Mock()
    stale_query.filter.return_value = stale_query
    pending_query = Mock()
    pending_query.filter.return_value = pending_query
    pending_query.order_by.return_value = pending_query
    pending_query.with_for_update.return_value = pending_query
    pending_query.limit.return_value = pending_query
    pending_query.all.return_value = [row]
    db = Mock()
    db.query.side_effect = [stale_query, pending_query]

    monkeypatch.setattr(console_router, "SessionLocal", lambda: db)

    batch = console_router._claim_fleet_incremental_prewarm_dispatch_batch()

    assert batch == [
        {
            "job_id": str(job_id),
            "company_ids": [str(company_id)],
            "global_required": True,
        }
    ]
    assert row.status == console_router._TENANTS_FLEET_PREWARM_JOB_STATUS_PROCESSING
    assert row.attempt_count == 1
    db.commit.assert_called()
    db.close.assert_called_once()


def test_drain_fleet_incremental_prewarm_dispatch_queue_once_marks_retry_on_scheduler_error(monkeypatch) -> None:
    company_id = uuid4()
    job_id = uuid4()
    retry_calls: list[tuple[set[UUID], str]] = []
    completed_calls: list[set[UUID]] = []

    monkeypatch.setattr(
        console_router,
        "_claim_fleet_incremental_prewarm_dispatch_batch",
        lambda: [
            {
                "job_id": str(job_id),
                "company_ids": [str(company_id)],
                "global_required": False,
            }
        ],
    )
    monkeypatch.setattr(
        console_router,
        "_schedule_fleet_summary_prewarm_for_company_ids",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        console_router,
        "_mark_fleet_incremental_prewarm_dispatch_jobs_completed",
        lambda job_ids: completed_calls.append(job_ids),
    )
    monkeypatch.setattr(
        console_router,
        "_mark_fleet_incremental_prewarm_dispatch_jobs_retry",
        lambda job_ids, error_message: retry_calls.append((job_ids, error_message)),
    )

    drained = console_router._drain_fleet_incremental_prewarm_dispatch_queue_once()

    assert drained is True
    assert completed_calls == []
    assert retry_calls
    assert retry_calls[0][0] == {job_id}
    assert "boom" in retry_calls[0][1]


def test_schedule_fleet_summary_prewarm_for_company_ids_starts_refresh_task(monkeypatch) -> None:
    company_id = uuid4()
    first_client_id = uuid4()
    second_client_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.all.return_value = [
        (first_client_id, company_id),
        (second_client_id, company_id),
    ]
    started_tasks: list[dict[str, object]] = []

    monkeypatch.setattr(console_router, "SessionLocal", lambda: db)
    monkeypatch.setattr(console_router, "_try_claim_fleet_cache_refresh", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        console_router,
        "_start_fleet_summary_refresh_task",
        lambda **kwargs: started_tasks.append(kwargs),
    )

    console_router._schedule_fleet_summary_prewarm_for_company_ids(company_ids={company_id})

    assert len(started_tasks) == 1
    task_payload = started_tasks[0]["task"]
    assert task_payload["company_id"] == str(company_id)
    assert task_payload["lifecycle_mode"] == "active"
    assert set(task_payload["accessible_client_ids"]) == {str(first_client_id), str(second_client_id)}
    db.close.assert_called_once()


def test_schedule_fleet_attention_prewarm_for_company_ids_starts_refresh_task(monkeypatch) -> None:
    company_id = uuid4()
    first_client_id = uuid4()
    second_client_id = uuid4()
    db = Mock()
    db.query.return_value.filter.return_value.all.return_value = [
        (first_client_id, company_id),
        (second_client_id, company_id),
    ]
    started_tasks: list[dict[str, object]] = []

    monkeypatch.setattr(console_router, "SessionLocal", lambda: db)
    monkeypatch.setattr(console_router, "_try_claim_fleet_cache_refresh", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        console_router,
        "_start_fleet_attention_refresh_task",
        lambda **kwargs: started_tasks.append(kwargs),
    )

    console_router._schedule_fleet_attention_prewarm_for_company_ids(company_ids={company_id})

    assert len(started_tasks) == 1
    task_payload = started_tasks[0]["task"]
    assert set(task_payload["active_client_ids"]) == {str(first_client_id), str(second_client_id)}
    assert task_payload["stale_after_minutes"] == console_router._INTEGRATION_DEFAULT_STALE_MINUTES
    assert task_payload["limit"] == console_router._TENANTS_FLEET_CACHE_PREWARM_COMPANY_ATTENTION_LIMIT
    db.close.assert_called_once()


def test_schedule_fleet_global_prewarm_starts_summary_and_attention_tasks(monkeypatch) -> None:
    first_client_id = uuid4()
    second_client_id = uuid4()
    summary_tasks: list[dict[str, object]] = []
    attention_tasks: list[dict[str, object]] = []

    monkeypatch.setattr(
        console_router,
        "_reserve_fleet_global_prewarm_slot",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        console_router,
        "_load_global_active_client_ids",
        lambda **_kwargs: ({first_client_id, second_client_id}, False),
    )
    monkeypatch.setattr(
        console_router,
        "_try_claim_fleet_cache_refresh",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        console_router,
        "_start_fleet_summary_refresh_task",
        lambda **kwargs: summary_tasks.append(kwargs),
    )
    monkeypatch.setattr(
        console_router,
        "_start_fleet_attention_refresh_task",
        lambda **kwargs: attention_tasks.append(kwargs),
    )

    console_router._schedule_fleet_global_prewarm()

    assert len(summary_tasks) == 1
    assert len(attention_tasks) == 1
    summary_payload = summary_tasks[0]["task"]
    attention_payload = attention_tasks[0]["task"]
    assert set(summary_payload["accessible_client_ids"]) == {str(first_client_id), str(second_client_id)}
    assert set(attention_payload["active_client_ids"]) == {str(first_client_id), str(second_client_id)}
    assert attention_payload["limit"] == console_router._TENANTS_FLEET_CACHE_PREWARM_GLOBAL_ATTENTION_LIMIT


def test_schedule_fleet_global_prewarm_overflow_enqueues_projection_scope_prewarm(monkeypatch) -> None:
    first_client_id = uuid4()
    second_client_id = uuid4()
    fallback_calls: list[set[UUID]] = []
    summary_tasks: list[dict[str, object]] = []
    attention_tasks: list[dict[str, object]] = []

    monkeypatch.setattr(
        console_router,
        "_reserve_fleet_global_prewarm_slot",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        console_router,
        "_load_global_active_client_ids",
        lambda **_kwargs: ({first_client_id, second_client_id}, True),
    )
    monkeypatch.setattr(
        console_router,
        "_maybe_enqueue_projection_fallback_prewarm_for_client_ids",
        lambda **kwargs: fallback_calls.append(kwargs.get("client_ids") or set()),
    )
    monkeypatch.setattr(
        console_router,
        "_start_fleet_summary_refresh_task",
        lambda **kwargs: summary_tasks.append(kwargs),
    )
    monkeypatch.setattr(
        console_router,
        "_start_fleet_attention_refresh_task",
        lambda **kwargs: attention_tasks.append(kwargs),
    )

    console_router._schedule_fleet_global_prewarm()

    assert fallback_calls == [{first_client_id, second_client_id}]
    assert summary_tasks == []
    assert attention_tasks == []


def test_schedule_fleet_global_prewarm_skips_when_overflow_without_clients(monkeypatch) -> None:
    fallback_calls: list[set[UUID]] = []

    monkeypatch.setattr(
        console_router,
        "_reserve_fleet_global_prewarm_slot",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        console_router,
        "_load_global_active_client_ids",
        lambda **_kwargs: (set(), True),
    )
    monkeypatch.setattr(
        console_router,
        "_maybe_enqueue_projection_fallback_prewarm_for_client_ids",
        lambda **kwargs: fallback_calls.append(kwargs.get("client_ids") or set()),
    )

    console_router._schedule_fleet_global_prewarm()

    assert fallback_calls == []


@pytest.mark.asyncio
async def test_list_clients_uses_cached_summary_when_available(monkeypatch) -> None:
    cached_summary = _build_fleet_summary()
    db = Mock()
    db.query.return_value = _build_list_query_mock()
    build_summary_mock = Mock(side_effect=AssertionError("summary builder must not be called on cache hit"))
    store_summary_mock = Mock(side_effect=AssertionError("summary cache write must not happen on cache hit"))

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="platform_admin",
            accessible_clients=[],
            client=None,
        ),
    )
    monkeypatch.setattr(console_router, "_load_cached_fleet_summary", lambda *_, **__: cached_summary)
    monkeypatch.setattr(console_router, "_build_fleet_summary_for_scope", build_summary_mock)
    monkeypatch.setattr(console_router, "_store_cached_fleet_summary", store_summary_mock)

    response = await console_router.list_clients(
        request=_build_request(),
        include_summary="true",
        db=db,
    )

    assert response.summary == cached_summary
    assert build_summary_mock.call_count == 0
    assert store_summary_mock.call_count == 0


@pytest.mark.asyncio
async def test_list_clients_stores_summary_in_cache_after_miss(monkeypatch) -> None:
    computed_summary = _build_fleet_summary()
    db = Mock()
    db.query.return_value = _build_list_query_mock()
    store_calls: list[dict[str, object]] = []
    build_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="platform_admin",
            accessible_clients=[],
            client=None,
        ),
    )
    monkeypatch.setattr(console_router, "_load_cached_fleet_summary", lambda *_, **__: None)
    monkeypatch.setattr(
        console_router,
        "_build_fleet_summary_for_scope",
        lambda *_, **kwargs: build_calls.append(kwargs) or computed_summary,
    )
    monkeypatch.setattr(
        console_router,
        "_store_cached_fleet_summary",
        lambda *_, **kwargs: store_calls.append(kwargs),
    )

    response = await console_router.list_clients(
        request=_build_request(),
        include_summary="true",
        db=db,
    )

    assert response.summary == computed_summary
    assert len(build_calls) == 1
    assert build_calls[0]["persist_projection_missing"] is True
    assert build_calls[0]["persist_projection_missing_max_clients"] == (
        console_router._TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS
    )
    assert len(store_calls) == 1
    assert store_calls[0]["summary"] == computed_summary


@pytest.mark.asyncio
async def test_list_clients_cache_hit_schedules_async_refresh(monkeypatch) -> None:
    cached_summary = _build_fleet_summary()
    accessible_client_id = uuid4()
    db = Mock()
    db.query.return_value = _build_list_query_mock()
    schedule_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=accessible_client_id, status="active", company_id=None)],
            client=None,
        ),
    )
    monkeypatch.setattr(console_router, "_load_cached_fleet_summary", lambda *_, **__: cached_summary)
    monkeypatch.setattr(
        console_router,
        "_build_fleet_summary_for_scope",
        lambda *_, **__: (_ for _ in ()).throw(AssertionError("cache hit should not rebuild summary in request path")),
    )
    monkeypatch.setattr(
        console_router,
        "_store_cached_fleet_summary",
        lambda *_, **__: (_ for _ in ()).throw(AssertionError("cache hit should not write summary in request path")),
    )
    monkeypatch.setattr(
        console_router,
        "_schedule_fleet_summary_async_refresh",
        lambda *_, **kwargs: schedule_calls.append(kwargs),
    )

    response = await console_router.list_clients(
        request=_build_request(),
        include_summary="true",
        db=db,
    )

    assert response.summary == cached_summary
    assert len(schedule_calls) == 1
    assert schedule_calls[0]["accessible_client_ids"] == {accessible_client_id}


@pytest.mark.asyncio
async def test_list_fleet_attention_returns_cached_response(monkeypatch) -> None:
    cached_response = console_router.ConsoleFleetAttentionResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        stale_after_minutes=120,
        summary=console_router.ConsoleFleetAttentionSummary(
            active_clients_total=1,
            clients_with_attention=1,
            high_risk_clients=1,
            medium_risk_clients=0,
            low_risk_clients=0,
            stale_branches_total=1,
            integration_error_branches_total=1,
            integration_warn_branches_total=0,
            outbox_failed_24h_total=2,
            pending_handovers_total=1,
        ),
        items=[
            console_router.ConsoleFleetAttentionItem(
                client_id=uuid4(),
                client_slug="cached-client",
                client_name="Cached Client",
                company_id=None,
                company_name=None,
                lifecycle_state="active",
                payment_status="confirmed",
                commercial_state="payment_confirmed",
                service_state="degraded",
                owner_name="Owner",
                next_action="run_integration_recovery",
                total_branches=2,
                active_branches=2,
                degraded_branches=1,
                go_live_ready_branches=2,
                reference_branch_ids=[],
                reference_branch_reason="scored",
                stale_branches=1,
                integration_error_branches=1,
                integration_warn_branches=0,
                outbox_failed_24h=2,
                pending_handovers=1,
                attention_score=80,
                attention_level="high",
                reasons=["integration_error"],
                suggested_actions=["open_integrations_registry_and_fix_bindings"],
            )
        ],
    )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=uuid4(), status="active", company_id=None)],
            companies=[],
            client=None,
        ),
    )
    monkeypatch.setattr(console_router, "_load_cached_fleet_attention", lambda *_, **__: cached_response)
    monkeypatch.setattr(
        console_router,
        "_build_fleet_attention_response_for_clients",
        lambda *_, **__: (_ for _ in ()).throw(AssertionError("cache hit should short-circuit heavy path")),
    )

    response = await console_router.list_fleet_attention(
        request=_build_request(),
        stale_after_minutes=120,
        db=Mock(),
    )

    assert response == cached_response


@pytest.mark.asyncio
async def test_list_fleet_attention_cache_hit_schedules_async_refresh(monkeypatch) -> None:
    active_client_id = uuid4()
    cached_response = console_router.ConsoleFleetAttentionResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        stale_after_minutes=120,
        summary=console_router.ConsoleFleetAttentionSummary(
            active_clients_total=1,
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
    schedule_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=active_client_id, status="active", company_id=None)],
            companies=[],
            client=None,
        ),
    )
    monkeypatch.setattr(console_router, "_load_cached_fleet_attention", lambda *_, **__: cached_response)
    monkeypatch.setattr(
        console_router,
        "_schedule_fleet_attention_async_refresh",
        lambda *_, **kwargs: schedule_calls.append(kwargs),
    )

    response = await console_router.list_fleet_attention(
        request=_build_request(),
        stale_after_minutes=120,
        db=Mock(),
    )

    assert response == cached_response
    assert len(schedule_calls) == 1
    assert schedule_calls[0]["active_client_ids"] == {active_client_id}
    assert schedule_calls[0]["limit"] == 20


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
async def test_get_tenants_company_cockpit_skips_branches_when_not_requested(monkeypatch) -> None:
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
    captured: dict[str, dict[str, object]] = {}
    latency_calls: list[tuple[str, float | None]] = []

    async def _fake_list_clients(**kwargs):
        captured["clients"] = kwargs
        return clients_response

    async def _fake_list_branches(**kwargs):  # pragma: no cover - must not be called
        raise AssertionError("list_branches should not be called when include_branches=false")

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
        client_id=str(selected_client_id),
        include_branches="false",
        lifecycle="active",
        db=Mock(),
    )

    assert response.selected_client_id == selected_client_id
    assert response.clients == clients_response
    assert response.branches.items == []
    assert response.branches.cursor is None
    assert response.branches.has_more is False
    assert "clients" in captured
    assert latency_calls
    assert latency_calls[0][0] == "company_cockpit"


@pytest.mark.asyncio
async def test_get_tenants_company_cockpit_passes_large_scope_pagination_contract(monkeypatch) -> None:
    company_id = uuid4()
    selected_client_id = uuid4()
    client_cursor = "2026-02-23T00:00:00+00:00"
    branch_cursor = "2026-02-22T00:00:00+00:00"
    clients_response = console_router.ConsoleClientListResponse(items=[], cursor="client-next", has_more=True, summary=None)
    branches_response = console_router.ConsoleBranchListResponse(items=[], cursor="branch-next", has_more=True)
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
        lifecycle="all",
        client_limit=100,
        branch_limit=100,
        client_cursor=client_cursor,
        branch_cursor=branch_cursor,
        client_q="enterprise",
        branch_q="regional",
        db=Mock(),
    )

    assert response.company_id == company_id
    assert response.selected_client_id == selected_client_id
    assert captured["clients"]["limit"] == 100
    assert captured["clients"]["cursor"] == client_cursor
    assert captured["clients"]["q"] == "enterprise"
    assert captured["clients"]["include_fleet"] == "true"
    assert captured["clients"]["lifecycle"] == "all"
    assert captured["branches"]["limit"] == 100
    assert captured["branches"]["cursor"] == branch_cursor
    assert captured["branches"]["q"] == "regional"
    assert captured["branches"]["company_id"] == str(company_id)
    assert captured["branches"]["client_id"] == str(selected_client_id)
    assert captured["branches"]["lifecycle"] == "all"


@pytest.mark.asyncio
@pytest.mark.parametrize(("client_limit", "branch_limit"), [(101, 20), (20, 101)])
async def test_get_tenants_company_cockpit_rejects_oversized_limits_before_subqueries(
    monkeypatch,
    client_limit: int,
    branch_limit: int,
) -> None:
    called = {"clients": 0, "branches": 0}

    async def _fake_list_clients(**_kwargs):
        called["clients"] += 1
        return console_router.ConsoleClientListResponse(items=[], cursor=None, has_more=False, summary=None)

    async def _fake_list_branches(**_kwargs):
        called["branches"] += 1
        return console_router.ConsoleBranchListResponse(items=[], cursor=None, has_more=False)

    monkeypatch.setattr(console_router, "list_clients", _fake_list_clients)
    monkeypatch.setattr(console_router, "list_branches", _fake_list_branches)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_tenants_company_cockpit(
            request=_build_request(),
            company_id=str(uuid4()),
            client_limit=client_limit,
            branch_limit=branch_limit,
            db=Mock(),
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert called == {"clients": 0, "branches": 0}


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
        "_load_or_build_fleet_client_details_map",
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
    captured_load_calls: list[dict[str, object]] = []

    def _details_map(_db, *, clients, **_kwargs):
        captured_load_calls.append(_kwargs)
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

    monkeypatch.setattr(console_router, "_load_or_build_fleet_client_details_map", _details_map)

    response = await console_router.list_clients(
        request=request,
        payment_status="confirmed",
        db=db,
    )

    assert len(response.items) == 1
    assert response.items[0].id == client_a.id
    assert response.items[0].payment_status == "confirmed"
    assert len(captured_load_calls) >= 1
    assert captured_load_calls[0]["persist_missing"] is True
    assert captured_load_calls[0]["persist_missing_max_clients"] == (
        console_router._TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS
    )


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
    filters = _collect_filter_predicates(query)
    assert "clients.status = :status_1" in filters
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
    filters = _collect_filter_predicates(query)
    assert "branches.is_active IS false" in filters


@pytest.mark.asyncio
async def test_list_branches_company_scope_filters_on_clients_company_id(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={})
    company_id = uuid4()
    scoped_client_id = uuid4()

    def _fake_context(_request, _db, **_kwargs):
        return SimpleNamespace(
            role="platform_admin",
            client=None,
            accessible_clients=[SimpleNamespace(id=scoped_client_id, company_id=company_id)],
        )

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        company_id=str(company_id),
        db=db,
    )

    filters = _collect_filter_predicates(query)
    assert "clients.company_id = :company_id_1" in filters
    assert "clients.status = :status_1" in filters
    assert "branches.is_active IS true" in filters


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
    branch_lookup_query.join.return_value = branch_lookup_query
    branch_lookup_query.filter.return_value = branch_lookup_query
    branch_lookup_query.first.return_value = SimpleNamespace(
        id=branch_id,
        client_id=client_id,
        company_id=uuid4(),
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

    filters = _collect_filter_predicates(query)
    assert any("branches.id =" in item for item in filters)


@pytest.mark.asyncio
async def test_list_branches_rejects_branch_from_other_client(monkeypatch) -> None:
    branch_id = uuid4()
    selected_client_id = uuid4()
    foreign_client_id = uuid4()
    query = _build_list_query_mock()
    branch_lookup_query = Mock()
    branch_lookup_query.join.return_value = branch_lookup_query
    branch_lookup_query.filter.return_value = branch_lookup_query
    branch_lookup_query.first.return_value = SimpleNamespace(
        id=branch_id,
        client_id=foreign_client_id,
        company_id=uuid4(),
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
    branch_lookup_query.join.return_value = branch_lookup_query
    branch_lookup_query.filter.return_value = branch_lookup_query
    branch_lookup_query.first.return_value = SimpleNamespace(
        id=branch_id,
        client_id=foreign_client_id,
        company_id=foreign_company_id,
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
