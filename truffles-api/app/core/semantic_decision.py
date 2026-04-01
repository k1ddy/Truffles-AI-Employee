from __future__ import annotations

from typing import Any, Iterable, Literal, Mapping
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

SemanticRequestedOutcome = Literal["fact", "collect", "handoff"]
_SLOT_ALIASES = {
    "service_query": "service",
    "time": "datetime",
    "date": "datetime",
    "datetime": "datetime",
    "customer_name": "name",
    "phone_number": "phone",
}
_REFERENT_KEYS = {"service", "specialist", "branch", "booking_ref", "customer"}


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _normalize_token(item)
        if not cleaned or cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return normalized


def _normalize_string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for key, item in value.items():
        cleaned_key = _normalize_token(key)
        cleaned_value = _normalize_token(item)
        if not cleaned_key or cleaned_value is None:
            continue
        normalized[cleaned_key] = cleaned_value
    return normalized


def _normalize_booking_slot_name(value: Any) -> str | None:
    cleaned = _normalize_token(value)
    if not cleaned:
        return None
    return _SLOT_ALIASES.get(cleaned, cleaned)


def _normalize_slots(value: Any) -> dict[str, str]:
    normalized = _normalize_string_dict(value)
    remapped: dict[str, str] = {}
    for key, item in normalized.items():
        canonical_key = _normalize_booking_slot_name(key) or key
        remapped[canonical_key] = item
    return remapped


