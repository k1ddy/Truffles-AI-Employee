from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


class _QueryMock:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


def test_resolve_fleet_attention_profile_high_score() -> None:
    score, level, reasons, actions = console_router._resolve_fleet_attention_profile(
        service_state="attention",
        stale_branches=1,
        integration_error_branches=1,
        integration_warn_branches=0,
        outbox_failed_24h=6,
        pending_handovers=1,
    )

    assert score >= console_router._FLEET_ATTENTION_HIGH_THRESHOLD
    assert level == "high"
    assert "integration_error" in reasons
    assert "outbox_failed" in reasons
    assert "open_integrations_registry_and_fix_bindings" in actions


@pytest.mark.asyncio
async def test_list_fleet_attention_filters_low_by_default(monkeypatch) -> None:
    client_a_id = uuid4()
    client_b_id = uuid4()
    company_id = uuid4()
    now_branch_a = uuid4()
    now_branch_b = uuid4()

    client_a = SimpleNamespace(id=client_a_id, name="alpha", status="active", company_id=company_id)
    client_b = SimpleNamespace(id=client_b_id, name="beta", status="active", company_id=company_id)
    context = SimpleNamespace(
        role="platform_admin",
        accessible_clients=[client_a, client_b],
        companies=[SimpleNamespace(id=company_id, name="Acme")],
    )

    branches = [
        SimpleNamespace(
            id=now_branch_a,
            client_id=client_a_id,
            is_active=True,
            instance_id="a-1",
            telegram_chat_id="100",
            webhook_secret="secret-a",
            integration_state="ok",
            integration_reason=None,
            integration_checked_at=None,
            integration_degraded_at=None,
            integration_recovered_at=None,
            slug="alpha-main",
            name="Alpha Main",
        ),
        SimpleNamespace(
            id=now_branch_b,
            client_id=client_b_id,
            is_active=True,
            instance_id="b-1",
            telegram_chat_id="200",
            webhook_secret="secret-b",
            integration_state="ok",
            integration_reason=None,
            integration_checked_at=None,
            integration_degraded_at=None,
            integration_recovered_at=None,
            slug="beta-main",
            name="Beta Main",
        ),
    ]

    db = Mock()

    def _query_side_effect(*entities):
        if len(entities) == 1 and entities[0] is console_router.Branch:
            return _QueryMock(branches)
        if len(entities) == 2:
            return _QueryMock([(client_a_id, "token-a"), (client_b_id, "token-b")])
        raise AssertionError(f"unexpected query entities: {entities}")

    db.query.side_effect = _query_side_effect

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: {
            client_a_id: console_router._FleetClientDetails(
                lifecycle_state="active",
                payment_status="confirmed",
                commercial_state="payment_confirmed",
                service_state="attention",
                owner_name="Owner A",
                next_action="resolve_attention_items",
                total_branches=1,
                active_branches=1,
                degraded_branches=0,
                go_live_ready_branches=1,
            ),
            client_b_id: console_router._FleetClientDetails(
                lifecycle_state="active",
                payment_status="confirmed",
                commercial_state="payment_confirmed",
                service_state="ok",
                owner_name="Owner B",
                next_action="monitor_sla_and_quality",
                total_branches=1,
                active_branches=1,
                degraded_branches=0,
                go_live_ready_branches=1,
            ),
        },
    )
    monkeypatch.setattr(
        console_router,
        "_load_latest_branch_inbound_observations_for_clients",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        console_router,
        "_query_outbox_failed_24h_map",
        lambda *_args, **_kwargs: {client_a_id: 6, client_b_id: 0},
    )
    monkeypatch.setattr(
        console_router,
        "_query_pending_handovers_map",
        lambda *_args, **_kwargs: {client_a_id: 1, client_b_id: 0},
    )

    status_by_branch = {
        now_branch_a: SimpleNamespace(whatsapp_status="no_recent_inbound", status="error"),
        now_branch_b: SimpleNamespace(whatsapp_status="ok", status="ok"),
    }
    monkeypatch.setattr(
        console_router,
        "_build_branch_integration_status",
        lambda **kwargs: status_by_branch[kwargs["branch"].id],
    )

    request = SimpleNamespace(query_params={})
    response = await console_router.list_fleet_attention(
        request=request,
        db=db,
    )

    assert response.summary.active_clients_total == 2
    assert response.summary.clients_with_attention == 1
    assert len(response.items) == 1
    assert response.items[0].client_id == client_a_id
    assert response.items[0].attention_level == "high"
    assert "integration_error" in response.items[0].reasons


@pytest.mark.asyncio
async def test_list_fleet_attention_include_low(monkeypatch) -> None:
    client_id = uuid4()
    company_id = uuid4()
    branch_id = uuid4()
    context = SimpleNamespace(
        role="platform_admin",
        accessible_clients=[SimpleNamespace(id=client_id, name="alpha", status="active", company_id=company_id)],
        companies=[SimpleNamespace(id=company_id, name="Acme")],
    )
    db = Mock()

    def _query_side_effect(*entities):
        if len(entities) == 1 and entities[0] is console_router.Branch:
            return _QueryMock(
                [
                    SimpleNamespace(
                        id=branch_id,
                        client_id=client_id,
                        is_active=True,
                        instance_id="a-1",
                        telegram_chat_id="100",
                        webhook_secret="secret-a",
                        integration_state="ok",
                        integration_reason=None,
                        integration_checked_at=None,
                        integration_degraded_at=None,
                        integration_recovered_at=None,
                        slug="alpha-main",
                        name="Alpha Main",
                    )
                ]
            )
        if len(entities) == 2:
            return _QueryMock([(client_id, "token-a")])
        raise AssertionError(f"unexpected query entities: {entities}")

    db.query.side_effect = _query_side_effect

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_fleet_client_details_map",
        lambda *_args, **_kwargs: {
            client_id: console_router._FleetClientDetails(
                lifecycle_state="active",
                payment_status="confirmed",
                commercial_state="payment_confirmed",
                service_state="ok",
                owner_name="Owner A",
                next_action="monitor_sla_and_quality",
                total_branches=1,
                active_branches=1,
                degraded_branches=0,
                go_live_ready_branches=1,
            )
        },
    )
    monkeypatch.setattr(
        console_router,
        "_load_latest_branch_inbound_observations_for_clients",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(console_router, "_query_outbox_failed_24h_map", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(console_router, "_query_pending_handovers_map", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        console_router,
        "_build_branch_integration_status",
        lambda **_kwargs: SimpleNamespace(whatsapp_status="ok", status="ok"),
    )

    request = SimpleNamespace(query_params={"include_low": "true"})
    response = await console_router.list_fleet_attention(
        request=request,
        include_low="true",
        db=db,
    )

    assert response.summary.active_clients_total == 1
    assert len(response.items) == 1
    assert response.items[0].attention_level == "low"


@pytest.mark.asyncio
async def test_list_fleet_attention_requires_platform_admin(monkeypatch) -> None:
    request = SimpleNamespace(query_params={})
    db = Mock()

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: SimpleNamespace(role="owner", accessible_clients=[]),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_fleet_attention(request=request, db=db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"
