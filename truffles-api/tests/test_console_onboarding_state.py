from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import app.services.onboarding_state as onboarding_state
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.onboarding_contract import OnboardingContractPayload
from app.services.console_errors import ConsoleAPIError
from app.services.onboarding_state import (
    OnboardingInputs,
    OnboardingStep,
    build_onboarding_scorecard_from_inputs,
    can_advance_to_step,
    missing_prerequisites,
)


def _make_inputs(*, capabilities: CapabilitiesPayload, has_capabilities: bool = True, **overrides) -> OnboardingInputs:
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
        reference_pack_domain_slug=overrides.get("reference_pack_domain_slug", "beauty"),
        capability_mismatches=overrides.get("capability_mismatches", []),
        has_instance_id=overrides.get("has_instance_id", False),
        has_phone=overrides.get("has_phone", True),
        branch_is_active=overrides.get("branch_is_active", False),
        has_team=overrides.get("has_team", False),
        has_telegram_chat=overrides.get("has_telegram_chat", False),
        has_knowledge_tag=overrides.get("has_knowledge_tag", False),
        has_published_knowledge=overrides.get("has_published_knowledge", False),
        missing_pack_fields=overrides.get("missing_pack_fields", []),
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
        missing_pack_fields=["client_pack.salon.address.full"],
    )

    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    assert "client_pack.salon.address.full" in missing


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
        has_phone=True,
        branch_is_active=True,
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
