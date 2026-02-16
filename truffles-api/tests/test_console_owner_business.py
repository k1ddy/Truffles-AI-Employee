from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import (
    ConsoleKnowledgePublishRequest,
    ConsoleMetricFactMeta,
    ConsoleOwnerOperationApplyRequest,
    ConsoleOwnerOperationMetricSnapshot,
    ConsoleOwnerOperationRollbackRequest,
    ConsoleSettingsUpdateRequest,
)
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


def test_resolve_subscription_alert_levels() -> None:
    normal_level, _normal_message = console_router._resolve_subscription_alert(
        monthly_quota=1000,
        usage_percent=42.0,
        over_quota=False,
        projected_over_quota=False,
    )
    warning_level, _warning_message = console_router._resolve_subscription_alert(
        monthly_quota=1000,
        usage_percent=79.0,
        over_quota=False,
        projected_over_quota=True,
    )
    limit_level, _limit_message = console_router._resolve_subscription_alert(
        monthly_quota=1000,
        usage_percent=101.0,
        over_quota=True,
        projected_over_quota=True,
    )

    assert normal_level == "normal"
    assert warning_level == "warning_80"
    assert limit_level == "limit_100"


def test_resolve_subscription_channel_limit_prefers_company_billing_info() -> None:
    context = _build_context(
        role="owner",
        company_billing={
            "subscription": {
                "whatsapp_channels": 3,
            }
        },
        client_config={
            "billing": {
                "whatsapp_channels": 1,
            }
        },
    )

    included, source = console_router._resolve_subscription_channel_limit(
        context=context,
        channel="whatsapp",
        onboarding_enabled=True,
    )

    assert included == 3
    assert source == "company_billing_info"


def test_resolve_subscription_channel_limit_uses_onboarding_contract_when_missing_billing() -> None:
    context = _build_context(role="owner", company_billing={}, client_config={})

    included_enabled, source_enabled = console_router._resolve_subscription_channel_limit(
        context=context,
        channel="telegram",
        onboarding_enabled=True,
    )
    included_disabled, source_disabled = console_router._resolve_subscription_channel_limit(
        context=context,
        channel="telegram",
        onboarding_enabled=False,
    )

    assert included_enabled == 1
    assert source_enabled == "onboarding_contract"
    assert included_disabled == 0
    assert source_disabled == "onboarding_contract"


def test_resolve_subscription_count_meter_status_thresholds() -> None:
    over_limit_status, over_limit_remaining = console_router._resolve_subscription_count_meter_status(
        included=2,
        used=5,
    )
    limit_status, limit_remaining = console_router._resolve_subscription_count_meter_status(
        included=2,
        used=2,
    )
    warning_status, warning_remaining = console_router._resolve_subscription_count_meter_status(
        included=10,
        used=8,
    )
    ok_status, ok_remaining = console_router._resolve_subscription_count_meter_status(
        included=10,
        used=3,
    )
    unknown_status, unknown_remaining = console_router._resolve_subscription_count_meter_status(
        included=None,
        used=3,
    )

    assert over_limit_status == "over_limit"
    assert over_limit_remaining == 0
    assert limit_status == "limit_reached"
    assert limit_remaining == 0
    assert warning_status == "warning"
    assert warning_remaining == 2
    assert ok_status == "ok"
    assert ok_remaining == 7
    assert unknown_status == "unknown"
    assert unknown_remaining is None


def test_resolve_subscription_toggle_meter_status() -> None:
    assert console_router._resolve_subscription_toggle_meter_status(included=1, used=1) == "ok"
    assert (
        console_router._resolve_subscription_toggle_meter_status(included=1, used=0)
        == "included_not_configured"
    )
    assert console_router._resolve_subscription_toggle_meter_status(included=0, used=0) == "not_included"
    assert console_router._resolve_subscription_toggle_meter_status(included=0, used=1) == "over_limit"


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


