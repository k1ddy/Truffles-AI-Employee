from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field


class ToolRegistryEntrySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "tool_registry_entry_snapshot.v1"
    tool_action: str
    tool_group: str
    accepts_service_query: bool = False
    accepts_specialist_name: bool = False
    accepts_specialist_id: bool = False
    accepts_appointment_id: bool = False
    accepts_customer_name: bool = False
    accepts_customer_phone: bool = False


class ToolRegistrySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "tool_registry_snapshot.v1"
    registry_version: str = "v1"
    entries: dict[str, ToolRegistryEntrySnapshotV1] = Field(default_factory=dict)
    policy_info_action_map: dict[str, str] = Field(default_factory=dict)

    @property
    def tool_actions(self) -> tuple[str, ...]:
        return tuple(self.entries.keys())


_ENTRY_DEFINITIONS_V1: tuple[dict[str, object], ...] = (
    {
        "tool_action": "calendar.list_slots",
        "tool_group": "calendar",
        "accepts_service_query": True,
        "accepts_specialist_name": True,
        "accepts_specialist_id": True,
    },
    {
        "tool_action": "calendar.book_slot",
        "tool_group": "calendar",
        "accepts_service_query": True,
        "accepts_specialist_name": True,
        "accepts_specialist_id": True,
        "accepts_customer_name": True,
        "accepts_customer_phone": True,
    },
    {
        "tool_action": "calendar.get_booking",
        "tool_group": "calendar",
        "accepts_appointment_id": True,
    },
    {
        "tool_action": "calendar.reschedule",
        "tool_group": "calendar",
        "accepts_appointment_id": True,
    },
    {
        "tool_action": "calendar.cancel",
        "tool_group": "calendar",
        "accepts_appointment_id": True,
    },
    {
        "tool_action": "catalog.service_query",
        "tool_group": "catalog",
        "accepts_service_query": True,
    },
    {
        "tool_action": "catalog.location",
        "tool_group": "catalog",
    },
    {
        "tool_action": "catalog.portfolio",
        "tool_group": "catalog",
        "accepts_service_query": True,
    },
)

_POLICY_INFO_ACTION_MAP_V1: dict[str, str] = {
    "pricing": "catalog.service_query",
    "duration": "catalog.service_query",
    "promotions": "catalog.service_query",
    "services_overview": "catalog.service_query",
    "location": "catalog.location",
    "hours": "catalog.location",
    "parking": "catalog.location",
}


@lru_cache(maxsize=1)
def build_tool_registry_snapshot() -> ToolRegistrySnapshotV1:
    entries = {
        str(payload["tool_action"]): ToolRegistryEntrySnapshotV1.model_validate(payload)
        for payload in _ENTRY_DEFINITIONS_V1
    }
    return ToolRegistrySnapshotV1(
        entries=entries,
        policy_info_action_map=dict(_POLICY_INFO_ACTION_MAP_V1),
    )


def list_declared_tool_actions() -> tuple[str, ...]:
    return build_tool_registry_snapshot().tool_actions


def declared_tool_action_set() -> frozenset[str]:
    return frozenset(list_declared_tool_actions())


def resolve_tool_registry_entry(tool_action: str | None) -> ToolRegistryEntrySnapshotV1 | None:
    if not isinstance(tool_action, str):
        return None
    normalized = tool_action.strip().casefold()
    if not normalized:
        return None
    return build_tool_registry_snapshot().entries.get(normalized)


def resolve_policy_info_tool_action(info_ref: str | None) -> str | None:
    if not isinstance(info_ref, str):
        return None
    normalized = info_ref.strip().casefold()
    if not normalized:
        return None
    return build_tool_registry_snapshot().policy_info_action_map.get(normalized)


def list_policy_info_tool_actions() -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for tool_action in build_tool_registry_snapshot().policy_info_action_map.values():
        normalized = tool_action.strip().casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


__all__ = [
    "ToolRegistryEntrySnapshotV1",
    "ToolRegistrySnapshotV1",
    "build_tool_registry_snapshot",
    "declared_tool_action_set",
    "list_policy_info_tool_actions",
    "list_declared_tool_actions",
    "resolve_policy_info_tool_action",
    "resolve_tool_registry_entry",
]
