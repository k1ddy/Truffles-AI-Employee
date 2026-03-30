from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from app.models import Client
from app.schemas.capabilities import CapabilityPolicyOverrides
from app.services.capabilities_runtime import get_runtime_capabilities
from app.services.pack_runtime_service import load_policy_pack
from app.services.policy_registry_service import resolve_effective_policy_version
from app.services.state_machine import ConversationState

_POLICY_SECTIONS = (
    "payment_info",
    "reschedule",
    "cancel",
    "medical",
    "legal",
    "complaint",
    "discounts",
    "refund",
)

_HARD_LAW_INTENT_MAP = {
    "payment": "payment_info",
    "reschedule": "reschedule",
    "cancel_request": "cancel",
    "cancel": "cancel",
    "medical": "medical",
    "legal": "legal",
    "complaint": "complaint",
    "refund": "refund",
}

_DEFAULT_HARD_LAW_SECTIONS = (
    "reschedule",
    "cancel",
    "medical",
    "legal",
    "complaint",
    "refund",
)

_ALLOWED_OPERATIONAL_POLICY_OVERRIDE_SECTIONS = {
    "payment_info",
    "discounts",
}

_DEFAULT_ROUTING_POLICY = {
    "allow_booking_flow": False,
    "allow_truth_gate_reply": False,
    "allow_handover_create": False,
    "allow_bot_reply": False,
}

ROUTING_MATRIX_V1 = {
    ConversationState.BOT_ACTIVE.value: {
        "allow_booking_flow": True,
        "allow_truth_gate_reply": True,
        "allow_handover_create": True,
        "allow_bot_reply": True,
    },
    ConversationState.PENDING.value: {
        "allow_booking_flow": True,
        "allow_truth_gate_reply": True,
        "allow_handover_create": False,
        "allow_bot_reply": True,
    },
    ConversationState.MANAGER_ACTIVE.value: {
        "allow_booking_flow": False,
        "allow_truth_gate_reply": False,
        "allow_handover_create": False,
        "allow_bot_reply": False,
    },
}


class RoutingPolicySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "routing_policy_snapshot.v1"
    conversation_state: str
    allow_booking_flow: bool = False
    allow_truth_gate_reply: bool = False
    allow_handover_create: bool = False
    allow_bot_reply: bool = False
    source: str = "routing_matrix.v1"

    def as_compat_policy(self) -> dict[str, bool]:
        return {
            "allow_booking_flow": self.allow_booking_flow,
            "allow_truth_gate_reply": self.allow_truth_gate_reply,
            "allow_handover_create": self.allow_handover_create,
            "allow_bot_reply": self.allow_bot_reply,
        }


class PolicyPackSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "policy_pack_snapshot.v1"
    client_slug: str | None = None
    policy_type: str | None = None
    policy_pack: dict[str, Any] | None = None
    policy_source: str | None = None
    runtime_capabilities_source: str | None = None
    registry_policy_version_id: str | None = None


def _policy_str_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _get_policy_section(policy_pack: dict | None, key: str) -> dict | None:
    if not isinstance(policy_pack, dict):
        return None
    section = policy_pack.get(key)
    return section if isinstance(section, dict) else None


def _resolve_hard_law_sections(policy_pack: dict | None) -> list[str]:
    hard_law = _get_policy_section(policy_pack, "hard_law")
    sections = _policy_str_list(hard_law.get("sections") if isinstance(hard_law, dict) else None)
    if sections:
        return [section for section in sections if section in _POLICY_SECTIONS]

    intents = _policy_str_list(hard_law.get("intents") if isinstance(hard_law, dict) else None)
    resolved: list[str] = []
    for intent in intents:
        mapped = _HARD_LAW_INTENT_MAP.get(intent.casefold())
        if mapped and mapped not in resolved:
            resolved.append(mapped)
    if resolved:
        return resolved

    return [
        section
        for section in _DEFAULT_HARD_LAW_SECTIONS
        if _get_policy_section(policy_pack, section) is not None
    ]


