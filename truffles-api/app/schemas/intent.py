from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


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
