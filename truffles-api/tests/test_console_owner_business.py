from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import (
    ConsoleConsultantVerificationOverviewResponse,
    ConsoleIncidentItem,
    ConsoleKnowledgePublishRequest,
    ConsoleKnowledgeValidateRequest,
    ConsoleMetricFactMeta,
    ConsoleOwnerOperationApplyRequest,
    ConsoleOwnerOperationMetricSnapshot,
    ConsoleOwnerOperationRollbackRequest,
    ConsoleSettingsUpdateRequest,
)
from app.services import console_consultant_verification as verification_service
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
    assert console_router._resolve_subscription_toggle_meter_status(included=None, used=0) == "unknown"
    assert console_router._resolve_subscription_toggle_meter_status(included=1, used=1) == "ok"
    assert (
        console_router._resolve_subscription_toggle_meter_status(included=1, used=0)
        == "included_not_configured"
    )
    assert console_router._resolve_subscription_toggle_meter_status(included=0, used=0) == "not_included"
    assert console_router._resolve_subscription_toggle_meter_status(included=0, used=1) == "over_limit"


def test_resolve_subscription_contract_health_missing() -> None:
    health = console_router._resolve_subscription_contract_health(
        plan_name=None,
        contract_label=None,
        monthly_quota=None,
        quota_source="unknown",
        whatsapp_included=None,
        whatsapp_source="unknown",
        whatsapp_used=0,
        payment_status="unknown",
        payment_status_source="unknown",
        has_active_onboarding_contract=False,
    )

    gap_codes = {gap.code for gap in health.gaps}
    assert health.status == "missing"
    assert health.has_active_onboarding_contract is False
    assert gap_codes == {
        "plan_missing",
        "monthly_quota_missing",
        "whatsapp_limit_missing",
        "payment_status_missing",
    }


def test_resolve_subscription_contract_health_partial_on_whatsapp_mismatch() -> None:
    health = console_router._resolve_subscription_contract_health(
        plan_name="Starter",
        contract_label="starter-2026",
        monthly_quota=1000,
        quota_source="company_billing_info",
        whatsapp_included=0,
        whatsapp_source="company_billing_info",
        whatsapp_used=1,
        payment_status="confirmed",
        payment_status_source="onboarding_contract",
        has_active_onboarding_contract=True,
    )

    gap_codes = {gap.code for gap in health.gaps}
    assert health.status == "partial"
    assert health.has_active_onboarding_contract is True
    assert "whatsapp_contract_mismatch" in gap_codes


def test_resolve_subscription_contract_health_ok() -> None:
    health = console_router._resolve_subscription_contract_health(
        plan_name="Starter",
        contract_label="starter-2026",
        monthly_quota=1000,
        quota_source="company_billing_info",
        whatsapp_included=1,
        whatsapp_source="company_billing_info",
        whatsapp_used=1,
        payment_status="confirmed",
        payment_status_source="onboarding_contract",
        has_active_onboarding_contract=True,
    )

    assert health.status == "ok"
    assert health.gaps == []


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


def test_resolve_consultant_verification_enabled_prefers_nested_flag() -> None:
    context_enabled = _build_context(
        role="owner",
        client_config={
            "console_features": {
                "consultant_verification": {
                    "enabled": True,
                }
            },
            "consultant_verification_enabled": False,
        },
    )
    context_disabled = _build_context(
        role="owner",
        client_config={
            "owner_consultant_verification": {
                "enabled": "false",
            }
        },
    )

    assert console_router._resolve_consultant_verification_enabled(context_enabled) is True
    assert console_router._resolve_consultant_verification_enabled(context_disabled) is False
    assert verification_service.resolve_consultant_verification_workspace_enabled(context_disabled) is True


def test_build_workspace_blockers_returns_stable_codes() -> None:
    blockers, blocker_codes = verification_service._build_workspace_blockers(
        workspace_enabled=False,
        branch_selected=False,
        preview_available=False,
    )

    assert blocker_codes == ["workspace_disabled", "branch_required"]
    assert blockers == [
        "Интерактивный preview временно выключен для этого клиента.",
        "Выберите филиал, чтобы привязать preview к конкретному business scope.",
    ]

    blockers, blocker_codes = verification_service._build_workspace_blockers(
        workspace_enabled=True,
        branch_selected=True,
        preview_available=False,
    )

    assert blocker_codes == ["preview_source_missing"]
    assert blockers == [
        "Сохраните draft или опубликуйте live знания, чтобы открыть preview-проверку.",
    ]


def test_derive_consultant_verification_status_thresholds() -> None:
    disabled_status, disabled_label, disabled_summary, disabled_can_verify = console_router._derive_consultant_verification_status(
        workspace_enabled=False,
        branch_selected=True,
        preview_available=True,
        default_source_mode="live",
        knowledge_stale_hours=4,
        blockers=[],
    )
    missing_status, missing_label, missing_summary, missing_can_verify = console_router._derive_consultant_verification_status(
        workspace_enabled=True,
        branch_selected=True,
        preview_available=False,
        default_source_mode=None,
        knowledge_stale_hours=None,
        blockers=["preview_missing"],
    )
    branch_status, branch_label, branch_summary, branch_can_verify = console_router._derive_consultant_verification_status(
        workspace_enabled=True,
        branch_selected=False,
        preview_available=True,
        default_source_mode="live",
        knowledge_stale_hours=None,
        blockers=["branch_required"],
    )
    stale_status, stale_label, stale_summary, stale_can_verify = console_router._derive_consultant_verification_status(
        workspace_enabled=True,
        branch_selected=True,
        preview_available=True,
        default_source_mode="draft",
        knowledge_stale_hours=24 * 8,
        blockers=[],
    )
    ready_status, ready_label, ready_summary, ready_can_verify = console_router._derive_consultant_verification_status(
        workspace_enabled=True,
        branch_selected=True,
        preview_available=True,
        default_source_mode="live",
        knowledge_stale_hours=12,
        blockers=[],
    )

    assert disabled_status == "not_enabled"
    assert "не включен" in disabled_label.lower()
    assert "обзор" in disabled_summary.lower()
    assert disabled_can_verify is False
    assert missing_status == "needs_attention"
    assert "preview" in missing_label.lower()
    assert "draft" in missing_summary.lower()
    assert missing_can_verify is False
    assert branch_status == "needs_attention"
    assert "филиал" in branch_label.lower()
    assert "branch" in branch_summary.lower()
    assert branch_can_verify is False
    assert stale_status == "needs_attention"
    assert "доступна" in stale_label.lower()
    assert "черновик" in stale_summary.lower()
    assert stale_can_verify is True
    assert ready_status == "ready"
    assert "доступна" in ready_label.lower()
    assert "pinned snapshot" in ready_summary.lower()
    assert ready_can_verify is True


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
    reason_billing, _ = console_router._classify_outbox_incident_reason(
        last_error="[CHATFLOW_BILLING_BLOCKED] ChatFlow billing blocked: plan renewal required",
        integration_degraded=False,
    )
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
    reason_invalid_recipient, _ = console_router._classify_outbox_incident_reason(
        last_error="recipient not found for this WhatsApp number",
        integration_degraded=False,
    )
    reason_drift, _ = console_router._classify_outbox_incident_reason(
        last_error=None,
        integration_degraded=True,
    )

    assert reason_billing == "provider_billing_blocked"
    assert reason_unavailable == "provider_unavailable"
    assert reason_auth == "provider_auth"
    assert reason_rate == "provider_rate_limited"
    assert reason_invalid_recipient == "provider_invalid_recipient"
    assert reason_drift == "integration_degraded"