def test_resolve_owner_mode_profile_capture_leads() -> None:
    label, settings, warnings = console_router._resolve_owner_mode_profile("capture_leads")

    assert "лидов" in label.lower()
    assert settings.reminder_1_minutes == 5
    assert settings.reminder_2_minutes == 30
    assert settings.escalation_timeout_minutes == 60
    assert warnings


def test_classify_outbox_incident_reason_markers() -> None:
    reason_unavailable, _ = console_router._classify_outbox_incident_reason(
        last_error="provider timeout while sending message",
        integration_degraded=False,
    )
    reason_auth, _ = console_router._classify_outbox_incident_reason(
        last_error="401 unauthorized token expired",
        integration_degraded=False,
    )
    reason_rate, _ = console_router._classify_outbox_incident_reason(
        last_error="429 too many requests",
        integration_degraded=False,
    )
    reason_drift, _ = console_router._classify_outbox_incident_reason(
        last_error=None,
        integration_degraded=True,
    )

    assert reason_unavailable == "provider_unavailable"
    assert reason_auth == "provider_auth"
    assert reason_rate == "provider_rate_limited"
    assert reason_drift == "integration_degraded"


def test_build_scope_incident_items_empty_for_healthy_signals() -> None:
    items = console_router._build_scope_incident_items(
        scope="client",
        signals=console_router._IncidentSignals(
            outbox_backlog=10,
            outbox_failed_24h=0,
            pending_handovers=0,
            integration_degraded_branches=0,
            last_error=None,
        ),
        detected_at=datetime.now(timezone.utc),
        client_id=uuid4(),
        client_slug="demo",
        branch_id=None,
        branch_ids=None,
        platform_scope=False,
    )

    assert items == []


def test_build_scope_incident_items_includes_delivery_and_handover_risks() -> None:
    items = console_router._build_scope_incident_items(
        scope="client",
        signals=console_router._IncidentSignals(
            outbox_backlog=1200,
            outbox_failed_24h=140,
            pending_handovers=35,
            integration_degraded_branches=2,
            last_error="service unavailable",
        ),
        detected_at=datetime.now(timezone.utc),
        client_id=uuid4(),
        client_slug="demo",
        branch_id=None,
        branch_ids=None,
        platform_scope=False,
    )

    assert len(items) == 2
    assert items[0].reason_code in {"provider_unavailable", "integration_degraded"}
    assert items[0].severity == "critical"
    assert items[1].reason_code == "handover_backlog"
    assert items[1].severity == "critical"


def test_summarize_owner_operation_delta_states() -> None:
    improved = console_router._summarize_owner_operation_delta(
        {
            "a": console_router.ConsoleOwnerOperationMetricDelta(trend="down"),
            "b": console_router.ConsoleOwnerOperationMetricDelta(trend="stable"),
        }
    )
    regressed = console_router._summarize_owner_operation_delta(
        {
            "a": console_router.ConsoleOwnerOperationMetricDelta(trend="up"),
        }
    )
    mixed = console_router._summarize_owner_operation_delta(
        {
            "a": console_router.ConsoleOwnerOperationMetricDelta(trend="up"),
            "b": console_router.ConsoleOwnerOperationMetricDelta(trend="down"),
        }
    )

    assert improved == "improved"
    assert regressed == "regressed"
    assert mixed == "mixed_or_stable"


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


def test_knowledge_publish_request_defaults_preflight_gate_enabled() -> None:
    body = ConsoleKnowledgePublishRequest(draft_text="test")

    assert body.skip_preflight_check is False


