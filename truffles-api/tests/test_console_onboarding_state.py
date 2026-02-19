from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import app.services.onboarding_state as onboarding_state
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.onboarding_contract import OnboardingContractPayload
from app.services.console_errors import ConsoleAPIError
from app.services.onboarding_state import (
    OnboardingInputs,
    OnboardingSlaControlLoop,
    OnboardingStep,
    build_onboarding_scorecard_from_inputs,
    can_advance_to_step,
    missing_prerequisites,
)


def _make_inputs(*, capabilities: CapabilitiesPayload, has_capabilities: bool = True, **overrides) -> OnboardingInputs:
    has_instance_id = overrides.get("has_instance_id", False)
    instance_id = overrides.get("instance_id")
    if instance_id is None and has_instance_id:
        instance_id = "instance-123"
    return OnboardingInputs(
        has_capabilities=has_capabilities,
        capabilities=capabilities,
        has_onboarding_contract=overrides.get("has_onboarding_contract", True),
        onboarding_contract=overrides.get(
            "onboarding_contract",
            OnboardingContractPayload.model_validate({"purchased": {}}),
        ),
        payment_status=overrides.get("payment_status", "confirmed"),
        payment_confirmed=overrides.get("payment_confirmed", True),
        payment_confirmed_at=overrides.get("payment_confirmed_at", None),
        payment_confirmed_by=overrides.get("payment_confirmed_by", None),
        has_webhook_secret=overrides.get("has_webhook_secret", True),
        has_reference_pack=overrides.get("has_reference_pack", True),
        has_reference_pack_integrity=overrides.get("has_reference_pack_integrity", True),
        reference_pack_integrity_missing=overrides.get("reference_pack_integrity_missing", []),
        reference_pack_domain_slug=overrides.get("reference_pack_domain_slug", "beauty"),
        capability_mismatches=overrides.get("capability_mismatches", []),
        instance_id=instance_id,
        has_instance_id=has_instance_id,
        has_phone=overrides.get("has_phone", True),
        branch_is_active=overrides.get("branch_is_active", False),
        has_team=overrides.get("has_team", False),
        has_telegram_chat=overrides.get("has_telegram_chat", False),
        has_knowledge_tag=overrides.get("has_knowledge_tag", False),
        has_published_knowledge=overrides.get("has_published_knowledge", False),
        missing_pack_fields=overrides.get("missing_pack_fields", []),
        document_ingestion_valid=overrides.get("document_ingestion_valid", True),
        document_ingestion_source=overrides.get("document_ingestion_source", "published"),
        document_ingestion_missing_fields=overrides.get("document_ingestion_missing_fields", []),
        document_ingestion_critical_missing_fields=overrides.get(
            "document_ingestion_critical_missing_fields", []
        ),
        has_working_hours=overrides.get("has_working_hours", False),
        has_booking_settings=overrides.get("has_booking_settings", False),
        has_specialists=overrides.get("has_specialists", False),
    )


def test_skip_required_step_blocked():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(capabilities=capabilities, has_instance_id=False)

    assert can_advance_to_step(
        OnboardingStep.BRANCH_DRAFT,
        OnboardingStep.TEAM,
        inputs,
    ) is False


def test_skip_optional_step_allowed():
    capabilities = CapabilitiesPayload.model_validate(
        {"channels": {"whatsapp": True, "telegram": False}, "features": {"knowledge_upload": True}}
    )
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        has_team=True,
    )

    assert can_advance_to_step(
        OnboardingStep.TEAM,
        OnboardingStep.KNOWLEDGE,
        inputs,
    ) is True


def test_go_no_go_requires_capabilities():
    capabilities = CapabilitiesPayload()
    inputs = _make_inputs(capabilities=capabilities, has_capabilities=False)

    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "capabilities" in missing


