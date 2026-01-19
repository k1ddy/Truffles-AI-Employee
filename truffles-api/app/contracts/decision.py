"""
Decision contracts and data structures.

Extracted from app/routers/webhook/decision.py for better modularity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.webhook import (
    ActionContract,
    ContextContract,
    FactContract,
    IntentContract,
    ResponseContract,
    WebhookRequest,
)
from app.services.intent_service import Intent

# =============================================================================
# Core Types
# =============================================================================

DecisionStage = str

DECISION_GRAPH_STAGES: tuple[DecisionStage, ...] = (
    "state",
    "risk",
    "expected",
    "semantic",
    "data",
    "action",
    "response",
    "update",
)


# =============================================================================
# Decision Plan
# =============================================================================

@dataclass(frozen=True)
class DecisionPlan:
    """
    Represents the execution plan for processing a message through the decision graph.
    """
    stages: tuple[DecisionStage, ...]
    state: str
    routing: dict[str, bool]
    client_slug: str | None
    plan_id: str

    def to_trace(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "routing": self.routing,
            "client_slug": self.client_slug,
            "plan_id": self.plan_id,
            "stages": list(self.stages),
        }


def build_decision_plan(
    *,
    state: str,
    routing: dict[str, bool],
    client_slug: str | None,
) -> DecisionPlan:
    """Create a new decision plan for message processing."""
    return DecisionPlan(
        stages=DECISION_GRAPH_STAGES,
        state=state,
        routing=dict(routing),
        client_slug=client_slug,
        plan_id=str(uuid4()),
    )


# =============================================================================
# Signal Dataclasses
# =============================================================================

@dataclass(frozen=True)
class DecisionSignals:
    """Signals detected from the user's message."""
    intent: Intent
    is_greeting: bool
    is_thanks: bool
    is_ack: bool
    is_low_signal: bool
    is_status_question: bool


@dataclass(frozen=True)
class DecisionOutcome:
    """The action determined by the decision graph."""
    action: str


# =============================================================================
# State Containers
# =============================================================================

@dataclass(frozen=True)
class ExpectedReplyState:
    """State after processing expected reply contract."""
    context: dict[str, Any]
    context_manager: dict[str, Any]
    expected_reply_type: str | None
    intent_queue: list[str] | None
    expected_reply_matched: bool | None
    expected_reply_shortcircuit: bool
    expected_reply_blocked_by_info: bool
    memory_expected_reply_type: str | None
    current_goal: str | None


@dataclass(frozen=True)
class IntentDecompositionState:
    """State after intent decomposition stage."""
    intent_decomp_payload: dict[str, Any] | None
    intent_decomp_intents: list[str]
    intent_decomp_primary: str | None
    intent_decomp_secondary: list[str]
    intent_decomp_service_query: str | None
    intent_decomp_multi: bool
    intent_decomp_used: bool
    intent_decomp_set: set[str]
    consult_intent: bool
    consult_topic: str | None
    consult_question: str | None
    intent_queue_choice: str | None
    pending_intent_queue: list[str] | None
    pending_expected_reply_type: str | None
    intent_queue_expected_next: str | None
    intent_queue_event: dict | None
    info_class_intents: set[str]
    info_class_meta: dict[str, Any]
    basic_info_message: bool
    allow_service_carryover: bool
    consult_return_pending: bool
    consult_return_reason: str | None
    consult_return_prompt: str | None
    booking_signal: bool
    booking_block_meta: dict | None
    booking_wants_flow: bool
    booking_blocked: bool
    booking_active: bool
    booking_context: dict | None
    booking: dict | None
    class_carryover: dict | None
    context: dict[str, Any]
    context_manager: dict[str, Any]
    current_goal: str | None


@dataclass(frozen=True)
class IntentRoutingState:
    """State after intent routing stage."""
    signals: DecisionSignals
    intent: Intent
    domain_intent: Any
    domain_meta: dict[str, Any]
    class_router_result: dict[str, Any]
    out_of_domain_signal: bool


# =============================================================================
# Contract Builders
# =============================================================================

def build_context_contract(
    conversation,  # Conversation
    payload: WebhookRequest,
    settings,  # ClientSettings | None
) -> tuple[dict[str, Any] | None, str | None]:
    """Build and validate context contract from conversation and payload."""
    contract_payload = {
        "tenant_id": payload.client_slug,
        "branch_id": str(conversation.branch_id) if conversation.branch_id else None,
        "state": conversation.state,
        "timezone": None,
        "mode": settings.branch_resolution_mode if settings and settings.branch_resolution_mode else None,
    }
    try:
        contract = ContextContract(**contract_payload)
    except ValidationError as exc:
        return None, str(exc)
    return contract.model_dump(exclude_none=True), None


def build_intent_contract(
    signals: DecisionSignals,
    intent_decomp_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Build and validate intent contract from signals and decomposition."""
    contract_payload = {
        "intent": signals.intent.value if signals and signals.intent else None,
        "slots": dict(intent_decomp_payload) if isinstance(intent_decomp_payload, dict) else None,
        "language": None,
        "emotion": None,
        "confidence": None,
        "risk_signals": None,
    }
    try:
        contract = IntentContract(**contract_payload)
    except ValidationError as exc:
        return None, str(exc)
    return contract.model_dump(exclude_none=True), None


def build_fact_contract(
    *,
    facts: dict[str, Any] | None,
    sources: list[str] | None,
    policy_flags: list[str] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Build and validate fact contract from RAG results."""
    contract_payload = {
        "facts": dict(facts) if isinstance(facts, dict) else None,
        "sources": list(sources) if isinstance(sources, list) else None,
        "policy_flags": list(policy_flags) if isinstance(policy_flags, list) else None,
    }
    try:
        contract = FactContract(**contract_payload)
    except ValidationError as exc:
        return None, str(exc)
    return contract.model_dump(exclude_none=True), None


def build_action_contract(
    *,
    action_type: str | None,
    required_next_slots: list[str] | None,
    escalation_reason: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Build and validate action contract."""
    contract_payload = {
        "action_type": action_type if isinstance(action_type, str) else None,
        "required_next_slots": list(required_next_slots) if isinstance(required_next_slots, list) else None,
        "escalation_reason": escalation_reason if isinstance(escalation_reason, str) else None,
    }
    try:
        contract = ActionContract(**contract_payload)
    except ValidationError as exc:
        return None, str(exc)
    return contract.model_dump(exclude_none=True), None


def build_response_contract(
    *,
    tone: str | None,
    must_include: list[str] | None,
    must_not_include: list[str] | None,
    language: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Build and validate response contract."""
    contract_payload = {
        "tone": tone if isinstance(tone, str) else None,
        "must_include": list(must_include) if isinstance(must_include, list) else None,
        "must_not_include": list(must_not_include) if isinstance(must_not_include, list) else None,
        "language": language if isinstance(language, str) else None,
    }
    try:
        contract = ResponseContract(**contract_payload)
    except ValidationError as exc:
        return None, str(exc)
    return contract.model_dump(exclude_none=True), None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Types
    "DecisionStage",
    "DECISION_GRAPH_STAGES",
    # Plan
    "DecisionPlan",
    "build_decision_plan",
    # Signals
    "DecisionSignals",
    "DecisionOutcome",
    # States
    "ExpectedReplyState",
    "IntentDecompositionState",
    "IntentRoutingState",
    # Contract builders
    "build_context_contract",
    "build_intent_contract",
    "build_fact_contract",
    "build_action_contract",
    "build_response_contract",
]
