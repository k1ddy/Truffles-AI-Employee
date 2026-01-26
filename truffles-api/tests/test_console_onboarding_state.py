from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.schemas.capabilities import CapabilitiesPayload
from app.services.console_errors import ConsoleAPIError
import app.services.onboarding_state as onboarding_state
from app.services.onboarding_state import (
    OnboardingInputs,
    OnboardingStep,
    can_advance_to_step,
    missing_prerequisites,
)


def _make_inputs(*, capabilities: CapabilitiesPayload, has_capabilities: bool = True, **overrides) -> OnboardingInputs:
    return OnboardingInputs(
        has_capabilities=has_capabilities,
        capabilities=capabilities,
        has_instance_id=overrides.get("has_instance_id", False),
        branch_is_active=overrides.get("branch_is_active", False),
        has_team=overrides.get("has_team", False),
        has_telegram_chat=overrides.get("has_telegram_chat", False),
        has_knowledge_tag=overrides.get("has_knowledge_tag", False),
        has_published_knowledge=overrides.get("has_published_knowledge", False),
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