def _normalize_entity_refs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in value:
        entry: dict[str, Any] = {}
        if isinstance(item, Mapping):
            entity_id = _normalize_token(item.get("entity_id")) or _normalize_token(item.get("id"))
            entity_type = _normalize_token(item.get("entity_type")) or _normalize_token(item.get("type"))
            source_ref = _normalize_token(item.get("source_ref"))
            value_token = _normalize_token(item.get("value")) or _normalize_token(item.get("label"))
            if entity_id:
                entry["entity_id"] = entity_id
            if entity_type:
                entry["entity_type"] = entity_type
            if source_ref:
                entry["source_ref"] = source_ref
            if value_token:
                entry["value"] = value_token
            confidence = item.get("confidence")
            if isinstance(confidence, (int, float)):
                entry["confidence"] = max(0.0, min(float(confidence), 1.0))
        elif isinstance(item, str):
            entity_id = _normalize_token(item)
            if entity_id:
                entry["entity_id"] = entity_id
        if not entry:
            continue
        dedupe_key = (
            str(entry.get("entity_id") or ""),
            str(entry.get("entity_type") or ""),
            str(entry.get("source_ref") or ""),
            str(entry.get("value") or ""),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(entry)
    return normalized


def _normalize_referents(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for raw_key, raw_payload in value.items():
        referent_key = _normalize_token(raw_key)
        if referent_key not in _REFERENT_KEYS or not isinstance(raw_payload, Mapping):
            continue
        entry: dict[str, Any] = {}
        for source_key, target_key in (
            ("value", "value"),
            ("entity_id", "entity_id"),
            ("entity_type", "entity_type"),
            ("source_ref", "source_ref"),
        ):
            token = _normalize_token(raw_payload.get(source_key))
            if token:
                entry[target_key] = token
        if entry:
            normalized[referent_key] = entry
    return normalized


def _confidence_band(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    confidence = max(0.0, min(float(value), 1.0))
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.55:
        return "medium"
    return "low"


class MissingInformationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_reply_type: str | None = None
    reason: str | None = None
    pending_question_act: str | None = None
    pending_question_target: str | None = None
    active_question_relation: str | None = None
    next_question: str | None = None
    open_questions: list[str] = Field(default_factory=list)


class GroundingRequirementsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pack_refs: list[str] = Field(default_factory=list)
    entity_refs: list[dict[str, Any]] = Field(default_factory=list)
    referents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    subject_kind: str | None = None
    temporal_scope: str | None = None
    resolution_mode: str | None = None
    resolver_id: str | None = None
    resolver_version: str | None = None


class SemanticDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "semantic_decision.v1"
    decision_id: str = Field(default_factory=lambda: uuid4().hex)
    turn_id: str | None = None
    conversation_id: str | None = None
    requested_outcome: SemanticRequestedOutcome
    intent: str
    capability_id: str | None = None
    tool_action_hint: str | None = None
    semantic_slots: dict[str, str] = Field(default_factory=dict)
    missing_information: MissingInformationV1 = Field(default_factory=MissingInformationV1)
    grounding_requirements: GroundingRequirementsV1 = Field(default_factory=GroundingRequirementsV1)
    needs_human: bool = False
    degrade_reason_code: str | None = None
    handoff_reason_code: str | None = None
    decision_summary: str | None = None
    goal: str | None = None
    confidence_band: str | None = None
    risk_signals: list[str] = Field(default_factory=list)
    language: str | None = None

    @classmethod
    def from_policy_core_payload(cls, payload: Mapping[str, Any]) -> SemanticDecisionV1:
        action = _normalize_token(payload.get("action")) or "handoff"
        if action not in {"fact", "collect", "handoff"}:
            raise ValueError(f"semantic_requested_outcome_invalid:{action}")

        next_question = _normalize_booking_slot_name(payload.get("next_question"))
        open_questions = [
            item
            for item in (
                _normalize_booking_slot_name(raw_item)
                for raw_item in _normalize_list(payload.get("open_questions"))
            )
            if item
        ]
        if next_question and not open_questions:
            open_questions = [next_question]

        pending_question_act = _normalize_token(payload.get("pending_question_act"))
        pending_question_target = _normalize_token(payload.get("pending_question_target"))
        active_question_relation = _normalize_token(payload.get("active_question_relation"))
        expected_reply_type = _normalize_token(payload.get("expected_reply_type"))
        reason = _normalize_token(payload.get("reason"))
        if action == "handoff":
            next_question = None
            open_questions = []
            pending_question_act = None
            pending_question_target = None
            active_question_relation = None
            expected_reply_type = None

        needs_human = bool(payload.get("needs_manager")) or action == "handoff"

        return cls(
            requested_outcome=action,
            intent=_normalize_token(payload.get("intent")) or "other",
            capability_id=_normalize_token(payload.get("capability")),
            tool_action_hint=_normalize_token(
                payload.get("tool_action_hint") or payload.get("tool_action")
            ),
            semantic_slots=_normalize_slots(payload.get("slots")),
            missing_information=MissingInformationV1(
                expected_reply_type=expected_reply_type,
                reason=reason if any(
                    (
                        expected_reply_type,
                        pending_question_act,
                        pending_question_target,
                        active_question_relation,
                        next_question,
                        open_questions,
                    )
                ) else None,
                pending_question_act=pending_question_act,
                pending_question_target=pending_question_target,
                active_question_relation=active_question_relation,
                next_question=next_question,
                open_questions=open_questions,
            ),
            grounding_requirements=GroundingRequirementsV1(
                pack_refs=_normalize_list(payload.get("pack_refs")),
                entity_refs=_normalize_entity_refs(payload.get("entity_refs")),
                referents=_normalize_referents(payload.get("referents")),
                subject_kind=_normalize_token(payload.get("subject_kind")),
                temporal_scope=_normalize_token(payload.get("temporal_scope")),
                resolution_mode=_normalize_token(payload.get("resolution_mode")),
                resolver_id=_normalize_token(payload.get("resolver_id")),
                resolver_version=_normalize_token(payload.get("resolver_version")),
            ),
            needs_human=needs_human,
            handoff_reason_code=reason if needs_human else None,
            decision_summary=reason or _normalize_token(payload.get("goal")) or _normalize_token(
                payload.get("intent")
            ),
            goal=_normalize_token(payload.get("goal")),
            confidence_band=_confidence_band(payload.get("confidence")),
            risk_signals=_normalize_list(payload.get("risk_signals")),
            language=_normalize_token(payload.get("language")),
        )

    def as_policy_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "intent": self.intent,
            "action": self.requested_outcome,
            "slots": dict(self.semantic_slots),
            "needs_manager": self.needs_human,
            "risk_signals": list(self.risk_signals),
        }
        if self.tool_action_hint:
            payload["tool_action_hint"] = self.tool_action_hint
        if self.goal:
            payload["goal"] = self.goal
        if self.decision_summary:
            payload["reason"] = self.decision_summary
        if self.language:
            payload["language"] = self.language
        if self.capability_id:
            payload["capability"] = self.capability_id

        missing_information = self.missing_information.model_dump(
            mode="python",
            exclude_none=True,
        )
        payload.update(missing_information)

        grounding = self.grounding_requirements.model_dump(
            mode="python",
            exclude_none=True,
        )
        payload.update(grounding)
        return payload


__all__ = [
    "GroundingRequirementsV1",
    "MissingInformationV1",
    "SemanticDecisionV1",
    "SemanticRequestedOutcome",
]
