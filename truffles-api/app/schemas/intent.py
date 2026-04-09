from __future__ import annotations

from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


def _summarize_validation_error(exc: ValidationError, *, limit: int = 3) -> str:
    parts: list[str] = []
    for item in exc.errors():
        loc = item.get("loc") or []
        loc_text = ".".join(str(entry) for entry in loc) if loc else ""
        msg = item.get("msg") or "invalid"
        if loc_text:
            parts.append(f"{loc_text}:{msg}")
        else:
            parts.append(msg)
        if len(parts) >= limit:
            break
    return "; ".join(parts) or "invalid_payload"


ANSWER_INTERPRETER_SLOT_ALIASES = {
    "service": "service",
    "service_choice": "service",
    "service_query": "service",
    "time": "datetime",
    "datetime": "datetime",
    "date": "datetime",
    "name": "name",
}

_TOOL_ARGS_ALLOWED_FIELDS: dict[str, set[str]] = {
    "calendar.list_slots": {
        "service_query",
        "date",
        "start_at",
        "duration_min",
        "specialist_id",
        "specialist_name",
    },
    "calendar.book_slot": {
        "service_query",
        "start_at",
        "end_at",
        "specialist_id",
        "specialist_name",
        "customer_name",
        "customer_phone",
    },
    "calendar.get_booking": {"appointment_id"},
    "calendar.reschedule": {"appointment_id", "start_at", "end_at"},
    "calendar.cancel": {"appointment_id", "reason"},
    "catalog.service_query": {"service_query"},
    "catalog.location": {"info_ref", "info_refs"},
    "catalog.portfolio": {"service_query"},
}

_TOOL_ARG_KIND_TEXT = "text"
_TOOL_ARG_KIND_TEXT_LIST = "text_list"
_TOOL_ARG_KIND_NUMBER = "number"
_TOOL_ARG_FALLBACK_KINDS: dict[str, str] = {
    "info_refs": _TOOL_ARG_KIND_TEXT_LIST,
    "duration_min": _TOOL_ARG_KIND_NUMBER,
}

_TOOL_ARGS_FIELD_KINDS: dict[str, dict[str, str]] = {
    "calendar.list_slots": {
        "service_query": _TOOL_ARG_KIND_TEXT,
        "date": _TOOL_ARG_KIND_TEXT,
        "start_at": _TOOL_ARG_KIND_TEXT,
        "duration_min": _TOOL_ARG_KIND_NUMBER,
        "specialist_id": _TOOL_ARG_KIND_TEXT,
        "specialist_name": _TOOL_ARG_KIND_TEXT,
    },
    "calendar.book_slot": {
        "service_query": _TOOL_ARG_KIND_TEXT,
        "start_at": _TOOL_ARG_KIND_TEXT,
        "end_at": _TOOL_ARG_KIND_TEXT,
        "specialist_id": _TOOL_ARG_KIND_TEXT,
        "specialist_name": _TOOL_ARG_KIND_TEXT,
        "customer_name": _TOOL_ARG_KIND_TEXT,
        "customer_phone": _TOOL_ARG_KIND_TEXT,
    },
    "calendar.get_booking": {
        "appointment_id": _TOOL_ARG_KIND_TEXT,
    },
    "calendar.reschedule": {
        "appointment_id": _TOOL_ARG_KIND_TEXT,
        "start_at": _TOOL_ARG_KIND_TEXT,
        "end_at": _TOOL_ARG_KIND_TEXT,
    },
    "calendar.cancel": {
        "appointment_id": _TOOL_ARG_KIND_TEXT,
        "reason": _TOOL_ARG_KIND_TEXT,
    },
    "catalog.service_query": {
        "service_query": _TOOL_ARG_KIND_TEXT,
    },
    "catalog.location": {
        "info_ref": _TOOL_ARG_KIND_TEXT,
        "info_refs": _TOOL_ARG_KIND_TEXT_LIST,
    },
    "catalog.portfolio": {
        "service_query": _TOOL_ARG_KIND_TEXT,
    },
}

