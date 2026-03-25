from uuid import uuid4

from app.schemas.capabilities import CapabilitiesPayload
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.capability_manifest_service import resolve_tool_protocol_decision


def _runtime(payload: dict, *, source: str = "test_tool_protocol_gate") -> RuntimeCapabilities:
    return RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate(payload),
        client_id=uuid4(),
        branch_id=None,
        source=source,
        has_records=True,
    )


def test_tool_protocol_gate_deny_token_has_priority_over_allow():
    runtime = _runtime(
        {
            "tools": {
                "allow": ["calendar.*", "catalog.location"],
                "deny": ["calendar.list_slots"],
            }
        }
    )
    set_runtime_capabilities(runtime)
    try:
        denied = resolve_tool_protocol_decision("calendar.list_slots")
        allowed = resolve_tool_protocol_decision("calendar.book_slot")
    finally:
        set_runtime_capabilities(None)

    assert denied.allowed is False
    assert denied.reason == "deny:calendar.list_slots"
    assert denied.enforcement_enabled is True
    assert denied.source == "test_tool_protocol_gate"

    assert allowed.allowed is True
    assert allowed.reason is None


def test_tool_protocol_gate_blocks_allowlist_miss():
    runtime = _runtime({"tools": {"allow": ["catalog.location"]}})
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_tool_protocol_decision("calendar.list_slots")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is False
    assert decision.reason == "allowlist_miss"


def test_tool_protocol_gate_deny_by_default(monkeypatch):
    monkeypatch.setenv("TOOL_PROTOCOL_DENY_BY_DEFAULT", "1")
    runtime = _runtime({})
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_tool_protocol_decision("catalog.location")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is False
    assert decision.reason == "deny_by_default"
    assert decision.deny_by_default is True


def test_tool_protocol_gate_enforcement_toggle(monkeypatch):
    monkeypatch.setenv("TOOL_POLICY_ENFORCEMENT", "0")
    runtime = _runtime({"tools": {"deny": ["*"]}})
    set_runtime_capabilities(runtime)
    try:
        decision = resolve_tool_protocol_decision("calendar.list_slots")
    finally:
        set_runtime_capabilities(None)

    assert decision.allowed is True
    assert decision.enforcement_enabled is False