def _looks_like_policy_pack(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("hard_law") or value.get("guard_topics"):
        return True
    return any(key in value for key in _POLICY_SECTIONS)


def _extract_policy_pack_from_config(config: dict | None) -> dict | None:
    if not isinstance(config, dict):
        return None
    direct = config.get("policy_pack")
    if _looks_like_policy_pack(direct):
        return dict(direct)
    client_pack = config.get("client_pack")
    if isinstance(client_pack, dict):
        policy = client_pack.get("policy")
        if _looks_like_policy_pack(policy):
            return dict(policy)
    legacy = config.get("policy")
    if _looks_like_policy_pack(legacy):
        return dict(legacy)
    return None


def resolve_policy_type(client: Client | None, *, client_slug: str | None) -> str | None:
    if not client or not isinstance(client.config, dict):
        return None
    policy = client.config.get("policy")
    if isinstance(policy, dict):
        policy_type = policy.get("type") or policy.get("policy_type")
        if isinstance(policy_type, str) and policy_type.strip():
            return policy_type.strip()
    legacy = client.config.get("policy_type")
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()
    if isinstance(client_slug, str) and client_slug.strip():
        return client_slug.strip()
    return None


def _load_policy_pack(*, policy_type: str | None, client_slug: str | None) -> dict | None:
    slug = policy_type or client_slug
    if not slug:
        return None
    policy_pack = load_policy_pack(slug)
    return policy_pack if isinstance(policy_pack, dict) and policy_pack else None


def _normalize_policy_override_payload(payload: dict | None) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict):
        return {}
    resolved: dict[str, dict[str, str]] = {}
    for section_key, section_payload in payload.items():
        if section_key not in _ALLOWED_OPERATIONAL_POLICY_OVERRIDE_SECTIONS:
            continue
        if not isinstance(section_payload, dict):
            continue
        response = section_payload.get("response")
        if not isinstance(response, str):
            continue
        normalized_response = response.strip()
        if not normalized_response:
            continue
        resolved[section_key] = {"response": normalized_response}
    return resolved


def _resolve_runtime_policy_overrides() -> tuple[dict[str, dict[str, str]], str | None]:
    runtime = get_runtime_capabilities()
    if runtime is None:
        return {}, None
    override_payload = runtime.payload.policy_overrides.model_dump(exclude_none=True)
    return _normalize_policy_override_payload(override_payload), runtime.source


def _resolve_registry_policy_snapshot(
    *,
    db: Session | None,
) -> tuple[dict[str, dict[str, str]], str | None]:
    runtime = get_runtime_capabilities()
    if db is None or runtime is None or runtime.client_id is None:
        return {}, None
    record = resolve_effective_policy_version(
        db,
        client_id=runtime.client_id,
        branch_id=runtime.branch_id,
    )
    if record is None:
        return {}, None
    try:
        overrides = CapabilityPolicyOverrides.model_validate(record.payload_json or {})
    except ValidationError:
        return {}, str(record.id)
    return _normalize_policy_override_payload(overrides.model_dump(exclude_none=True)), str(record.id)


def _apply_policy_overrides(
    policy_pack: dict | None,
    *,
    overrides: dict[str, dict[str, str]],
) -> dict | None:
    if not isinstance(policy_pack, dict):
        return None
    if not overrides:
        return policy_pack
    hard_law_sections = set(_resolve_hard_law_sections(policy_pack))
    merged = dict(policy_pack)
    for section_key, section_override in overrides.items():
        if section_key in hard_law_sections:
            continue
        section = _get_policy_section(policy_pack, section_key)
        if not isinstance(section, dict):
            continue
        updated_section = dict(section)
        response = section_override.get("response")
        if isinstance(response, str) and response.strip():
            updated_section["response"] = response.strip()
        merged[section_key] = updated_section
    return merged


def build_routing_policy_snapshot(state: str) -> RoutingPolicySnapshotV1:
    resolved = dict(ROUTING_MATRIX_V1.get(state) or _DEFAULT_ROUTING_POLICY)
    return RoutingPolicySnapshotV1(conversation_state=state, **resolved)


def build_policy_pack_snapshot(
    client: Client | None,
    *,
    client_slug: str | None,
    db: Session | None = None,
) -> PolicyPackSnapshotV1:
    policy_type = resolve_policy_type(client, client_slug=client_slug)
    policy_pack = None
    policy_source = None

    if client and isinstance(client.config, dict):
        config_policy_pack = _extract_policy_pack_from_config(client.config)
        if config_policy_pack is not None:
            policy_pack = config_policy_pack
            policy_source = "client.config.policy_pack"
        elif policy_type:
            policy_pack = _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
            if policy_pack is not None:
                policy_source = f"pack_runtime:{policy_type}"

    registry_overrides, registry_policy_version_id = _resolve_registry_policy_snapshot(db=db)
    runtime_overrides, runtime_source = _resolve_runtime_policy_overrides()
    policy_pack = _apply_policy_overrides(policy_pack, overrides=registry_overrides)
    policy_pack = _apply_policy_overrides(policy_pack, overrides=runtime_overrides)

    return PolicyPackSnapshotV1(
        client_slug=client_slug.strip() if isinstance(client_slug, str) and client_slug.strip() else None,
        policy_type=policy_type,
        policy_pack=policy_pack,
        policy_source=policy_source,
        runtime_capabilities_source=runtime_source,
        registry_policy_version_id=registry_policy_version_id,
    )


__all__ = [
    "PolicyPackSnapshotV1",
    "ROUTING_MATRIX_V1",
    "RoutingPolicySnapshotV1",
    "_resolve_hard_law_sections",
    "build_policy_pack_snapshot",
    "build_routing_policy_snapshot",
    "resolve_policy_type",
]