def test_build_incident_actions_include_subscription_steps_for_billing_block() -> None:
    actions = console_router._build_incident_actions(
        reason_code="provider_billing_blocked",
        outbox_backlog=120,
        integration_degraded_branches=0,
        branch_ids=None,
        platform_scope=False,
    )

    action_ids = {item.id for item in actions}
    assert "open_subscription" in action_ids
    assert "open_integrations" in action_ids


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


def test_build_scope_incident_items_applies_sla_escalation_mapping(monkeypatch) -> None:
    profile_id = uuid4()
    monkeypatch.setattr(
        console_router,
        "_resolve_sla_action_for_scope",
        lambda *_args, **_kwargs: console_router._SlaActionResolution(
            action="escalate",
            profile_id=profile_id,
            profile_version=4,
            profile_scope="client",
        ),
    )

    items = console_router._build_scope_incident_items(
        scope="client",
        signals=console_router._IncidentSignals(
            outbox_backlog=600,
            outbox_failed_24h=35,
            pending_handovers=0,
            integration_degraded_branches=0,
            last_error="temporary provider timeout",
        ),
        detected_at=datetime.now(timezone.utc),
        client_id=uuid4(),
        company_id=uuid4(),
        domain_key="beauty",
        client_slug="demo",
        branch_id=None,
        branch_ids=None,
        platform_scope=False,
        db=SimpleNamespace(),
    )

    assert len(items) == 1
    item = items[0]
    assert item.metrics.get("sla_violation_action") == "escalate"
    assert item.metrics.get("sla_profile_id") == str(profile_id)
    assert item.metrics.get("sla_profile_version") == 4
    assert item.metrics.get("sla_profile_scope") == "client"
    assert "integration_reconcile_dry_run" in {action.id for action in item.actions}


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


def test_apply_incident_state_map_updates_item_fields() -> None:
    item = ConsoleIncidentItem(
        id="outbox-demo",
        scope="client",
        severity="warn",
        title="Delivery risk",
        summary="backlog=10",
        reason_code="outbox_backlog",
        reason_label="Delivery backlog",
        source="outbox_messages",
        detected_at=datetime.now(timezone.utc).isoformat(),
    )

    console_router._apply_incident_state_map(
        [item],
        state_map={
            "outbox-demo": {
                "incident_state": "in_progress",
                "incident_state_updated_at": "2026-02-20T10:00:00+00:00",
                "incident_state_owner": "ops@truffles",
                "incident_state_due_at": "2026-02-21T10:00:00+00:00",
                "incident_state_note": "working on provider binding",
            }
        },
    )

    assert item.incident_state == "in_progress"
    assert item.incident_state_owner == "ops@truffles"
    assert item.incident_state_due_at == "2026-02-21T10:00:00+00:00"
    assert item.incident_state_note == "working on provider binding"


def test_apply_incident_state_map_defaults_to_open_without_event() -> None:
    item = ConsoleIncidentItem(
        id="handover-demo",
        scope="client",
        severity="warn",
        title="Handover backlog",
        summary="pending=12",
        reason_code="handover_backlog",
        reason_label="Escalation queue overloaded",
        source="handovers",
        detected_at=datetime.now(timezone.utc).isoformat(),
        incident_state="resolved",
        incident_state_owner="legacy-owner",
    )

    console_router._apply_incident_state_map([item], state_map={})

    assert item.incident_state == "open"
    assert item.incident_state_updated_at is None
    assert item.incident_state_owner is None
    assert item.incident_state_due_at is None
    assert item.incident_state_note is None


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


def test_summarize_daily_visit_outcomes_uses_terminal_business_counts() -> None:
    rows = [
        SimpleNamespace(status="PENDING_CONFIRMATION", count=5),
        SimpleNamespace(status="COMPLETED", count=3),
        SimpleNamespace(status="CHECKED_IN", count=1),
        SimpleNamespace(status="NO_SHOW", count=2),
        SimpleNamespace(status="CANCELLED", count=1),
    ]

    (
        scheduled_visits_today,
        arrived_visits_today,
        no_show_visits_today,
        cancelled_visits_today,
        effective_planned_today,
        arrival_rate_percent,
    ) = console_router._summarize_daily_visit_outcomes(rows)

    assert scheduled_visits_today == 12
    assert arrived_visits_today == 4
    assert no_show_visits_today == 2
    assert cancelled_visits_today == 1
    assert effective_planned_today == 11
    assert arrival_rate_percent == pytest.approx(36.4, abs=0.01)