def test_go_no_go_includes_missing_pack_fields():
    capabilities = CapabilitiesPayload.model_validate({"features": {"knowledge_upload": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_capabilities=True,
        has_knowledge_tag=True,
        has_published_knowledge=True,
        missing_pack_fields=["client_pack.location.address.full"],
    )

    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "client_pack.location.address.full" in missing


def test_go_no_go_requires_document_ingestion_gate_when_knowledge_enabled():
    capabilities = CapabilitiesPayload.model_validate({"features": {"knowledge_upload": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_capabilities=True,
        has_knowledge_tag=True,
        has_published_knowledge=True,
        document_ingestion_valid=False,
        document_ingestion_source="draft",
        document_ingestion_missing_fields=["client_pack.policy.hard_law"],
        document_ingestion_critical_missing_fields=["client_pack.policy.hard_law"],
    )

    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "document_ingestion_invalid" in missing
    assert "client_pack.policy.hard_law" in missing


def test_go_no_go_requires_payment_confirmation():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        branch_is_active=True,
        payment_confirmed=False,
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "payment_confirmed" in missing


def test_go_no_go_requires_reference_pack():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        branch_is_active=True,
        has_reference_pack=False,
        reference_pack_domain_slug="beauty",
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "reference_pack" in missing


def test_go_no_go_requires_reference_pack_integrity():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        branch_is_active=True,
        has_reference_pack=True,
        has_reference_pack_integrity=False,
        reference_pack_integrity_missing=["reference_pack_schema_version"],
        reference_pack_domain_slug="beauty",
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "reference_pack_schema_version" in missing


def test_go_no_go_includes_capability_mismatches():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        branch_is_active=True,
        capability_mismatches=["channels.whatsapp"],
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "capability_mismatch:channels.whatsapp" in missing


def test_integrations_requires_phone():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        has_phone=False,
    )
    missing = missing_prerequisites(OnboardingStep.INTEGRATIONS, inputs)
    assert "phone" in missing


def test_go_no_go_requires_phone_when_whatsapp_enabled():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        has_phone=False,
        branch_is_active=True,
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "phone" in missing


def test_go_no_go_requires_provider_binding_for_whatsapp():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "provider_binding.whatsapp" in missing


def test_go_no_go_requires_provider_binding_owner():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
        onboarding_contract=OnboardingContractPayload.model_validate(
            {
                "purchased": {"channels": {"whatsapp": True}},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": (date.today() + timedelta(days=5)).isoformat(),
                    }
                },
            }
        ),
    )

    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "provider_binding.whatsapp.owner" in missing


def test_go_no_go_requires_non_expired_provider_binding():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
        onboarding_contract=OnboardingContractPayload.model_validate(
            {
                "purchased": {"channels": {"whatsapp": True}},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": "2020-01-01",
                        "owner": "platform-admin",
                    }
                },
            }
        ),
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "provider_binding.whatsapp.paid_until_expired" in missing


def test_go_no_go_requires_rebind_resolved():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
        onboarding_contract=OnboardingContractPayload.model_validate(
            {
                "purchased": {"channels": {"whatsapp": True}},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "rebind_required",
                        "paid_until": (date.today() + timedelta(days=30)).isoformat(),
                        "owner": "platform-admin",
                        "rebind_required": True,
                    }
                },
            }
        ),
    )
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "provider_binding.whatsapp.rebind_required" in missing


def test_go_no_go_requires_provider_capability_check_signal():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
        onboarding_contract=OnboardingContractPayload.model_validate(
            {
                "purchased": {"channels": {"whatsapp": True}},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": (date.today() + timedelta(days=30)).isoformat(),
                        "owner": "platform-admin",
                    }
                },
            }
        ),
    )

    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "provider_binding.whatsapp.alert_state" in missing


def test_go_no_go_blocks_when_provider_capability_check_failed():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
        onboarding_contract=OnboardingContractPayload.model_validate(
            {
                "purchased": {"channels": {"whatsapp": True}},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": (date.today() + timedelta(days=30)).isoformat(),
                        "owner": "platform-admin",
                        "alert_state": "critical",
                    }
                },
            }
        ),
    )

    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "provider_binding.whatsapp.capability_check_failed" in missing


