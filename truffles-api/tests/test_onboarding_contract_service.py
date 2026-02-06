from app.schemas.capabilities import CapabilitiesPayload
from app.services.onboarding_contract_service import find_capability_mismatches


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
