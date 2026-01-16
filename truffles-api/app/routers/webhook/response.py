"""CTA/quiet-hours/text assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
from app.schemas.webhook import WebhookResponse


def _maybe_append_booking_cta(
    bot_response: str | None,
    *,
    conversation_state: str,
    allow_booking_flow: bool,
    has_followup: bool = False,
) -> str | None:
    if not bot_response:
        return bot_response
    from . import _legacy as legacy

    if conversation_state != legacy.ConversationState.BOT_ACTIVE.value:
        return bot_response
    if not allow_booking_flow or has_followup:
        return bot_response
    normalized = legacy._normalize_text(bot_response)
    if not normalized or "запис" in normalized:
        return bot_response
    return f"{bot_response}\n\n{legacy.MSG_BOOKING_CTA}"


def _apply_quiet_hours_notice(text: str, notice: str | None) -> str:
    if not text or not notice:
        return text
    from . import _legacy as legacy

    normalized_text = legacy._normalize_text(text)
    normalized_notice = legacy._normalize_text(notice)
    if normalized_notice and normalized_notice in normalized_text:
        return text
    if "салон закрыт" in normalized_text:
        return text
    return f"{notice}\n\n{text}"


@dataclass(frozen=True)
class ConsultFlowResult:
    response: WebhookResponse | None
    consult_intent: bool | None
    consult_topic: str | None
    consult_question: str | None
    intent_decomp_payload: dict[str, Any] | None


def _handle_consult_flow(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    routing: dict,
    bypass_domain_flows: bool,
    booking_wants_flow: bool,
    booking_active: bool,
    booking_signal: bool,
    intent_decomp_set: set[str],
    consult_intent: bool | None,
    consult_topic: str | None,
    consult_question: str | None,
    intent_decomp_payload: dict[str, Any] | None,
    intent_decomp_service_query: str | None,
    info_class_intents: set[str],
    intent_queue_followup: str | None,
    message_count: int,
    now: datetime,
    send_and_save: Callable[..., tuple[str, bool]],
    record_escalation_metric: Callable[[str], None],
) -> ConsultFlowResult:
    from app.services.demo_salon_knowledge import (
        DemoSalonDecision,
        build_consult_reply,
        get_demo_salon_service_hint,
    )

    from . import _legacy as legacy

    if not (routing.get("allow_bot_reply") and not bypass_domain_flows and message_text):
        return ConsultFlowResult(
            response=None,
            consult_intent=consult_intent,
            consult_topic=consult_topic,
            consult_question=consult_question,
            intent_decomp_payload=intent_decomp_payload,
        )

    consult_decision = None
    consult_meta: dict[str, Any] = {}
    consult_signal = False
    consult_flow_decision = None
    consult_short_circuit = False
    consult_short_circuit_reason = None
    consult_short_circuit_service = None
    consult_blocked = bool(booking_wants_flow or booking_active or booking_signal)
    if consult_intent:
        consult_blocked = False
    elif intent_decomp_set & {"booking", "pricing", "duration", "location", "hours"}:
        consult_blocked = True
    consult_candidate = None
    if not consult_blocked:
        consult_candidate = build_consult_reply(
            message_text,
            client_slug=client_slug,
            intent_decomp=intent_decomp_payload,
            conversation_id=str(conversation.id),
        )
    if consult_candidate and not consult_intent and isinstance(intent_decomp_payload, dict):
        consult_intent = True
        intent_decomp_payload = dict(intent_decomp_payload)
        intent_decomp_payload["consult_intent"] = True
        candidate_meta = consult_candidate.meta if isinstance(consult_candidate.meta, dict) else {}
        candidate_topic = candidate_meta.get("consult_topic")
        candidate_question = candidate_meta.get("consult_question")
        if candidate_topic and not consult_topic:
            consult_topic = candidate_topic
            intent_decomp_payload["consult_topic"] = candidate_topic
        if candidate_question and not consult_question:
            consult_question = candidate_question
            intent_decomp_payload["consult_question"] = candidate_question
    consult_intent_signal = bool(consult_intent or consult_candidate)
    normalized_message = legacy.normalize_for_matching(message_text) if message_text else ""
    explicit_info_signal = bool(
        booking_signal
        or legacy._has_price_signal(normalized_message, message_text)
        or legacy._has_duration_signal(normalized_message, message_text)
        or (legacy._looks_like_info_query(message_text) and not consult_intent_signal)
    )
    explicit_info_intent = bool(
        explicit_info_signal
        or (
            intent_decomp_set & {"booking", "pricing", "duration", "location", "hours"}
            and not consult_intent_signal
        )
        or (info_class_intents & {"location", "hours"} and not consult_intent_signal)
    )
    consult_candidate_meta = (
        consult_candidate.meta if consult_candidate and isinstance(consult_candidate.meta, dict) else None
    )
    if consult_intent_signal:
        consult_short_circuit_service = intent_decomp_service_query
        if not consult_short_circuit_service and client_slug == "demo_salon":
            consult_short_circuit_service = get_demo_salon_service_hint(message_text)
            if consult_short_circuit_service:
                consult_short_circuit_reason = "service_hint"
        if consult_short_circuit_service and explicit_info_intent:
            consult_short_circuit = True
            if not consult_short_circuit_reason:
                consult_short_circuit_reason = "explicit_info"
            consult_flow_trace = {
                "stage": "consult_flow",
                "decision": "short_circuit",
                "state": conversation.state,
                "reason": consult_short_circuit_reason,
            }
            consult_flow_trace["explicit_info"] = True
            consult_flow_trace["service_query"] = consult_short_circuit_service
            if consult_topic:
                consult_flow_trace["consult_topic"] = consult_topic
            if consult_question:
                consult_flow_trace["consult_question"] = consult_question
            if consult_candidate_meta:
                consult_playbook_id = consult_candidate_meta.get("consult_playbook_id")
                if consult_playbook_id:
                    consult_flow_trace["consult_playbook_id"] = consult_playbook_id
                consult_variant_id = consult_candidate_meta.get("consult_variant_id")
                if consult_variant_id:
                    consult_flow_trace["consult_variant_id"] = consult_variant_id
            legacy._record_decision_trace(conversation, consult_flow_trace)
    consult_decision = None if consult_short_circuit else consult_candidate
    if consult_decision:
        consult_meta = consult_decision.meta if isinstance(consult_decision.meta, dict) else {}
        consult_meta = dict(consult_meta)
        consult_signal = True
    if consult_intent and not consult_short_circuit:
        consult_signal = True
        consult_meta["consult_intent"] = True
        if consult_topic:
            consult_meta["consult_topic"] = consult_topic
        if consult_question:
            consult_meta["consult_question"] = consult_question
    if consult_signal:
        context = legacy._get_conversation_context(conversation)
        context_manager = legacy._get_context_manager(context)
        if consult_decision:
            consult_flow_decision = (
                "consult_escalate" if consult_decision.action == "escalate" else "consult_reply"
            )
        elif legacy._should_escalate_for_clarify(context_manager, "consult"):
            clarify_count, _ = legacy._get_clarify_attempt_state(context_manager, "consult")
            legacy._record_context_manager_decision(
                conversation,
                saved_message,
                decision="clarify_limit",
                updates={
                    "clarify_attempt": {"intent": "consult", "count": clarify_count},
                    "clarify_reason": "consult_no_service",
                    "clarify_limit": True,
                },
            )
            consult_meta["clarify_limit"] = True
            consult_meta["clarify_reason"] = "consult_no_service"
            consult_meta["clarify_attempt"] = {"intent": "consult", "count": clarify_count}
            consult_decision = DemoSalonDecision(
                action="escalate",
                response=legacy.MSG_ESCALATED,
                intent="consult_no_service",
                meta=consult_meta,
            )
            consult_flow_decision = "consult_escalate"
        else:
            clarify_count = legacy._register_clarify_attempt(
                conversation=conversation,
                saved_message=saved_message,
                intent="consult",
                now=now,
                reason="consult",
            )
            context = legacy._get_conversation_context(conversation)
            context = legacy._set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
                reason="consult_clarify",
                now=now,
            )
            consult_meta["consult_questions"] = [legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC]
            consult_meta["clarify_attempt"] = {"intent": "consult", "count": clarify_count}
            consult_meta["clarify_reason"] = "consult"
            consult_meta["expected_reply_type"] = legacy.EXPECTED_REPLY_SERVICE
            consult_decision = DemoSalonDecision(
                action="reply",
                response=legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC,
                intent="consult_reply",
                meta=consult_meta,
            )
            consult_flow_decision = "consult_clarify"

    if consult_decision:
        if consult_flow_decision:
            consult_flow_trace = {
                "stage": "consult_flow",
                "decision": consult_flow_decision,
                "state": conversation.state,
            }
            if consult_flow_decision == "consult_clarify":
                consult_flow_trace["expected_reply_type"] = legacy.EXPECTED_REPLY_SERVICE
                consult_flow_trace["reason"] = "consult_clarify"
            elif consult_flow_decision == "consult_escalate":
                consult_flow_trace["reason"] = "consult_no_service"
            else:
                consult_flow_trace["reason"] = "consult_pack"
            consult_playbook_id = consult_meta.get("consult_playbook_id")
            if consult_playbook_id:
                consult_flow_trace["consult_playbook_id"] = consult_playbook_id
            consult_variant_id = consult_meta.get("consult_variant_id")
            if consult_variant_id:
                consult_flow_trace["consult_variant_id"] = consult_variant_id
            legacy._record_decision_trace(conversation, consult_flow_trace)
        if consult_decision.action == "reply":
            context = legacy._get_conversation_context(conversation)
            context_manager = legacy._get_context_manager(context)
            context_manager["current_goal"] = "consult"
            context_manager = legacy._set_consult_context(
                context_manager,
                consult_meta=consult_meta,
                message_count=message_count,
            )
            context = legacy._set_context_manager(context, context_manager)
            legacy._set_conversation_context(conversation, context)
            context, memory = legacy._update_session_memory_goal(
                context, active_goal="consult", now=now
            )
            legacy._set_conversation_context(conversation, context)
            legacy._record_session_memory_update(
                conversation,
                saved_message,
                memory=memory,
                reason="active_goal",
            )
            consult_trace = {
                "stage": "consult_context",
                "decision": "set",
                "current_goal": "consult",
                "ttl": legacy.CONSULT_CONTEXT_TTL_MESSAGES,
            }
            consult_topic = consult_meta.get("consult_topic")
            if consult_topic:
                consult_trace["consult_topic"] = consult_topic
            legacy._record_decision_trace(conversation, consult_trace)
            if saved_message:
                legacy._update_message_decision_metadata(saved_message, {"current_goal": "consult"})
        consult_trace = {
            "stage": "consult",
            "decision": consult_decision.action,
            "intent": consult_decision.intent,
            "state": conversation.state,
        }
        consult_trace.update(consult_meta)
        legacy._record_decision_trace(conversation, consult_trace)
        legacy._record_message_decision_meta(
            saved_message,
            action=consult_decision.action,
            intent=consult_decision.intent,
            source="consult",
            fast_intent=False,
        )
        if saved_message and consult_meta:
            legacy._update_message_decision_metadata(saved_message, consult_meta)

        if consult_decision.action == "escalate":
            bot_response = consult_decision.response or legacy.MSG_ESCALATED
            legacy._reset_low_confidence_retry(conversation)

            result_message = "Consult escalation"
            _, reused, telegram_sent = legacy._reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source="consult",
                intent=consult_decision.intent,
            )
            if reused:
                result_message = f"Consult reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == legacy.ConversationState.BOT_ACTIVE.value and routing.get(
                "allow_handover_create"
            ):
                record_escalation_metric("intent")
                result = legacy.escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value=consult_decision.intent or "consult",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = legacy.send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"Consult escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"Consult escalation failed: {result.error}"
            else:
                result_message = "Consult escalation skipped (already pending)"

            bot_response, sent = send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return ConsultFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                consult_intent=consult_intent,
                consult_topic=consult_topic,
                consult_question=consult_question,
                intent_decomp_payload=intent_decomp_payload,
            )

        bot_response = consult_decision.response
        bot_response = legacy._combine_sidecar(bot_response, intent_queue_followup)
        legacy._reset_low_confidence_retry(conversation)
        bot_response, sent = send_and_save(bot_response)
        result_message = "Consult reply sent" if sent else "Consult reply send failed"
        db.commit()
        return ConsultFlowResult(
            response=WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            ),
            consult_intent=consult_intent,
            consult_topic=consult_topic,
            consult_question=consult_question,
            intent_decomp_payload=intent_decomp_payload,
        )

    return ConsultFlowResult(
        response=None,
        consult_intent=consult_intent,
        consult_topic=consult_topic,
        consult_question=consult_question,
        intent_decomp_payload=intent_decomp_payload,
    )


__all__ = ["ConsultFlowResult", "_apply_quiet_hours_notice", "_handle_consult_flow", "_maybe_append_booking_cta"]
