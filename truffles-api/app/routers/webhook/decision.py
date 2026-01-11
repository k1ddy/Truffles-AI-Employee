"""Intent and decision helpers for webhook routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.models import ClientSettings, Conversation
from app.schemas.webhook import ContextContract, IntentContract, WebhookRequest
from app.services.demo_salon_knowledge import DemoSalonDecision
from app.services.intent_service import Intent

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


@dataclass(frozen=True)
class DecisionPlan:
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


def build_decision_plan(*, state: str, routing: dict[str, bool], client_slug: str | None) -> DecisionPlan:
    return DecisionPlan(
        stages=DECISION_GRAPH_STAGES,
        state=state,
        routing=dict(routing),
        client_slug=client_slug,
        plan_id=str(uuid4()),
    )


def build_context_contract(
    conversation: Conversation,
    payload: WebhookRequest,
    settings: ClientSettings | None,
) -> tuple[dict[str, Any] | None, str | None]:
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


@dataclass(frozen=True)
class DecisionSignals:
    intent: Intent
    is_greeting: bool
    is_thanks: bool
    is_ack: bool
    is_low_signal: bool
    is_status_question: bool


@dataclass(frozen=True)
class DecisionOutcome:
    action: str


def _normalize_message_text(message_text: str | None) -> str:
    return (message_text or "").strip()


def _detect_fast_intent(
    message_text: str,
    *,
    policy_type: str | None,
    booking_wants_flow: bool,
    bypass_domain_flows: bool,
) -> DemoSalonDecision | None:
    if not message_text or booking_wants_flow or bypass_domain_flows:
        return None

    from . import _legacy as legacy

    if legacy.is_greeting_message(message_text):
        return DemoSalonDecision(action="smalltalk", response=legacy.GREETING_RESPONSE, intent="greeting")
    if legacy.is_thanks_message(message_text):
        return DemoSalonDecision(action="smalltalk", response=legacy.THANKS_RESPONSE, intent="thanks")
    if legacy.is_acknowledgement_message(message_text):
        return DemoSalonDecision(action="smalltalk", response=legacy.ACKNOWLEDGEMENT_RESPONSE, intent="ack")
    return None


def _detect_intent_signals(message_text: str) -> DecisionSignals:
    from . import _legacy as legacy

    is_greeting = legacy.is_greeting_message(message_text)
    is_thanks = legacy.is_thanks_message(message_text)
    is_ack = legacy.is_acknowledgement_message(message_text)
    is_low_signal = legacy.is_low_signal_message(message_text)
    is_status_question = legacy.is_bot_status_question(message_text)

    if is_greeting:
        intent = Intent.GREETING
        legacy.logger.info("Intent shortcut: greeting")
    elif is_thanks:
        intent = Intent.THANKS
        legacy.logger.info("Intent shortcut: thanks")
    elif is_ack or is_low_signal:
        intent = Intent.OTHER
        legacy.logger.info("Intent shortcut: acknowledgement/low-signal -> other")
    else:
        intent = legacy.classify_intent(message_text)
        legacy.logger.info(f"Intent classified: {intent.value}")

    return DecisionSignals(
        intent=intent,
        is_greeting=is_greeting,
        is_thanks=is_thanks,
        is_ack=is_ack,
        is_low_signal=is_low_signal,
        is_status_question=is_status_question,
    )


def _resolve_action(
    *,
    routing: dict[str, bool],
    state: str,
    signals: DecisionSignals,
    is_pending_status_question: bool,
    style_reference: bool,
    out_of_domain_signal: bool,
    rag_confident: bool,
) -> DecisionOutcome:
    from . import _legacy as legacy

    if routing["allow_bot_reply"] and (signals.is_greeting or signals.is_thanks):
        return DecisionOutcome("smalltalk")
    if routing["allow_bot_reply"] and state == legacy.ConversationState.PENDING.value and is_pending_status_question:
        return DecisionOutcome("pending_status")
    if routing["allow_bot_reply"] and signals.is_status_question:
        return DecisionOutcome("bot_status")
    if routing["allow_bot_reply"] and out_of_domain_signal and not rag_confident:
        return DecisionOutcome("out_of_domain")
    if routing["allow_bot_reply"] and style_reference:
        return DecisionOutcome("style_reference")
    if legacy._should_escalate_to_pending(routing, signals.intent):
        return DecisionOutcome("escalate")
    if legacy.should_escalate(signals.intent) and not routing["allow_handover_create"]:
        return DecisionOutcome("pending_escalation")
    if legacy.is_rejection(signals.intent):
        return DecisionOutcome("rejection")
    if routing["allow_bot_reply"]:
        return DecisionOutcome("ai_response")
    return DecisionOutcome("unknown_state")


def is_handover_status_question(text: str) -> bool:
    """Detect 'did you forward / when manager replies' questions in pending state."""
    if not text:
        return False

    normalized = text.strip().casefold()
    keywords = [
        "передал",
        "передали",
        "передано",
        "заявк",
        "менеджер",
        "админ",
        "администратор",
        "когда ответ",
        "когда ответит",
        "не отвеч",
        "не отвечает",
        "почему не отвеч",
        "почему молч",
        "молч",
        "тишин",
        "сколько ждать",
        "ждать",
        "ответит",
        "взял",
        "взяли",
        "беру",
    ]
    return any(k in normalized for k in keywords)
