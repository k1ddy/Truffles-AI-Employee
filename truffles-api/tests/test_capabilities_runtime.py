from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.routers.webhook.booking import _resolve_booking_settings
from app.schemas.capabilities import CapabilitiesPayload
from app.services import capabilities_runtime
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities


def test_build_runtime_capabilities_missing_client():
    runtime = capabilities_runtime.build_runtime_capabilities(
        db=Mock(),
        client_id=None,
        branch_id=uuid4(),
    )
    assert runtime.source == "missing_client"
    assert runtime.payload.model_dump() == CapabilitiesPayload().model_dump()
    assert runtime.has_records is False


def test_build_runtime_capabilities_merges_client_and_branch(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    client_payload = {
        "features": {"booking_mode": "collect_preferences"},
        "providers": {"availability_provider": "none"},
    }
    branch_payload = {
        "features": {"booking_mode": "confirm_slots"},
        "providers": {"availability_provider": "google_calendar"},
    }

    def _fake_get_latest_capability(_db, *, client_id, scope, branch_id):
        assert client_id is not None
        if scope == "client" and branch_id is None:
            return SimpleNamespace(payload_json=client_payload, status="active")
        if scope == "branch" and branch_id is not None:
            return SimpleNamespace(payload_json=branch_payload, status="active")
        return None

    monkeypatch.setattr(capabilities_runtime, "_get_latest_capability", _fake_get_latest_capability)

    runtime = capabilities_runtime.build_runtime_capabilities(
        db=Mock(),
        client_id=client_id,
        branch_id=branch_id,
    )
    assert runtime.has_records is True
    assert runtime.source == "client_capabilities"
    assert runtime.payload.features.booking_mode == "confirm_slots"
    assert runtime.payload.providers.availability_provider == "google_calendar"


def test_resolve_booking_settings_uses_runtime_capabilities():
    payload = CapabilitiesPayload.model_validate(
        {
            "features": {"booking_mode": "confirm_slots"},
            "providers": {"availability_provider": "google_calendar"},
        }
    )
    runtime = RuntimeCapabilities(
        payload=payload,
        client_id=uuid4(),
        branch_id=uuid4(),
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        booking_mode, availability_provider, effective_mode = _resolve_booking_settings(
            None, provider_ready=True
        )
    finally:
        set_runtime_capabilities(None)

    assert booking_mode == "confirm_slots"
    assert availability_provider == "google_calendar"
    assert effective_mode == "confirm_slots"
