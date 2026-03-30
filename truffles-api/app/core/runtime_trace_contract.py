from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.binding_plan import BindingPlanV1
from app.core.conversation_projection import ConversationProjectionV1
from app.core.semantic_decision import SemanticDecisionV1
from app.core.turn_journal import TurnJournalV1, resolve_turn_id
from app.core.turn_planner import PolicyDecision


class RuntimeTraceOwnerTransitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str
    requested_outcome: str | None = None
    intent: str
    capability_id: str | None = None
    interaction_owner: str | None = None
    source: str | None = None
    tool_action_hint: str | None = None
    needs_human: bool = False
    goal: str | None = None


class RuntimeTraceBindingTransitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    binding_id: str | None = None
    decision_id: str
    binding_outcome_type: str | None = None
    capability_id: str | None = None
    selected_tool_or_workflow_ref: str | None = None
    idempotency_key: str | None = None
    resolved_args: dict[str, Any] = Field(default_factory=dict)
    authz_scope: dict[str, Any] = Field(default_factory=dict)
    timeout_policy: dict[str, Any] = Field(default_factory=dict)
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    boundary_reason_code: str | None = None


class RuntimeTraceActionTransitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_action: str
    runtime_entrypoint: str
    semantic_runtime_path: str
    reply_kind: str | None = None
    delivered: bool = False
    execution_tool_action: str | None = None
    execution_tool_decision: str | None = None
    reason_code: str | None = None
    earliest_failed_stage: str | None = None
    root_reason_code: str | None = None


class RuntimeTraceStateTransitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_id: str
    conversation_id: str | None = None
    current_semantic_decision_ref: str | None = None
    active_capability: str | None = None
    active_workflow_ref: str | None = None
    current_goal: str | None = None
    pending_question_contract: dict[str, Any] = Field(default_factory=dict)
    semantic_contract: dict[str, Any] = Field(default_factory=dict)
    semantic_state_before: dict[str, Any] = Field(default_factory=dict)
    semantic_state_after: dict[str, Any] = Field(default_factory=dict)
    journal_last_turn_id: str | None = None
    journal_event_types: list[str] = Field(default_factory=list)
    last_reply_ref: str | None = None


class RuntimeTraceContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "runtime_trace_contract.v1"
    trace_id: str | None = None
    owner_transition: RuntimeTraceOwnerTransitionV1
    binding_transition: RuntimeTraceBindingTransitionV1
    action_transition: RuntimeTraceActionTransitionV1
    state_transition: RuntimeTraceStateTransitionV1


def _binding_reason_code(binding_plan: BindingPlanV1 | None) -> str | None:
    if not isinstance(binding_plan, BindingPlanV1):
        return None
    return (
        binding_plan.deny_reason_code
        or binding_plan.degrade_reason_code
        or binding_plan.handoff_reason_code
    )


