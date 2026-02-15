from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routers import console as console_router
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
