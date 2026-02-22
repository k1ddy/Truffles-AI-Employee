from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI

from app.models.marketing_campaign import MarketingCampaign
from app.models.marketing_campaign_delivery import MarketingCampaignDelivery
from app.models.marketing_campaign_recipient import MarketingCampaignRecipient
from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError
from app.services.marketing import (
    MARKETING_STATUS_APPROVED,
    MARKETING_STATUS_DRAFT,
    MARKETING_STATUS_IN_REVIEW,
    check_marketing_transition,
)


def test_marketing_routes_registered_in_openapi() -> None:
    app = FastAPI()
    app.include_router(console_router.router)
    paths = app.openapi()["paths"]

    assert "/console/v1/admin/marketing/campaigns" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/preview" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/audience" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/request-approval" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/approve" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/preflight" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/pause" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/resume" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/execute" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/diagnostics" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/retry-failed" in paths
    assert "patch" in paths["/console/v1/admin/marketing/campaigns/{campaign_id}"]


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


def test_normalize_marketing_audience_limit() -> None:
    assert console_router._normalize_marketing_audience_limit(None) == 100
    assert console_router._normalize_marketing_audience_limit(250) == 250

    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_audience_limit(0)
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_marketing_audience_limit(501)


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


def test_check_marketing_transition_rules() -> None:
    assert check_marketing_transition(MARKETING_STATUS_DRAFT, MARKETING_STATUS_IN_REVIEW) is True
    assert check_marketing_transition(MARKETING_STATUS_IN_REVIEW, MARKETING_STATUS_APPROVED) is True
    assert check_marketing_transition(MARKETING_STATUS_APPROVED, MARKETING_STATUS_IN_REVIEW) is False


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
        segment_code=None,
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
    assert serialized.status == "approved"
    assert serialized.status_v2 == "approved"
    assert serialized.segment_code == "reactivation_30_120"
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


def test_serialize_marketing_recipient_fallback_segment() -> None:
    now = datetime.now(timezone.utc)
    recipient = MarketingCampaignRecipient(
        id=uuid4(),
        campaign_id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        recipient_jid="77000000000@s.whatsapp.net",
        segment_code=None,
        reason_codes=["segment=legacy"],
        suppressed=False,
        suppression_reasons=[],
        created_at=now,
        updated_at=now,
    )

    serialized = console_router._serialize_marketing_recipient(recipient)
    assert serialized.segment_code == "reactivation_30_120"
    assert serialized.reason_codes == ["segment=legacy"]


@pytest.mark.asyncio
async def test_update_marketing_campaign_rejects_post_approval_states(monkeypatch) -> None:
    campaign_id = uuid4()
    branch_id = uuid4()
    client_id = uuid4()
    campaign = SimpleNamespace(
        id=campaign_id,
        branch_id=branch_id,
        client_id=client_id,
        status="approved",
        status_v2="approved",
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Tester"),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(console_router, "_resolve_marketing_campaign", lambda *args, **kwargs: campaign)
    monkeypatch.setattr(console_router, "_resolve_marketing_branch", lambda *args, **kwargs: SimpleNamespace(id=branch_id))

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_marketing_campaign(
            campaign_id=str(campaign_id),
            request=Mock(),
            payload=SimpleNamespace(
                name="Updated campaign",
                message_text=None,
                segment_code=None,
                reason=None,
            ),
            db=Mock(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "INVALID_STATE"


@pytest.mark.asyncio
async def test_get_marketing_campaign_diagnostics_reports_failure_classes(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    branch_id = uuid4()
    client_id = uuid4()
    campaign = SimpleNamespace(
        id=campaign_id,
        branch_id=branch_id,
        client_id=client_id,
        status="running",
        status_v2="running",
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Tester"),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(console_router, "_resolve_marketing_campaign", lambda *args, **kwargs: campaign)
    monkeypatch.setattr(console_router, "_resolve_marketing_branch", lambda *args, **kwargs: SimpleNamespace(id=branch_id))
    monkeypatch.setattr(
        console_router,
        "refresh_marketing_campaign_lifecycle",
        lambda *args, **kwargs: {"queued": 0, "sent": 1, "failed": 2, "replied": 0},
    )

    failed_permanent = MarketingCampaignDelivery(
        id=uuid4(),
        campaign_id=campaign_id,
        client_id=client_id,
        branch_id=branch_id,
        recipient_jid="77000000001@s.whatsapp.net",
        status="queued",
        outbox_id=uuid4(),
        created_at=now,
        updated_at=now,
    )
    failed_retryable = MarketingCampaignDelivery(
        id=uuid4(),
        campaign_id=campaign_id,
        client_id=client_id,
        branch_id=branch_id,
        recipient_jid="77000000002@s.whatsapp.net",
        status="queued",
        outbox_id=uuid4(),
        created_at=now,
        updated_at=now,
    )
    sent_delivery = MarketingCampaignDelivery(
        id=uuid4(),
        campaign_id=campaign_id,
        client_id=client_id,
        branch_id=branch_id,
        recipient_jid="77000000003@s.whatsapp.net",
        status="queued",
        outbox_id=uuid4(),
        created_at=now,
        updated_at=now,
    )

    rows = [
        (
            failed_permanent,
            "FAILED",
            "Outbound delivery failed: [CHATFLOW_BILLING_BLOCKED] plan renewal required",
        ),
        (
            failed_retryable,
            "FAILED",
            "timeout contacting provider",
        ),
        (
            sent_delivery,
            "SENT",
            None,
        ),
    ]
    query = Mock()
    query.outerjoin.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = rows
    db = Mock()
    db.query.return_value = query
    db.commit = Mock()

    response = await console_router.get_marketing_campaign_diagnostics(
        campaign_id=str(campaign_id),
        request=Mock(),
        sample_limit=5,
        db=db,
    )

    assert response.total_count == 3
    assert response.failed_count == 2
    assert response.failure_classes["provider_billing_blocked"] == 1
    assert response.failure_classes["provider_unavailable"] == 1
    assert response.retryable_failed_count == 1
    assert response.permanent_failed_count == 1
    assert len(response.sample_failed) == 2
    db.commit.assert_called_once()
