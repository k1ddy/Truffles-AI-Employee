import pytest

from app.schemas.capabilities import CapabilitiesPayload
from app.services.console_errors import ConsoleAPIError
from app.services.onboarding_contract_service import (
    find_capability_mismatches,
    merge_onboarding_contract,
    validate_onboarding_contract_payload,
)


def test_find_capability_mismatches_detects_unpurchased_channel():
    purchased = CapabilitiesPayload.model_validate({"channels": {"whatsapp": False}})
    effective = CapabilitiesPayload.model_validate({"channels": {"whatsapp": True}})
    mismatches = find_capability_mismatches(purchased=purchased, effective=effective)
    assert "channels.whatsapp" in mismatches


def test_find_capability_mismatches_detects_provider_mismatch():
    purchased = CapabilitiesPayload.model_validate(
        {"providers": {"calendar_provider": "google_calendar"}}
    )
    effective = CapabilitiesPayload.model_validate({"providers": {"calendar_provider": "local"}})
    mismatches = find_capability_mismatches(purchased=purchased, effective=effective)
    assert "providers.calendar_provider" in mismatches


def test_find_capability_mismatches_allows_subset_configuration():
    purchased = CapabilitiesPayload.model_validate(
        {"channels": {"whatsapp": True}, "features": {"booking_mode": "confirm_slots"}}
    )
    effective = CapabilitiesPayload.model_validate(
        {"channels": {"whatsapp": True}, "features": {"booking_mode": "collect_preferences"}}
    )
    mismatches = find_capability_mismatches(purchased=purchased, effective=effective)
    assert not mismatches


def test_merge_onboarding_contract_merges_provider_binding_whatsapp_fields():
    merged = merge_onboarding_contract(
        base={
            "domain_slug": "beauty",
            "purchased": {"channels": {"whatsapp": True}},
            "provider_binding": {
                "whatsapp": {
                    "provider": "chatflow",
                    "instance_id": "instance-old",
                    "webhook_status": "pending",
                    "paid_until": "2030-01-01",
                }
            },
        },
        override={
            "provider_binding": {
                "whatsapp": {
                    "instance_id": "instance-new",
                    "webhook_status": "configured",
                }
            }
        },
    )
    assert merged["provider_binding"]["whatsapp"]["provider"] == "chatflow"
    assert merged["provider_binding"]["whatsapp"]["instance_id"] == "instance-new"
    assert merged["provider_binding"]["whatsapp"]["webhook_status"] == "configured"
    assert merged["provider_binding"]["whatsapp"]["paid_until"] == "2030-01-01"


def test_validate_onboarding_contract_payload_rejects_invalid_provider_binding_date():
    with pytest.raises(ConsoleAPIError) as exc_info:
        validate_onboarding_contract_payload(
            {
                "domain_slug": "beauty",
                "purchased": {},
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": "2026-02-31",
                    }
                },
            }
        )
    assert exc_info.value.code == "INVALID_PARAM"
