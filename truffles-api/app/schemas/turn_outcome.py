from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXPECTED_REPLY_ALLOWED_TYPES = {
    "service_choice",
    "time",
    "name",
    "phone",
    "intent_choice",
}

TurnOutcomeContractStatus = Literal["ok", "degraded", "invalid"]


def _normalize_optional_token(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("token_invalid")
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned.casefold()


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("text_invalid")
    cleaned = value.strip()
    return cleaned or None


class TurnOutcomeObservability(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reply_observed: bool = False
    transport_status: str | None = None
    transport_reason: str | None = None

    @field_validator("transport_status", mode="before")
    @classmethod
    def _validate_transport_status(cls, value: Any) -> str | None:
        return _normalize_optional_token(value)

    @field_validator("transport_reason", mode="before")
    @classmethod
    def _validate_transport_reason(cls, value: Any) -> str | None:
        return _normalize_optional_text(value)


class TurnOutcome(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: str | None = None
    intent: str | None = None
    source: str | None = None
    tool_action: str | None = None
    tool_decision: str | None = None
    expected_reply_type: str | None = None
    expected_reply_reason: str | None = None
    followup_prompt: str | None = None
    contract_status: TurnOutcomeContractStatus = "ok"
    observability: TurnOutcomeObservability = Field(default_factory=TurnOutcomeObservability)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action", "intent", "source", "tool_action", "tool_decision", mode="before")
    @classmethod
    def _normalize_tokens(cls, value: Any) -> str | None:
        return _normalize_optional_token(value)

    @field_validator("expected_reply_reason", "followup_prompt", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("expected_reply_type", mode="before")
    @classmethod
    def _validate_expected_reply_type(cls, value: Any) -> str | None:
        normalized = _normalize_optional_token(value)
        if normalized is None:
            return None
        if normalized not in EXPECTED_REPLY_ALLOWED_TYPES:
            raise ValueError("expected_reply_type_invalid")
        return normalized

    def to_metadata(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)