@pytest.mark.asyncio
async def test_publish_knowledge_requires_recent_preflight(monkeypatch):
    branch = SimpleNamespace(id=uuid4())
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        companies=[],
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda _context: branch)
    monkeypatch.setattr(console_router, "ensure_onboarding_step", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_inputs",
        lambda *_args, **_kwargs: SimpleNamespace(
            has_capabilities=False,
            reference_pack_domain_slug=None,
        ),
    )
    monkeypatch.setattr(console_router, "has_recent_knowledge_preflight", lambda *_args, **_kwargs: False)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.publish_knowledge(
            body=ConsoleKnowledgePublishRequest(draft_text="knowledge draft"),
            request=SimpleNamespace(),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "KNOWLEDGE_PREFLIGHT_REQUIRED"


@pytest.mark.asyncio
async def test_publish_knowledge_allows_skip_preflight_override(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="old",
        knowledge_safe_mode_at=None,
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        companies=[],
    )
    db = Mock()
    version_id = uuid4()

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda _context: branch)
    monkeypatch.setattr(console_router, "ensure_onboarding_step", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_inputs",
        lambda *_args, **_kwargs: SimpleNamespace(
            has_capabilities=False,
            reference_pack_domain_slug=None,
        ),
    )
    monkeypatch.setattr(
        console_router,
        "has_recent_knowledge_preflight",
        lambda *_args, **_kwargs: pytest.fail("preflight check must be skipped when override is true"),
    )
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "validate_draft", lambda *_args, **_kwargs: ({"sections": []}, [], [], None))
    monkeypatch.setattr(
        console_router,
        "publish_version",
        lambda *_args, **_kwargs: SimpleNamespace(
            id=version_id,
            payload_json={"sections": []},
            published_at=datetime.now(timezone.utc),
        ),
    )
    monkeypatch.setattr(console_router, "sync_published_branch_docs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "extract_compiled_artifacts", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    response = await console_router.publish_knowledge(
        body=ConsoleKnowledgePublishRequest(
            draft_text="knowledge draft",
            skip_preflight_check=True,
        ),
        request=SimpleNamespace(),
        db=db,
    )

    assert response.success is True
    assert response.version_id == version_id
    assert branch.knowledge_safe_mode is False
    assert branch.knowledge_safe_mode_reason is None
    assert db.commit.call_count == 2


@pytest.mark.asyncio
async def test_apply_owner_mode_operation_persists_server_snapshot(monkeypatch):
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        companies=[],
    )
    settings = SimpleNamespace(reminder_timeout_1=10, reminder_timeout_2=45, auto_close_timeout=120)
    db = Mock()
    audit_calls: list[dict] = []

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_ensure_client_settings_row", lambda *_args, **_kwargs: settings)
    monkeypatch.setattr(
        console_router,
        "_collect_owner_operation_metrics",
        lambda *_args, **_kwargs: (
            ConsoleOwnerOperationMetricSnapshot(
                outbox_backlog=120,
                unresolved_older_than_60m=4,
                manager_median_response_seconds=210.0,
            ),
            {
                "outbox_backlog": ConsoleMetricFactMeta(
                    kind="fact",
                    source="outbox_messages",
                    as_of=datetime.now(timezone.utc).isoformat(),
                    scope="client",
                    sample_size=120,
                ),
            },
        ),
    )
    monkeypatch.setattr(
        console_router,
        "record_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    response = await console_router.apply_owner_mode_operation(
        body=ConsoleOwnerOperationApplyRequest(mode="capture_leads"),
        request=SimpleNamespace(),
        db=db,
    )

    assert response.success is True
    assert response.mode == "capture_leads"
    assert response.applied_settings.reminder_1_minutes == 5
    assert response.applied_settings.reminder_2_minutes == 30
    assert response.applied_settings.escalation_timeout_minutes == 60
    assert response.previous_settings.reminder_1_minutes == 10
    assert settings.reminder_timeout_1 == 5
    assert settings.reminder_timeout_2 == 30
    assert settings.auto_close_timeout == 60
    assert db.commit.call_count == 1
    assert audit_calls


