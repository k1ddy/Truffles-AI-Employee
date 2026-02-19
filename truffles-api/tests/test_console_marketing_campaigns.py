from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI

from app.models.marketing_campaign import MarketingCampaign
from app.models.marketing_campaign_delivery import MarketingCampaignDelivery
from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


def test_marketing_routes_registered_in_openapi() -> None:
    app = FastAPI()
    app.include_router(console_router.router)
    paths = app.openapi()["paths"]

    assert "/console/v1/admin/marketing/campaigns" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/preview" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/execute" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/diagnostics" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/retry-failed" in paths


def test_require_marketing_access_denies_manager() -> None:
    context = SimpleNamespace(role="manager")
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._require_marketing_access(context, action="create")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


def test_normalize_marketing_sample_limit() -> None:
    assert console_router._normalize_marketing_sample_limit(None) == 5
    assert console_router._normalize_marketing_sample_limit(10) == 10

    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_sample_limit(0)
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_sample_limit(21)


def test_normalize_marketing_max_recipients() -> None:
    assert console_router._normalize_marketing_max_recipients(None) is None
    assert console_router._normalize_marketing_max_recipients(100) == 100

    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_max_recipients(0)
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_max_recipients(501)


def test_normalize_marketing_retry_limit() -> None:
    assert console_router._normalize_marketing_retry_limit(None) == 100
    assert console_router._normalize_marketing_retry_limit(250) == 250

    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_retry_limit(0)
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_retry_limit(501)


def test_effective_marketing_delivery_status_prefers_replied_then_outbox() -> None:
    assert (
        console_router._effective_marketing_delivery_status(
            delivery_status="replied",
            outbox_status="FAILED",
        )
        == "replied"
    )
    assert (
        console_router._effective_marketing_delivery_status(
            delivery_status="queued",
            outbox_status="SENT",
        )
        == "sent"
    )
    assert (
        console_router._effective_marketing_delivery_status(
            delivery_status="queued",
            outbox_status="FAILED",
        )
        == "failed"
    )
    assert (
        console_router._effective_marketing_delivery_status(
            delivery_status="queued",
            outbox_status="PROCESSING",
        )
        == "queued"
    )


def test_serialize_marketing_campaign_includes_dates() -> None:
    now = datetime.now(timezone.utc)
    campaign = MarketingCampaign(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        created_by=uuid4(),
        name="Spring Reactivation",
        message_text="Возвращайтесь, для вас есть окно на этой неделе.",
        status="ready",
        audience_mode="branch_active_conversations",
        audience_filter={},
        preview_total=42,
        last_preview_at=now,
        executed_at=None,
        created_at=now,
        updated_at=now,
    )

    serialized = console_router._serialize_marketing_campaign(campaign)
    assert serialized.name == "Spring Reactivation"
    assert serialized.preview_total == 42
    assert serialized.last_preview_at is not None
    assert serialized.created_at is not None


def test_serialize_marketing_delivery_sample_includes_error_and_outbox() -> None:
    now = datetime.now(timezone.utc)
    delivery = MarketingCampaignDelivery(
        id=uuid4(),
        campaign_id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        conversation_id=uuid4(),
        user_id=uuid4(),
        recipient_jid="77000000000@s.whatsapp.net",
        status="queued",
        outbox_id=uuid4(),
        error_reason="provider timeout",
        created_at=now,
        updated_at=now,
    )

    serialized = console_router._serialize_marketing_delivery_sample(
        delivery,
        status="failed",
        outbox_status="FAILED",
        last_error="provider timeout",
    )
    assert serialized.status == "failed"
    assert serialized.outbox_status == "FAILED"
    assert serialized.last_error == "provider timeout"
