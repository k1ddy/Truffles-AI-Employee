from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.binding_plan import BindingPlanV1
from app.core.conversation_projection import ConversationProjectionV1
from app.core.turn_planner import PolicyDecision

_ALLOWED_EVENT_TYPES = {
    "TurnReceived",
    "SemanticDecisionIssued",
    "BindingPlanIssued",
    "ExecutionStarted",
    "ExecutionCompleted",
    "ExecutionFailed",
    "DegradeIssued",
    "HandoffIssued",
    "ReplyCommitted",
}


class TurnJournalEventV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    schema_version: str = "turn_journal.event.v1"
    turn_id: str
    conversation_id: str | None = None
    event_type: str
    timestamp: str
    source_component: str
    causal_parent_id: str | None = None
    trace_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def _validate_event_type(cls, value: str) -> str:
        if value not in _ALLOWED_EVENT_TYPES:
            raise ValueError(f"turn_journal_event_type_invalid:{value}")
        return value


class TurnJournalV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "turn_journal.v1"
    conversation_id: str | None = None
    last_turn_id: str | None = None
    events: list[TurnJournalEventV1] = Field(default_factory=list)

    def append_events(self, new_events: list[TurnJournalEventV1]) -> TurnJournalV1:
        appended = [event.model_copy(deep=True) for event in new_events]
        last_turn_id = self.last_turn_id
        conversation_id = self.conversation_id
        if appended:
            last_turn_id = appended[-1].turn_id
            conversation_id = appended[-1].conversation_id or conversation_id
        return self.model_copy(
            update={
                "conversation_id": conversation_id,
                "last_turn_id": last_turn_id,
                "events": [*self.events, *appended],
            },
            deep=True,
        )


def resolve_turn_id(decision: PolicyDecision) -> str:
    if decision.semantic_decision is not None:
        return decision.semantic_decision.decision_id
    if isinstance(decision.binding_plan, BindingPlanV1):
        return decision.binding_plan.decision_id
    return uuid4().hex


def build_turn_journal_events(
    *,
    conversation_id: str | None,
    decision: PolicyDecision,
    projection: ConversationProjectionV1,
    timestamp: str,
    trace_id: str | None,
) -> list[TurnJournalEventV1]:
    turn_id = resolve_turn_id(decision)
    events: list[TurnJournalEventV1] = []
    parent_id: str | None = None

    if decision.semantic_decision is not None:
        semantic_event = TurnJournalEventV1(
            turn_id=turn_id,
            conversation_id=conversation_id,
            event_type="SemanticDecisionIssued",
            timestamp=timestamp,
            source_component="turn_planner",
            trace_id=trace_id,
            payload={
                "semantic_decision_ref": decision.semantic_decision.decision_id,
                "requested_outcome": decision.semantic_decision.requested_outcome,
                "intent": decision.semantic_decision.intent,
                "capability_id": decision.semantic_decision.capability_id,
            },
        )
        events.append(semantic_event)
        parent_id = semantic_event.event_id

    if isinstance(decision.binding_plan, BindingPlanV1):
        binding_event = TurnJournalEventV1(
            turn_id=turn_id,
            conversation_id=conversation_id,
            event_type="BindingPlanIssued",
            timestamp=timestamp,
            source_component="policy_tool_projector",
            causal_parent_id=parent_id,
            trace_id=trace_id,
            payload={
                "binding_id": decision.binding_plan.binding_id,
                "binding_outcome_type": decision.binding_plan.binding_outcome_type,
                "selected_tool_or_workflow_ref": decision.binding_plan.selected_tool_or_workflow_ref,
            },
        )
        events.append(binding_event)
        parent_id = binding_event.event_id

    terminal_type = "ExecutionCompleted"
    if decision.meta.get("degrade_path"):
        terminal_type = "DegradeIssued"
    elif decision.outcome == "HANDOFF":
        terminal_type = "HandoffIssued"

    terminal_event = TurnJournalEventV1(
        turn_id=turn_id,
        conversation_id=conversation_id,
        event_type=terminal_type,
        timestamp=timestamp,
        source_component="dialog_state_service",
        causal_parent_id=parent_id,
        trace_id=trace_id,
        payload={
            "projection_state": projection.model_dump(mode="python", exclude_none=True),
            "reason_code": str(decision.meta.get("reason_code") or "").strip() or None,
            "action": decision.action,
            "outcome": decision.outcome,
        },
    )
    events.append(terminal_event)
    return events


__all__ = [
    "TurnJournalEventV1",
    "TurnJournalV1",
    "build_turn_journal_events",
    "resolve_turn_id",
]