def test_compute_no_show_followup_pending_deduplicates_and_bounds() -> None:
    a = uuid4()
    b = uuid4()
    c = uuid4()
    pending = console_router._compute_no_show_followup_pending(
        [a, b, c, a],
        [a, a, uuid4()],
    )

    assert pending == 2


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
async def test_get_knowledge_current_returns_published_and_saved_draft(monkeypatch):
    branch = SimpleNamespace(id=uuid4())
    published = SimpleNamespace(
        id=uuid4(),
        payload_json={"client_pack": {"salon": {"name": "Published"}}},
        pack_yaml=None,
        sync_status="ready",
        sync_error=None,
        sync_completed_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    draft = SimpleNamespace(
        id=uuid4(),
        payload_json={"client_pack": {"salon": {"name": "Draft"}}},
        pack_yaml=None,
        published_at=None,
        created_at=datetime.now(timezone.utc),
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        companies=[],
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda _context: branch)
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: published)
    monkeypatch.setattr(console_router, "get_active_knowledge_version", lambda *_args, **_kwargs: published)
    monkeypatch.setattr(console_router, "get_latest_draft", lambda *_args, **_kwargs: draft)
    monkeypatch.setattr(console_router, "get_latest_knowledge_activation_job", lambda *_args, **_kwargs: None)

    response = await console_router.get_knowledge_current(
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert response.version_id == published.id
    assert response.active_version_id == published.id
    assert response.activation_status == "ready"
    assert response.activation_stage == "ready"
    assert response.draft_version_id == draft.id
    assert response.edit_base_source == "draft"
    assert response.edit_base_version_id == draft.id


@pytest.mark.asyncio
async def test_list_knowledge_history_exposes_active_live_and_candidate_activation_metadata(monkeypatch):
    branch = SimpleNamespace(id=uuid4(), active_knowledge_version_id=uuid4())
    active_version = SimpleNamespace(
        id=branch.active_knowledge_version_id,
        status="published",
        created_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc),
        summary="Live version",
        sync_status="ready",
        sync_error=None,
        sync_completed_at=datetime.now(timezone.utc),
    )
    candidate_version = SimpleNamespace(
        id=uuid4(),
        status="published",
        created_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc),
        summary="Candidate version",
        sync_status="pending",
        sync_error=None,
        sync_completed_at=None,
    )
    activation_job = SimpleNamespace(
        id=uuid4(),
        state="running",
        current_stage="applying_client_config",
        error_code=None,
        last_error=None,
        queued_at=datetime.now(timezone.utc),
        heartbeat_at=datetime.now(timezone.utc),
        attempt_count=2,
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        companies=[],
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda _context: branch)
    monkeypatch.setattr(console_router, "list_history", lambda *_args, **_kwargs: [candidate_version, active_version])
    monkeypatch.setattr(
        console_router,
        "get_latest_knowledge_activation_job",
        lambda _db, *, branch_id, version_id=None: activation_job if version_id == candidate_version.id else None,
    )

    response = await console_router.list_knowledge_history(
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert len(response.items) == 2
    assert response.items[0].id == candidate_version.id
    assert response.items[0].is_active is False
    assert response.items[0].activation_status == "running"
    assert response.items[0].activation_stage == "applying_client_config"
    assert response.items[0].activation_attempt_count == 2
    assert response.items[1].id == active_version.id
    assert response.items[1].is_active is True
    assert response.items[1].activation_status == "ready"
    assert response.items[1].activation_stage == "ready"


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
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: None)
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
async def test_validate_knowledge_blocks_draft_persist_on_lossy_structured_rewrite(monkeypatch):
    branch = SimpleNamespace(id=uuid4())
    current = SimpleNamespace(
        payload_json={
            "client_pack": {
                "guest_policy": {"allow_new_clients": True},
                "policy": {"payment_info": {"methods": ["card"]}},
            }
        }
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4(), company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        companies=[],
    )
    db = Mock()
    upsert_mock = Mock()
    audit_mock = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda _context: branch)
    monkeypatch.setattr(console_router, "ensure_onboarding_step", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        console_router,
        "build_onboarding_inputs",
        lambda *_args, **_kwargs: SimpleNamespace(
            has_capabilities=False,
            reference_pack_domain_slug="beauty",
        ),
    )
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(console_router, "upsert_draft", upsert_mock)
    monkeypatch.setattr(console_router, "record_audit_event", audit_mock)

    response = await console_router.validate_knowledge(
        body=ConsoleKnowledgeValidateRequest(
            draft_text="""
client_pack:
  guest_policy: ""
  policy:
    payment_info: "Оплата наличными"
"""
        ),
        request=SimpleNamespace(),
        db=db,
    )

    assert response.valid is False
    assert response.draft_saved is False
    assert "Lossy structured field rewrite blocked: client_pack.guest_policy" in response.errors
    assert "Lossy structured field rewrite blocked: client_pack.policy.payment_info" in response.errors
    upsert_mock.assert_not_called()
    audit_mock.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_publish_knowledge_surfaces_pack_compiler_lossy_rewrite_errors(monkeypatch):
    branch = SimpleNamespace(id=uuid4())
    current = SimpleNamespace(id=uuid4(), payload_json={"client_pack": {"salon": {"name": "Demo"}}})
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(
            id=uuid4(),
            company_id=uuid4(),
            name="demo_salon",
            config={"consultant_verification_enabled": False},
        ),
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
            reference_pack_domain_slug="beauty",
        ),
    )
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(console_router, "validate_draft", lambda *_args, **_kwargs: ({"sections": []}, [], [], None))
    monkeypatch.setattr(console_router, "has_recent_knowledge_preflight", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        console_router,
        "publish_version",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            console_router.PackCompilerError(
                "Pack compiler blocked lossy structured rewrite",
                errors=["Lossy structured field rewrite blocked: client_pack.policy.payment_info"],
            )
        ),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.publish_knowledge(
            body=ConsoleKnowledgePublishRequest(draft_text="knowledge draft"),
            request=SimpleNamespace(),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "KNOWLEDGE_INVALID"
    assert exc_info.value.details == {
        "errors": ["Lossy structured field rewrite blocked: client_pack.policy.payment_info"],
    }


@pytest.mark.asyncio
async def test_publish_knowledge_requires_compare_for_existing_live_when_rollout_enabled(monkeypatch):
    branch = SimpleNamespace(id=uuid4())
    current = SimpleNamespace(id=uuid4(), payload_json={"client_pack": {"salon": {"name": "Demo"}}})
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(
            id=uuid4(),
            company_id=uuid4(),
            name="demo_salon",
            config={"consultant_verification_enabled": True},
        ),
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
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(console_router, "get_active_knowledge_version", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(console_router, "validate_draft", lambda *_args, **_kwargs: ({"sections": []}, [], [], None))
    monkeypatch.setattr(console_router, "has_recent_knowledge_preflight", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(console_router, "has_recent_knowledge_compare_preflight", lambda *_args, **_kwargs: False)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.publish_knowledge(
            body=ConsoleKnowledgePublishRequest(draft_text="knowledge draft"),
            request=SimpleNamespace(),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "KNOWLEDGE_COMPARE_REQUIRED"


@pytest.mark.asyncio
async def test_publish_knowledge_allows_first_publish_without_compare(monkeypatch):
    client_id = uuid4()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="old",
        knowledge_safe_mode_at=None,
    )
    context = SimpleNamespace(
            role="owner",
            client=SimpleNamespace(
                id=client_id,
                company_id=uuid4(),
                name="demo_salon",
                config={"consultant_verification_enabled": True},
        ),
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
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "has_recent_knowledge_preflight", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        console_router,
        "has_recent_knowledge_compare_preflight",
        lambda *_args, **_kwargs: pytest.fail("compare should not be required for first publish"),
    )
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
    monkeypatch.setattr(
        console_router,
        "enqueue_knowledge_sync_event",
        lambda *_args, **_kwargs: pytest.fail("publish must not enqueue generic outbox activation"),
        raising=False,
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    response = await console_router.publish_knowledge(
        body=ConsoleKnowledgePublishRequest(draft_text="knowledge draft"),
        request=SimpleNamespace(),
        db=db,
    )

    assert response.success is True
    assert response.version_id == version_id
    assert response.activation_status == "queued"
    assert response.activation_stage == "queued"
    assert response.sync_status == "pending"
    assert response.partial_success is False
    assert "выполня" in (response.message or "").lower()


@pytest.mark.asyncio
async def test_publish_knowledge_allows_live_update_without_compare_when_rollout_disabled(monkeypatch):
    client_id = uuid4()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="old",
        knowledge_safe_mode_at=None,
    )
    current = SimpleNamespace(id=uuid4(), payload_json={"client_pack": {"salon": {"name": "Demo"}}})
    context = SimpleNamespace(
            role="owner",
            client=SimpleNamespace(
                id=client_id,
                company_id=uuid4(),
                name="demo_salon",
                config={"consultant_verification_enabled": False},
        ),
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
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(console_router, "has_recent_knowledge_preflight", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        console_router,
        "has_recent_knowledge_compare_preflight",
        lambda *_args, **_kwargs: pytest.fail("compare should be skipped when rollout is disabled"),
    )
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
    monkeypatch.setattr(
        console_router,
        "enqueue_knowledge_sync_event",
        lambda *_args, **_kwargs: pytest.fail("publish must not enqueue generic outbox activation"),
        raising=False,
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    response = await console_router.publish_knowledge(
        body=ConsoleKnowledgePublishRequest(draft_text="knowledge draft"),
        request=SimpleNamespace(),
        db=db,
    )

    assert response.success is True
    assert response.version_id == version_id
    assert response.activation_status == "queued"
    assert response.activation_stage == "queued"
    assert response.sync_status == "pending"
    assert response.partial_success is False


@pytest.mark.asyncio
async def test_publish_knowledge_allows_skip_preflight_override(monkeypatch):
    client_id = uuid4()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="old",
        knowledge_safe_mode_at=None,
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=client_id, company_id=uuid4(), name="demo_salon", config={}),
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
    monkeypatch.setattr(
        console_router,
        "enqueue_knowledge_sync_event",
        lambda *_args, **_kwargs: pytest.fail("publish must not enqueue generic outbox activation"),
        raising=False,
    )
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
    assert response.activation_status == "queued"
    assert response.activation_stage == "queued"
    assert response.sync_status == "pending"
    assert response.partial_success is False
    assert branch.knowledge_safe_mode is False
    assert branch.knowledge_safe_mode_reason is None
    assert db.commit.call_count == 1


@pytest.mark.asyncio
async def test_publish_knowledge_queues_sync_without_running_it_inline(monkeypatch):
    client_id = uuid4()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        knowledge_safe_mode=False,
        knowledge_safe_mode_reason=None,
        knowledge_safe_mode_at=None,
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=client_id, company_id=uuid4(), name="demo_salon", config={}),
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
    monkeypatch.setattr(console_router, "get_current_published", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "has_recent_knowledge_preflight", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(console_router, "validate_draft", lambda *_args, **_kwargs: ({"sections": []}, [], [], None))
    monkeypatch.setattr(
        console_router,
        "publish_version",
        lambda *_args, **_kwargs: SimpleNamespace(
            id=version_id,
            payload_json={"sections": []},
            published_at=datetime.now(timezone.utc),
            sync_status="pending",
            sync_error=None,
            sync_completed_at=None,
        ),
    )
    monkeypatch.setattr(
        console_router,
        "enqueue_knowledge_sync_event",
        lambda *_args, **_kwargs: pytest.fail("retry must not enqueue generic outbox activation"),
        raising=False,
    )
    monkeypatch.setattr(
        console_router,
        "sync_published_branch_docs",
        lambda *_args, **_kwargs: pytest.fail("publish must not run sync inline"),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    response = await console_router.publish_knowledge(
        body=ConsoleKnowledgePublishRequest(draft_text="knowledge draft"),
        request=SimpleNamespace(),
        db=db,
    )

    assert response.success is True
    assert response.version_id == version_id
    assert response.activation_status == "queued"
    assert response.activation_stage == "queued"
    assert response.sync_status == "pending"
    assert response.partial_success is False
    assert response.sync_error is None
    assert branch.knowledge_safe_mode is False
    assert branch.knowledge_safe_mode_reason is None


@pytest.mark.asyncio
async def test_retry_knowledge_sync_requeues_failed_published_version(monkeypatch):
    client_id = uuid4()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="timed out",
        knowledge_safe_mode_at=None,
    )
    version_id = uuid4()
    version = SimpleNamespace(
        id=version_id,
        branch_id=branch.id,
        status="published",
        payload_json={"sections": []},
        sync_status="failed",
        sync_error="timed out",
        sync_completed_at=None,
    )
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=client_id, company_id=uuid4(), name="demo_salon", config={}),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        companies=[],
    )
    db = Mock()

    query = Mock()
    query.filter.return_value = query
    query.first.return_value = version
    db.query.return_value = query

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda _context: branch)
    monkeypatch.setattr(
        console_router,
        "enqueue_knowledge_sync_event",
        lambda *_args, **_kwargs: pytest.fail("rollback must not enqueue generic outbox activation"),
        raising=False,
    )
    monkeypatch.setattr(
        console_router,
        "sync_published_branch_docs",
        lambda *_args, **_kwargs: pytest.fail("retry must not run sync inline"),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *_args, **_kwargs: None)

    response = await console_router.retry_knowledge_version_sync(
        version_id=version_id,
        request=SimpleNamespace(),
        db=db,
    )

    assert response.success is True
    assert response.version_id == version_id
    assert response.activation_status == "queued"
    assert response.activation_stage == "queued"
    assert response.sync_status == "pending"
    assert response.sync_error is None
    assert branch.knowledge_safe_mode is False
    assert branch.knowledge_safe_mode_reason is None


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
async def test_consultant_verification_overview_requires_business_permission(monkeypatch):
    context = _build_context(role="support")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_business_consultant_verification_overview(
            request=SimpleNamespace(),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_consultant_verification_overview_returns_service_payload(monkeypatch):
    context = _build_context(role="owner")
    db = SimpleNamespace()
    expected = ConsoleConsultantVerificationOverviewResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        feature_enabled=False,
        status="not_enabled",
        status_label="Контур проверки еще не включен",
        summary="Сейчас доступен обзор готовности.",
        next_wave_summary="Следующая волна подключит безопасный тестовый диалог.",
        readiness_cards=[],
        stress_test_examples=["Задайте неудобный вопрос."],
        actions=[],
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_resolve_branch_scope", lambda _context: None)
    monkeypatch.setattr(
        console_router,
        "_build_consultant_verification_overview",
        lambda **kwargs: expected,
    )

    response = await console_router.get_business_consultant_verification_overview(
        request=SimpleNamespace(),
        db=db,
    )

    assert response == expected


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
async def test_admin_control_tower_overview_requires_platform_admin(monkeypatch):
    context = _build_context(role="owner")
    context.accessible_clients = []
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: context,
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_admin_control_tower_overview(
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_control_tower_overview_returns_empty_without_active_clients(monkeypatch):
    context = _build_context(role="platform_admin")
    context.accessible_clients = []
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: context,
    )
    monkeypatch.setattr(console_router, "_build_ops_job_catalog_items", lambda: [])

    response = await console_router.get_admin_control_tower_overview(
        request=SimpleNamespace(query_params={}),
        db=SimpleNamespace(),
    )

    assert response.summary.active_clients_total == 0
    assert response.summary.incidents_total == 0
    assert response.summary.ops_jobs_total_24h == 0
    assert response.fleet_attention.items == []
    assert response.incidents.items == []
    assert response.recent_ops_jobs == []


@pytest.mark.asyncio
async def test_admin_control_tower_overview_aggregates_fleet_incidents_and_ops(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    context = _build_context(role="platform_admin")
    context.companies = [SimpleNamespace(id=company_id, name="Acme")]
    context.accessible_clients = [
        SimpleNamespace(id=client_id, name="alpha", status="active", company_id=company_id, config={})
    ]

    captured: dict[str, object] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    fleet_attention = console_router.ConsoleFleetAttentionResponse(
        generated_at=now_iso,
        stale_after_minutes=120,
        summary=console_router.ConsoleFleetAttentionSummary(
            active_clients_total=3,
            clients_with_attention=2,
            high_risk_clients=1,
            medium_risk_clients=1,
            low_risk_clients=0,
            stale_branches_total=4,
            integration_error_branches_total=2,
            integration_warn_branches_total=1,
            outbox_failed_24h_total=7,
            pending_handovers_total=3,
        ),
        items=[],
    )
    incidents = console_router.ConsoleIncidentListResponse(
        generated_at=now_iso,
        scope="fleet",
        summary=console_router.ConsoleIncidentSummary(total=5, critical=1, warn=3, info=1),
        items=[],
    )
    job_record = console_router.ConsoleOpsJobRecord(
        id=uuid4(),
        job_type="outbox_process",
        mode="dry_run",
        status="success",
        created_at=now_iso,
        finished_at=now_iso,
        error_message=None,
        request_payload={"limit": 10},
        result_payload={"ok": True},
    )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *_args, **_kwargs: context,
    )
    monkeypatch.setattr(
        console_router,
        "_build_platform_admin_fleet_attention_response",
        lambda _db, *, active_clients, companies_by_id, stale_after_minutes, include_low_mode, limit, now: (
            captured.update(
                {
                    "attention_limit": limit,
                    "stale_after_minutes": stale_after_minutes,
                    "include_low_mode": include_low_mode,
                    "companies": companies_by_id,
                    "active_clients": active_clients,
                }
            )
            or fleet_attention
        ),
    )
    monkeypatch.setattr(
        console_router,
        "_build_admin_incidents_response",
        lambda _db, *, active_clients, limit, now: (
            captured.update({"incident_limit": limit, "incident_clients": active_clients}) or incidents
        ),
    )
    monkeypatch.setattr(
        console_router,
        "_build_admin_recent_ops_jobs",
        lambda _db, *, client_ids, limit, now: (
            captured.update({"ops_jobs_limit": limit, "ops_client_ids": client_ids}) or ([job_record], 14, 2)
        ),
    )
    monkeypatch.setattr(console_router, "_build_ops_job_catalog_items", lambda: [])

    response = await console_router.get_admin_control_tower_overview(
        request=SimpleNamespace(query_params={}),
        attention_limit=12,
        incident_limit=15,
        ops_jobs_limit=8,
        db=SimpleNamespace(),
    )

    assert captured["attention_limit"] == 12
    assert captured["incident_limit"] == 15
    assert captured["ops_jobs_limit"] == 8
    assert captured["ops_client_ids"] == [client_id]
    assert response.summary.active_clients_total == 3
    assert response.summary.clients_with_attention == 2
    assert response.summary.high_risk_clients == 1
    assert response.summary.incidents_total == 5
    assert response.summary.incidents_critical == 1
    assert response.summary.incidents_warn == 3
    assert response.summary.incidents_info == 1
    assert response.summary.ops_jobs_total_24h == 14
    assert response.summary.ops_jobs_failed_24h == 2
    assert response.recent_ops_jobs == [job_record]


def test_build_control_tower_issue_counts_sorts_by_count_then_code() -> None:
    counts = console_router._build_control_tower_issue_counts(
        {
            "beta": 2,
            "alpha": 3,
            "gamma": 2,
        },
        limit=3,
    )

    assert [item.code for item in counts] == ["alpha", "beta", "gamma"]
    assert [item.count for item in counts] == [3, 2, 2]


@pytest.mark.asyncio
async def test_admin_control_tower_readiness_board_requires_platform_admin(monkeypatch):
    context = _build_context(role="owner")
    context.accessible_clients = []
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_admin_control_tower_readiness_board(
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_control_tower_readiness_board_passes_scope_and_flags(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    context = _build_context(role="platform_admin")
    context.companies = [SimpleNamespace(id=company_id, name="Acme")]
    context.accessible_clients = [
        SimpleNamespace(id=client_id, name="alpha", status="active", company_id=company_id, config={})
    ]
    captured: dict[str, object] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_readiness_board",
        lambda _db, *, active_clients, companies_by_id, include_ready_mode, limit, now: (
            captured.update(
                {
                    "active_clients": active_clients,
                    "companies_by_id": companies_by_id,
                    "include_ready_mode": include_ready_mode,
                    "limit": limit,
                }
            )
            or console_router.ConsoleAdminControlTowerReadinessBoardResponse(
                generated_at=now_iso,
                limit=limit,
                include_ready=include_ready_mode,
                summary=console_router.ConsoleAdminControlTowerReadinessSummary(
                    total_branches=0,
                    ready_branches=0,
                    blocked_branches=0,
                    hard_gate_failed_branches=0,
                    go_live_draft_branches=0,
                    go_live_approved_branches=0,
                    go_live_rejected_branches=0,
                    degraded_branches=0,
                ),
                top_blockers=[],
                items=[],
            )
        ),
    )

    response = await console_router.get_admin_control_tower_readiness_board(
        request=SimpleNamespace(query_params={"include_ready": "true", "limit": "7"}),
        include_ready="true",
        limit=7,
        db=SimpleNamespace(),
    )

    assert captured["limit"] == 7
    assert captured["include_ready_mode"] is True
    assert captured["active_clients"][0].id == client_id
    assert company_id in captured["companies_by_id"]
    assert response.limit == 7
    assert response.include_ready is True


@pytest.mark.asyncio
async def test_admin_control_tower_drift_board_requires_platform_admin(monkeypatch):
    context = _build_context(role="owner")
    context.accessible_clients = []
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_admin_control_tower_drift_board(
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_control_tower_drift_board_passes_scope_and_flags(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    context = _build_context(role="platform_admin")
    context.companies = [SimpleNamespace(id=company_id, name="Acme")]
    context.accessible_clients = [
        SimpleNamespace(id=client_id, name="alpha", status="active", company_id=company_id, config={})
    ]
    captured: dict[str, object] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_drift_board",
        lambda _db, *, active_clients, companies_by_id, stale_after_minutes, only_problematic_mode, limit, now: (
            captured.update(
                {
                    "active_clients": active_clients,
                    "companies_by_id": companies_by_id,
                    "stale_after_minutes": stale_after_minutes,
                    "only_problematic_mode": only_problematic_mode,
                    "limit": limit,
                }
            )
            or console_router.ConsoleAdminControlTowerDriftBoardResponse(
                generated_at=now_iso,
                stale_after_minutes=stale_after_minutes,
                limit=limit,
                only_problematic=only_problematic_mode,
                summary=console_router.ConsoleAdminControlTowerDriftSummary(
                    total_branches=0,
                    ok_branches=0,
                    warn_branches=0,
                    error_branches=0,
                    degraded_branches=0,
                    queue_p0=0,
                    queue_p1=0,
                    queue_p2=0,
                ),
                top_issues=[],
                items=[],
                provider_ops_queue=[],
            )
        ),
    )

    response = await console_router.get_admin_control_tower_drift_board(
        request=SimpleNamespace(query_params={"only_problematic": "false", "stale_after_minutes": "120", "limit": "9"}),
        only_problematic="false",
        stale_after_minutes=120,
        limit=9,
        db=SimpleNamespace(),
    )

    assert captured["limit"] == 9
    assert captured["stale_after_minutes"] == 120
    assert captured["only_problematic_mode"] is False
    assert captured["active_clients"][0].id == client_id
    assert company_id in captured["companies_by_id"]
    assert response.limit == 9
    assert response.only_problematic is False


@pytest.mark.asyncio
async def test_admin_control_tower_action_center_requires_platform_admin(monkeypatch):
    context = _build_context(role="owner")
    context.accessible_clients = []
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_admin_control_tower_action_center(
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_control_tower_action_center_passes_scope_and_flags(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    context = _build_context(role="platform_admin")
    context.companies = [SimpleNamespace(id=company_id, name="Acme")]
    context.accessible_clients = [
        SimpleNamespace(id=client_id, name="alpha", status="active", company_id=company_id, config={})
    ]
    captured: dict[str, object] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_action_center",
        lambda _db, *, active_clients, companies_by_id, stale_after_minutes, include_p2_mode, limit, now: (
            captured.update(
                {
                    "active_clients": active_clients,
                    "companies_by_id": companies_by_id,
                    "stale_after_minutes": stale_after_minutes,
                    "include_p2_mode": include_p2_mode,
                    "limit": limit,
                }
            )
            or console_router.ConsoleAdminControlTowerActionCenterResponse(
                generated_at=now_iso,
                stale_after_minutes=stale_after_minutes,
                limit=limit,
                include_p2=include_p2_mode,
                summary=console_router.ConsoleAdminControlTowerActionCenterSummary(
                    total_actions=0,
                    p0_actions=0,
                    p1_actions=0,
                    p2_actions=0,
                    incident_actions=0,
                    provider_ops_actions=0,
                    readiness_actions=0,
                ),
                top_reasons=[],
                items=[],
            )
        ),
    )

    response = await console_router.get_admin_control_tower_action_center(
        request=SimpleNamespace(query_params={"include_p2": "false", "stale_after_minutes": "120", "limit": "11"}),
        include_p2="false",
        stale_after_minutes=120,
        limit=11,
        db=SimpleNamespace(),
    )

    assert captured["limit"] == 11
    assert captured["stale_after_minutes"] == 120
    assert captured["include_p2_mode"] is False
    assert captured["active_clients"][0].id == client_id
    assert company_id in captured["companies_by_id"]
    assert response.limit == 11
    assert response.include_p2 is False


@pytest.mark.asyncio
async def test_admin_control_tower_migration_program_requires_platform_admin(monkeypatch):
    context = _build_context(role="owner")
    context.accessible_clients = []
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_admin_control_tower_migration_program(
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_control_tower_migration_program_passes_scope_and_flags(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    context = _build_context(role="platform_admin")
    context.companies = [SimpleNamespace(id=company_id, name="Acme")]
    context.accessible_clients = [
        SimpleNamespace(id=client_id, name="alpha", status="active", company_id=company_id, config={})
    ]
    captured: dict[str, object] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_migration_program",
        lambda _db, *, active_clients, companies_by_id, stale_after_minutes, include_p2_mode, limit, now: (
            captured.update(
                {
                    "active_clients": active_clients,
                    "companies_by_id": companies_by_id,
                    "stale_after_minutes": stale_after_minutes,
                    "include_p2_mode": include_p2_mode,
                    "limit": limit,
                }
            )
            or console_router.ConsoleAdminControlTowerMigrationProgramResponse(
                generated_at=now_iso,
                stale_after_minutes=stale_after_minutes,
                limit=limit,
                include_p2=include_p2_mode,
                summary=console_router.ConsoleAdminControlTowerMigrationProgramSummary(
                    active_clients_total=1,
                    total_branches=3,
                    ready_branches=3,
                    blocked_branches=0,
                    p0_actions=0,
                    p1_actions=0,
                    p2_actions=0,
                    waves_go=3,
                    waves_hold=0,
                ),
                waves=[],
            )
        ),
    )

    response = await console_router.get_admin_control_tower_migration_program(
        request=SimpleNamespace(query_params={"include_p2": "false", "stale_after_minutes": "90", "limit": "13"}),
        include_p2="false",
        stale_after_minutes=90,
        limit=13,
        db=SimpleNamespace(),
    )

    assert captured["limit"] == 13
    assert captured["stale_after_minutes"] == 90
    assert captured["include_p2_mode"] is False
    assert captured["active_clients"][0].id == client_id
    assert company_id in captured["companies_by_id"]
    assert response.limit == 13
    assert response.include_p2 is False


@pytest.mark.asyncio
async def test_admin_control_tower_migration_wave_detail_requires_platform_admin(monkeypatch):
    context = _build_context(role="owner")
    context.accessible_clients = []
    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_admin_control_tower_migration_wave_detail(
            wave="canary",
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_control_tower_migration_wave_detail_passes_scope_and_filters(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    context = _build_context(role="platform_admin")
    context.companies = [SimpleNamespace(id=company_id, name="Acme")]
    context.accessible_clients = [
        SimpleNamespace(id=client_id, name="alpha", status="active", company_id=company_id, config={})
    ]
    captured: dict[str, object] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(console_router, "get_console_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_migration_program",
        lambda _db, *, active_clients, companies_by_id, stale_after_minutes, include_p2_mode, limit, now: (
            captured.update(
                {
                    "active_clients": active_clients,
                    "companies_by_id": companies_by_id,
                    "stale_after_minutes": stale_after_minutes,
                    "include_p2_mode": include_p2_mode,
                    "limit": limit,
                }
            )
            or console_router.ConsoleAdminControlTowerMigrationProgramResponse(
                generated_at=now_iso,
                stale_after_minutes=stale_after_minutes,
                limit=limit,
                include_p2=include_p2_mode,
                summary=console_router.ConsoleAdminControlTowerMigrationProgramSummary(
                    active_clients_total=1,
                    total_branches=3,
                    ready_branches=2,
                    blocked_branches=1,
                    p0_actions=1,
                    p1_actions=1,
                    p2_actions=0,
                    waves_go=1,
                    waves_hold=2,
                ),
                waves=[
                    console_router.ConsoleAdminControlTowerMigrationWave(
                        wave="canary",
                        gate="go",
                        reason="wave_ready_for_promotion",
                        candidate_clients_total=1,
                        candidate_branches_total=2,
                        blockers_total=0,
                    ),
                    console_router.ConsoleAdminControlTowerMigrationWave(
                        wave="cohort",
                        gate="hold",
                        reason="hard_blockers_present",
                        candidate_clients_total=1,
                        candidate_branches_total=2,
                        blockers_total=2,
                    ),
                    console_router.ConsoleAdminControlTowerMigrationWave(
                        wave="fleet",
                        gate="hold",
                        reason="blocked_branches_remaining",
                        candidate_clients_total=1,
                        candidate_branches_total=2,
                        blockers_total=2,
                    ),
                ],
                signals=[],
                promotion_actions=[
                    console_router.ConsoleAdminControlTowerPromotionAction(
                        id="a1",
                        wave="canary",
                        gate="go",
                        priority="p0",
                        source="incident",
                        kind="ops_job",
                        title="Run canary",
                        description="Canary action",
                        job_type="integration_reconcile",
                        mode="dry_run",
                    ),
                    console_router.ConsoleAdminControlTowerPromotionAction(
                        id="a2",
                        wave="cohort",
                        gate="hold",
                        priority="p1",
                        source="provider_ops",
                        kind="navigate",
                        title="Open integrations",
                        description="Cohort action",
                        href="/integrations",
                    ),
                ],
            )
        ),
    )

    response = await console_router.get_admin_control_tower_migration_wave_detail(
        wave="canary",
        request=SimpleNamespace(query_params={"include_p2": "false", "stale_after_minutes": "90", "limit": "13"}),
        include_p2="false",
        stale_after_minutes=90,
        limit=13,
        db=SimpleNamespace(),
    )

    assert captured["limit"] == 13
    assert captured["stale_after_minutes"] == 90
    assert captured["include_p2_mode"] is False
    assert captured["active_clients"][0].id == client_id
    assert company_id in captured["companies_by_id"]
    assert response.wave == "canary"
    assert response.decision == "promote"
    assert response.reason == "wave_ready_for_promotion"
    assert response.promotion_actions_total == 1
    assert len(response.promotion_actions) == 1
    assert response.promotion_actions[0].wave == "canary"
    assert response.include_p2 is False


def test_build_admin_control_tower_action_center_aggregates_sources_and_filters_p2(monkeypatch) -> None:
    client_id = uuid4()
    company_id = uuid4()
    branch_id = uuid4()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    active_clients = [SimpleNamespace(id=client_id, name="alpha", company_id=company_id, status="active", config={})]
    companies_by_id = {company_id: SimpleNamespace(id=company_id, name="Acme")}

    incidents = console_router.ConsoleIncidentListResponse(
        generated_at=now_iso,
        scope="fleet",
        summary=console_router.ConsoleIncidentSummary(total=2, critical=1, warn=0, info=1),
        items=[
            console_router.ConsoleIncidentItem(
                id="incident-critical",
                scope="fleet",
                severity="critical",
                title="Critical delivery risk",
                summary="outbox failed",
                reason_code="integration_degraded",
                reason_label="Integration degraded",
                source="outbox_messages+branches",
                detected_at=now_iso,
                client_id=client_id,
                client_slug="alpha",
                branch_id=branch_id,
                metrics={},
                actions=[
                    console_router.ConsoleIncidentAction(
                        id="integration_reconcile_dry_run",
                        title="Run integration dry-run",
                        description="Dry-run integration remediation",
                        job_type="integration_reconcile",
                        mode="dry_run",
                        params={"limit": 10},
                    )
                ],
            ),
            console_router.ConsoleIncidentItem(
                id="incident-info",
                scope="fleet",
                severity="info",
                title="Info signal",
                summary="observe only",
                reason_code="unknown",
                reason_label="Unknown",
                source="outbox_messages+branches",
                detected_at=now_iso,
                client_id=client_id,
                client_slug="alpha",
                branch_id=branch_id,
                metrics={},
                actions=[
                    console_router.ConsoleIncidentAction(
                        id="open_ops",
                        title="Open ops",
                        description="Navigate to ops",
                        href="/ops",
                    )
                ],
            ),
        ],
    )
    drift_board = console_router.ConsoleAdminControlTowerDriftBoardResponse(
        generated_at=now_iso,
        stale_after_minutes=60,
        limit=20,
        only_problematic=True,
        summary=console_router.ConsoleAdminControlTowerDriftSummary(
            total_branches=1,
            ok_branches=0,
            warn_branches=0,
            error_branches=1,
            degraded_branches=1,
            queue_p0=0,
            queue_p1=1,
            queue_p2=0,
        ),
        top_issues=[],
        items=[],
        provider_ops_queue=[
            console_router.ConsoleProviderOpsQueueItem(
                client_id=client_id,
                client_slug="alpha",
                branch_id=branch_id,
                branch_slug="main",
                branch_name="Main Branch",
                priority="p1",
                recommended_action="provider_start_rebind",
                reasons=["provider_binding_alert_critical"],
                requires_confirmation=True,
            )
        ],
    )
    readiness_board = console_router.ConsoleAdminControlTowerReadinessBoardResponse(
        generated_at=now_iso,
        limit=20,
        include_ready=False,
        summary=console_router.ConsoleAdminControlTowerReadinessSummary(
            total_branches=1,
            ready_branches=0,
            blocked_branches=1,
            hard_gate_failed_branches=1,
            go_live_draft_branches=1,
            go_live_approved_branches=0,
            go_live_rejected_branches=0,
            degraded_branches=1,
        ),
        top_blockers=[],
        items=[
            console_router.ConsoleAdminControlTowerReadinessItem(
                company_id=company_id,
                company_name="Acme",
                client_id=client_id,
                client_slug="alpha",
                branch_id=branch_id,
                branch_slug="main",
                branch_name="Main Branch",
                current_step="go_no_go",
                scorecard_status="fail",
                readiness_status="fail",
                hard_gate_status="fail",
                ready=False,
                go_live_state="pending",
                integration_state="degraded",
                missing=["knowledge:missing_facts"],
                hard_gate_blockers=["delivery:failed_24h_critical"],
            )
        ],
    )

    monkeypatch.setattr(console_router, "_build_admin_incidents_response", lambda *_args, **_kwargs: incidents)
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_drift_board",
        lambda *_args, **_kwargs: drift_board,
    )
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_readiness_board",
        lambda *_args, **_kwargs: readiness_board,
    )

    response = console_router._build_admin_control_tower_action_center(
        SimpleNamespace(),
        active_clients=active_clients,
        companies_by_id=companies_by_id,
        stale_after_minutes=60,
        include_p2_mode=False,
        limit=20,
        now=now,
    )

    assert response.summary.total_actions == 3
    assert response.summary.p0_actions == 2
    assert response.summary.p1_actions == 1
    assert response.summary.p2_actions == 0
    assert response.summary.incident_actions == 1
    assert response.summary.provider_ops_actions == 1
    assert response.summary.readiness_actions == 1
    assert response.items[0].priority == "p0"
    assert all(item.priority != "p2" for item in response.items)
    assert any(item.source == "provider_ops" and item.provider_action == "provider_start_rebind" for item in response.items)
    assert any(item.source == "readiness" and item.href == "/tenants" for item in response.items)
    assert any(item.source == "incident" and item.job_type == "integration_reconcile" for item in response.items)


def test_build_admin_control_tower_migration_program_aggregates_wave_gates(monkeypatch) -> None:
    client_id = uuid4()
    company_id = uuid4()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    active_clients = [SimpleNamespace(id=client_id, name="alpha", company_id=company_id, status="active", config={})]
    companies_by_id = {company_id: SimpleNamespace(id=company_id, name="Acme")}

    readiness_board = console_router.ConsoleAdminControlTowerReadinessBoardResponse(
        generated_at=now_iso,
        limit=50,
        include_ready=True,
        summary=console_router.ConsoleAdminControlTowerReadinessSummary(
            total_branches=4,
            ready_branches=3,
            blocked_branches=1,
            hard_gate_failed_branches=1,
            go_live_draft_branches=1,
            go_live_approved_branches=2,
            go_live_rejected_branches=1,
            degraded_branches=1,
        ),
        top_blockers=[
            console_router.ConsoleAdminControlTowerIssueCount(
                code="delivery:failed_24h_critical",
                count=4,
            )
        ],
        items=[],
    )
    drift_board = console_router.ConsoleAdminControlTowerDriftBoardResponse(
        generated_at=now_iso,
        stale_after_minutes=60,
        limit=50,
        only_problematic=False,
        summary=console_router.ConsoleAdminControlTowerDriftSummary(
            total_branches=4,
            ok_branches=1,
            warn_branches=2,
            error_branches=1,
            degraded_branches=1,
            queue_p0=1,
            queue_p1=2,
            queue_p2=1,
        ),
        top_issues=[
            console_router.ConsoleAdminControlTowerIssueCount(
                code="provider_binding_alert_critical",
                count=3,
            )
        ],
        items=[],
        provider_ops_queue=[],
    )
    action_center = console_router.ConsoleAdminControlTowerActionCenterResponse(
        generated_at=now_iso,
        stale_after_minutes=60,
        limit=50,
        include_p2=True,
        summary=console_router.ConsoleAdminControlTowerActionCenterSummary(
            total_actions=5,
            p0_actions=1,
            p1_actions=1,
            p2_actions=1,
            incident_actions=2,
            provider_ops_actions=2,
            readiness_actions=1,
        ),
        top_reasons=[
            console_router.ConsoleAdminControlTowerIssueCount(
                code="delivery:failed_24h_critical",
                count=2,
            )
        ],
        items=[
            console_router.ConsoleAdminControlTowerActionItem(
                id="incident:critical:run",
                priority="p0",
                source="incident",
                kind="ops_job",
                title="Run critical remediation",
                description="Dry-run reconcile",
                reasons=["delivery:failed_24h_critical"],
                job_type="integration_reconcile",
                mode="dry_run",
                params={"limit": 10},
                evidence_links=["/admin/incidents"],
            ),
            console_router.ConsoleAdminControlTowerActionItem(
                id="drift:warn:navigate",
                priority="p2",
                source="provider_ops",
                kind="navigate",
                title="Open integrations",
                description="Inspect drift lane",
                reasons=["provider_binding_alert_critical"],
                href="/integrations",
                evidence_links=["/admin/control-tower/drift-board"],
            ),
        ],
    )

    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_readiness_board",
        lambda *_args, **_kwargs: readiness_board,
    )
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_drift_board",
        lambda *_args, **_kwargs: drift_board,
    )
    monkeypatch.setattr(
        console_router,
        "_build_admin_control_tower_action_center",
        lambda *_args, **_kwargs: action_center,
    )

    response = console_router._build_admin_control_tower_migration_program(
        SimpleNamespace(),
        active_clients=active_clients,
        companies_by_id=companies_by_id,
        stale_after_minutes=60,
        include_p2_mode=True,
        limit=20,
        now=now,
    )

    assert response.summary.active_clients_total == 1
    assert response.summary.total_branches == 4
    assert response.summary.ready_branches == 3
    assert response.summary.blocked_branches == 1
    assert response.summary.p0_actions == 1
    assert response.summary.p1_actions == 1
    assert response.summary.p2_actions == 1
    assert response.summary.waves_hold == 3
    assert response.summary.waves_go == 0
    assert [wave.wave for wave in response.waves] == ["canary", "cohort", "fleet"]
    assert all(wave.gate == "hold" for wave in response.waves)
    assert "incident_p0_open" in response.waves[0].rollback_triggers
    assert response.waves[0].top_blockers[0].code == "delivery:failed_24h_critical"
    assert response.waves[0].top_blockers[0].count == 6
    assert len(response.signals) == 4
    assert any(signal.code == "hard_blockers" and signal.status == "fail" for signal in response.signals)
    assert len(response.promotion_actions) == 2
    assert response.promotion_actions[0].wave == "canary"
    assert response.promotion_actions[0].gate == "hold"
    assert response.promotion_actions[0].job_type == "integration_reconcile"
    assert response.promotion_actions[1].wave == "fleet"
    assert response.promotion_actions[1].gate == "hold"


def test_build_admin_control_tower_migration_program_empty_scope_has_fail_signal() -> None:
    response = console_router._build_admin_control_tower_migration_program(
        SimpleNamespace(),
        active_clients=[],
        companies_by_id={},
        stale_after_minutes=60,
        include_p2_mode=True,
        limit=20,
        now=datetime.now(timezone.utc),
    )

    assert response.summary.active_clients_total == 0
    assert response.summary.waves_hold == 3
    assert response.waves[0].reason == "no_active_clients"
    assert response.signals[0].code == "active_clients"
    assert response.signals[0].status == "fail"
    assert response.promotion_actions == []


def test_build_admin_control_tower_migration_wave_detail_filters_actions_and_counts() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    migration_program = console_router.ConsoleAdminControlTowerMigrationProgramResponse(
        generated_at=now_iso,
        stale_after_minutes=60,
        limit=10,
        include_p2=True,
        summary=console_router.ConsoleAdminControlTowerMigrationProgramSummary(
            active_clients_total=2,
            total_branches=6,
            ready_branches=4,
            blocked_branches=2,
            p0_actions=1,
            p1_actions=2,
            p2_actions=1,
            waves_go=1,
            waves_hold=2,
        ),
        waves=[
            console_router.ConsoleAdminControlTowerMigrationWave(
                wave="canary",
                gate="go",
                reason="wave_ready_for_promotion",
                candidate_clients_total=1,
                candidate_branches_total=2,
                blockers_total=0,
            ),
            console_router.ConsoleAdminControlTowerMigrationWave(
                wave="cohort",
                gate="hold",
                reason="soft_blocker_budget_exceeded",
                candidate_clients_total=2,
                candidate_branches_total=4,
                blockers_total=3,
            ),
            console_router.ConsoleAdminControlTowerMigrationWave(
                wave="fleet",
                gate="hold",
                reason="blocked_branches_remaining",
                candidate_clients_total=2,
                candidate_branches_total=4,
                blockers_total=4,
            ),
        ],
        signals=[],
        promotion_actions=[
            console_router.ConsoleAdminControlTowerPromotionAction(
                id="cohort-a1",
                wave="cohort",
                gate="hold",
                priority="p1",
                source="provider_ops",
                kind="navigate",
                title="Open integrations",
                description="Investigate cohort drift",
            ),
            console_router.ConsoleAdminControlTowerPromotionAction(
                id="cohort-a2",
                wave="cohort",
                gate="hold",
                priority="p1",
                source="readiness",
                kind="navigate",
                title="Open tenants",
                description="Clear readiness blockers",
            ),
            console_router.ConsoleAdminControlTowerPromotionAction(
                id="fleet-a1",
                wave="fleet",
                gate="hold",
                priority="p2",
                source="provider_ops",
                kind="navigate",
                title="Observe fleet drift",
                description="Non-blocking follow-up",
            ),
        ],
    )

    response = console_router._build_admin_control_tower_migration_wave_detail(
        migration_program=migration_program,
        wave="cohort",
        limit=1,
    )

    assert response.wave == "cohort"
    assert response.decision == "hold"
    assert response.reason == "soft_blocker_budget_exceeded"
    assert response.promotion_actions_total == 2
    assert len(response.promotion_actions) == 1
    assert response.promotion_actions[0].id == "cohort-a1"


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