def build_runtime_trace_contract(
    *,
    trace_id: str | None,
    runtime_entrypoint: str,
    semantic_runtime_path: str,
    decision: PolicyDecision,
    contract_source: str,
    contract_action: str,
    reply_kind: str | None,
    delivered: bool,
    execution_tool_action: str | None,
    execution_tool_decision: str | None,
    reason_code: str | None,
    earliest_failed_stage: str | None,
    root_reason_code: str | None,
    projection: ConversationProjectionV1 | None,
    turn_journal: TurnJournalV1 | None,
    pending_question_contract: dict[str, Any] | None,
    semantic_contract: dict[str, Any] | None,
    semantic_state_before: dict[str, Any] | None,
    semantic_state_after: dict[str, Any] | None,
) -> RuntimeTraceContractV1:
    semantic_decision = (
        decision.semantic_decision
        if isinstance(decision.semantic_decision, SemanticDecisionV1)
        else None
    )
    binding_plan = decision.binding_plan if isinstance(decision.binding_plan, BindingPlanV1) else None
    turn_id = resolve_turn_id(decision)
    journal_event_types: list[str] = []
    if isinstance(turn_journal, TurnJournalV1):
        journal_event_types = [
            event.event_type
            for event in turn_journal.events
            if getattr(event, "turn_id", None) == turn_id and isinstance(event.event_type, str)
        ]

    return RuntimeTraceContractV1(
        trace_id=trace_id,
        owner_transition=RuntimeTraceOwnerTransitionV1(
            decision_id=(semantic_decision.decision_id if semantic_decision else turn_id),
            requested_outcome=(semantic_decision.requested_outcome if semantic_decision else decision.outcome.lower()),
            intent=(semantic_decision.intent if semantic_decision else decision.intent),
            capability_id=(semantic_decision.capability_id if semantic_decision else None),
            interaction_owner=decision.interaction.owner,
            source=contract_source,
            tool_action_hint=(semantic_decision.tool_action_hint if semantic_decision else decision.tool_action),
            needs_human=(semantic_decision.needs_human if semantic_decision else decision.outcome == "HANDOFF"),
            goal=(semantic_decision.goal if semantic_decision else None),
        ),
        binding_transition=RuntimeTraceBindingTransitionV1(
            binding_id=(binding_plan.binding_id if binding_plan else None),
            decision_id=(binding_plan.decision_id if binding_plan else turn_id),
            binding_outcome_type=(binding_plan.binding_outcome_type if binding_plan else None),
            capability_id=(binding_plan.capability_id if binding_plan else None),
            selected_tool_or_workflow_ref=(
                binding_plan.selected_tool_or_workflow_ref if binding_plan else None
            ),
            idempotency_key=(binding_plan.idempotency_key if binding_plan else None),
            resolved_args=(dict(binding_plan.resolved_args) if binding_plan else {}),
            authz_scope=(dict(binding_plan.authz_scope) if binding_plan else {}),
            timeout_policy=(dict(binding_plan.timeout_policy) if binding_plan else {}),
            retry_policy=(dict(binding_plan.retry_policy) if binding_plan else {}),
            boundary_reason_code=_binding_reason_code(binding_plan),
        ),
        action_transition=RuntimeTraceActionTransitionV1(
            contract_action=contract_action,
            runtime_entrypoint=runtime_entrypoint,
            semantic_runtime_path=semantic_runtime_path,
            reply_kind=reply_kind,
            delivered=delivered,
            execution_tool_action=execution_tool_action,
            execution_tool_decision=execution_tool_decision,
            reason_code=reason_code,
            earliest_failed_stage=earliest_failed_stage,
            root_reason_code=root_reason_code,
        ),
        state_transition=RuntimeTraceStateTransitionV1(
            turn_id=turn_id,
            conversation_id=(
                projection.conversation_id
                if isinstance(projection, ConversationProjectionV1)
                else getattr(semantic_decision, "conversation_id", None)
            ),
            current_semantic_decision_ref=(
                projection.current_semantic_decision_ref
                if isinstance(projection, ConversationProjectionV1)
                else getattr(semantic_decision, "decision_id", None)
            ),
            active_capability=(
                projection.active_capability
                if isinstance(projection, ConversationProjectionV1)
                else (binding_plan.capability_id if binding_plan else None)
            ),
            active_workflow_ref=(
                projection.active_workflow_ref if isinstance(projection, ConversationProjectionV1) else None
            ),
            current_goal=(projection.current_goal if isinstance(projection, ConversationProjectionV1) else None),
            pending_question_contract=dict(pending_question_contract or {}),
            semantic_contract=dict(semantic_contract or {}),
            semantic_state_before=dict(semantic_state_before or {}),
            semantic_state_after=dict(semantic_state_after or {}),
            journal_last_turn_id=(turn_journal.last_turn_id if isinstance(turn_journal, TurnJournalV1) else None),
            journal_event_types=journal_event_types,
            last_reply_ref=(projection.last_reply_ref if isinstance(projection, ConversationProjectionV1) else None),
        ),
    )


__all__ = [
    "RuntimeTraceActionTransitionV1",
    "RuntimeTraceBindingTransitionV1",
    "RuntimeTraceContractV1",
    "RuntimeTraceOwnerTransitionV1",
    "RuntimeTraceStateTransitionV1",
    "build_runtime_trace_contract",
]
