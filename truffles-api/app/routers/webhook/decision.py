"""Intent and decision helpers for webhook routing."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

from pydantic import ValidationError

from app.models import ClientSettings, Conversation, Message
from app.schemas.webhook import (
    ActionContract,
    ContextContract,
    FactContract,
    IntentContract,
    ResponseContract,
    WebhookRequest,
)
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


def build_fact_contract(
    *,
    facts: dict[str, Any] | None,
    sources: list[str] | None,
    policy_flags: list[str] | None,
) -> tuple[dict[str, Any] | None, str | None]:
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


@dataclass(frozen=True)
class ExpectedReplyState:
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
    signals: DecisionSignals
    intent: Intent
    domain_intent: Any
    domain_meta: dict[str, Any]
    class_router_result: dict[str, Any]
    out_of_domain_signal: bool


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


def _apply_expected_reply_contract(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    message_text: str | None,
    batch_messages: list[str] | None,
    context: dict[str, Any],
    context_manager: dict[str, Any],
    now: datetime,
    current_goal: str | None,
    class_carryover: dict | None,
    message_count: int,
    policy_type: str | None,
    policy_pack: dict | None,
    client_slug: str | None,
) -> ExpectedReplyState:
    from . import _legacy as legacy

    expected_reply_type = legacy._get_expected_reply_type(context)
    intent_queue = legacy._get_intent_queue(context)
    session_memory = legacy._get_session_memory(context)
    re_entry_required = legacy._is_re_entry_required(context)
    memory_expected_reply_type = None
    if (
        not expected_reply_type
        and session_memory
        and not re_entry_required
        and not legacy._is_session_memory_expired(session_memory, now)
    ):
        memory_active_goal = session_memory.get("active_goal")
        last_question_type = session_memory.get("last_question_type")
        if isinstance(last_question_type, str):
            last_question_type = last_question_type.strip()
        if (
            (not memory_active_goal or not current_goal or memory_active_goal == current_goal)
            and last_question_type
            in {
                legacy.EXPECTED_REPLY_SERVICE,
                legacy.EXPECTED_REPLY_TIME,
                legacy.EXPECTED_REPLY_NAME,
            }
            and legacy._is_short_reply(message_text)
            and not legacy._looks_like_info_query(message_text)
            and not legacy._looks_like_policy_topic(
                message_text,
                policy_type=policy_type,
                policy_pack=policy_pack,
            )
        ):
            expected_reply_type = last_question_type
            memory_expected_reply_type = last_question_type
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "session_memory",
                    "decision": "expected_reply_fallback",
                    "expected_reply_type": last_question_type,
                },
            )
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message, {"session_memory_expected_reply": last_question_type}
                )

    expected_reply_matched: bool | None = None
    expected_reply_shortcircuit = False
    expected_reply_blocked_by_info = False
    expected_reply_text = (
        legacy._select_expected_reply_message(
            batch_messages,
            expected_reply_type=expected_reply_type,
            client_slug=client_slug,
        )
        or message_text
    )
    if expected_reply_type in {
        legacy.EXPECTED_REPLY_SERVICE,
        legacy.EXPECTED_REPLY_TIME,
        legacy.EXPECTED_REPLY_NAME,
    }:
        if message_text:
            normalized_message = legacy._normalize_service_text(message_text)
            expected_reply_blocked_by_info = (
                legacy._looks_like_info_query(message_text)
                or legacy._has_price_signal(normalized_message, message_text)
                or legacy._has_duration_signal(normalized_message, message_text)
            )
        expected_reply_text = expected_reply_text or ""
        answer_result = None
        answer_confidence = 0.0
        answer_slot = ""
        answer_value = ""
        answer_error = "blocked_by_info"
        if expected_reply_blocked_by_info:
            answer_meta = {
                "answer_interpreter_used": False,
                "answer_confidence": 0.0,
                "answer_slot": "",
                "answer_value": "",
                "answer_error": "blocked_by_info",
            }
            matched = False
            value = None
        else:
            answer_error = "invalid_result"
            prompt_hint = None
            booking_context = legacy._get_booking_context(context)
            last_question = booking_context.get("last_question")
            if expected_reply_type == legacy.EXPECTED_REPLY_SERVICE:
                prompt_hint = (
                    legacy.MSG_BOOKING_ASK_SERVICE
                    if last_question == "service"
                    else legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC
                )
            elif expected_reply_type == legacy.EXPECTED_REPLY_TIME:
                prompt_hint = legacy.MSG_BOOKING_ASK_DATETIME
            elif expected_reply_type == legacy.EXPECTED_REPLY_NAME:
                prompt_hint = legacy.MSG_BOOKING_ASK_NAME

            question_context = {
                "prompt_hint": prompt_hint,
                "booking": booking_context,
                "current_goal": current_goal,
                "service_carryover": legacy._get_service_carryover(
                    context_manager, message_count=message_count
                ),
            }
            answer_result = legacy.interpret_expected_reply(
                expected_reply_text,
                expected_reply_type=expected_reply_type,
                carryover=class_carryover,
                question_context=question_context,
                client_slug=client_slug,
            )
            answer_payload = answer_result.get("payload") if isinstance(answer_result, dict) else None
            if isinstance(answer_result, dict):
                answer_error = answer_result.get("error") or "none"
            if isinstance(answer_payload, dict):
                answer_slot = answer_payload.get("slot") or ""
                answer_value = answer_payload.get("value") or ""
                try:
                    answer_confidence = float(answer_payload.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    answer_confidence = 0.0
                answer_confidence = max(0.0, min(answer_confidence, 1.0))
            answer_meta = {
                "answer_interpreter_used": True,
                "answer_confidence": answer_confidence,
                "answer_slot": answer_slot,
                "answer_value": answer_value,
                "answer_error": answer_error,
            }

        answer_confidence_floor = 0.65
        answer_value_ok = isinstance(answer_value, str) and answer_value.strip()
        answer_slot_ok = isinstance(answer_slot, str) and answer_slot.strip()
        answer_result_ok = isinstance(answer_result, dict) and answer_result.get("ok") is True
        answer_valid = answer_result_ok and answer_slot_ok and answer_value_ok
        answer_confidence_ok = (
            answer_result_ok and answer_value_ok and answer_confidence >= answer_confidence_floor
        )
        answer_used = answer_confidence_ok or answer_valid
        answer_value_validated = True
        deterministic_matched, deterministic_value = legacy._match_expected_reply(
            expected_reply_type=expected_reply_type,
            message_text=expected_reply_text,
            client_slug=client_slug,
        )
        if deterministic_matched:
            if answer_used and isinstance(answer_value, str) and isinstance(deterministic_value, str):
                if answer_value != deterministic_value:
                    answer_error = "deterministic_override"
                    answer_confidence = 0.0
                    answer_value = deterministic_value
            matched = True
            value = deterministic_value
        else:
            if answer_used:
                answer_used = False
                answer_value_validated = False
                answer_confidence = 0.0
                answer_error = "deterministic_miss"
                answer_slot = ""
                answer_value = ""
            matched = False
            value = None
        answer_meta.update(
            {
                "answer_confidence": answer_confidence,
                "answer_slot": answer_slot,
                "answer_value": answer_value,
                "answer_error": answer_error,
            }
        )
        expected_reply_matched = matched
        if matched:
            expected_reply_shortcircuit = True
        if matched and isinstance(value, str) and expected_reply_type == legacy.EXPECTED_REPLY_SERVICE:
            context = legacy._set_service_hint(context, value, now)
            legacy._set_conversation_context(conversation, context)
            legacy._maybe_store_service_carryover(
                conversation=conversation,
                service_meta={
                    "service_query": value,
                    "service_query_source": "expected_reply",
                    "service_query_score": 1.0,
                },
                intent=None,
                message_count=message_count,
                reason="expected_reply",
            )
            context = legacy._get_conversation_context(conversation)
        if matched and isinstance(value, str):
            context = legacy._apply_expected_reply_slot(
                context,
                expected_reply_type=expected_reply_type,
                value=value,
            )
            legacy._set_conversation_context(conversation, context)
        if matched:
            next_expected = legacy.EXPECTED_REPLY_INTENT_CHOICE if intent_queue else None
            context = legacy._set_expected_reply_type(context, next_expected)
            legacy._set_conversation_context(conversation, context)
        if matched and isinstance(value, str) and isinstance(expected_reply_type, str):
            context = legacy._get_conversation_context(conversation)
            context, memory = legacy._update_session_memory_on_answer(
                context,
                expected_reply_type=expected_reply_type,
                value=value,
                now=now,
            )
            legacy._set_conversation_context(conversation, context)
            legacy._record_session_memory_update(
                conversation,
                saved_message,
                memory=memory,
                reason="answer_matched",
            )
        if expected_reply_shortcircuit:
            context_manager = legacy._get_context_manager(context)
            if context_manager.get("current_goal") != "booking":
                context_manager["current_goal"] = "booking"
                context = legacy._set_context_manager(context, context_manager)
                legacy._set_conversation_context(conversation, context)
                legacy._record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="current_goal",
                    updates={"current_goal": "booking"},
                )
                context, memory = legacy._update_session_memory_goal(
                    context, active_goal="booking", now=now
                )
                legacy._set_conversation_context(conversation, context)
                legacy._record_session_memory_update(
                    conversation,
                    saved_message,
                    memory=memory,
                    reason="active_goal",
                )
            current_goal = "booking"
        trace_payload = {
            "stage": "question_contract",
            "decision": "matched" if matched else "missed",
            "expected_reply_type": expected_reply_type,
            "value": value,
        }
        if expected_reply_shortcircuit:
            trace_payload["expected_reply_shortcircuit"] = True
        if expected_reply_blocked_by_info:
            trace_payload["expected_reply_blocked_by_info"] = True
            trace_payload.update(
                legacy._set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="expected_reply_deferred",
                )
            )
        trace_payload.update(answer_meta)
        if not answer_value_validated:
            trace_payload["expected_reply_value_validated"] = False
        legacy._record_decision_trace(conversation, trace_payload)
        if saved_message:
            updates = {
                "expected_reply_type": expected_reply_type,
                "expected_reply_matched": matched,
                "expected_reply_value": value,
            }
            if expected_reply_shortcircuit:
                updates["expected_reply_shortcircuit"] = True
            if expected_reply_blocked_by_info:
                updates["expected_reply_blocked_by_info"] = True
            updates.update(answer_meta)
            if not answer_value_validated:
                updates["expected_reply_value_validated"] = False
            legacy._update_message_decision_metadata(saved_message, updates)
        context = legacy._get_conversation_context(conversation)
        expected_reply_type = legacy._get_expected_reply_type(context)
        intent_queue = legacy._get_intent_queue(context)

    context = legacy._get_conversation_context(conversation)
    context_manager = legacy._get_context_manager(context)
    return ExpectedReplyState(
        context=context,
        context_manager=context_manager,
        expected_reply_type=expected_reply_type,
        intent_queue=intent_queue,
        expected_reply_matched=expected_reply_matched,
        expected_reply_shortcircuit=expected_reply_shortcircuit,
        expected_reply_blocked_by_info=expected_reply_blocked_by_info,
        memory_expected_reply_type=memory_expected_reply_type,
        current_goal=current_goal,
    )


def _run_intent_decomposition(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    message_text: str | None,
    expected_reply_type: str | None,
    intent_queue: list[str] | None,
    class_carryover: dict | None,
    routing: dict[str, bool],
    bypass_domain_flows: bool,
    booking_signal: bool,
    booking_block_meta: dict | None,
    booking_context: dict | None,
    booking: dict | None,
    booking_active: bool,
    expected_reply_shortcircuit: bool,
    context: dict[str, Any],
    context_manager: dict[str, Any],
    current_goal: str | None,
    consult_context: dict | None,
    message_count: int,
    now: datetime,
    client_slug: str | None,
) -> IntentDecompositionState:
    from . import _legacy as legacy

    intent_decomp_payload = None
    intent_decomp_intents: list[str] = []
    intent_decomp_primary = None
    intent_decomp_secondary: list[str] = []
    intent_decomp_service_query = None
    intent_decomp_multi = False
    intent_decomp_used = False
    consult_intent = False
    consult_topic = None
    consult_question = None
    intent_queue_choice = None
    pending_intent_queue: list[str] | None = None
    pending_expected_reply_type: str | None = None
    intent_queue_expected_next: str | None = None
    intent_queue_event: dict | None = None
    consult_return_pending = False
    consult_return_reason = None
    consult_return_prompt = None

    if routing["allow_bot_reply"] and not bypass_domain_flows and message_text:
        intent_decomp_payload = legacy.detect_multi_intent(message_text, client_slug=client_slug)
        if isinstance(intent_decomp_payload, dict):
            intent_decomp_used = True
            raw_intents = intent_decomp_payload.get("intents")
            if isinstance(raw_intents, list):
                intent_decomp_intents = [
                    item.strip().casefold()
                    for item in raw_intents
                    if isinstance(item, str) and item.strip()
                ]
            primary = intent_decomp_payload.get("primary_intent")
            if isinstance(primary, str):
                intent_decomp_primary = primary.strip().casefold()
            secondary = intent_decomp_payload.get("secondary_intents") or []
            if isinstance(secondary, list):
                intent_decomp_secondary = [
                    item.strip().casefold()
                    for item in secondary
                    if isinstance(item, str) and item.strip()
                ]
            if not intent_decomp_intents:
                if intent_decomp_primary:
                    intent_decomp_intents.append(intent_decomp_primary)
                for item in intent_decomp_secondary:
                    if item not in intent_decomp_intents:
                        intent_decomp_intents.append(item)
            intent_decomp_multi = bool(intent_decomp_payload.get("multi_intent") is True)
            service_query = intent_decomp_payload.get("service_query")
            if isinstance(service_query, str):
                service_query = service_query.strip()
                if service_query:
                    intent_decomp_service_query = service_query
            consult_intent = intent_decomp_payload.get("consult_intent") is True
            consult_topic = intent_decomp_payload.get("consult_topic")
            if isinstance(consult_topic, str):
                consult_topic = consult_topic.strip() or None
            else:
                consult_topic = None
            consult_question = intent_decomp_payload.get("consult_question")
            if isinstance(consult_question, str):
                consult_question = consult_question.strip() or None
            else:
                consult_question = None
            service_query_source = "intent_decomp"
            service_query_score = 1.0 if intent_decomp_service_query else 0.0
            consult_meta = {}
            if consult_intent:
                consult_meta["consult_intent"] = True
            if consult_topic:
                consult_meta["consult_topic"] = consult_topic
            if consult_question:
                consult_meta["consult_question"] = consult_question
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message,
                    {
                        "intent_decomp_used": True,
                        "intents": intent_decomp_intents,
                        "service_query": intent_decomp_service_query,
                        "service_query_source": service_query_source,
                        "service_query_score": service_query_score,
                        **consult_meta,
                    },
                )
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "intent_decomposition",
                    "intents": intent_decomp_intents,
                    "primary_intent": intent_decomp_primary,
                    "secondary_intents": intent_decomp_secondary,
                    "multi_intent": intent_decomp_multi,
                    "service_query": intent_decomp_service_query,
                    "service_query_source": service_query_source,
                    "service_query_score": service_query_score,
                    **consult_meta,
                },
            )

    if expected_reply_type == legacy.EXPECTED_REPLY_INTENT_CHOICE and intent_queue and message_text:
        intent_queue_choice = legacy._select_intent_from_queue(
            intent_queue,
            intent_decomp_intents if intent_decomp_used else [],
            message_text=message_text,
        )
        if intent_queue_choice:
            if intent_queue_choice == "booking":
                pending_intent_queue = []
                pending_expected_reply_type = None
                intent_queue_expected_next = "booking"
            else:
                pending_intent_queue = [
                    intent for intent in intent_queue if intent != intent_queue_choice
                ]
                pending_expected_reply_type = (
                    legacy.EXPECTED_REPLY_INTENT_CHOICE if pending_intent_queue else None
                )
                intent_queue_expected_next = pending_expected_reply_type
            intent_queue_event = {
                "decision": "dequeue",
                "chosen_intent": intent_queue_choice,
                "remaining_queue": pending_intent_queue,
                "expected_reply_matched": True,
                "expected_reply_choice": intent_queue_choice,
                "expected_reply_next": intent_queue_expected_next,
            }
            if intent_decomp_used:
                reordered_intents = [intent_queue_choice] + [
                    intent for intent in intent_decomp_intents if intent != intent_queue_choice
                ]
                intent_decomp_intents = reordered_intents
                intent_decomp_primary = intent_queue_choice
                intent_decomp_secondary = [
                    intent for intent in reordered_intents if intent != intent_decomp_primary
                ]
                intent_decomp_multi = len(reordered_intents) > 1
                if isinstance(intent_decomp_payload, dict):
                    intent_decomp_payload = {
                        **intent_decomp_payload,
                        "primary_intent": intent_decomp_primary,
                        "secondary_intents": intent_decomp_secondary,
                        "intents": intent_decomp_intents,
                        "multi_intent": intent_decomp_multi,
                    }
        else:
            intent_queue_event = {
                "decision": "no_match",
                "expected_reply_type": expected_reply_type,
                "intent_queue": intent_queue,
                "intents": intent_decomp_intents,
                "expected_reply_matched": False,
            }

    intent_decomp_set = (
        {intent.strip().casefold() for intent in intent_decomp_intents if intent}
        if intent_decomp_used
        else set()
    )
    info_class_intents: set[str] = set()
    info_class_meta: dict[str, Any] = {}
    if message_text:
        info_class_intents, info_class_meta = legacy._detect_info_class_intents(
            message_text,
            intent_decomp_set=intent_decomp_set,
        )
        if client_slug == "demo_salon" and legacy._matches_guest_policy_lexicon(message_text):
            if not isinstance(info_class_meta, dict):
                info_class_meta = {}
            info_signals = info_class_meta.get("info_signals")
            if not isinstance(info_signals, dict):
                info_signals = {}
            info_signals["guest"] = True
            info_class_meta["info_signals"] = info_signals
    info_signals = (
        info_class_meta.get("info_signals")
        if isinstance(info_class_meta, dict)
        else None
    )
    basic_info_message = bool(
        {"location", "hours"} & info_class_intents
        or (
            isinstance(info_signals, dict)
            and (info_signals.get("parking") or info_signals.get("guest"))
        )
    )
    carryover_followup = legacy._looks_like_carryover_followup(message_text)
    allow_service_carryover = bool(carryover_followup and not basic_info_message)
    preserve_info_carryover = bool(
        not os.environ.get("OPENAI_API_KEY")
        and isinstance(class_carryover, dict)
        and class_carryover.get("class") == "info_bundle"
        and class_carryover.get("info_sections")
    )
    if not allow_service_carryover:
        existing_service_carryover = legacy._get_service_carryover(
            context_manager, message_count=message_count
        )
        if (basic_info_message or class_carryover or existing_service_carryover) and not preserve_info_carryover:
            carryover_reason = "basic_info_lock" if basic_info_message else "no_followup"
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message,
                    {
                        "carryover_ignored": True,
                        "carryover_ignored_reason": carryover_reason,
                    },
                )
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "carryover_guard",
                    "decision": "ignored",
                    "reason": carryover_reason,
                },
            )
        if not preserve_info_carryover:
            class_carryover = None
    consult_interrupt_intents = (
        intent_decomp_set & legacy.CONSULT_INTERRUPT_INTENTS if intent_decomp_used else set()
    )
    if (
        current_goal == "consult"
        and consult_context
        and not consult_intent
        and (consult_interrupt_intents or booking_signal)
    ):
        consult_return_pending = True
        consult_return_reason = (
            "intent_interrupt" if consult_interrupt_intents else "booking_signal"
        )
        consult_return_prompt = legacy._build_consult_return_prompt(consult_context)
    if intent_decomp_used:
        new_goal = legacy._resolve_current_goal(intent_decomp_set, consult_intent)
        if not expected_reply_shortcircuit and not (
            current_goal == "consult" and consult_return_pending
        ):
            if new_goal and new_goal != current_goal:
                context = legacy._get_conversation_context(conversation)
                context_manager = legacy._get_context_manager(context)
                context_manager["current_goal"] = new_goal
                context = legacy._set_context_manager(context, context_manager)
                legacy._set_conversation_context(conversation, context)
                legacy._record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="current_goal",
                    updates={"current_goal": new_goal},
                )
                context, memory = legacy._update_session_memory_goal(
                    context, active_goal=new_goal, now=now
                )
                legacy._set_conversation_context(conversation, context)
                legacy._record_session_memory_update(
                    conversation,
                    saved_message,
                    memory=memory,
                    reason="active_goal",
                )
                legacy._update_compact_summary(
                    conversation=conversation,
                    saved_message=saved_message,
                    reason="intent_change",
                    now=now,
                )
                context = legacy._get_conversation_context(conversation)
                current_goal = new_goal
    if booking_context is not None:
        booking_context = legacy._get_conversation_context(conversation)
        booking = legacy._get_booking_context(booking_context)
        booking_active = bool(booking.get("active"))

    if (
        intent_decomp_used
        and not consult_intent
        and not intent_decomp_service_query
        and intent_decomp_set & legacy.SERVICE_CARRYOVER_INTENTS
        and allow_service_carryover
    ):
        skip_service_carryover = False
        if isinstance(class_carryover, dict) and legacy._looks_like_hours_followup(message_text):
            raw_sections = class_carryover.get("info_sections")
            if isinstance(raw_sections, list):
                for section in raw_sections:
                    if isinstance(section, str) and section.strip().casefold() == "hours":
                        skip_service_carryover = True
                        break
        if not skip_service_carryover:
            context = legacy._get_conversation_context(conversation)
            context_manager = legacy._get_context_manager(context)
            carryover = legacy._get_service_carryover(context_manager, message_count=message_count)
            if carryover and isinstance(intent_decomp_payload, dict):
                intent_decomp_payload = dict(intent_decomp_payload)
                intent_decomp_payload["service_query"] = carryover["service_query"]
                intent_decomp_payload["service_query_source"] = "context"
                carryover_score = carryover.get("service_query_score")
                if isinstance(carryover_score, (int, float)):
                    intent_decomp_payload["service_query_score"] = carryover_score
                intent_decomp_service_query = carryover["service_query"]
                service_query_score = (
                    float(carryover_score)
                    if isinstance(carryover_score, (int, float))
                    else 1.0
                )
                if saved_message:
                    legacy._update_message_decision_metadata(
                        saved_message,
                        {
                            "service_query": carryover["service_query"],
                            "service_query_source": "context",
                            "service_query_score": service_query_score,
                            "service_query_ttl": carryover.get("ttl"),
                            "service_query_ttl_remaining": carryover.get("remaining"),
                        },
                    )
                legacy._record_decision_trace(
                    conversation,
                    {
                        "stage": "service_carryover",
                        "decision": "used",
                        "service_query": carryover["service_query"],
                        "service_query_source": "context",
                        "service_query_score": service_query_score,
                        "ttl": carryover.get("ttl"),
                        "ttl_remaining": carryover.get("remaining"),
                    },
                )
    intent_decomp_has_booking = "booking" in intent_decomp_set
    intent_decomp_info = intent_decomp_set & legacy.BOOKING_INFO_QUESTION_TYPES
    if expected_reply_shortcircuit:
        booking_signal = True
        booking_block_meta = None
    elif intent_decomp_has_booking:
        booking_signal = True
        if booking_block_meta and booking_block_meta.get("booking_blocked_reason") == "info_question":
            booking_block_meta = None
    else:
        if booking_signal and not booking_block_meta:
            if intent_decomp_info:
                booking_block_meta = {
                    "booking_blocked_reason": "info_question",
                    "question_intents": sorted(intent_decomp_info),
                }
            elif intent_decomp_used and intent_decomp_set and intent_decomp_set != {"other"}:
                booking_block_meta = {
                    "booking_blocked_reason": "intent_decomp_no_booking",
                }
            elif not intent_decomp_used:
                booking_block_meta = {
                    "booking_blocked_reason": "intent_decomp_missing",
                }
        if booking_block_meta:
            booking_signal = False

    booking_wants_flow = (
        legacy._should_run_booking_flow(
            routing,
            booking_active=booking_active,
            booking_signal=booking_signal,
        )
        if not bypass_domain_flows
        else False
    )
    if booking_block_meta:
        legacy._record_decision_trace(
            conversation,
            {
                "stage": "booking_gate",
                "decision": "booking_blocked",
                **booking_block_meta,
            },
        )
        if saved_message:
            existing_meta = (
                saved_message.message_metadata.get("decision_meta")
                if isinstance(saved_message.message_metadata, dict)
                else None
            )
            if not isinstance(existing_meta, dict) or "booking_blocked_reason" not in existing_meta:
                legacy._update_message_decision_metadata(saved_message, booking_block_meta)
        if booking_active:
            context = (
                booking_context
                if isinstance(booking_context, dict)
                else legacy._get_conversation_context(conversation)
            )
            booking_state = (
                booking if isinstance(booking, dict) else legacy._get_booking_context(context)
            )
            booking_state = dict(booking_state)
            booking_state["active"] = False
            booking_state["last_question"] = None
            booking_state["service"] = None
            booking_state["datetime"] = None
            context = legacy._set_booking_context(context, booking_state)
            legacy._set_conversation_context(conversation, context)
            booking_active = False
            booking = booking_state
        booking_signal = False
        booking_wants_flow = False
    booking_blocked = bool(booking_block_meta)

    context = legacy._get_conversation_context(conversation)
    context_manager = legacy._get_context_manager(context)
    return IntentDecompositionState(
        intent_decomp_payload=intent_decomp_payload,
        intent_decomp_intents=intent_decomp_intents,
        intent_decomp_primary=intent_decomp_primary,
        intent_decomp_secondary=intent_decomp_secondary,
        intent_decomp_service_query=intent_decomp_service_query,
        intent_decomp_multi=intent_decomp_multi,
        intent_decomp_used=intent_decomp_used,
        intent_decomp_set=intent_decomp_set,
        consult_intent=consult_intent,
        consult_topic=consult_topic,
        consult_question=consult_question,
        intent_queue_choice=intent_queue_choice,
        pending_intent_queue=pending_intent_queue,
        pending_expected_reply_type=pending_expected_reply_type,
        intent_queue_expected_next=intent_queue_expected_next,
        intent_queue_event=intent_queue_event,
        info_class_intents=info_class_intents,
        info_class_meta=info_class_meta,
        basic_info_message=basic_info_message,
        allow_service_carryover=allow_service_carryover,
        consult_return_pending=consult_return_pending,
        consult_return_reason=consult_return_reason,
        consult_return_prompt=consult_return_prompt,
        booking_signal=booking_signal,
        booking_block_meta=booking_block_meta,
        booking_wants_flow=booking_wants_flow,
        booking_blocked=booking_blocked,
        booking_active=booking_active,
        booking_context=booking_context,
        booking=booking,
        class_carryover=class_carryover,
        context=context,
        context_manager=context_manager,
        current_goal=current_goal,
    )


def _build_router_state(
    *,
    routing: dict[str, bool],
    bypass_domain_flows: bool,
    message_text: str | None,
    booking_wants_flow: bool,
    expected_reply_shortcircuit: bool,
    expected_reply_type: str | None,
    class_carryover: dict | None,
    client_slug: str | None,
    client_config: dict | None,
    timing_context: dict,
    intent_decomp_set: set[str],
    booking_signal: bool,
    record_llm_budget_trace: Callable[[], None],
) -> dict[str, Any]:
    from . import _legacy as legacy

    controller_signal_class = legacy._resolve_controller_signal_class(
        intent_decomp_set=intent_decomp_set,
        booking_signal=booking_signal,
    )
    controller_state: dict[str, Any] | None = {
        "used": False,
        "confidence": 0.0,
        "output": legacy._build_controller_meta_output(error="skipped"),
        "error": "skipped",
        "fallback_reason": "skipped",
        "signal_class": controller_signal_class,
        "signal_match": False,
        "used_reason": None,
        "attempted": False,
        "sla": None,
    }
    controller_should_attempt = bool(
        routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
        and not booking_wants_flow
        and not expected_reply_shortcircuit
        and os.environ.get("OPENAI_API_KEY")
    )
    if controller_should_attempt:
        controller_state["attempted"] = True
        controller_state["error"] = None
        controller_state["fallback_reason"] = "skipped"
        controller_result = legacy.route_dialogue_controller(
            message_text,
            carryover=class_carryover,
            expected_reply_type=expected_reply_type,
            client_slug=client_slug,
            client_config=client_config,
            timing_context=timing_context,
        )
        if isinstance(controller_result, dict) and controller_result.get("ok") is True:
            controller_output = controller_result.get("payload")
            if isinstance(controller_output, dict):
                controller_state["output"] = legacy._ensure_controller_output_meta(
                    controller_output, error=None
                )
                confidence = controller_output.get("confidence")
                if isinstance(confidence, (int, float)):
                    controller_state["confidence"] = float(confidence)
            controller_class = controller_output.get("class")
            normalized_class = (
                legacy._normalize_class_name(controller_class)
                if isinstance(controller_class, str) and controller_class.strip()
                else None
            )
            signal_match = bool(controller_signal_class and normalized_class == controller_signal_class)
            controller_state["signal_match"] = signal_match
            if normalized_class:
                controller_state["used"] = True
                controller_state["used_reason"] = "controller"
                controller_state["fallback_reason"] = None
            else:
                controller_state["used"] = False
                controller_state["fallback_reason"] = legacy._normalize_controller_fallback_reason(
                    error="invalid_class"
                )
        else:
            controller_state["error"] = (
                controller_result.get("error")
                if isinstance(controller_result, dict)
                else "controller_failed"
            )
            controller_state["fallback_reason"] = legacy._normalize_controller_fallback_reason(
                error=controller_state["error"]
            )
            controller_state["confidence"] = 0.0
            controller_output = controller_result.get("payload") if isinstance(controller_result, dict) else None
            if isinstance(controller_output, dict):
                controller_state["output"] = legacy._ensure_controller_output_meta(
                    controller_output, error=controller_state["error"]
                )
            else:
                controller_state["output"] = legacy._build_controller_meta_output(
                    error=controller_state["error"]
                )

    record_llm_budget_trace()
    if isinstance(controller_state, dict):
        controller_output = controller_state.get("output")
        if isinstance(controller_output, dict):
            controller_output = legacy._ensure_controller_output_meta(
                controller_output, error=controller_state.get("error")
            )
            controller_state["output"] = controller_output
            controller_error_value = controller_output.get("controller_error")
        else:
            controller_state["output"] = legacy._build_controller_meta_output(
                error=str(controller_state.get("error") or "controller_failed")
            )
            controller_error_value = controller_state["output"].get("controller_error")
        controller_timeout = (
            isinstance(controller_error_value, str) and controller_error_value == "timeout"
        )
        controller_fallback_reason = controller_state.get("fallback_reason")
        if (
            isinstance(controller_fallback_reason, str)
            and controller_fallback_reason.strip().casefold() == "low_confidence"
        ):
            controller_state["fallback_reason"] = None
            controller_fallback_reason = None
        controller_fallback = controller_fallback_reason not in (None, "skipped")
        controller_state["timeout"] = controller_timeout
        controller_state["fallback"] = controller_fallback
        controller_state["sla"] = legacy._update_router_sla(  # reuse SLA tracker
            attempted=bool(controller_state.get("attempted")),
            fallback=bool(controller_fallback),
            timeout=bool(controller_timeout),
        )
    return controller_state


def _run_class_router_stage(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    message_text: str | None,
    client_slug: str | None,
    client_config: dict | None,
    remote_jid: str | None,
    info_class_intents: set[str],
    info_class_meta: dict[str, Any],
    booking_signal: bool,
    class_carryover: dict | None,
    router_state: dict | None,
    intent_decomp_payload: dict[str, Any] | None,
    expected_reply_shortcircuit: bool,
    log_timing: Callable[[str, float, dict | None], None],
) -> IntentRoutingState:
    from . import _legacy as legacy

    intent_t0 = time.monotonic()
    decision_text = _normalize_message_text(message_text)
    signals = _detect_intent_signals(decision_text)
    intent = signals.intent
    intent_contract, intent_error = build_intent_contract(signals, intent_decomp_payload)
    legacy._record_decision_trace(
        conversation,
        {
            "stage": "contract",
            "decision": "intent",
            "contract_ok": intent_error is None,
            "contract_error": intent_error,
            "contract": intent_contract,
        },
    )

    domain_intent = legacy.DomainIntent.UNKNOWN
    domain_in_score = 0.0
    domain_out_score = 0.0
    domain_meta: dict = {}
    if (
        conversation.state == legacy.ConversationState.BOT_ACTIVE.value
        and not (signals.is_greeting or signals.is_thanks or signals.is_ack or signals.is_low_signal)
        and not signals.is_status_question
    ):
        domain_intent, domain_in_score, domain_out_score, domain_meta = legacy.classify_domain_with_scores(
            message_text, client_config
        )
        log_scores = legacy._is_env_enabled(
            os.environ.get("DOMAIN_ROUTER_LOG_SCORES"), default=False
        )
        if log_scores and (domain_intent != legacy.DomainIntent.UNKNOWN or max(domain_in_score, domain_out_score) >= 0.45):
            legacy.logger.info(
                "Domain scores",
                extra={
                    "context": {
                        "client_slug": client_slug,
                        "remote_jid": remote_jid,
                        "intent": intent.value,
                        "domain_intent": domain_intent.value,
                        "in_score": round(domain_in_score, 4),
                        "out_score": round(domain_out_score, 4),
                        "in_threshold": domain_meta.get("in_threshold"),
                        "out_threshold": domain_meta.get("out_threshold"),
                        "margin": domain_meta.get("margin"),
                        "out_hits": domain_meta.get("out_hits"),
                        "strict_in_hits": domain_meta.get("strict_in_hits"),
                        "matched_in": domain_meta.get("matched_in"),
                        "matched_out": domain_meta.get("matched_out"),
                        "matched_strict_in": domain_meta.get("matched_strict_in"),
                        "anchors_in": domain_meta.get("anchors_in"),
                        "anchors_out": domain_meta.get("anchors_out"),
                        "strict_in_anchors": domain_meta.get("strict_in_anchors"),
                        "message_len": len(message_text),
                        "message_preview": message_text[:80],
                    }
                },
            )

    domain_out_hits = int(domain_meta.get("out_hits") or 0)
    domain_strict_in_hits = int(domain_meta.get("strict_in_hits") or 0)
    class_router_result = legacy._resolve_class_router_result(
        info_intents=info_class_intents,
        info_meta=info_class_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        router_state=router_state,
    )
    out_of_domain_signal = class_router_result["out_of_domain_signal"]
    log_timing(
        "intent_ms",
        (time.monotonic() - intent_t0) * 1000,
        {
            "intent": intent.value,
            "domain_intent": domain_intent.value,
            "out_of_domain_signal": out_of_domain_signal,
            "out_hits": domain_out_hits,
            "strict_in_hits": domain_strict_in_hits,
            "class_router": class_router_result,
        },
    )

    router_meta = legacy._set_router_observability(
        saved_message,
        eligible=not expected_reply_shortcircuit,
        reason="expected_reply_shortcircuit" if expected_reply_shortcircuit else "none",
    )
    controller_meta = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_used = bool(controller_meta.get("used")) if isinstance(controller_meta, dict) else False
    controller_attempted = bool(controller_meta.get("attempted")) if isinstance(controller_meta, dict) else False
    controller_fallback = bool(controller_meta.get("fallback")) if isinstance(controller_meta, dict) else False
    controller_low_confidence = (
        bool(controller_meta.get("low_confidence")) if isinstance(controller_meta, dict) else False
    )
    controller_used_reason = (
        controller_meta.get("used_reason") if isinstance(controller_meta, dict) else None
    )
    controller_confidence = (
        controller_meta.get("confidence") if isinstance(controller_meta, dict) else None
    )
    controller_error = controller_meta.get("error") if isinstance(controller_meta, dict) else None
    controller_goal = controller_meta.get("goal") if isinstance(controller_meta, dict) else None
    trace_payload = {
        "stage": "class_router",
        "classes": class_router_result.get("classes"),
        "intents": class_router_result.get("intents"),
        "carryover_intents": class_router_result.get("carryover_intents"),
        "in_signals": class_router_result.get("in_signals"),
        "out_signals": class_router_result.get("out_signals"),
        "anchors_in_hits": class_router_result.get("anchors_in_hits"),
        "anchors_out_hits": class_router_result.get("anchors_out_hits"),
        "out_of_domain_signal": out_of_domain_signal,
        "carryover_class": class_router_result.get("carryover_class"),
        "carryover_info_sections": class_router_result.get("carryover_info_sections"),
        "router_fallback_reason": class_router_result.get("router_fallback_reason"),
        "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
        "router": class_router_result.get("router"),
        "controller": controller_meta,
        "controller_used": controller_used,
        "controller_attempted": controller_attempted,
        "controller_fallback": controller_fallback,
        "controller_low_confidence": controller_low_confidence,
        "controller_used_reason": controller_used_reason,
        "controller_confidence": controller_confidence,
        "controller_error": controller_error,
        "controller_goal": controller_goal,
    }
    trace_payload.update(router_meta)
    legacy._record_decision_trace(conversation, trace_payload)
    if saved_message:
        legacy._update_message_decision_metadata(
            saved_message,
            {
                "class_router": class_router_result,
                "carryover_class": class_router_result.get("carryover_class"),
                "router_fallback_reason": class_router_result.get("router_fallback_reason"),
                "controller_used": controller_used,
                "controller_attempted": controller_attempted,
                "controller_fallback": controller_fallback,
                "controller_low_confidence": controller_low_confidence,
                "controller_used_reason": controller_used_reason,
                "controller_confidence": controller_confidence,
                "controller_error": controller_error,
                "controller_goal": controller_goal,
                "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
            },
        )

    legacy._record_decision_trace(
        conversation,
        {
            "stage": "intent",
            "decision": intent.value,
            "state": conversation.state,
            "domain_intent": domain_intent.value,
            "out_of_domain_signal": out_of_domain_signal,
            "rag_confident": False,
            "out_hits": domain_out_hits,
            "strict_in_hits": domain_strict_in_hits,
            "info_intents": sorted(info_class_intents),
        },
    )

    return IntentRoutingState(
        signals=signals,
        intent=intent,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        class_router_result=class_router_result,
        out_of_domain_signal=out_of_domain_signal,
    )