def test_ensure_onboarding_step_requires_previous(monkeypatch):
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(capabilities=capabilities, has_instance_id=False)
    branch = SimpleNamespace(onboarding_state=OnboardingStep.BRANCH_DRAFT.value)

    def fake_inputs(_db, _branch):
        return inputs

    monkeypatch.setattr(onboarding_state, "build_onboarding_inputs", fake_inputs)

    with pytest.raises(ConsoleAPIError) as exc_info:
        onboarding_state.ensure_onboarding_step(Mock(), branch, OnboardingStep.TEAM)

    assert exc_info.value.code == "ONBOARDING_STEP_REQUIRED"


def test_onboarding_scorecard_passes_when_go_no_go_requirements_are_satisfied():
    capabilities = CapabilitiesPayload.model_validate(
        {
            "channels": {"whatsapp": True, "telegram": True},
            "features": {"knowledge_upload": True, "booking_mode": "confirm_slots"},
        }
    )
    inputs = _make_inputs(
        capabilities=capabilities,
        has_capabilities=True,
        has_onboarding_contract=True,
        payment_confirmed=True,
        has_webhook_secret=True,
        has_reference_pack=True,
        reference_pack_domain_slug="beauty",
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
        onboarding_contract=OnboardingContractPayload.model_validate(
            {
                "purchased": {"channels": {"whatsapp": True, "telegram": True}},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": (date.today() + timedelta(days=30)).isoformat(),
                        "owner": "platform-admin",
                        "next_renewal_at": (date.today() + timedelta(days=30)).isoformat(),
                        "alert_state": "ok",
                    }
                },
            }
        ),
        has_team=True,
        has_telegram_chat=True,
        has_knowledge_tag=True,
        has_published_knowledge=True,
        has_working_hours=True,
        has_booking_settings=True,
        has_specialists=True,
    )

    scorecard = build_onboarding_scorecard_from_inputs(inputs)
    assert scorecard.ready is True
    go_no_go = next(check for check in scorecard.checks if check.id == OnboardingStep.GO_NO_GO)
    assert go_no_go.passed is True
    assert go_no_go.missing == []
    assert scorecard.document_ingestion is not None
    assert scorecard.document_ingestion.status == "pass"
    assert scorecard.document_ingestion.valid is True
    assert scorecard.operational_pipeline is not None
    assert scorecard.operational_pipeline.status == "pass"
    assert scorecard.operational_pipeline.blocked is False


def test_onboarding_scorecard_fails_when_go_no_go_requirements_missing():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_capabilities=True,
        has_instance_id=False,
        has_phone=False,
        payment_confirmed=False,
        has_webhook_secret=False,
    )

    scorecard = build_onboarding_scorecard_from_inputs(inputs)
    assert scorecard.ready is False
    assert "payment_confirmed" in scorecard.missing
    assert "instance_id" in scorecard.missing
    assert "phone" in scorecard.missing
    assert scorecard.operational_pipeline is not None
    assert scorecard.operational_pipeline.status == "fail"
    assert "payment_confirmed" in scorecard.operational_pipeline.blockers
    assert scorecard.operational_pipeline.current_stage_id == "contract_alignment"


def test_onboarding_scorecard_skips_document_ingestion_when_knowledge_feature_disabled():
    capabilities = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    inputs = _make_inputs(
        capabilities=capabilities,
        has_capabilities=True,
        has_instance_id=True,
        branch_is_active=True,
        has_phone=True,
        document_ingestion_valid=False,
        document_ingestion_source="none",
    )

    scorecard = build_onboarding_scorecard_from_inputs(inputs)
    assert scorecard.document_ingestion is not None
    assert scorecard.document_ingestion.status == "skipped"
    assert scorecard.document_ingestion.valid is True


