from uuid import uuid4

from app.schemas.capabilities import CapabilitiesPayload
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.capability_registry_snapshot_service import (
    build_capability_registry_snapshot,
    build_requested_fact_scopes,
)


def _runtime(payload: dict, *, source: str = "test_capability_registry_snapshot") -> RuntimeCapabilities:
    return RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate(payload),
        client_id=uuid4(),
        branch_id=None,
        source=source,
        has_records=True,
        has_tool_policy_records="tools" in payload,
    )


def test_build_capability_registry_snapshot_compiles_runtime_payload(monkeypatch):
    monkeypatch.delenv("TOOL_POLICY_ENFORCEMENT", raising=False)
    monkeypatch.delenv("TOOL_PROTOCOL_DENY_BY_DEFAULT", raising=False)
    runtime = _runtime(
        {
            "allowed_fact_scopes": [" INFO.HOURS ", "consult.*", "info.hours"],
            "handoff_policy": " manager_request_only ",
            "tools": {"allow": ["catalog.location", "calendar.*"]},
        }
    )
    set_runtime_capabilities(runtime)
    try:
        snapshot = build_capability_registry_snapshot()
    finally:
        set_runtime_capabilities(None)

    assert snapshot.schema_version == "capability_registry_snapshot.v1"
    assert snapshot.source == "test_capability_registry_snapshot"
    assert snapshot.fact_scope_policy.allowed_scopes == ("info.hours", "consult.*")
    assert snapshot.handoff_policy.policy == "manager_request_only"
    assert snapshot.tool_protocol_policy.allow_tokens == (
        "catalog.location",
        "calendar.*",
    )
    assert snapshot.tool_protocol_policy.enforcement_enabled is True
    assert snapshot.tool_protocol_policy.deny_by_default is True


def test_build_capability_registry_snapshot_respects_env_toggles(monkeypatch):
    monkeypatch.setenv("TOOL_POLICY_ENFORCEMENT", "0")
    monkeypatch.setenv("TOOL_PROTOCOL_DENY_BY_DEFAULT", "1")
    runtime = _runtime({})
    set_runtime_capabilities(runtime)
    try:
        snapshot = build_capability_registry_snapshot()
    finally:
        set_runtime_capabilities(None)

    assert snapshot.tool_protocol_policy.enforcement_enabled is False
    assert snapshot.tool_protocol_policy.deny_by_default is True


def test_build_requested_fact_scopes_is_snapshot_owned():
    assert build_requested_fact_scopes(
        tool_action="info",
        pack_refs=["pricing", " INFO.HOURS ", "pricing", " "],
    ) == ["info.pricing", "info.hours"]
