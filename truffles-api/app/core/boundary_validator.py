from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.turn_outcome import TurnOutcome, TurnOutcomeObservability
from app.core.turn_planner import PolicyDecision

BoundaryDecision = Literal["approve", "block", "degrade", "request_replan"]
_BOUNDARY_OVERRIDE_PRESERVE_FIELDS = (
    "outcome",
    "interaction_owner",
    "interaction_target",
    "interaction_relation",
    "pending_question_contract",
)


class BoundaryOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "boundary_override.v1"
    decision: BoundaryDecision
    reason_code: str
    preserve_fields: list[str] = Field(default_factory=list)
    public_message: str | None = None
    trace_message: str | None = None
    replan_hints: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class BoundaryValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecision
    override: BoundaryOverride | None = None


class BoundaryValidator:
    """Typed seam for future deterministic boundary validation."""

    @staticmethod
    def _build_turn_outcome_meta(
        turn_result: Any,
        *,
        reason_code: str,
        path_flag: str,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "schema_version": turn_result.schema_version,
            "reason_code": reason_code,
            "reply_kind": turn_result.reply.reply_kind,
            "boundary_decision": (
                turn_result.boundary_override.decision if turn_result.boundary_override else None
            ),
            "interaction_owner": turn_result.policy_decision.interaction.owner,
            path_flag: True,
        }
        if meta:
            payload.update(meta)
        return payload

    @staticmethod
    def _resolve_reason_code(turn_result: Any) -> str:
        if turn_result.boundary_override and turn_result.boundary_override.reason_code:
            return turn_result.boundary_override.reason_code
        reason_code = turn_result.observability.reason_code
        if isinstance(reason_code, str) and reason_code.strip():
            return reason_code
        raise ValueError("boundary_reason_code_missing")

    def _build_override(
        self,
        *,
        decision: BoundaryDecision,
        reason_code: str,
        public_message: str,
        trace_message: str,
        replan_hints: list[str],
        meta: dict[str, Any] | None = None,
    ) -> BoundaryOverride:
        return BoundaryOverride(
            decision=decision,
            reason_code=reason_code,
            preserve_fields=list(_BOUNDARY_OVERRIDE_PRESERVE_FIELDS),
            public_message=public_message,
            trace_message=trace_message,
            replan_hints=list(replan_hints),
            meta=meta or {},
        )

    def validate(
        self,
        decision: PolicyDecision,
        *,
        override: BoundaryOverride | None = None,
    ) -> BoundaryValidationResult:
        return BoundaryValidationResult(decision=decision, override=override)

    def build_degrade_override(
        self,
        *,
        reason_code: str,
        public_message: str,
        trace_message: str,
        meta: dict[str, Any] | None = None,
    ) -> BoundaryOverride:
        return self._build_override(
            decision="degrade",
            reason_code=reason_code,
            public_message=public_message,
            trace_message=trace_message,
            replan_hints=["preserve controlled degrade contract"],
            meta=meta,
        )

    def build_block_override(
        self,
        *,
        reason_code: str,
        trace_message: str,
        replan_hints: list[str],
        public_message: str = "",
        meta: dict[str, Any] | None = None,
    ) -> BoundaryOverride:
        return self._build_override(
            decision="block",
            reason_code=reason_code,
            public_message=public_message,
            trace_message=trace_message,
            replan_hints=replan_hints,
            meta=meta,
        )

    def build_block_turn_outcome(
        self,
        *,
        turn_result: Any,
        tool_action: str,
        ignored: bool = False,
        meta: dict[str, Any] | None = None,
    ) -> TurnOutcome:
        reason_code = self._resolve_reason_code(turn_result)
        return TurnOutcome(
            action="ignore" if ignored else "reject",
            intent=turn_result.policy_decision.intent,
            source="consultant_core_runtime",
            tool_action=tool_action,
            tool_decision="blocked",
            contract_status="invalid",
            observability=TurnOutcomeObservability(
                reply_observed=False,
                transport_status="skipped",
                transport_reason=reason_code,
            ),
            meta=self._build_turn_outcome_meta(
                turn_result,
                reason_code=reason_code,
                path_flag="ignored_path" if ignored else "preflight_path",
                meta=meta,
            ),
        )

    def build_degrade_turn_outcome(
        self,
        *,
        turn_result: Any,
        transport_status: str,
        transport_reason: str | None,
        tool_action: str = "handoff",
        tool_decision: str = "runtime_exception",
        meta: dict[str, Any] | None = None,
    ) -> TurnOutcome:
        reason_code = self._resolve_reason_code(turn_result)
        return TurnOutcome(
            action=turn_result.policy_decision.action,
            intent=turn_result.policy_decision.intent,
            source="consultant_core_runtime",
            tool_action=tool_action,
            tool_decision=tool_decision,
            contract_status="degraded",
            observability=TurnOutcomeObservability(
                reply_observed=transport_status == "delivered",
                transport_status=transport_status,
                transport_reason=transport_reason,
            ),
            meta=self._build_turn_outcome_meta(
                turn_result,
                reason_code=reason_code,
                path_flag="degrade_path",
                meta=meta,
            ),
        )


__all__ = [
    "BoundaryDecision",
    "BoundaryOverride",
    "BoundaryValidationResult",
    "BoundaryValidator",
]