def test_onboarding_scorecard_pipeline_reflects_sla_warning_status():
    capabilities = CapabilitiesPayload.model_validate(
        {
            "channels": {"whatsapp": True, "telegram": True},
            "features": {"knowledge_upload": True, "booking_mode": "confirm_slots"},
        }
    )
    inputs = _make_inputs(
        capabilities=capabilities,
        has_capabilities=True,
        has_onboarding_contract=True,
        payment_confirmed=True,
        has_webhook_secret=True,
        has_reference_pack=True,
        reference_pack_domain_slug="beauty",
        has_instance_id=True,
        instance_id="instance-123",
        has_phone=True,
        branch_is_active=True,
        onboarding_contract=OnboardingContractPayload.model_validate(
            {
                "purchased": {"channels": {"whatsapp": True, "telegram": True}},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": (date.today() + timedelta(days=30)).isoformat(),
                        "owner": "platform-admin",
                        "next_renewal_at": (date.today() + timedelta(days=30)).isoformat(),
                        "alert_state": "ok",
                    }
                },
            }
        ),
        has_team=True,
        has_telegram_chat=True,
        has_knowledge_tag=True,
        has_published_knowledge=True,
        has_working_hours=True,
        has_booking_settings=True,
        has_specialists=True,
    )
    sla_warning = OnboardingSlaControlLoop(
        status="warn",
        reminder_1_minutes=10,
        reminder_2_minutes=45,
        escalation_timeout_minutes=120,
        pending_total=2,
        warning_total=1,
        breached_total=0,
        provider_status="configured",
        provider_paid_until=(date.today() + timedelta(days=30)).isoformat(),
        provider_days_to_renewal=30,
        provider_alert_state="ok",
        active_incidents=["handover_sla_warning"],
        recommended_actions=["review_pending_handovers"],
    )

    scorecard = build_onboarding_scorecard_from_inputs(inputs, sla_control_loop=sla_warning)
    assert scorecard.sla_control_loop is not None
    assert scorecard.operational_pipeline is not None
    assert scorecard.operational_pipeline.status == "warn"
    assert scorecard.operational_pipeline.current_stage_id == "sla_escalation_loop"
    sla_stage = next(
        stage for stage in scorecard.operational_pipeline.stages if stage.id == "sla_escalation_loop"
    )
    assert sla_stage.status == "warn"
    assert "handover_sla_warning" in sla_stage.blockers
    assert "review_pending_handovers" in scorecard.operational_pipeline.next_actions


@pytest.mark.parametrize(
    ("last_error", "expected"),
    [
        ("stale_processing:max_attempts", "stale_processing"),
        ("ChatFlow billing blocked: plan renewal required [CHATFLOW_BILLING_BLOCKED]", "provider_billing_blocked"),
        ("HTTP 401 unauthorized", "provider_auth"),
        ("upstream 502 bad gateway", "provider_unavailable"),
        ("", "unknown"),
    ],
)
def test_classify_delivery_failure_reason(last_error, expected):
    assert onboarding_state._classify_delivery_failure_reason(last_error) == expected


def _build_delivery_dimension(*, backlog_total: int, failed_errors: list[str]):
    db = Mock()
    backlog_query = Mock()
    backlog_query.filter.return_value.scalar.return_value = backlog_total
    failed_query = Mock()
    failed_query.filter.return_value.all.return_value = [
        SimpleNamespace(last_error=error) for error in failed_errors
    ]
    db.query.side_effect = [backlog_query, failed_query]
    branch = SimpleNamespace(client_id="client-1", id="branch-1")
    return onboarding_state._build_delivery_health_readiness_dimension(db, branch)


def test_delivery_dimension_adds_provider_billing_blocker_and_actions():
    dimension = _build_delivery_dimension(
        backlog_total=0,
        failed_errors=["ChatFlow billing blocked: plan renewal required [CHATFLOW_BILLING_BLOCKED]"],
    )
    assert dimension.status == "fail"
    assert "delivery:provider_billing_blocked_critical" in dimension.blocker_codes
    assert "resolve_provider_billing_block" in dimension.next_action_codes
    assert "classify_delivery_errors_and_apply_remediation" in dimension.next_action_codes


def test_delivery_dimension_adds_provider_auth_blocker_and_actions():
    dimension = _build_delivery_dimension(
        backlog_total=0,
        failed_errors=["HTTP 401 unauthorized"],
    )
    assert dimension.status == "fail"
    assert "delivery:provider_auth_critical" in dimension.blocker_codes
    assert "rotate_provider_credentials" in dimension.next_action_codes
