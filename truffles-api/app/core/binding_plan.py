from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

BindingOutcomeType = Literal[
    "tool_call",
    "workflow_start",
    "workflow_advance",
    "deny",
    "degrade",
    "handoff",
]


class BindingPlanV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "binding_plan.v1"
    binding_id: str = Field(default_factory=lambda: uuid4().hex)
    decision_id: str
    binding_outcome_type: BindingOutcomeType
    capability_id: str | None = None
    selected_tool_or_workflow_ref: str | None = None
    authz_scope: dict[str, Any] = Field(default_factory=dict)
    resolved_args: dict[str, Any] = Field(default_factory=dict)
    timeout_policy: dict[str, Any] = Field(default_factory=dict)
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    deny_reason_code: str | None = None
    degrade_reason_code: str | None = None
    handoff_reason_code: str | None = None

    @model_validator(mode="after")
    def _validate_outcome_requirements(self) -> BindingPlanV1:
        if self.binding_outcome_type in {"tool_call", "workflow_start", "workflow_advance"}:
            if not self.selected_tool_or_workflow_ref:
                raise ValueError("binding_selected_ref_required")
        if self.binding_outcome_type == "deny" and not self.deny_reason_code:
            raise ValueError("binding_deny_reason_required")
        if self.binding_outcome_type == "degrade" and not self.degrade_reason_code:
            raise ValueError("binding_degrade_reason_required")
        if self.binding_outcome_type == "handoff" and not self.handoff_reason_code:
            raise ValueError("binding_handoff_reason_required")
        return self

    @classmethod
    def build_compat(
        cls,
        *,
        decision_id: str,
        requested_outcome: str,
        capability_id: str | None,
        selected_tool_or_workflow_ref: str,
        resolved_args: dict[str, Any] | None = None,
        handoff_reason_code: str | None = None,
    ) -> BindingPlanV1:
        normalized_requested_outcome = (requested_outcome or "").strip().casefold()
        if normalized_requested_outcome == "handoff":
            outcome_type: BindingOutcomeType = "handoff"
        elif normalized_requested_outcome == "collect":
            outcome_type = "workflow_advance"
        else:
            outcome_type = "tool_call"
        return cls(
            decision_id=decision_id,
            binding_outcome_type=outcome_type,
            capability_id=capability_id,
            selected_tool_or_workflow_ref=selected_tool_or_workflow_ref,
            resolved_args=dict(resolved_args or {}),
            authz_scope={},
            timeout_policy={},
            retry_policy={},
            idempotency_key=decision_id,
            handoff_reason_code=handoff_reason_code if outcome_type == "handoff" else None,
        )

    @classmethod
    def build_deny(
        cls,
        *,
        decision_id: str,
        deny_reason_code: str,
        capability_id: str | None = None,
    ) -> BindingPlanV1:
        return cls(
            decision_id=decision_id,
            binding_outcome_type="deny",
            capability_id=capability_id,
            selected_tool_or_workflow_ref=None,
            authz_scope={},
            resolved_args={},
            timeout_policy={},
            retry_policy={},
            idempotency_key=decision_id,
            deny_reason_code=deny_reason_code,
        )

    @classmethod
    def build_degrade(
        cls,
        *,
        decision_id: str,
        degrade_reason_code: str,
        capability_id: str | None = None,
    ) -> BindingPlanV1:
        return cls(
            decision_id=decision_id,
            binding_outcome_type="degrade",
            capability_id=capability_id,
            selected_tool_or_workflow_ref=None,
            authz_scope={},
            resolved_args={},
            timeout_policy={},
            retry_policy={},
            idempotency_key=decision_id,
            degrade_reason_code=degrade_reason_code,
        )

    @property
    def tool_action(self) -> str | None:
        return self.selected_tool_or_workflow_ref

    def as_compat_binding_payload(self) -> dict[str, Any]:
        return {
            "tool_action": self.selected_tool_or_workflow_ref or "",
            "tool_args": dict(self.resolved_args),
        }


__all__ = ["BindingOutcomeType", "BindingPlanV1"]
