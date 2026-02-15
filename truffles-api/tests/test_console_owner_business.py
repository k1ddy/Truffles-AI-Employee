from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleSettingsUpdateRequest
from app.services.console_errors import ConsoleAPIError


def _build_context(*, role: str, company_billing: dict | None = None, client_config: dict | None = None):
    company_id = uuid4()
    client_id = uuid4()
    return SimpleNamespace(
        role=role,
        client=SimpleNamespace(
            id=client_id,
            company_id=company_id,
            config=client_config or {},
        ),
        companies=[
            SimpleNamespace(
                id=company_id,
                billing_info=company_billing or {},
            )
        ],
    )


def test_resolve_subscription_contract_prefers_company_billing_info() -> None:
    context = _build_context(
        role="owner",
        company_billing={
            "plan_name": "Starter",
            "contract": "starter-2026",
            "currency": "kzt",
            "monthly_quota": 1200,
        },
        client_config={
            "billing": {
                "plan_name": "Legacy",
                "monthly_quota": 800,
            }
        },
    )

    plan_name, contract_label, currency, quota, source = console_router._resolve_subscription_contract_info(context)

    assert plan_name == "Starter"
    assert contract_label == "starter-2026"
    assert currency == "KZT"
    assert quota == 1200
    assert source == "company_billing_info"


def test_resolve_subscription_contract_falls_back_to_client_config() -> None:
    context = _build_context(
        role="owner",
        company_billing={},
        client_config={
            "billing": {
                "plan": "Pro",
                "contract_label": "pro-annual",
                "currency": "usd",
                "subscription": {
                    "message_quota": 5000,
                },
            }
        },
    )

    plan_name, contract_label, currency, quota, source = console_router._resolve_subscription_contract_info(context)

    assert plan_name == "Pro"
    assert contract_label == "pro-annual"
    assert currency == "USD"
    assert quota == 5000
    assert source == "client_config"


def test_derive_business_status_thresholds() -> None:
    unhealthy_status, _ = console_router._derive_business_status(
        outbox_backlog=1200,
        outbox_failed_24h=10,
        unresolved_cases=5,
    )
    degraded_status, _ = console_router._derive_business_status(
        outbox_backlog=600,
        outbox_failed_24h=10,
        unresolved_cases=5,
    )
    healthy_status, _ = console_router._derive_business_status(
        outbox_backlog=50,
        outbox_failed_24h=2,
        unresolved_cases=3,
    )

    assert unhealthy_status == "unhealthy"
    assert degraded_status == "degraded"
    assert healthy_status == "healthy"


def test_derive_data_trust_status_thresholds() -> None:
    unhealthy_status, _ = console_router._derive_data_trust_status(
        first_response_missing_total=30,
        escalation_meta_missing_total=20,
        intent_missing_total=10,
        knowledge_stale_hours=200,
        critical_audit_events_24h=0,
        analytics_scope_limited=False,
    )
    degraded_status, _ = console_router._derive_data_trust_status(
        first_response_missing_total=5,
        escalation_meta_missing_total=0,
        intent_missing_total=0,
        knowledge_stale_hours=80,
        critical_audit_events_24h=1,
        analytics_scope_limited=False,
    )
    healthy_status, _ = console_router._derive_data_trust_status(
        first_response_missing_total=0,
        escalation_meta_missing_total=0,
        intent_missing_total=0,
        knowledge_stale_hours=12,
        critical_audit_events_24h=0,
        analytics_scope_limited=False,
    )

    assert unhealthy_status == "unhealthy"
    assert degraded_status == "degraded"
    assert healthy_status == "healthy"


def test_derive_team_performance_status_thresholds() -> None:
    unhealthy_status, _ = console_router._derive_team_performance_status(
        unresolved_cases=45,
        unresolved_older_than_60m=21,
        manager_median_response_seconds=1000.0,
    )
    degraded_status, _ = console_router._derive_team_performance_status(
        unresolved_cases=18,
        unresolved_older_than_60m=6,
        manager_median_response_seconds=700.0,
    )
    healthy_status, _ = console_router._derive_team_performance_status(
        unresolved_cases=3,
        unresolved_older_than_60m=0,
        manager_median_response_seconds=220.0,
    )

    assert unhealthy_status == "unhealthy"
    assert degraded_status == "degraded"
    assert healthy_status == "healthy"


def test_apply_console_settings_update_maps_public_fields_to_model_columns() -> None:
    settings = SimpleNamespace(
        reminder_timeout_1=30,
        reminder_timeout_2=60,
        auto_close_timeout=120,
    )
    body = ConsoleSettingsUpdateRequest(
        reminder_1_minutes=10,
        reminder_2_minutes=45,
        escalation_timeout_minutes=90,
    )

    updated_fields = console_router._apply_console_settings_update(settings, body)

    assert settings.reminder_timeout_1 == 10
    assert settings.reminder_timeout_2 == 45
    assert settings.auto_close_timeout == 90
    assert updated_fields == [
        "reminder_timeout_1",
        "reminder_timeout_2",
        "auto_close_timeout",
    ]


def test_validate_console_settings_update_rejects_invalid_order() -> None:
    body = ConsoleSettingsUpdateRequest(
        reminder_1_minutes=30,
        reminder_2_minutes=20,
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._validate_console_settings_update(body)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_INPUT"


def test_validate_console_settings_update_rejects_invalid_range() -> None:
    body = ConsoleSettingsUpdateRequest(
        reminder_1_minutes=2,
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._validate_console_settings_update(body)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_business_summary_requires_business_permission(monkeypatch):
    context = _build_context(role="manager")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_business_summary(request=SimpleNamespace(), db=SimpleNamespace())

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_subscription_summary_requires_subscription_permission(monkeypatch):
    context = _build_context(role="support")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_subscription_summary(request=SimpleNamespace(), db=SimpleNamespace())

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_data_trust_summary_requires_business_permission(monkeypatch):
    context = _build_context(role="manager")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_business_data_trust(request=SimpleNamespace(), db=SimpleNamespace())

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_team_performance_summary_requires_business_permission(monkeypatch):
    context = _build_context(role="support")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_business_team_performance(request=SimpleNamespace(), db=SimpleNamespace())

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"