@pytest.mark.asyncio
async def test_rollback_owner_mode_operation_requires_existing_operation(monkeypatch):
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        companies=[],
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_load_owner_mode_apply_event", lambda *_args, **_kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.rollback_owner_mode_operation(
            body=ConsoleOwnerOperationRollbackRequest(),
            request=SimpleNamespace(),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "OWNER_OPERATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_owner_mode_operation_impact_returns_improved(monkeypatch):
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        effective_branch_id=None,
        branch_restricted=False,
        branches=[],
        companies=[],
    )
    operation_id = uuid4()
    event = SimpleNamespace(
        id=operation_id,
        created_at=datetime.now(timezone.utc),
        payload={
            "mode": "capture_leads",
            "impact_check_due_at": datetime.now(timezone.utc).isoformat(),
            "baseline": {
                "outbox_backlog": 100,
                "unresolved_older_than_60m": 10,
                "manager_median_response_seconds": 600.0,
            },
        },
    )
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_load_owner_mode_apply_event", lambda *_args, **_kwargs: event)
    monkeypatch.setattr(
        console_router,
        "_collect_owner_operation_metrics",
        lambda *_args, **_kwargs: (
            ConsoleOwnerOperationMetricSnapshot(
                outbox_backlog=80,
                unresolved_older_than_60m=3,
                manager_median_response_seconds=400.0,
            ),
            {
                "outbox_backlog": ConsoleMetricFactMeta(
                    kind="fact",
                    source="outbox_messages",
                    as_of=datetime.now(timezone.utc).isoformat(),
                    scope="client",
                    sample_size=80,
                ),
            },
        ),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    response = await console_router.get_owner_mode_operation_impact(
        operation_id=operation_id,
        request=SimpleNamespace(),
        db=db,
    )

    assert response.summary == "improved"
    assert response.metrics["outbox_backlog"].trend == "down"
    assert response.metrics["unresolved_older_than_60m"].trend == "down"
    assert response.metrics["manager_median_response_seconds"].trend == "down"
    assert db.commit.call_count == 1


@pytest.mark.asyncio
async def test_business_summary_requires_business_permission(monkeypatch):
    context = _build_context(role="manager")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_business_summary(request=SimpleNamespace(), db=SimpleNamespace())

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_business_incidents_requires_business_permission(monkeypatch):
    context = _build_context(role="manager")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_business_incidents(request=SimpleNamespace(), db=SimpleNamespace())

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_incidents_requires_platform_admin(monkeypatch):
    context = _build_context(role="owner")
    context.accessible_clients = []
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: context,
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_admin_incidents(
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_incidents_returns_empty_summary_without_active_clients(monkeypatch):
    context = _build_context(role="platform_admin")
    context.accessible_clients = []
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: context,
    )

    response = await console_router.list_admin_incidents(
        request=SimpleNamespace(query_params={}),
        db=SimpleNamespace(),
    )

    assert response.scope == "fleet"
    assert response.summary.total == 0
    assert response.items == []


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


@pytest.mark.asyncio
async def test_update_settings_persists_mapped_client_settings_fields(monkeypatch):
    client_id = uuid4()
    settings = SimpleNamespace(
        client_id=client_id,
        reminder_timeout_1=30,
        reminder_timeout_2=60,
        auto_close_timeout=120,
    )
    db = Mock()
    query = Mock()
    db.query.return_value = query
    query.filter.return_value = query
    query.first.return_value = settings
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=client_id, company_id=uuid4(), config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        companies=[],
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    audit_calls: list[dict] = []
    monkeypatch.setattr(
        console_router,
        "record_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    response = await console_router.update_settings(
        request=SimpleNamespace(),
        body=ConsoleSettingsUpdateRequest(
            reminder_1_minutes=5,
            reminder_2_minutes=30,
            escalation_timeout_minutes=60,
        ),
        db=db,
    )

    assert settings.reminder_timeout_1 == 5
    assert settings.reminder_timeout_2 == 30
    assert settings.auto_close_timeout == 60
    db.commit.assert_called_once()
    assert response.success is True
    assert audit_calls
