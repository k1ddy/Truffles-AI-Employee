from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


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


RiskTag = Literal["none", "medical", "legal", "payment", "safety", "privacy"]
EscalateRule = Literal[
    "risk_high",
    "needs_human",
    "missing_fact",
    "unknown_topic",
    "clarify_limit_exceeded",
]
FactRequirement = Literal["service_exists", "policy_present", "price_allowed", "duration_allowed"]
ConsultIntent = Literal["consult", "info", "booking", "handoff", "out_of_domain"]
ConsultAction = Literal["answer", "clarify", "handoff"]
RiskClass = Literal["low", "medium", "high", "blocked"]


class ConsultTopic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., pattern=r"^[a-z0-9_-]+$")
    title: str = Field(..., min_length=2)
    summary: str = Field(..., min_length=8)
    allowed_advice: list[str] = Field(default_factory=list)
    required_questions: list[str] = Field(default_factory=list)
    optional_questions: list[str] = Field(default_factory=list)
    disallowed_claims: list[str] = Field(default_factory=list)
    fact_requirements: list[FactRequirement] = Field(default_factory=list)
    risk_tags: list[RiskTag] = Field(default_factory=list)
    clarify_limit: int = Field(..., ge=0, le=2)
    escalate_when: list[EscalateRule] = Field(default_factory=list)
    next_step: str | None = None

    @model_validator(mode="after")
    def _validate_required(self) -> "ConsultTopic":
        if not self.allowed_advice:
            raise ValueError("allowed_advice_required")
        if not self.risk_tags:
            raise ValueError("risk_tags_required")
        if not self.escalate_when:
            raise ValueError("escalate_when_required")
        return self


class ConsultDefaultPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    clarify_limit: int | None = Field(default=None, ge=0, le=2)
    escalate_on_low_confidence: bool | None = None


class ConsultPlaybook(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: Literal["v1"]
    topics: list[ConsultTopic]
    default_policy: ConsultDefaultPolicy | None = None

    @model_validator(mode="after")
    def _validate_topics(self) -> "ConsultPlaybook":
        if not self.topics:
            raise ValueError("topics_required")
        return self


class ConsultControllerOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent: ConsultIntent
    topic_id: str
    confidence: float = Field(..., ge=0, le=1)
    risk_class: RiskClass
    actions: list[ConsultAction]
    slots: dict[str, str] | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_actions(self) -> "ConsultControllerOutput":
        if not self.actions:
            raise ValueError("actions_required")
        return self


def validate_consult_playbook(
    payload_json: dict[str, Any],
) -> tuple[ConsultPlaybook | None, str | None]:
    try:
        contract = ConsultPlaybook.model_validate(payload_json)
    except ValidationError as exc:
        return None, f"consult_playbook_error:{_summarize_validation_error(exc)}"
    return contract, None


def validate_consult_controller_output(
    payload_json: dict[str, Any],
) -> tuple[ConsultControllerOutput | None, str | None]:
    try:
        contract = ConsultControllerOutput.model_validate(payload_json)
    except ValidationError as exc:
        return None, f"consult_controller_error:{_summarize_validation_error(exc)}"
    return contract, None
