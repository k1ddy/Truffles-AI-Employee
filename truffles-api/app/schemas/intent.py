from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


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

_TOOL_ARGS_LIST_FIELDS = {"info_refs"}
_TOOL_ARGS_NUMBER_FIELDS = {"duration_min"}


def validate_tool_args_shape(
    *,
    tool_action: str | None,
    tool_args: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if tool_args is None:
        return {}, None
    if not isinstance(tool_args, dict):
        return None, "tool_args_invalid"
    normalized_action = (
        tool_action.strip().casefold()
        if isinstance(tool_action, str) and tool_action.strip()
        else None
    )
    if not normalized_action:
        return dict(tool_args), None

    allowed_fields = _TOOL_ARGS_ALLOWED_FIELDS.get(normalized_action)
    if allowed_fields is not None:
        for key in tool_args:
            if not isinstance(key, str):
                return None, "tool_args_key_invalid"
            if key not in allowed_fields:
                return None, f"tool_args_unknown_field:{key}"

    normalized_args = dict(tool_args)
    for key, value in normalized_args.items():
        if value is None:
            continue
        if key in _TOOL_ARGS_LIST_FIELDS:
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return None, f"tool_args_type_invalid:{key}"
            continue
        if key in _TOOL_ARGS_NUMBER_FIELDS:
            if isinstance(value, bool):
                return None, f"tool_args_type_invalid:{key}"
            if not isinstance(value, (int, float, str)):
                return None, f"tool_args_type_invalid:{key}"
            continue
        if not isinstance(value, str):
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


class LlmPolicyCoreOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent: str
    action: str
    tool_action: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    pack_refs: list[str] = Field(default_factory=list)
    slots: dict[str, str]
    next_question: str | None = None
    open_questions: list[str] = Field(default_factory=list)
    needs_manager: bool = False
    risk_signals: list[str] = Field(default_factory=list)
    language: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    reason: str | None = None
    goal: str | None = None

    @field_validator("intent", "action", "tool_action", mode="before")
    @classmethod
    def _validate_action(cls, value: Any, info) -> str:
        return _normalize_required_string(value, field=info.field_name)

    @field_validator("tool_action", "language", "reason", "goal", "next_question", mode="before")
    @classmethod
    def _validate_optional_fields(cls, value: Any, info) -> str | None:
        return _normalize_optional_string(value, field=info.field_name)

    @field_validator("tool_args", mode="before")
    @classmethod
    def _validate_tool_args(cls, value: Any) -> dict[str, Any]:
        normalized, error = validate_tool_args_shape(tool_action=None, tool_args=value)
        if error:
            raise ValueError(error)
        return normalized or {}

    @field_validator("pack_refs", "open_questions", "risk_signals", mode="before")
    @classmethod
    def _validate_string_lists(cls, value: Any, info) -> list[str]:
        return _normalize_string_list(value, field=info.field_name)

    @field_validator("slots", mode="before")
    @classmethod
    def _validate_slots(cls, value: Any) -> dict[str, str]:
        return _normalize_slots(value)

    @field_validator("needs_manager", mode="before")
    @classmethod
    def _validate_needs_manager(cls, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        raise ValueError("needs_manager_invalid")

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
