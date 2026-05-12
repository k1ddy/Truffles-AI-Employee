"""Typed contracts for Policy-Core v3 input and output.

Spec: SPECS/POLICY_CORE_V3.md section 3 and 4.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .pack_view import EvidenceItem, PackView, ToolContract, Turn


class Intent(str, Enum):
    fact_question = "fact_question"
    slot_collect = "slot_collect"
    booking_request = "booking_request"
    booking_manage = "booking_manage"
    handoff_request = "handoff_request"
    smalltalk = "smalltalk"
    unsupported = "unsupported"
    unknown = "unknown"


class Uncertainty(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DegradeReason(str, Enum):
    empty_response = "empty_response"
    schema_invalid = "schema_invalid"
    timeout = "timeout"
    provider_error = "provider_error"
    tool_not_in_contract = "tool_not_in_contract"
    intent_not_in_enum = "intent_not_in_enum"


class CandidateAction(BaseModel):
    """The model's proposed (not executed) tool call.

    `tool` must be `"none"` or a tool id present in the input `tool_contracts`.
    Argument deep-validation is the planner's responsibility.
    """

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(..., description="Tool id or 'none'.")
    args: dict[str, Any] = Field(default_factory=dict)


class PolicyDecisionV3(BaseModel):
    """The single typed semantic decision for one customer turn."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    slots: dict[str, Any] = Field(default_factory=dict)
    candidate_action: CandidateAction
    evidence_refs: list[str] = Field(default_factory=list)
    message_draft: str = Field(default="")
    uncertainty: Uncertainty = Uncertainty.medium
    notes: str = ""

    @field_validator("message_draft")
    @classmethod
    def _strip_message(cls, v: str) -> str:
        return v.strip()


class DegradeVerdict(BaseModel):
    """Returned by v3 when retry policy is exhausted.

    Boundary is responsible for translating this to a customer-facing handoff
    or clarifying question. v3 never renders a customer message in this case.
    """

    model_config = ConfigDict(extra="forbid")

    degrade_reason: DegradeReason
    last_raw_output: str | None = None
    attempts: int = Field(..., ge=1)
    notes: str = ""


class PolicyTurnInput(BaseModel):
    """All inputs Policy-Core v3 needs for one turn.

    Pure data — no callables, no lazy loaders. Construction is the upstream
    Turn Context Loader's job.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    tenant_id: str
    conversation_id: str
    current_message: str
    conversation_history: list[Turn] = Field(default_factory=list)
    state_slots: dict[str, Any] = Field(default_factory=dict)
    pack_view: PackView
    capabilities: list[str] = Field(default_factory=list)
    tool_contracts: list[ToolContract] = Field(default_factory=list)
    evidence_bundle: list[EvidenceItem] = Field(default_factory=list)
    now: datetime
    locale: str = "ru-KZ"
    policy_version: str = "v3-poc"
    history_max_turns: int = 12
