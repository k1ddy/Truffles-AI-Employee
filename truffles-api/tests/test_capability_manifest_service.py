from uuid import uuid4

from app.schemas.capabilities import CapabilitiesPayload
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.capability_manifest_service import (
    build_requested_fact_scopes,
    resolve_fact_scope_decision,
    resolve_handoff_policy_decision,
    resolve_tool_protocol_decision,
)


def test_tool_protocol_decision_blocks_on_deny_token():
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"tools": {"deny": ["calendar.*"]}}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_tool_protocol_decision("calendar.list_slots")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is False
    assert decision.reason == "deny:calendar.*"
    assert decision.source == "client_capabilities"
    assert decision.enforcement_enabled is True


def test_tool_protocol_decision_allowlist_miss():
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"tools": {"allow": ["catalog.location"]}}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_tool_protocol_decision("catalog.portfolio")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is False
    assert decision.reason == "allowlist_miss"


def test_tool_protocol_decision_deny_by_default(monkeypatch):
    monkeypatch.setenv("TOOL_PROTOCOL_DENY_BY_DEFAULT", "1")
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_tool_protocol_decision("catalog.location")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is False
    assert decision.reason == "deny_by_default"
    assert decision.deny_by_default is True


def test_tool_protocol_decision_deny_by_default_when_runtime_records_exist(monkeypatch):
    monkeypatch.delenv("TOOL_PROTOCOL_DENY_BY_DEFAULT", raising=False)
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_tool_protocol_decision("catalog.location")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is False
    assert decision.reason == "deny_by_default"
    assert decision.deny_by_default is True


def test_tool_protocol_decision_allows_without_runtime_records(monkeypatch):
    monkeypatch.delenv("TOOL_PROTOCOL_DENY_BY_DEFAULT", raising=False)
    set_runtime_capabilities(None)
    decision = resolve_tool_protocol_decision("catalog.location")

    assert decision.allowed is True
    assert decision.reason is None
    assert decision.deny_by_default is False


def test_fact_scope_decision_blocks_scope_outside_allowlist():
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"allowed_fact_scopes": ["info.hours"]}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_fact_scope_decision("info.pricing")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is False
    assert decision.reason == "fact_scope_not_allowed"
    assert decision.requested_scope == "info.pricing"


def test_fact_scope_decision_allows_matching_scope():
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"allowed_fact_scopes": ["consult.*"]}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_fact_scope_decision("consult.master")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is True
    assert decision.reason is None


def test_build_requested_fact_scopes_normalizes_refs():
    scopes = build_requested_fact_scopes(
        tool_action="info",
        pack_refs=["pricing", "INFO.HOURS", " ", "pricing"],
    )

    assert scopes == ["info.pricing", "info.hours"]


def test_build_requested_fact_scopes_defaults_to_namespace_wildcard():
    scopes = build_requested_fact_scopes(tool_action="consult", pack_refs=[])

    assert scopes == ["consult.*"]


def test_handoff_policy_manager_request_only_requires_explicit_signal():
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"handoff_policy": "manager_request_only"}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
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