_MASTER_QUERY_INTENTS = {"master_query"}
_MASTER_QUERY_INTENT_ALIASES = {"master": "master_query"}
_MASTER_QUERY_FACT_TOOL_ACTIONS = {"info", "catalog.service_query"}
_MASTER_QUERY_COLLECT_TOOL_ACTIONS = {"collect", "catalog.service_query"}

SEMANTIC_SUBJECT_KIND_VALUES = {
    "service",
    "specialist",
    "branch",
    "booking",
    "general",
}
SEMANTIC_CAPABILITY_VALUES = {
    "pricing",
    "duration",
    "master",
    "location",
    "hours",
    "promotions",
    "bookability",
    "live_availability",
    "booking_manage",
    "consultation",
    "portfolio",
    "other",
}
SEMANTIC_TEMPORAL_SCOPE_VALUES = {
    "none",
    "specific_time",
    "day",
    "weekday",
    "weekend",
    "date_range",
}
SEMANTIC_RESOLUTION_MODE_VALUES = {
    "direct",
    "referent_followup",
    "clarify_missing_subject",
    "clarify_missing_time",
    "ask_about_requested_slot",
    "policy_fact",
    "live_calendar",
}
SEMANTIC_RESOLUTION_MODE_ALIASES = {
    "collect": "direct",
}
SEMANTIC_PENDING_QUESTION_ACT_VALUES = {
    "fill_requested_slot",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
}
SEMANTIC_PENDING_QUESTION_ACT_ALIASES = {
    "referent_followup": None,
}
SEMANTIC_PENDING_QUESTION_TARGET_VALUES = {
    "time",
    "specialist",
}
SEMANTIC_ACTIVE_QUESTION_RELATION_VALUES = {
    "fill_requested_slot",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
    "referent_followup",
    "generic_info_interrupt",
    "specialist_availability_interrupt",
    "specialist_availability_followup",
    "tool_result_followup_specialist_missing",
}
SEMANTIC_REFERENT_KEYS = {
    "service",
    "specialist",
    "branch",
    "booking_ref",
    "customer",
}


def _is_supported_number_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        if stripped.startswith(("+", "-")):
            stripped = stripped[1:]
        return stripped.isdigit()
    return False


def _validate_tool_arg_value(*, kind: str, value: Any) -> bool:
    if kind == _TOOL_ARG_KIND_TEXT:
        return isinstance(value, str)
    if kind == _TOOL_ARG_KIND_TEXT_LIST:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if kind == _TOOL_ARG_KIND_NUMBER:
        return _is_supported_number_value(value)
    return False


def validate_tool_args_shape(
    *,
    tool_action: str | None,
    tool_args: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if tool_args is None:
        return {}, None
    if not isinstance(tool_args, dict):
        return None, "tool_args_invalid"
    for key in tool_args:
        if not isinstance(key, str):
            return None, "tool_args_key_invalid"

    normalized_action = (
        tool_action.strip().casefold()
        if isinstance(tool_action, str) and tool_action.strip()
        else None
    )

    normalized_args = dict(tool_args)
    if not normalized_action:
        return normalized_args, None

    allowed_fields = _TOOL_ARGS_ALLOWED_FIELDS.get(normalized_action) or set()
    if allowed_fields:
        for key in tool_args:
            if key not in allowed_fields:
                return None, f"tool_args_unknown_field:{key}"

    field_kinds = _TOOL_ARGS_FIELD_KINDS.get(normalized_action) or {}
    for key, value in normalized_args.items():
        if value is None:
            continue
        kind = field_kinds.get(key) or _TOOL_ARG_FALLBACK_KINDS.get(key, _TOOL_ARG_KIND_TEXT)
        if not _validate_tool_arg_value(kind=kind, value=value):
            return None, f"tool_args_type_invalid:{key}"
    return normalized_args, None


def _normalize_required_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}_required")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field}_required")
    return cleaned.casefold()


