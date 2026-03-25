from uuid import uuid4

import pytest

from app.schemas.capabilities import CapabilitiesPayload
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.capability_manifest_service import (
    build_requested_fact_scopes,
    resolve_fact_scope_decision,
    resolve_handoff_policy_decision,
)


def _runtime(payload: dict, *, source: str = "test_capability_manifest") -> RuntimeCapabilities:
    return RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate(payload),
        client_id=uuid4(),
        branch_id=None,
        source=source,
        has_records=True,
    )


def test_capability_manifest_fact_scopes_isolate_domains():
    runtime = _runtime({"allowed_fact_scopes": ["info.hours", "consult.*"]})
    set_runtime_capabilities(runtime)
    try:
        assert resolve_fact_scope_decision("info.hours").allowed is True
        assert resolve_fact_scope_decision("consult.master").allowed is True

        blocked = resolve_fact_scope_decision("info.pricing")
        assert blocked.allowed is False
        assert blocked.reason == "fact_scope_not_allowed"
        assert blocked.source == "test_capability_manifest"
    finally:
        set_runtime_capabilities(None)


def test_capability_manifest_handoff_policy_enforced():
    runtime = _runtime({"handoff_policy": "manager_request_only"})
    set_runtime_capabilities(runtime)
    try:
        blocked = resolve_handoff_policy_decision(explicit_manager_request=False)
        allowed = resolve_handoff_policy_decision(explicit_manager_request=True)
    finally:
        set_runtime_capabilities(None)

    assert blocked.allowed is False
    assert blocked.reason == "manager_request_required"
    assert allowed.allowed is True
    assert allowed.reason is None


def test_build_requested_fact_scopes_contract():
    assert build_requested_fact_scopes(
        tool_action="info",
        pack_refs=["HOURS", "hours", "pricing", " "],
    ) == ["info.hours", "info.pricing"]
    assert build_requested_fact_scopes(tool_action="consult", pack_refs=[]) == ["consult.*"]
    assert build_requested_fact_scopes(tool_action="booking", pack_refs=["hours"]) == []


def test_capabilities_payload_rejects_invalid_fact_scope_token():
    with pytest.raises(
        ValueError, match="fact scope token must be '\\*', '<group>\\.\\*' or '<group>\\.<scope>'"
    ):
        CapabilitiesPayload.model_validate({"allowed_fact_scopes": ["bad token"]})
