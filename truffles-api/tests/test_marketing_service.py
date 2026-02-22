from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services.marketing import (
    MARKETING_STATUS_COMPLETED,
    MARKETING_STATUS_FAILED,
    MARKETING_STATUS_RUNNING,
    build_marketing_campaign_preflight,
    derive_marketing_terminal_status,
    normalize_marketing_status,
    refresh_marketing_campaign_lifecycle,
)
from app.services.marketing.service import _message_has_service_or_pricing_signal


def _count_query(value: int) -> Mock:
    query = Mock()
    query.filter.return_value.scalar.return_value = value
    return query


def _delivery_query(rows: list[SimpleNamespace]) -> Mock:
    query = Mock()
    query.outerjoin.return_value = query
    query.filter.return_value = query
    query.all.return_value = rows
    return query


def test_normalize_marketing_status_maps_legacy_values() -> None:
    assert normalize_marketing_status("ready") == "approved"
    assert normalize_marketing_status("executed") == "completed"
    assert normalize_marketing_status("RUNNING") == "running"
    assert normalize_marketing_status("unknown") == "draft"


def test_derive_marketing_terminal_status_rules() -> None:
    assert derive_marketing_terminal_status(queued_count=1, failed_count=0, total_count=4) is None
    assert derive_marketing_terminal_status(queued_count=0, failed_count=0, total_count=0) is None
    assert derive_marketing_terminal_status(queued_count=0, failed_count=2, total_count=2) == MARKETING_STATUS_FAILED
    assert derive_marketing_terminal_status(queued_count=0, failed_count=0, total_count=3) == MARKETING_STATUS_COMPLETED


def test_build_marketing_campaign_preflight_blocks_on_template_gate(monkeypatch) -> None:
    monkeypatch.setenv("MARKETING_TEMPLATE_GATE_ENABLED", "1")
    db = Mock()
    db.query.side_effect = [_count_query(12), _count_query(2)]
    campaign = SimpleNamespace(
        id=uuid4(),
        status="approved",
        status_v2="approved",
        client_id=uuid4(),
        branch_id=uuid4(),
        audience_filter={"template_state": "pending"},
        preflight_snapshot={},
        preflight_valid=False,
        updated_at=None,
    )
    monkeypatch.setattr(
        "app.services.marketing.service.build_outbox_health_snapshot",
        lambda _db, now=None: {"status": "healthy", "pending": 0, "failed_24h": 0},
    )
    monkeypatch.setattr(
        "app.services.marketing.service._count_recent_provider_billing_blocked_failures",
        lambda *args, **kwargs: 0,
    )

    snapshot = build_marketing_campaign_preflight(db, campaign=campaign)

    assert snapshot["template_gate_enabled"] is True
    assert snapshot["template_ok"] is False
    assert "template_not_approved" in snapshot["blocked_reasons"]
    assert snapshot["preflight_valid"] is False


def test_build_marketing_campaign_preflight_blocks_on_provider_billing(monkeypatch) -> None:
    db = Mock()
    db.query.side_effect = [_count_query(8), _count_query(1)]
    campaign = SimpleNamespace(
        id=uuid4(),
        status="approved",
        status_v2="approved",
        client_id=uuid4(),
        branch_id=uuid4(),
        audience_filter={},
        preflight_snapshot={},
        preflight_valid=False,
        updated_at=None,
    )
    monkeypatch.setattr(
        "app.services.marketing.service.build_outbox_health_snapshot",
        lambda _db, now=None: {"status": "healthy", "pending": 0, "failed_24h": 0},
    )
    monkeypatch.setattr(
        "app.services.marketing.service._count_recent_provider_billing_blocked_failures",
        lambda *args, **kwargs: 3,
    )

    snapshot = build_marketing_campaign_preflight(db, campaign=campaign)

    assert snapshot["provider_billing_blocked"] is True
    assert snapshot["provider_billing_blocked_count"] == 3
    assert "provider_billing_blocked" in snapshot["blocked_reasons"]
    assert snapshot["preflight_valid"] is False


def test_message_has_service_or_pricing_signal_detects_intent() -> None:
    detected, signal = _message_has_service_or_pricing_signal(
        intent="price_query",
        metadata={},
    )
    assert detected is True
    assert signal == "intent:price_query"


def test_message_has_service_or_pricing_signal_detects_metadata() -> None:
    detected, signal = _message_has_service_or_pricing_signal(
        intent="other",
        metadata={"info_sections": ["pricing"]},
    )
    assert detected is True
    assert signal == "meta:info_sections"


def test_refresh_marketing_campaign_lifecycle_marks_completed() -> None:
    db = Mock()
    rows = [
        SimpleNamespace(delivery_status="sent", outbox_status="SENT"),
        SimpleNamespace(delivery_status="replied", outbox_status="SENT"),
    ]
    db.query.return_value = _delivery_query(rows)
    campaign = SimpleNamespace(
        id=uuid4(),
        status=MARKETING_STATUS_RUNNING,
        status_v2=MARKETING_STATUS_RUNNING,
        run_completed_at=None,
        updated_at=None,
    )

    counts = refresh_marketing_campaign_lifecycle(db, campaign=campaign, now=datetime.now(timezone.utc))

    assert counts["queued"] == 0
    assert counts["failed"] == 0
    assert campaign.status == MARKETING_STATUS_COMPLETED
    assert campaign.status_v2 == MARKETING_STATUS_COMPLETED
    assert campaign.run_completed_at is not None