def _normalize_string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field}_invalid")
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field}_invalid")
        text = item.strip()
        if text:
            cleaned.append(text)
    return cleaned


def _normalize_slots(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("slots_invalid")
    cleaned: dict[str, str] = {}
    for key, val in value.items():
        if not isinstance(key, str):
            raise ValueError("slots_invalid")
        if val is None:
            continue
        if not isinstance(val, str):
            raise ValueError("slots_invalid")
        cleaned[key] = val.strip()
    return cleaned


def _normalize_optional_string(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field}_invalid")
    cleaned = value.strip()
    return cleaned or None


def _normalize_optional_semantic_token(
    value: Any,
    *,
    field: str,
    allowed: set[str],
    aliases: dict[str, str | None] | None = None,
) -> str | None:
    cleaned = _normalize_optional_string(value, field=field)
    if cleaned is None:
        return None
    token = cleaned.casefold()
    if aliases and token in aliases:
        return aliases[token]
    if token not in allowed:
        raise ValueError(f"{field}_invalid")
    return token


def _normalize_optional_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        raise ValueError("confidence_invalid")
    if not isinstance(value, (int, float)):
        raise ValueError("confidence_invalid")
    normalized = float(value)
    if normalized < 0 or normalized > 1:
        raise ValueError("confidence_invalid")
    return normalized


def _normalize_master_service_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_entity_refs(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("entity_refs_invalid")
    cleaned: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, str):
            token = item.strip()
            if token:
                cleaned.append({"entity_id": token})
            continue
        if not isinstance(item, dict):
            raise ValueError("entity_refs_invalid")
        row: dict[str, Any] = {}
        entity_id = item.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id.strip():
            fallback_id = item.get("id")
            if isinstance(fallback_id, str) and fallback_id.strip():
                entity_id = fallback_id
        if isinstance(entity_id, str) and entity_id.strip():
            row["entity_id"] = entity_id.strip()
        entity_type = item.get("entity_type")
        if not isinstance(entity_type, str) or not entity_type.strip():
            fallback_type = item.get("type")
            if isinstance(fallback_type, str) and fallback_type.strip():
                entity_type = fallback_type
        if isinstance(entity_type, str) and entity_type.strip():
            row["entity_type"] = entity_type.strip()
        source_ref = item.get("source_ref")
        if isinstance(source_ref, str) and source_ref.strip():
            row["source_ref"] = source_ref.strip()
        entity_value = item.get("value")
        if not isinstance(entity_value, str) or not entity_value.strip():
            fallback_value = item.get("label")
            if isinstance(fallback_value, str) and fallback_value.strip():
                entity_value = fallback_value
        if isinstance(entity_value, str) and entity_value.strip():
            row["value"] = entity_value.strip()
        confidence = item.get("confidence")
        if isinstance(confidence, (int, float)):
            row["confidence"] = max(0.0, min(float(confidence), 1.0))
        if row:
            cleaned.append(row)
    return cleaned


def _normalize_referent_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("referents_invalid")
    row: dict[str, Any] = {}
    for source_key, target_key in (
        ("value", "value"),
        ("entity_id", "entity_id"),
        ("entity_type", "entity_type"),
        ("source_ref", "source_ref"),
    ):
        raw_value = value.get(source_key)
        if isinstance(raw_value, str) and raw_value.strip():
            row[target_key] = raw_value.strip()
    if not row:
        return {}
    return row


def _normalize_referents(value: Any) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("referents_invalid")
    cleaned: dict[str, dict[str, Any]] = {}
    for key, raw_payload in value.items():
        if not isinstance(key, str):
            raise ValueError("referents_invalid")
        referent_key = key.strip().casefold()
        if referent_key not in SEMANTIC_REFERENT_KEYS:
            raise ValueError("referents_invalid")
        payload = _normalize_referent_payload(raw_payload)
        if payload:
            cleaned[referent_key] = payload
    return cleaned


def _referent_value(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("value")
    if isinstance(value, str) and value.strip():
        return value.strip()
    entity_id = payload.get("entity_id")
    if isinstance(entity_id, str) and entity_id.strip():
        return entity_id.strip()
    return None


def _referent_entity_id(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    entity_id = payload.get("entity_id")
    if isinstance(entity_id, str) and entity_id.strip():
        return entity_id.strip()
    return None


class DialogueControllerOutput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    class_name: str = Field(alias="class")
    goal: str
    intents: list[str] = Field(default_factory=list)
    slots: dict[str, str] = Field(default_factory=dict)
    followups: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    reason: str | None = None
    carryover: dict[str, Any] | None = None

    @field_validator("class_name", mode="before")
    @classmethod
    def _validate_class_name(cls, value: Any) -> str:
        return _normalize_required_string(value, field="class")

    @field_validator("goal", mode="before")
    @classmethod
    def _validate_goal(cls, value: Any) -> str:
        return _normalize_required_string(value, field="goal")

    @field_validator("intents", mode="before")
    @classmethod
    def _validate_intents(cls, value: Any) -> list[str]:
        return _normalize_string_list(value, field="intents")

    @field_validator("followups", mode="before")
    @classmethod
    def _validate_followups(cls, value: Any) -> list[str]:
        return _normalize_string_list(value, field="followups")

    @field_validator("safety_flags", mode="before")
    @classmethod
    def _validate_safety_flags(cls, value: Any) -> list[str]:
        return _normalize_string_list(value, field="safety_flags")

    @field_validator("slots", mode="before")
    @classmethod
    def _validate_slots(cls, value: Any) -> dict[str, str]:
        return _normalize_slots(value)


class AnswerInterpreterOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slot: str
    value: str = ""
    confidence: float = Field(..., ge=0, le=1)
    reason: str | None = None

    @field_validator("slot", mode="before")
    @classmethod
    def _validate_slot(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("slot_required")
        cleaned = value.strip().casefold()
        if not cleaned:
            raise ValueError("slot_required")
        normalized = ANSWER_INTERPRETER_SLOT_ALIASES.get(cleaned)
        if not normalized:
            raise ValueError("invalid_slot")
        return normalized

    @field_validator("value", mode="before")
    @classmethod
    def _validate_value(cls, value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("value_invalid")
        return value.strip()


class LlmPlanOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome: str
    tool_action: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    pack_refs: list[str] = Field(default_factory=list)
    language: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    reason: str | None = None
    goal: str | None = None
    slot_state: dict[str, str] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("outcome", mode="before")
    @classmethod
    def _validate_outcome(cls, value: Any) -> str:
        return _normalize_required_string(value, field="outcome")

    @field_validator("tool_action", "language", "reason", "goal", mode="before")
    @classmethod
    def _validate_optional_fields(cls, value: Any, info) -> str | None:
        return _normalize_optional_string(value, field=info.field_name)

    @field_validator("tool_args", mode="before")
    @classmethod
    def _validate_tool_args(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("tool_args_invalid")
        return dict(value)

    @field_validator("pack_refs", "open_questions", mode="before")
    @classmethod
    def _validate_string_lists(cls, value: Any, info) -> list[str]:
        return _normalize_string_list(value, field=info.field_name)

    @field_validator("slot_state", mode="before")
    @classmethod
    def _validate_slot_state(cls, value: Any) -> dict[str, str]:
        return _normalize_slots(value)

    @model_validator(mode="after")
    def _validate_tool_args_for_action(self):
        normalized, error = validate_tool_args_shape(
            tool_action=self.tool_action,
            tool_args=self.tool_args,
        )
        if error:
            raise ValueError(error)
        self.tool_args = normalized or {}
        return self


class LlmPolicyCoreOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent: str
    action: str
    tool_action_hint: str = Field(
        validation_alias=AliasChoices("tool_action_hint", "tool_action")
    )
    pack_refs: list[str] = Field(default_factory=list)
    slots: dict[str, str] = Field(default_factory=dict)
    expected_reply_type: str | None = None
    next_question: str | None = None
    open_questions: list[str] = Field(default_factory=list)
    needs_manager: bool = False
    risk_signals: list[str] = Field(default_factory=list)
    language: str | None = None
    confidence: float = Field(0.0, ge=0, le=1)
    reason: str | None = None
    goal: str | None = None
    entity_refs: list[dict[str, Any]] = Field(default_factory=list)
    referents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    subject_kind: str | None = None
    capability: str | None = None
    temporal_scope: str | None = None
    alternate_datetime: str | None = None
    resolution_mode: str | None = None
    pending_question_act: str | None = None
    pending_question_target: str | None = None
    active_question_relation: str | None = None
    resolver_id: str | None = None
    resolver_version: str | None = None

    @field_validator("intent", "action", "tool_action_hint", mode="before")
    @classmethod
    def _validate_action(cls, value: Any, info) -> str:
        normalized = _normalize_required_string(value, field=info.field_name)
        if info.field_name == "intent":
            return _MASTER_QUERY_INTENT_ALIASES.get(normalized, normalized)
        return normalized

    @field_validator("confidence", mode="before")
    @classmethod
    def _validate_confidence(cls, value: Any) -> float:
        return _normalize_optional_confidence(value)

    @field_validator(
        "tool_action_hint",
        "language",
        "reason",
        "goal",
        "expected_reply_type",
        "next_question",
        "alternate_datetime",
        "resolver_id",
        "resolver_version",
        mode="before",
    )
    @classmethod
    def _validate_optional_fields(cls, value: Any, info) -> str | None:
        return _normalize_optional_string(value, field=info.field_name)

    @field_validator("pack_refs", "open_questions", "risk_signals", mode="before")
    @classmethod
    def _validate_string_lists(cls, value: Any, info) -> list[str]:
        return _normalize_string_list(value, field=info.field_name)

    @field_validator("slots", mode="before")
    @classmethod
    def _validate_slots(cls, value: Any) -> dict[str, str]:
        return _normalize_slots(value)

    @field_validator("entity_refs", mode="before")
    @classmethod
    def _validate_entity_refs(cls, value: Any) -> list[dict[str, Any]]:
        return _normalize_entity_refs(value)

    @field_validator("referents", mode="before")
    @classmethod
    def _validate_referents(cls, value: Any) -> dict[str, dict[str, Any]]:
        return _normalize_referents(value)

    @field_validator("subject_kind", mode="before")
    @classmethod
    def _validate_subject_kind(cls, value: Any) -> str | None:
        return _normalize_optional_semantic_token(
            value,
            field="subject_kind",
            allowed=SEMANTIC_SUBJECT_KIND_VALUES,
        )

    @field_validator("capability", mode="before")
    @classmethod
    def _validate_capability(cls, value: Any) -> str | None:
        return _normalize_optional_semantic_token(
            value,
            field="capability",
            allowed=SEMANTIC_CAPABILITY_VALUES,
        )

    @field_validator("temporal_scope", mode="before")
    @classmethod
    def _validate_temporal_scope(cls, value: Any) -> str | None:
        return _normalize_optional_semantic_token(
            value,
            field="temporal_scope",
            allowed=SEMANTIC_TEMPORAL_SCOPE_VALUES,
        )

    @field_validator("resolution_mode", mode="before")
    @classmethod
    def _validate_resolution_mode(cls, value: Any) -> str | None:
        return _normalize_optional_semantic_token(
            value,
            field="resolution_mode",
            allowed=SEMANTIC_RESOLUTION_MODE_VALUES,
            aliases=SEMANTIC_RESOLUTION_MODE_ALIASES,
        )

    @field_validator("pending_question_act", mode="before")
    @classmethod
    def _validate_pending_question_act(cls, value: Any) -> str | None:
        return _normalize_optional_semantic_token(
            value,
            field="pending_question_act",
            allowed=SEMANTIC_PENDING_QUESTION_ACT_VALUES,
            aliases=SEMANTIC_PENDING_QUESTION_ACT_ALIASES,
        )

    @field_validator("pending_question_target", mode="before")
    @classmethod
    def _validate_pending_question_target(cls, value: Any) -> str | None:
        return _normalize_optional_semantic_token(
            value,
            field="pending_question_target",
            allowed=SEMANTIC_PENDING_QUESTION_TARGET_VALUES,
        )

    @field_validator("active_question_relation", mode="before")
    @classmethod
    def _validate_active_question_relation(cls, value: Any) -> str | None:
        return _normalize_optional_semantic_token(
            value,
            field="active_question_relation",
            allowed=SEMANTIC_ACTIVE_QUESTION_RELATION_VALUES,
        )

    @field_validator("needs_manager", mode="before")
    @classmethod
    def _validate_needs_manager(cls, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        raise ValueError("needs_manager_invalid")

    @model_validator(mode="after")
    def _validate_master_query_contract(self):
        if self.intent not in _MASTER_QUERY_INTENTS:
            return self

        slot_service = _normalize_master_service_value(self.slots.get("service"))
        referent_service = _referent_value(self.referents.get("service"))
        has_service_query = bool(slot_service or referent_service)

        if self.action == "fact":
            if self.tool_action_hint not in _MASTER_QUERY_FACT_TOOL_ACTIONS:
                raise ValueError("master_query_tool_action_invalid")
            if not has_service_query:
                raise ValueError("master_query_service_required")
            return self

        if self.action == "collect":
            if self.tool_action_hint not in _MASTER_QUERY_COLLECT_TOOL_ACTIONS:
                raise ValueError("master_query_collect_tool_action_invalid")
            # Clarify path is valid when service is missing and the model explicitly asks for it.
            collect_requires_service = bool(
                self.next_question == "service" or "service" in self.open_questions
            )
            if not has_service_query and not collect_requires_service:
                raise ValueError("master_query_collect_service_clarify_required")
            return self

        return self

def validate_dialogue_controller_output(
    payload_json: dict[str, Any],
) -> tuple[DialogueControllerOutput | None, str | None]:
    try:
        contract = DialogueControllerOutput.model_validate(payload_json)
    except ValidationError as exc:
        return None, f"dialogue_controller_error:{_summarize_validation_error(exc)}"
    return contract, None


def validate_answer_interpreter_output(
    payload_json: dict[str, Any],
) -> tuple[AnswerInterpreterOutput | None, str | None]:
    try:
        contract = AnswerInterpreterOutput.model_validate(payload_json)
    except ValidationError as exc:
        return None, f"answer_interpreter_error:{_summarize_validation_error(exc)}"
    return contract, None


def validate_llm_plan_output(
    payload_json: dict[str, Any],
) -> tuple[LlmPlanOutput | None, str | None]:
    try:
        contract = LlmPlanOutput.model_validate(payload_json)
    except ValidationError as exc:
        return None, f"llm_plan_error:{_summarize_validation_error(exc)}"
    return contract, None


def validate_llm_policy_core_output(
    payload_json: dict[str, Any],
) -> tuple[LlmPolicyCoreOutput | None, str | None]:
    try:
        contract = LlmPolicyCoreOutput.model_validate(payload_json)
    except ValidationError as exc:
        return None, f"llm_policy_core_error:{_summarize_validation_error(exc)}"
    return contract, None
