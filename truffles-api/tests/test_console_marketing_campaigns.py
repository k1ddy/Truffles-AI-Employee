from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI

from app.models.marketing_campaign import MarketingCampaign
from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


def test_marketing_routes_registered_in_openapi() -> None:
    app = FastAPI()
    app.include_router(console_router.router)
    paths = app.openapi()["paths"]

    assert "/console/v1/admin/marketing/campaigns" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/preview" in paths
    assert "/console/v1/admin/marketing/campaigns/{campaign_id}/execute" in paths


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
