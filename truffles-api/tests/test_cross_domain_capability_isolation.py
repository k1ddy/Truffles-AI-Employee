from uuid import uuid4

from app.schemas.capabilities import CapabilitiesPayload
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.capability_manifest_service import (
    resolve_fact_scope_decision,
    resolve_handoff_policy_decision,
    resolve_tool_protocol_decision,
)


def test_cross_domain_capability_isolation_tenant_a_policy():
    tenant_a = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate(
            {
                "tools": {"allow": ["calendar.*"]},
                "allowed_fact_scopes": ["info.hours"],
                "handoff_policy": "manager_request_only",
            }
        ),
        client_id=uuid4(),
        branch_id=None,
        source="tenant_a_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(tenant_a)
    try:
        assert resolve_tool_protocol_decision("calendar.list_slots").allowed is True
        tool_block = resolve_tool_protocol_decision("catalog.location")
        assert tool_block.allowed is False
        assert tool_block.reason == "allowlist_miss"

        assert resolve_fact_scope_decision("info.hours").allowed is True
        fact_block = resolve_fact_scope_decision("info.location")
        assert fact_block.allowed is False
        assert fact_block.reason == "fact_scope_not_allowed"

        handoff_block = resolve_handoff_policy_decision(explicit_manager_request=False)
        assert handoff_block.allowed is False
        assert handoff_block.reason == "manager_request_required"
    finally:
        set_runtime_capabilities(None)


def test_cross_domain_capability_isolation_tenant_b_policy():
    tenant_b = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate(
            {
                "tools": {"allow": ["catalog.location"]},
                "allowed_fact_scopes": ["info.location"],
                "handoff_policy": "deny",
            }
        ),
        client_id=uuid4(),
        branch_id=None,
        source="tenant_b_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(tenant_b)
    try:
        assert resolve_tool_protocol_decision("catalog.location").allowed is True
        tool_block = resolve_tool_protocol_decision("calendar.list_slots")
        assert tool_block.allowed is False
        assert tool_block.reason == "allowlist_miss"

        assert resolve_fact_scope_decision("info.location").allowed is True
        fact_block = resolve_fact_scope_decision("info.hours")
        assert fact_block.allowed is False
        assert fact_block.reason == "fact_scope_not_allowed"

        handoff_block = resolve_handoff_policy_decision(explicit_manager_request=True)
        assert handoff_block.allowed is False
        assert handoff_block.reason == "handoff_denied_by_policy"
    finally:
        set_runtime_capabilities(None)
