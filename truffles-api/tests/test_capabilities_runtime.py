from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
    assert runtime.has_tool_policy_records is False


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
    assert runtime.has_tool_policy_records is False
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


def test_build_runtime_capabilities_merges_tool_policy():
    client_id = uuid4()
    branch_id = uuid4()
    client_payload = {
        "tools": {"allow": ["calendar.*", "catalog.service_query"]},
    }
    branch_payload = {
        "tools": {"deny": ["calendar.book_slot"]},
    }

    def _fake_get_latest_capability(_db, *, client_id, scope, branch_id):
        assert client_id is not None
        if scope == "client" and branch_id is None:
            return SimpleNamespace(payload_json=client_payload, status="active")
        if scope == "branch" and branch_id is not None:
            return SimpleNamespace(payload_json=branch_payload, status="active")
        return None

    original = capabilities_runtime._get_latest_capability
    capabilities_runtime._get_latest_capability = _fake_get_latest_capability
    try:
        runtime = capabilities_runtime.build_runtime_capabilities(
            db=Mock(),
            client_id=client_id,
            branch_id=branch_id,
        )
    finally:
        capabilities_runtime._get_latest_capability = original

    assert runtime.payload.tools.allow == ["calendar.*", "catalog.service_query"]
    assert runtime.payload.tools.deny == ["calendar.book_slot"]
    assert runtime.has_tool_policy_records is True


def test_build_runtime_capabilities_merges_fact_scopes_and_handoff_policy():
    client_id = uuid4()
    branch_id = uuid4()
    client_payload = {
        "allowed_fact_scopes": ["info.*", "consult.master"],
        "handoff_policy": "allow",
    }
    branch_payload = {
        "allowed_fact_scopes": ["info.hours"],
        "handoff_policy": "manager_request_only",
    }

    def _fake_get_latest_capability(_db, *, client_id, scope, branch_id):
        assert client_id is not None
        if scope == "client" and branch_id is None:
            return SimpleNamespace(payload_json=client_payload, status="active")
        if scope == "branch" and branch_id is not None:
            return SimpleNamespace(payload_json=branch_payload, status="active")
        return None

    original = capabilities_runtime._get_latest_capability
    capabilities_runtime._get_latest_capability = _fake_get_latest_capability
    try:
        runtime = capabilities_runtime.build_runtime_capabilities(
            db=Mock(),
            client_id=client_id,
            branch_id=branch_id,
        )
    finally:
        capabilities_runtime._get_latest_capability = original

    assert runtime.payload.allowed_fact_scopes == ["info.hours"]
    assert runtime.payload.handoff_policy == "manager_request_only"


def test_capabilities_payload_normalizes_tool_policy_tokens():
    payload = CapabilitiesPayload.model_validate(
        {
            "tools": {
                "allow": [" CALENDAR.* ", "calendar.book_slot", "calendar.book_slot"],
                "deny": ["Catalog.Location"],
            }
        }
    )

    assert payload.tools.allow == ["calendar.*", "calendar.book_slot"]
    assert payload.tools.deny == ["catalog.location"]


def test_capabilities_payload_normalizes_fact_scopes_and_handoff_policy():
    payload = CapabilitiesPayload.model_validate(
        {
            "allowed_fact_scopes": [" INFO.* ", "info.hours", "INFO.HOURS"],
            "handoff_policy": " MANAGER_REQUEST_ONLY ",
        }
    )

    assert payload.allowed_fact_scopes == ["info.*", "info.hours"]
    assert payload.handoff_policy == "manager_request_only"


def test_capabilities_payload_rejects_invalid_fact_scope_token():
    with pytest.raises(ValidationError):
        CapabilitiesPayload.model_validate({"allowed_fact_scopes": ["info scope"]})
