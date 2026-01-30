"""Intent and decision helpers for webhook routing."""

from __future__ import annotations

import asyncio
import base64
import functools
import hashlib
import mimetypes
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import UUID

import httpx
from pydantic import ValidationError
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.adapters.chatflow import ChatFlowAdapter
from app.contracts.decision import (
    DECISION_GRAPH_STAGES,
    DecisionOutcome,
    DecisionPlan,
    DecisionSignals,
    DecisionStage,
    ExpectedReplyState,
    IntentDecompositionState,
    IntentRoutingState,
    build_action_contract,
    build_context_contract,
    build_decision_plan,
    build_fact_contract,
    build_intent_contract,
    build_response_contract,
)
from app.logging_config import (
    get_logger,
    get_trace_id,
    record_escalation_count,
    record_inbound_count,
    record_policy_count,
    start_span,
)
from app.models import Branch, Client, ClientSettings, Conversation, Handover, Message, User
from app.ports.messaging import MessageOptions
from app.routers.webhook.booking import (
    BOOKING_SLOT_ORDER,
    _apply_booking_slot,
    _apply_expected_reply_slot,
    _build_booking_summary,
    _clear_service_hint,
    _expected_reply_for_booking_question,
    _get_booking_confirm_threshold,
    _get_booking_confirmation,
    _get_booking_context,
    _get_recent_service_hint,
    _handle_booking_flow,
    _handle_booking_interrupt,
    _is_blocked_slot_message,
    _is_booking_confirm_enabled,
    _is_booking_related_message,
    _is_booking_time_service_decision,
    _match_expected_reply,
    _next_booking_prompt,
    _resolve_datetime_offline,
    _select_expected_reply_message,
    _select_last_non_booking_message,
    _set_booking_confirmation,
    _set_booking_context,
    _set_service_hint,
    _update_booking_from_message,
    _update_booking_from_messages,
    _validate_datetime_slot,
    _validate_name_slot,
    _validate_service_slot,
)
from app.routers.webhook.branch_selection import (
    BRANCH_CONTEXT_KEY,
    BRANCH_SELECTION_KEY,
    MSG_BRANCH_SELECTED,
    _apply_branch_selection,
    _build_branch_prompt,
    _build_branch_selection,
    _coerce_uuid,
    _get_active_branches,
    _get_branch_selection,
    _get_user_branch_preference,
    _handle_branch_selection_gate,
    _is_branch_only_message,
    _match_branch_choice,
    _set_branch_selection,
    _set_user_branch_preference,
)
from app.routers.webhook.context_manager import (
    _build_compact_summary_text,
    _build_consult_return_prompt,
    _get_asr_confirmation,
    _get_asr_inflight,
    _get_class_carryover,
    _get_consult_context,
    _get_context_manager,
    _get_conversation_context,
    _get_expected_reply_reason,
    _get_expected_reply_type,
    _get_low_confidence_retry_count,
    _get_memory_pending,
    _get_memory_profile,
    _get_reengage_confirmation,
    _get_service_carryover,
    _get_style_reference_pending,
    _increment_context_message_count,
    _is_asr_confirmation_active,
    _is_re_entry_required,
    _is_reengage_confirmation_active,
    _maybe_store_class_carryover,
    _maybe_store_service_carryover,
    _prune_class_carryover,
    _prune_consult_context,
    _prune_service_carryover,
    _record_context_manager_decision,
    _reset_low_confidence_retry,
    _resolve_current_goal,
    _set_asr_confirmation,
    _set_asr_inflight,
    _set_class_carryover,
    _set_consult_context,
    _set_context_manager,
    _set_conversation_context,
    _set_expected_reply_context,
    _set_expected_reply_type,
    _set_handover_confirmation,
    _set_low_confidence_retry_count,
    _set_memory_pending,
    _set_memory_profile,
    _set_re_entry_required,
    _set_reengage_confirmation,
    _set_service_carryover,
    _set_style_reference_pending,
    _update_compact_summary,
)
from app.routers.webhook.dedup import (
    _buffer_user_message,
    _drain_buffered_messages,
    _get_debounce_redis,
    _handle_debounce_gate,
    _handle_dedup_gate,
    is_duplicate_message_id,
    should_process_debounced_message,
)
from app.routers.webhook.guards import (
    _apply_session_timeout_reset,
    _booking_clarify_guard_reason,
    _format_intent_queue_prompt,
    _format_multi_intent_followup,
    _get_clarify_attempt_state,
    _get_intent_queue,  # noqa: F401
    _handle_clarify_limit_escalation,
    _handle_opt_out_mute_gate,
    _handle_reengage_and_mute_gate,
    _register_clarify_attempt,
    _select_intent_from_queue,  # noqa: F401
    _set_clarify_attempt,
    _set_intent_queue,
    _should_escalate_for_clarify,
)
from app.routers.webhook.info import (
    _build_info_intent_reply,
    _count_anchor_hits,
    _detect_info_class_intents,
    _extract_truth_gate_info_intents,
    _handle_info_flow,
    _handle_offline_info_class,
    _handle_truth_gate_fallback,
    _is_short_reply,
    _looks_like_info_query,
    _tokenize_for_matching,
)
from app.routers.webhook.media import (
    MediaDecision,
    MediaInfo,
    _build_media_caption,
    _deserialize_media_decision,
    _evaluate_media_decision,
    _extract_media_info,
    _get_media_policy,
    _get_media_rate_settings,
    _get_transcription_settings,
    _is_asr_low_confidence,
    _is_placeholder_text,
    _is_style_reference_request,
    _is_voice_note,
    _maybe_transcribe_voice,
    _send_telegram_media,
    _serialize_media_decision,
    _store_media_locally,
    _update_message_asr_metadata,
    _update_message_media_metadata,
)
from app.routers.webhook.outbox import _handle_enqueue_only_accept, _prepare_skip_persist
from app.routers.webhook.pending import (
    _forward_pending_to_telegram,
    _handle_handover_confirmation_gate,
    _handle_manager_active_gate,
    _handle_pending_gate,
)
from app.routers.webhook.policy import (
    _demo_salon_escalation_gate,
    _demo_salon_price_sidecar,
    _detect_booking_cancel,
    _detect_llm_guard_topics,
    _format_discounts_policy_reply,
    _get_policy_handler,
    _get_policy_pack,
    _get_policy_type,
    _get_routing_policy,
    _handle_hard_law_gate,
    _handle_policy_escalation_gate,
    _has_discount_policy_rules,
    _looks_like_policy_topic,
    _looks_like_promotions_request,
    _resolve_hard_law_sections,
    _should_escalate_to_pending,
    _should_run_booking_flow,
    _should_run_demo_truth_gate,
    _should_run_truth_gate,
)
from app.routers.webhook.response import (
    _compose_fact_response,
    _ensure_rag_rewrite,
    _handle_ai_response_action,
    _handle_consult_flow,
    _handle_llm_primary,
    _maybe_apply_consult_return,
    _record_rag_meta,
)
from app.routers.webhook.response import (
    _finalize_bot_response as _finalize_bot_response_helper,
)
from app.routers.webhook.response import (
    _record_llm_budget_trace as _record_llm_budget_trace_helper,
)
from app.routers.webhook.response import (
    _send_and_save as _send_and_save_helper,
)
from app.routers.webhook.response import (
    _send_response as _send_response_helper,
)
from app.routers.webhook.router_sla import _update_router_sla
from app.routers.webhook.session_memory import (
    _get_session_memory,
    _is_session_memory_expired,
    _is_session_reset_only_message,
    _normalize_session_memory,
    _parse_session_memory_time,
    _record_session_memory_update,
    _reset_session_memory,
    _session_memory_snapshot,
    _set_session_memory,
    _should_reset_session_memory,
    _update_session_memory_goal,
    _update_session_memory_on_answer,
    _update_session_memory_on_question,
)
from app.routers.webhook.shield import _handle_shield_gate
from app.routers.webhook.trace import (
    _attach_llm_cache_flag,
    _merge_message_timing,
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.ai_service import (
    ACKNOWLEDGEMENT_RESPONSE,
    BOT_STATUS_RESPONSE,
    GREETING_RESPONSE,
    HIGH_CONFIDENCE_THRESHOLD,
    MID_CONFIDENCE_THRESHOLD,
    OUT_OF_DOMAIN_RESPONSE,
    THANKS_RESPONSE,
    classify_confirmation,
    detect_multi_intent,
    detect_refusal_flags,
    is_acknowledgement_message,
    is_bot_status_question,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
    normalize_for_matching,
    rewrite_for_service_match,
    transcribe_audio_with_fallback,
)
from app.services.chatflow_service import get_instance_id
from app.services.conversation_service import get_or_create_conversation, get_or_create_user
from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    _detect_promotion_intent,
    _has_duration_signal,
    _has_price_signal,
    _match_service,
    build_evening_greeting,
    build_quiet_hours_notice,
    compose_multi_truth_reply,
    format_reply_from_truth,
    get_demo_salon_decision,
    get_demo_salon_price_item,
    get_demo_salon_price_reply,
    get_demo_salon_service_decision,
    get_demo_salon_service_hint,
    load_yaml_truth,
    semantic_question_type,
    semantic_service_match,
)
from app.services.demo_salon_knowledge import (
    _normalize_text as _normalize_service_text,
)
from app.services.escalation_service import get_telegram_credentials, send_telegram_notification
from app.services.intent_service import (
    CONTROLLER_TIMEOUT_SECONDS,
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    classify_intent,
    interpret_expected_reply,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
    is_rejection,
    route_dialogue_controller,
    should_escalate,
)
from app.services.message_service import generate_bot_response, save_message, select_handover_user_message
from app.services.outbox_service import build_inbound_message_id, enqueue_outbox_message
from app.services.state_machine import ConversationState
from app.services.state_service import (
    apply_simulation_context,
    build_simulation_context,
    escalate_to_pending,
    get_simulation_time,
    is_simulation_context,
    manager_resolve,
    transition_state,
)
from app.services.telegram_service import TelegramService


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


def _detect_intent_signals(message_text: str, *, timing_context: dict | None = None) -> DecisionSignals:
    from . import _legacy as legacy

    intent_hint = None
    if isinstance(timing_context, dict):
        hinted = timing_context.get("short_intent_hint")
        if isinstance(hinted, str):
            try:
                intent_hint = Intent(hinted)
            except ValueError:
                intent_hint = None

    is_greeting = legacy.is_greeting_message(message_text)
    is_thanks = legacy.is_thanks_message(message_text)
    is_ack = legacy.is_acknowledgement_message(message_text)
    is_low_signal = legacy.is_low_signal_message(message_text)
    is_status_question = legacy.is_bot_status_question(message_text)

    if intent_hint == Intent.GREETING:
        intent = Intent.GREETING
        legacy.logger.info("Intent shortcut: greeting (llm hint)")
    elif intent_hint == Intent.THANKS:
        intent = Intent.THANKS
        legacy.logger.info("Intent shortcut: thanks (llm hint)")
    elif intent_hint == Intent.QUESTION:
        intent = Intent.QUESTION
        legacy.logger.info("Intent shortcut: question (llm hint)")
    elif is_greeting:
        intent = Intent.GREETING
        legacy.logger.info("Intent shortcut: greeting")
    elif is_thanks:
        intent = Intent.THANKS
        legacy.logger.info("Intent shortcut: thanks")
    elif is_ack or is_low_signal:
        intent = Intent.OTHER
        legacy.logger.info("Intent shortcut: acknowledgement/low-signal -> other")
    else:
        intent = legacy.classify_intent(message_text, timing_context=timing_context)
        legacy.logger.info(f"Intent classified: {intent.value}")

    if intent_hint in {Intent.GREETING, Intent.THANKS, Intent.QUESTION}:
        is_greeting = intent_hint == Intent.GREETING
        is_thanks = intent_hint == Intent.THANKS
        is_ack = False
        is_low_signal = False
        is_status_question = False

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
    expected_reply_reason = legacy._get_expected_reply_reason(context)
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
            and not legacy._looks_like_info_query(message_text, client_slug=client_slug)
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
                legacy._looks_like_info_query(message_text, client_slug=client_slug)
                or legacy._has_price_signal(normalized_message, message_text)
                or legacy._has_duration_signal(normalized_message, message_text)
            )
            if (
                expected_reply_blocked_by_info
                and expected_reply_type == legacy.EXPECTED_REPLY_TIME
                and legacy._extract_datetime(message_text)
            ):
                expected_reply_blocked_by_info = False
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

            confirmation_pending = _get_booking_confirmation(booking_context)
            if confirmation_pending:
                answer_error = "booking_confirm_pending"
                answer_meta = {
                    "answer_interpreter_used": False,
                    "answer_confidence": 0.0,
                    "answer_slot": "",
                    "answer_value": "",
                    "answer_error": "booking_confirm_pending",
                }
            else:
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

        if answer_meta.get("answer_interpreter_used"):
            _record_decision_trace(
                conversation,
                {
                    "stage": "slot_extract",
                    "decision": "llm",
                    "slot": answer_slot,
                    "value": answer_value,
                    "confidence": answer_confidence,
                    "error": answer_error,
                },
            )
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
        expected_slot_key = _expected_reply_slot_key(expected_reply_type)
        if answer_used and expected_slot_key and answer_slot and answer_slot != expected_slot_key:
            answer_used = False
            answer_confidence = 0.0
            answer_error = "slot_mismatch"
            answer_slot = ""
            answer_value = ""
        matched = False
        value = None
        slot_source = None
        slot_confidence = 0.0
        slot_validation_error = None
        use_llm_slot = _is_booking_confirm_enabled()
        (
            deterministic_matched,
            deterministic_value,
            normalization_flags,
        ) = _match_expected_reply_candidates(
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
            slot_source = "deterministic"
            slot_confidence = 1.0
        else:
            if answer_used and use_llm_slot:
                validated_value = _validate_expected_reply_value(
                    expected_reply_type=expected_reply_type,
                    value=answer_value,
                    client_slug=client_slug,
                )
                if validated_value:
                    matched = True
                    value = validated_value
                    slot_source = "llm"
                    slot_confidence = answer_confidence
                else:
                    answer_value_validated = False
                    slot_validation_error = "validation_failed"
            elif answer_used and not use_llm_slot:
                answer_used = False
                answer_value_validated = False
                answer_confidence = 0.0
                answer_error = "deterministic_miss"
                answer_slot = ""
                answer_value = ""
        slot_confirmation_required = False
        if matched and slot_source == "llm" and use_llm_slot:
            threshold = _get_booking_confirm_threshold()
            if slot_confidence < threshold:
                slot_confirmation_required = True
        answer_meta["normalization_flags"] = normalization_flags
        answer_meta.update(
            {
                "answer_confidence": answer_confidence,
                "answer_slot": answer_slot,
                "answer_value": answer_value,
                "answer_error": answer_error,
                "slot_confidence": slot_confidence,
                "slot_source": slot_source,
                "slot_validation_error": slot_validation_error,
                "slot_confirmation_required": slot_confirmation_required,
            }
        )
        if matched:
            _record_decision_trace(
                conversation,
                {
                    "stage": "slot_validate",
                    "decision": "matched",
                    "slot": expected_slot_key,
                    "value": value,
                    "confidence": slot_confidence,
                    "source": slot_source,
                    "confirmation_required": slot_confirmation_required,
                    "validation_error": slot_validation_error,
                },
            )
        expected_reply_matched = matched
        if matched and not slot_confirmation_required:
            expected_reply_shortcircuit = True
        if matched and not slot_confirmation_required and isinstance(value, str) and expected_reply_type == legacy.EXPECTED_REPLY_SERVICE:
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
        if matched and not slot_confirmation_required and isinstance(value, str):
            context = legacy._apply_expected_reply_slot(
                context,
                expected_reply_type=expected_reply_type,
                value=value,
            )
            legacy._set_conversation_context(conversation, context)
            if expected_slot_key:
                confirmation_state = _get_booking_confirmation(
                    legacy._get_booking_context(context)
                )
                if (
                    confirmation_state
                    and confirmation_state.get("slot") == expected_slot_key
                ):
                    booking_state = _set_booking_confirmation(
                        legacy._get_booking_context(context), None
                    )
                    context = legacy._set_booking_context(context, booking_state)
                    legacy._set_conversation_context(conversation, context)
        if matched and not slot_confirmation_required:
            next_expected = legacy.EXPECTED_REPLY_INTENT_CHOICE if intent_queue else None
            context = legacy._set_expected_reply_type(context, next_expected)
            legacy._set_conversation_context(conversation, context)
        if matched and not slot_confirmation_required and isinstance(value, str) and isinstance(expected_reply_type, str):
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
        if matched and slot_confirmation_required and isinstance(value, str) and expected_slot_key:
            context = legacy._get_conversation_context(conversation)
            booking_state = legacy._get_booking_context(context)
            if not _get_booking_confirmation(booking_state):
                confirmation = {
                    "slot": expected_slot_key,
                    "value": value,
                    "confidence": slot_confidence,
                    "source": slot_source,
                }
                booking_state = _set_booking_confirmation(booking_state, confirmation)
                context = legacy._set_booking_context(context, booking_state)
                legacy._set_conversation_context(conversation, context)
        if expected_reply_shortcircuit:
            if not expected_reply_reason or expected_reply_reason == "booking_prompt":
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
    expected_reply_reason: str | None,
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
    timing_context: dict | None = None,
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

    controller_reserve_ms = 0.0
    if (
        routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
        and not expected_reply_shortcircuit
        and os.environ.get("OPENAI_API_KEY")
    ):
        controller_reserve_ms = max(float(CONTROLLER_TIMEOUT_SECONDS) * 1000, 0.0)

    if routing["allow_bot_reply"] and not bypass_domain_flows and message_text:
        intent_decomp_payload = legacy.detect_multi_intent(
            message_text,
            client_slug=client_slug,
            timing_context=timing_context,
            reserve_ms=controller_reserve_ms,
        )
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
            pending_intent_queue = []
            pending_expected_reply_type = None
            intent_queue_event = {
                "decision": "drop",
                "expected_reply_type": expected_reply_type,
                "intent_queue": intent_queue,
                "intents": intent_decomp_intents,
                "expected_reply_matched": False,
                "expected_reply_next": None,
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
        if legacy._matches_guest_policy_lexicon(message_text, client_slug=client_slug):
            if not isinstance(info_class_meta, dict):
                info_class_meta = {}
            info_signals = info_class_meta.get("info_signals")
            if not isinstance(info_signals, dict):
                info_signals = {}
            info_signals["guest"] = True
            info_class_meta["info_signals"] = info_signals
    if (
        not info_class_intents
        and expected_reply_shortcircuit
        and current_goal != "booking"
        and isinstance(class_carryover, dict)
    ):
        carryover_intents = class_carryover.get("intents")
        if isinstance(carryover_intents, list):
            for intent_name in carryover_intents:
                if isinstance(intent_name, str) and intent_name.strip():
                    info_class_intents.add(intent_name.strip().casefold())
    info_signals = (
        info_class_meta.get("info_signals")
        if isinstance(info_class_meta, dict)
        else None
    )
    guest_policy_signal = bool(
        isinstance(info_signals, dict) and info_signals.get("guest")
    )
    basic_info_message = bool(
        {"location", "hours"} & info_class_intents
        or (
            isinstance(info_signals, dict)
            and (info_signals.get("parking") or info_signals.get("guest"))
        )
    )
    carryover_followup = legacy._looks_like_carryover_followup(message_text)
    hours_followup = legacy._looks_like_hours_followup(message_text)
    expected_reply_followup = bool(
        expected_reply_shortcircuit and current_goal != "booking"
    )
    allow_service_carryover = bool(
        (carryover_followup or expected_reply_followup) and not basic_info_message
    )
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_key_missing = not openai_key or openai_key.strip().casefold() in {"none", "null"}
    short_noisy_followup = False
    if (
        openai_key_missing
        and isinstance(class_carryover, dict)
        and class_carryover.get("class") == "info_bundle"
        and class_carryover.get("info_sections")
        and message_text
    ):
        normalized = normalize_for_matching(message_text)
        tokens = _tokenize_for_matching(normalized)
        if tokens and len(tokens) <= SESSION_MEMORY_SHORT_TOKENS:
            has_digits = any(ch.isdigit() for ch in message_text)
            has_service_hint = bool(
                get_demo_salon_service_hint(message_text, client_slug=client_slug)
            )
            short_noisy_followup = not has_digits and "?" not in message_text and not has_service_hint
    preserve_info_carryover = bool(
        openai_key_missing
        and (carryover_followup or hours_followup or short_noisy_followup)
        and isinstance(class_carryover, dict)
        and class_carryover.get("class") == "info_bundle"
        and class_carryover.get("info_sections")
    )
    if not allow_service_carryover:
        force_keep_info_carryover = bool(
            isinstance(class_carryover, dict)
            and class_carryover.get("class") == "info_bundle"
            and hours_followup
        )
        existing_service_carryover = legacy._get_service_carryover(
            context_manager, message_count=message_count
        )
        if (
            (basic_info_message or class_carryover or existing_service_carryover)
            and not preserve_info_carryover
            and not force_keep_info_carryover
        ):
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
        if not preserve_info_carryover and not force_keep_info_carryover:
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
        new_goal = legacy._resolve_current_goal(
            intent_decomp_set,
            consult_intent,
            expected_reply_type,
            expected_reply_reason,
        )
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
        if not expected_reply_reason or expected_reply_reason == "booking_prompt":
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
    if guest_policy_signal and not booking_active:
        booking_signal = False
        booking_wants_flow = False
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
    timing_context: dict | None,
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
    signals = _detect_intent_signals(decision_text, timing_context=timing_context)
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
    in_signals = class_router_result.get("in_signals") or []
    if (
        conversation.state == legacy.ConversationState.BOT_ACTIVE.value
        and intent == Intent.OTHER
        and not expected_reply_shortcircuit
        and not in_signals
        and not out_of_domain_signal
    ):
        out_of_domain_signal = True
        out_signals = list(class_router_result.get("out_signals") or [])
        if "intent_other" not in out_signals:
            out_signals.append("intent_other")
        class_router_result["out_signals"] = out_signals
        classes = list(class_router_result.get("classes") or [])
        if "out_of_domain" not in classes:
            classes.append("out_of_domain")
        class_router_result["classes"] = classes
        class_router_result["out_of_domain_signal"] = True
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

# Legacy webhook orchestrator + helpers moved from _legacy.py.

logger = get_logger("webhook")
_BRANCH_EXPORTS = (
    BRANCH_CONTEXT_KEY,
    BRANCH_SELECTION_KEY,
    MSG_BRANCH_SELECTED,
    _apply_branch_selection,
    _build_branch_prompt,
    _build_branch_selection,
    _coerce_uuid,
    _get_active_branches,
    _get_branch_selection,
    _get_user_branch_preference,
    _is_branch_only_message,
    _match_branch_choice,
    _set_branch_selection,
    _set_user_branch_preference,
)
_DEDUP_EXPORTS = (
    _buffer_user_message,
    _drain_buffered_messages,
    is_duplicate_message_id,
    should_process_debounced_message,
)
ROUTER_SIGNAL_CONFIDENCE_BONUS = 0.1
ROUTER_SIGNAL_CONFIDENCE_FLOOR = 0.2
CONTROLLER_CONFIDENCE_THRESHOLD = float(
    os.getenv("CONTROLLER_CONFIDENCE_THRESHOLD", "0.3") or 0.3
)
WEBHOOK_PIPELINE_BUDGET_DEFAULT_MS = 7000


def _get_pipeline_budget_ms() -> int:
    raw = os.environ.get("WEBHOOK_PIPELINE_BUDGET_MS")
    if raw is None or not str(raw).strip():
        return WEBHOOK_PIPELINE_BUDGET_DEFAULT_MS
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return WEBHOOK_PIPELINE_BUDGET_DEFAULT_MS
    if value <= 0:
        return WEBHOOK_PIPELINE_BUDGET_DEFAULT_MS
    return value


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


MEDIA_TYPE_ALIASES = {
    "image": "photo",
    "photo": "photo",
    "jpg": "photo",
    "jpeg": "photo",
    "png": "photo",
    "audio": "audio",
    "voice": "audio",
    "ptt": "audio",
    "document": "document",
    "pdf": "document",
    "doc": "document",
    "docx": "document",
    "xlsx": "document",
    "xls": "document",
    "video": "video",
}
MEDIA_MAX_DEFAULT_MB = {"photo": 8, "audio": 8, "document": 10}
MEDIA_RATE_LIMIT_DEFAULTS = {
    "count": 5,
    "window_seconds": 600,
    "daily_count": 20,
    "bytes_mb": 30,
    "block_seconds": 900,
}
MEDIA_STORAGE_DEFAULT_DIR = os.environ.get("MEDIA_STORAGE_DIR", "/home/zhan/truffles-media")
MEDIA_STORAGE_MAX_BYTES = 25 * 1024 * 1024
AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB = 2.0

STYLE_REFERENCE_PATTERNS = (
    re.compile(r"\bкак на (фото|картин\w+|примере)\b"),
    re.compile(r"\bпо (фото|картин\w+|референс\w*)\b"),
    re.compile(r"\bреференс\w*\b"),
    re.compile(r"\bреф\b"),
    re.compile(r"\bв стиле\b"),
    re.compile(r"\bпохоже на\b"),
)
STYLE_REFERENCE_HINT_TOKENS = ("фото", "картин", "референс", "реф", "пример")


def _find_message_by_message_id(db: Session, client_id: UUID, message_id: str) -> Message | None:
    if not message_id:
        return None
    return (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            or_(
                Message.message_metadata["message_id"].astext == message_id,
                Message.message_metadata["messageId"].astext == message_id,
            ),
        )
        .order_by(Message.created_at.desc())
        .first()
    )


def _find_message_by_conversation_created_at(
    db: Session,
    conversation_id: UUID,
    created_at: datetime | None,
    *,
    message_text: str | None = None,
    lookback_seconds: int = 120,
) -> Message | None:
    if not conversation_id or not created_at:
        return None
    window_start = created_at - timedelta(seconds=lookback_seconds)
    window_end = created_at + timedelta(seconds=lookback_seconds)
    rows = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == "user",
            Message.created_at >= window_start,
            Message.created_at <= window_end,
        )
        .order_by(Message.created_at.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return None
    normalized_target = normalize_for_matching(message_text) if message_text else ""
    if normalized_target:
        for msg in rows:
            if normalize_for_matching(msg.content or "") == normalized_target:
                return msg
    return min(
        rows,
        key=lambda msg: abs((msg.created_at - created_at).total_seconds()) if msg.created_at else float("inf"),
    )


def _router_observability_meta(*, eligible: bool, reason: str) -> dict:
    return {
        "router_eligible": bool(eligible),
        "router_skipped_reason": reason,
        "controller_eligible": bool(eligible),
        "controller_skipped_reason": reason,
    }


def _set_router_observability(message: Message | None, *, eligible: bool, reason: str) -> dict:
    updates = _router_observability_meta(eligible=eligible, reason=reason)
    if message:
        _update_message_decision_metadata(message, updates)
    return updates


_DEFAULT_RAG_SCORES = {"bm25_max": 0.0, "vector_max": 0.0, "hybrid_max": 0.0}


def _merge_rag_scores(rag_scores: dict | None) -> dict:
    merged = dict(rag_scores) if isinstance(rag_scores, dict) else {}
    for key, value in _DEFAULT_RAG_SCORES.items():
        if not isinstance(merged.get(key), (int, float)):
            merged[key] = value
    return merged if merged else dict(_DEFAULT_RAG_SCORES)


def _derive_rag_status(
    *,
    rag_scores: dict,
    rag_best_score: float | None,
    rag_attempted: bool,
) -> tuple[bool, str | None]:
    if not rag_attempted:
        return False, "overridden_by_gate"
    best_score = float(rag_best_score or 0.0)
    if best_score >= MID_CONFIDENCE_THRESHOLD:
        return True, None
    vector_count = int(rag_scores.get("vector_count") or 0)
    bm25_count = int(rag_scores.get("bm25_count") or 0)
    if vector_count <= 0 and bm25_count <= 0:
        return False, "empty"
    return False, "low_score"


def _ensure_rag_meta_defaults(message: Message | None) -> None:
    if not message:
        return
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    rag_scores = _merge_rag_scores(decision_meta.get("rag_scores"))
    updates = {"rag_scores": rag_scores}
    if "rag_confident" not in decision_meta:
        updates["rag_confident"] = False
    if "rag_reason" not in decision_meta:
        updates["rag_reason"] = "overridden_by_gate"
    if "router_eligible" not in decision_meta:
        updates["router_eligible"] = False
    if "router_skipped_reason" not in decision_meta:
        updates["router_skipped_reason"] = "not_run"
    _update_message_decision_metadata(message, updates)


def _resolve_backlog_language(message: Message | None) -> str:
    if not message or not isinstance(message.message_metadata, dict):
        return "unknown"
    metadata = message.message_metadata
    for key in ("language", "lang", "locale"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    media_meta = metadata.get("media")
    if isinstance(media_meta, dict):
        transcript_language = media_meta.get("transcript_language")
        if isinstance(transcript_language, str) and transcript_language.strip():
            return transcript_language.strip().lower()
    return "unknown"


def _record_knowledge_backlog(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: UUID,
    message: Message | None,
    user_text: str,
    miss_type: str,
) -> None:
    text_value = (user_text or "").strip()
    if not text_value:
        return
    language = _resolve_backlog_language(message)
    miss_value = (miss_type or "unknown").strip().lower()
    try:
        db.execute(
            text(
                """
                INSERT INTO knowledge_backlog (
                  id,
                  client_id,
                  conversation_id,
                  message_id,
                  user_text,
                  language,
                  miss_type,
                  repeat_count,
                  first_seen_at,
                  last_seen_at
                )
                VALUES (
                  gen_random_uuid(),
                  :client_id,
                  :conversation_id,
                  :message_id,
                  :user_text,
                  :language,
                  :miss_type,
                  1,
                  NOW(),
                  NOW()
                )
                ON CONFLICT (client_id, language, miss_type, user_text)
                DO UPDATE SET
                  repeat_count = knowledge_backlog.repeat_count + 1,
                  last_seen_at = EXCLUDED.last_seen_at,
                  conversation_id = EXCLUDED.conversation_id,
                  message_id = EXCLUDED.message_id
                """
            ),
            {
                "client_id": client_id,
                "conversation_id": conversation_id,
                "message_id": message.id if message else None,
                "user_text": text_value,
                "language": language,
                "miss_type": miss_value,
            },
        )
    except Exception:
        logger.warning(
            "Knowledge backlog upsert failed",
            extra={
                "context": {
                    "client_id": str(client_id),
                    "conversation_id": str(conversation_id),
                    "message_id": str(message.id) if message else None,
                    "miss_type": miss_type,
                }
            },
            exc_info=True,
        )


# Default values (can be overridden in client_settings)
DEFAULT_MUTE_DURATION_FIRST_MINUTES = 30
DEFAULT_MUTE_DURATION_SECOND_HOURS = 24
SESSION_TIMEOUT_HOURS = 24
LOW_CONFIDENCE_RETRY_WINDOW_MINUTES = 10
LOW_CONFIDENCE_MAX_RETRIES = 2
HANDOVER_CONFIRM_WINDOW_MINUTES = 15
REENGAGE_CONFIRM_WINDOW_MINUTES = 15
ASR_CONFIRM_WINDOW_MINUTES = 10
ASR_INFLIGHT_TTL_SECONDS = 90
SERVICE_HINT_WINDOW_MINUTES = 120
ASR_LOW_CONFIDENCE_MIN_CHARS = 6
ASR_LOW_CONFIDENCE_MIN_WORDS = 3
ASR_LOW_CONFIDENCE_MIN_DURATION_SECONDS = 6.0
ASR_LOW_CONFIDENCE_NON_LETTER_RATIO = 0.4
MULTI_INTENT_MIN_CHARS = 350
STYLE_REFERENCE_PENDING_TTL_MINUTES = 10
QUIET_HOURS_NOTICE_TTL_MINUTES = 10
EVENING_GREETING_TTL_HOURS = 12
MSG_ESCALATED = (
    "Передал менеджеру. Пока заявка активна, я не отвечаю — сообщения уходят администратору. "
    "Если есть детали (услуга/время/имя), напишите — я передам."
)
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"
MSG_LOW_CONFIDENCE = "Хороший вопрос! Уточню у коллег и вернусь с ответом."
MSG_HANDOVER_CONFIRM = "Не уверен, что понял. Подключить менеджера? Ответьте 'да' или 'нет'."
MSG_REENGAGE_CONFIRM = "Вы просили не писать. Хотите снова общаться? Ответьте 'да' или 'нет'."
MSG_REENGAGE_DECLINED = "Хорошо, не буду писать. Если передумаете — напишите снова."
MSG_MEMORY_CONSENT = (
    "Могу запомнить ваши предпочтения (имя/услуга/время), чтобы не задавать одно и то же. "
    "Ответьте 'да' или 'нет'.\n\n"
    "Қалауыңызды есте сақтай аламын ба (атыңыз/қызмет/уақыт)? "
    "'иә' немесе 'жоқ' деп жазыңыз."
)
MSG_MEMORY_CONSENT_ACCEPTED = "Спасибо! Запомнил ваши предпочтения."
MSG_MEMORY_CONSENT_DECLINED = "Хорошо, не буду запоминать."
MSG_HANDOVER_DECLINED = (
    "Ок. Напишите, что именно интересует по салону: цена/запись/адрес/мастер/жалоба."
)
MSG_LOW_CONFIDENCE_RETRY = "Уточните, пожалуйста: интересуют услуги/цены или запись/адрес?"
MSG_EXPECTED_SERVICE_OFF_TOPIC = "Я могу помочь по услугам салона. Какая услуга интересует?"
MSG_PENDING_LOW_CONFIDENCE = (
    "Я уже передал менеджеру — он скоро подключится. "
    "Пока ждём, уточните: услуги/цены или запись/адрес."
)
MSG_PENDING_ESCALATION = (
    "Я уже передал менеджеру. Пока заявка активна, я не отвечаю — сообщения уходят администратору."
)
MSG_PENDING_STATUS = (
    "Да, передал. Сейчас менеджер ещё не взял заявку. "
    "Пока он не подключился, я не отвечаю — сообщения уходят администратору."
)
MSG_PENDING_RESCHEDULE = (
    "Перенос записи подтверждает администратор. Передам ваш запрос. "
    "Пока заявка активна, я не отвечаю."
)
MSG_PENDING_COMPLAINT = (
    "Жаль, что так вышло. Передам администратору, разберутся. "
    "Пока заявка активна, я не отвечаю."
)
MSG_PENDING_WAIT = "Менеджер подключится. Пока заявка активна, я не отвечаю."
MSG_PENDING_SLA_PING = (
    "Напоминаю: менеджер ещё не подключился. "
    "Если всё актуально — напишите детали, я передам администратору."
)
MSG_PENDING_AUTO_CLOSE = "Закрываю ожидание. Если всё ещё актуально — напишите, я помогу."
MSG_PENDING_ACK = "Хорошо. Напишите, что именно нужно: цена/запись/адрес/мастер."
MSG_AI_ERROR = "Извините, произошла ошибка. Попробуйте позже."
MSG_MEDIA_UNSUPPORTED = (
    "Сейчас принимаем только фото, аудио и документы. Видео не поддерживаются. Опишите вопрос текстом."
)
MSG_MEDIA_TOO_LARGE = "Файл слишком большой. Пришлите, пожалуйста, фото/аудио поменьше или опишите текстом."
MSG_MEDIA_RATE_LIMIT = "Слишком много файлов за короткое время. Давайте продолжим позже или опишите текстом."
MSG_MEDIA_RECEIVED = (
    "Файл получил. Напишите, пожалуйста, что именно нужно: цена/запись/адрес/мастер/жалоба. "
    "Если это референс, напишите: «как на фото»."
)
MSG_MEDIA_DOC_RECEIVED = "Документ получил. Напишите, пожалуйста, что именно нужно."
MSG_MEDIA_TRANSCRIPT_FAILED = "Не смог разобрать аудио. Напишите, пожалуйста, текстом."
MSG_ASR_CONFIRM = "Я услышал: «{text}». Правильно? (да/нет)"
MSG_ASR_CONFIRM_DECLINED = "Пожалуйста, напишите текстом или перешлите аудио."
MSG_ASR_INFLIGHT_WAIT = "Расшифровываю предыдущее аудио. Можно написать текстом, чтобы быстрее."
MSG_MEDIA_PENDING_NEED_TEXT = (
    "Я уже передал менеджеру. Чтобы ускорить, напишите детали: цена/запись/адрес/мастер/жалоба — я передам."
)
MSG_MEDIA_STYLE_REFERENCE = (
    "Спасибо за фото/референс. Передал администратору для подтверждения возможности и деталей. "
    "Пока заявка активна, я не отвечаю. Чтобы ускорить, напишите услугу, дату/время и имя."
)
MSG_STYLE_REFERENCE_NEED_MEDIA = (
    "Можем ориентироваться на фото/референс. Пришлите фото и кратко опишите запрос — "
    "я передам администратору для подтверждения."
)

PENDING_SLA_PING_MINUTES = 15
PENDING_AUTO_CLOSE_HOURS = 4
PENDING_SLA_CONTEXT_KEY = "pending_sla"
PENDING_SLA_PING_SENT_KEY = "ping_sent_at"
PENDING_SLA_AUTO_CLOSE_KEY = "auto_closed_at"
PENDING_RESUME_KEY = "pending_resume"
MEMORY_PROFILE_KEY = "memory_profile"
MEMORY_PENDING_KEY = "memory_pending"
MEMORY_PROFILE_TTL_DAYS = 180
MEMORY_PENDING_TTL_HOURS = 168
MEMORY_PROFILE_ENABLED = os.environ.get("MEMORY_PROFILE_ENABLED", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

PENDING_ACK_PHRASES = {
    "ага",
    "актуально",
    "да",
    "давай",
    "жду",
    "можно",
    "ок",
    "ответьте",
}
PENDING_CLOSE_PHRASES = {
    "закрыто",
    "решено",
    "не надо",
    "уже сделал",
    "по телефону",
    "спасибо все",
    "спасибо всё",
}

MSG_BOOKING_ASK_SERVICE = "На какую услугу хотите записаться?"
MSG_BOOKING_ASK_DATETIME = "На какую дату и время вам удобно?"
MSG_BOOKING_ASK_NAME = "Как вас зовут?"
MSG_BOOKING_ASK_ALL = "Чтобы записать, пожалуйста, напишите: услуга, точная дата, точное время, имя, контактный номер."
MSG_BOOKING_SLOT_LOCK_STUB = "Я помогаю только по вопросам салона и записи."
MSG_BOOKING_CANCELLED = "Хорошо, если передумаете — пишите."
MSG_BOOKING_REENGAGE = "Хотите продолжить запись? Если да — напишите услугу."
MSG_BOOKING_CTA = "Хотите записаться?"

SERVICE_HINT_KEY = "last_service_hint"
SERVICE_HINT_AT_KEY = "last_service_hint_at"
RE_ENTRY_REQUIRED_KEY = "re_entry_required"
REENGAGE_CONFIRM_KEY = "reengage_confirmation"
ASR_CONFIRM_KEY = "asr_confirm_pending"
ASR_INFLIGHT_KEY = "asr_inflight"
STYLE_REFERENCE_PENDING_KEY = "style_reference_pending"
QUIET_HOURS_NOTICE_KEY = "quiet_hours_notice"
EVENING_GREETING_KEY = "evening_greeting"
DECISION_TRACE_KEY = "decision_trace"
CONTEXT_MANAGER_KEY = "context_manager"
INTENT_QUEUE_KEY = "intent_queue"
EXPECTED_REPLY_TYPE_KEY = "expected_reply_type"
EXPECTED_REPLY_REASON_KEY = "expected_reply_reason"

EXPECTED_REPLY_SERVICE = "service_choice"
EXPECTED_REPLY_TIME = "time"
EXPECTED_REPLY_NAME = "name"
EXPECTED_REPLY_INTENT_CHOICE = "intent_choice"

CLARIFY_MAX_ATTEMPTS = 2
REFUSAL_TTL_MESSAGES = 10
SUMMARY_MESSAGE_THRESHOLD = 12
FACT_GUARD_ENABLED = False
FACT_GUARD_INTENT = "fact_guard"
FACT_GUARD_SKIP_INTENTS = {"service_clarify", "duration_or_price_clarify"}
FACT_GUARD_MAX_ATTEMPTS = 1
MSG_FACT_GUARD_CLARIFY = "Подскажите, пожалуйста, что именно вас интересует?"

ROUTING_MATRIX = {
    ConversationState.BOT_ACTIVE.value: {
        "allow_booking_flow": True,
        "allow_truth_gate_reply": True,
        "allow_handover_create": True,
        "allow_bot_reply": True,
    },
    ConversationState.PENDING.value: {
        "allow_booking_flow": False,
        "allow_truth_gate_reply": False,
        "allow_handover_create": False,
        "allow_bot_reply": False,
    },
    ConversationState.MANAGER_ACTIVE.value: {
        "allow_booking_flow": False,
        "allow_truth_gate_reply": False,
        "allow_handover_create": False,
        "allow_bot_reply": False,
    },
}


SHIELD_CONTEXT_KEY = "shield"
SHIELD_RECENT_KEY = "recent_messages"
SHIELD_LAST_TEXT_KEY = "last_text"
SHIELD_SPAM_WINDOW_SECONDS = 5.0
SHIELD_SPAM_MAX_MESSAGES = 3
SHIELD_MAX_MESSAGE_LENGTH = 1000
SHIELD_SHORT_MESSAGE_LEN = 12
SHIELD_TOXIC_PATTERNS = [
    re.compile(r"\b(хуй|пизд|пидор|еба|сука|нахуй|убью|иди\s+на\s+хуй|бля[тд])", re.IGNORECASE),
]
SHIELD_MEANINGFUL_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9]{2,}")
HYGIENE_KEYWORDS = [
    "стерилиз",
    "дезраств",
    "дезинф",
    "ультразвук",
    "уз-ванн",
    "сухожар",
    "крафт",
    "однораз",
    "инструмент",
    "обрабатыва",
]


BOOKING_REQUEST_KEYWORDS = [
    "запис",
    "запись",
    "запишите",
    "записаться",
    "бронь",
    "окошк",
    "свободн",
]

SERVICE_KEYWORDS = [
    "маникюр",
    "маник",
    "педикюр",
    "стриж",
    "окраш",
    "мелирован",
    "кератин",
    "ботокс",
    "бров",
    "ресниц",
    "депиляц",
    "шугар",
    "воск",
    "чистк",
    "пилинг",
    "макияж",
    "укладк",
    "прическ",
    "наращив",
    "лак",
]

DATE_KEYWORDS = [
    "сегодня",
    "завтра",
    "послезавтра",
    "понедель",
    "вторник",
    "сред",
    "четверг",
    "пятниц",
    "суббот",
    "воскрес",
    "утром",
    "днем",
    "днём",
    "вечером",
]

TIME_PATTERN = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
TIME_HOUR_PATTERN = re.compile(r"\b(?:в|к)\s*(?:[01]?\d|2[0-3])\b", re.IGNORECASE)
DATE_PATTERN = re.compile(
    r"\b(?:сегодня|завтра|послезавтра|понедель\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскрес\w*|утром|днем|днём|вечером)\b",
    re.IGNORECASE,
)
DATE_NUMERIC_PATTERN = re.compile(r"\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b")
DATE_MONTH_PATTERN = re.compile(
    r"\b\d{1,2}\s*(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*\b",
    re.IGNORECASE,
)
NAME_PATTERN = re.compile(r"\bменя зовут\s+([a-zа-яё-]{2,})", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-\(\)]{8,}\d")
NAME_NOISE_TOKENS = {"меня", "зовут", "это", "я", "имя"}
LATIN_PATTERN = re.compile(r"[a-z]")
CYRILLIC_PATTERN = re.compile(r"[а-яё]")

LATIN_TO_CYRILLIC_DIGRAPHS = (
    ("shch", "щ"),
    ("yo", "ё"),
    ("zh", "ж"),
    ("kh", "х"),
    ("ts", "ц"),
    ("ch", "ч"),
    ("sh", "ш"),
    ("yu", "ю"),
    ("ya", "я"),
)
LATIN_TO_CYRILLIC_MAP = {
    "a": "а",
    "b": "б",
    "v": "в",
    "g": "г",
    "d": "д",
    "e": "е",
    "z": "з",
    "i": "и",
    "j": "й",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "f": "ф",
    "h": "х",
    "y": "ы",
    "c": "с",
    "q": "к",
    "w": "в",
    "x": "кс",
}


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.strip().casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _has_latin(text: str) -> bool:
    return bool(LATIN_PATTERN.search(text))


def _has_cyrillic(text: str) -> bool:
    return bool(CYRILLIC_PATTERN.search(text))


def _transliterate_latin_to_cyrillic(text: str) -> str | None:
    if not text:
        return None
    lowered = text.casefold()
    if not _has_latin(lowered) or _has_cyrillic(lowered):
        return None
    result: list[str] = []
    idx = 0
    while idx < len(lowered):
        matched = False
        for token, replacement in LATIN_TO_CYRILLIC_DIGRAPHS:
            if lowered.startswith(token, idx):
                result.append(replacement)
                idx += len(token)
                matched = True
                break
        if matched:
            continue
        char = lowered[idx]
        result.append(LATIN_TO_CYRILLIC_MAP.get(char, char))
        idx += 1
    transliterated = "".join(result)
    if transliterated == lowered:
        return None
    return transliterated


def _match_expected_reply_candidates(
    *,
    expected_reply_type: str | None,
    message_text: str,
    client_slug: str | None,
) -> tuple[bool, str | None, list[str]]:
    matched, value, inner_flags = _match_expected_reply(
        expected_reply_type=expected_reply_type,
        message_text=message_text,
        client_slug=client_slug,
    )
    if matched:
        flags = list(inner_flags) if isinstance(inner_flags, list) else []
        return True, value, flags
    transliterated = _transliterate_latin_to_cyrillic(message_text)
    if transliterated:
        matched, value, inner_flags = _match_expected_reply(
            expected_reply_type=expected_reply_type,
            message_text=transliterated,
            client_slug=client_slug,
        )
        if matched:
            flags = list(inner_flags) if isinstance(inner_flags, list) else []
            if "latin_to_cyrillic" not in flags:
                flags.insert(0, "latin_to_cyrillic")
            return True, value, flags
    return False, None, []


def _expected_reply_slot_key(expected_reply_type: str | None) -> str | None:
    if expected_reply_type == EXPECTED_REPLY_SERVICE:
        return "service"
    if expected_reply_type == EXPECTED_REPLY_TIME:
        return "datetime"
    if expected_reply_type == EXPECTED_REPLY_NAME:
        return "name"
    return None


def _validate_expected_reply_value(
    *,
    expected_reply_type: str | None,
    value: str | None,
    client_slug: str | None,
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = value.strip()
    if expected_reply_type == EXPECTED_REPLY_SERVICE:
        return _validate_service_slot(cleaned, allow_freeform=True, client_slug=client_slug)
    if expected_reply_type == EXPECTED_REPLY_TIME:
        return _validate_datetime_slot(cleaned, allow_freeform=True, client_slug=client_slug)
    if expected_reply_type == EXPECTED_REPLY_NAME:
        return _validate_name_slot(cleaned, allow_freeform=True, client_slug=client_slug)
    return None


def _coerce_batch_messages(message_text: str, batch_messages: list[str] | None) -> list[str]:
    raw_messages = batch_messages if batch_messages else ([message_text] if message_text else [])
    cleaned: list[str] = []
    for msg in raw_messages:
        if not msg:
            continue
        text = msg.strip()
        if text:
            cleaned.append(text)
    if not cleaned and message_text:
        fallback = message_text.strip()
        if fallback:
            cleaned.append(fallback)
    return cleaned


def _contains_any(normalized: str, keywords: list[str]) -> bool:
    return any(keyword in normalized for keyword in keywords)


def _matches_guest_policy_lexicon(
    message_text: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    lexicon = domain_pack.get("guest_policy_lexicon") if isinstance(domain_pack, dict) else None
    if not isinstance(lexicon, dict):
        return False
    for lang_key in ("ru", "kk"):
        phrases = lexicon.get(lang_key)
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if not isinstance(phrase, str):
                continue
            candidate = normalize_for_matching(phrase)
            if candidate and candidate in normalized:
                return True
    return False


def _is_booking_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return _contains_any(normalized, BOOKING_REQUEST_KEYWORDS)


def _is_booking_cancel(text: str, *, policy_pack: dict | None) -> bool:
    return _detect_booking_cancel(text, policy_pack=policy_pack)


def _extract_service_hint(text: str, client_slug: str | None) -> str | None:
    if not text:
        return None
    slug = client_slug or "demo_salon"
    normalized_text = _normalize_text(text)
    booking_like = _is_booking_request(text)
    if not booking_like:
        booking_like = bool(
            TIME_PATTERN.search(text)
            or TIME_HOUR_PATTERN.search(text)
            or DATE_PATTERN.search(text)
            or DATE_NUMERIC_PATTERN.search(text)
            or DATE_MONTH_PATTERN.search(text)
        )
    match = semantic_service_match(text, slug)
    if not match or match.action != "match":
        fallback = get_demo_salon_service_hint(text, client_slug=slug)
        if fallback:
            return fallback
        return None
    canonical_name = match.canonical_name
    if isinstance(canonical_name, str) and canonical_name.strip():
        if booking_like and normalized_text:
            canonical_tokens = _normalize_text(canonical_name).split()
            message_tokens = normalized_text.split()
            if canonical_tokens and message_tokens:
                if not any(token in message_tokens for token in canonical_tokens):
                    return None
        return canonical_name.strip()
    return None


def _extract_datetime(
    text: str,
    *,
    client_slug: str | None = None,
    relative_base: datetime | None = None,
) -> str | None:
    if not text:
        return None
    resolved = _resolve_datetime_offline(
        text,
        client_slug=client_slug,
        relative_base=relative_base,
    )
    if isinstance(resolved, dict):
        value = resolved.get("value")
        if isinstance(value, str) and value.strip():
            return value
    time_match = TIME_PATTERN.search(text)
    if time_match:
        return time_match.group(0)
    hour_match = TIME_HOUR_PATTERN.search(text)
    if hour_match:
        return hour_match.group(0)
    numeric_date_match = DATE_NUMERIC_PATTERN.search(text)
    if numeric_date_match:
        return numeric_date_match.group(0)
    month_date_match = DATE_MONTH_PATTERN.search(text)
    if month_date_match:
        return month_date_match.group(0)
    date_match = DATE_PATTERN.search(text)
    if date_match:
        return date_match.group(0)
    return None


BOOKING_INFO_QUESTION_TYPES = {"pricing", "hours", "duration"}
INFO_INTENTS = {"pricing", "hours", "duration", "location", "promotions"}
CONSULT_INTERRUPT_INTENTS = {"booking", "pricing", "duration", "location", "hours"}
INFO_INTENT_PRIORITY_SERVICE = ("pricing", "duration", "location", "hours")
INFO_INTENT_PRIORITY_GENERIC = ("location", "hours", "pricing", "duration")
BOOKING_TIME_SERVICE_INTENTS = {
    "service_match",
    "service_not_found",
    "price_query",
    "price_manicure",
    "service_duration",
    "service_clarify",
    "duration_or_price_clarify",
}
BOOKING_CTA_SERVICE_INTENTS = BOOKING_TIME_SERVICE_INTENTS - {
    "service_not_found",
    "service_clarify",
    "duration_or_price_clarify",
}
CLASS_CARRYOVER_KEY = "class_carryover"
CLASS_CARRYOVER_TTL_MESSAGES = 4
CLASS_CARRYOVER_CLASSES = {"info_bundle"}
SERVICE_CARRYOVER_KEY = "service_carryover"
SERVICE_CARRYOVER_TTL_MESSAGES = 4
CONSULT_CONTEXT_KEY = "consult_context"
CONSULT_CONTEXT_TTL_MESSAGES = 6
SERVICE_CARRYOVER_INTENTS = {"pricing", "duration"}
SERVICE_CARRYOVER_SKIP_INTENTS = {
    "service_clarify",
    "duration_or_price_clarify",
    "service_not_found",
}
SESSION_MEMORY_KEY = "session_memory"
SESSION_MEMORY_TTL_HOURS = 24
SESSION_MEMORY_SHORT_TOKENS = 4
SESSION_MEMORY_RESET_PHRASES = (
    "новый вопрос",
    "другая тема",
    "начнем сначала",
    "начнём сначала",
    "начнем заново",
    "начнём заново",
    "давай сначала",
)


def _normalize_class_name(class_name: str) -> str:
    normalized = class_name.strip()
    if normalized.casefold() in {"info", "info_bundle"}:
        return "info_bundle"
    return normalized


def _evaluate_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None,
    message_text: str | None,
    relative_base: datetime | None = None,
) -> tuple[bool, dict | None]:
    if not messages:
        return False, None
    if any(_is_booking_request(message) for message in messages):
        return True, None
    has_service = any(_extract_service_hint(message, client_slug) for message in messages)
    has_datetime = any(
        _extract_datetime(
            message,
            client_slug=client_slug,
            relative_base=relative_base,
        )
        for message in messages
    )
    booking_signal = has_service and has_datetime
    if booking_signal and message_text:
        normalized = normalize_for_matching(message_text)
        if normalized and _contains_any(normalized, ["совмещ", "в один день"]) and _contains_any(
            normalized,
            ["чистк", "пилинг"],
        ):
            return False, {"booking_blocked_reason": "procedure_combo"}
        segments = [segment.strip() for segment in re.split(r"[?!\.,;]+", message_text) if segment.strip()]
        if not segments:
            segments = [message_text.strip()]
        for segment in segments:
            question_type = semantic_question_type(
                segment,
                include_kinds=BOOKING_INFO_QUESTION_TYPES,
                client_slug=client_slug,
            )
            if question_type and question_type.kind in BOOKING_INFO_QUESTION_TYPES:
                return (
                    False,
                    {
                        "booking_blocked_reason": "info_question",
                        "question_type": question_type.kind,
                        "question_type_score": question_type.score,
                    },
                )
    return booking_signal, None


def _has_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None = None,
    message_text: str | None = None,
) -> bool:
    booking_signal, _ = _evaluate_booking_signal(
        messages,
        client_slug=client_slug,
        message_text=message_text,
    )
    return booking_signal


INFO_ANCHOR_GROUPS: dict[str, list[tuple[str, ...]]] = {
    "pricing": [
        ("цен",),
        ("стоим",),
        ("скольк", "стоит"),
        ("поч",),
    ],
    "duration": [
        ("длит",),
        ("длител",),
        ("скольк", "врем"),
        ("врем", "заним"),
        ("минут",),
        ("час",),
    ],
    "hours": [
        ("график",),
        ("режим", "работ"),
        ("каког", "врем"),
        ("работ", "скольк"),
        ("работ", "когда"),
        ("работ", "до"),
        ("откры",),
        ("закры",),
    ],
    "location": [
        ("адрес",),
        ("где", "наход"),
        ("где", "вы"),
        ("локац",),
        ("перекр",),
        ("угол",),
        ("ориентир",),
        ("как", "доех"),
        ("как", "добрат"),
        ("как", "найт"),
        ("куда", "ехать"),
        ("улиц",),
    ],
}

QUESTION_WORD_PREFIXES = ("скольк", "где", "когда", "како")


def _looks_like_time_only_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    if _is_booking_request(message_text):
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    if any(keyword in normalized for keyword in SERVICE_KEYWORDS):
        return False
    if TIME_PATTERN.search(message_text):
        return True
    return bool(DATE_PATTERN.search(normalized))


def _looks_like_hours_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    if _contains_any(normalized, ["по времени", "по часам", "по час"]):
        return True
    return _contains_any(
        normalized,
        [
            "график",
            "до скольк",
            "во скольк",
            "время работы",
            "часы",
            "часов",
            "работае",
            "открыт",
            "когда откры",
            "открывает",
        ],
    )


def _looks_like_carryover_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    if not tokens:
        return False
    followup_phrases = [
        "по времени",
        "по цене",
        "по стоимости",
        "по длитель",
        "по адресу",
        "по месту",
        "по час",
        "по график",
    ]
    if _contains_any(normalized, followup_phrases):
        return True
    if tokens[0].startswith("скольк") and "мест" in normalized:
        return True
    if len(tokens) <= SESSION_MEMORY_SHORT_TOKENS:
        pricing_groups = INFO_ANCHOR_GROUPS.get("pricing", [])
        if pricing_groups and _count_anchor_hits(tokens, pricing_groups) > 0:
            return True
    if tokens[0] in {"и", "а", "еще", "ещё"} and _contains_any(
        normalized,
        [
            "сколько",
            "когда",
            "где",
            "до скольк",
            "во скольк",
            "цена",
            "стоим",
            "длител",
            "время",
            "час",
        ],
    ):
        return True
    return False


def _build_controller_meta_output(*, error: str, retry: bool = False, elapsed_ms: float = 0.0) -> dict:
    return {
        "class": None,
        "goal": None,
        "intents": [],
        "slots": {},
        "followups": [],
        "safety_flags": [],
        "confidence": 0.0,
        "reason": "",
        "carryover": {},
        "controller_llm_ms": round(elapsed_ms, 2),
        "controller_error": error,
        "controller_retry": bool(retry),
    }


def _ensure_controller_output_meta(controller_output: dict, *, error: str | None) -> dict:
    if not isinstance(controller_output.get("controller_llm_ms"), (int, float)):
        controller_output["controller_llm_ms"] = 0.0
    if not isinstance(controller_output.get("controller_error"), str) or not controller_output.get("controller_error"):
        controller_output["controller_error"] = error or "none"
    if not isinstance(controller_output.get("controller_retry"), bool):
        controller_output["controller_retry"] = False
    if "controller_goal" in controller_output and not controller_output.get("goal"):
        controller_output["goal"] = controller_output.get("controller_goal")
    return controller_output


CONTROLLER_FALLBACK_IGNORE_VALUES = {"none", "skipped", "ok", "low_confidence"}
CONTROLLER_FALLBACK_REASON_MAP = {
    "timeout": "timeout",
    "invalid_json": "invalid_json",
    "budget_exceeded": "budget_exceeded",
    "no_api_key": "no_api_key",
    "prompt_missing": "prompt_missing",
    "empty_message": "empty_message",
    "empty_response": "empty_response",
    "invalid_class": "invalid_class",
    "unsupported_temperature": "unsupported_temperature",
}
CONTROLLER_FALLBACK_ERROR_VALUES = {"controller_failed", "error"}
CONTROLLER_FALLBACK_REASONS = set(CONTROLLER_FALLBACK_REASON_MAP.values()) | {"error"}


def _normalize_controller_fallback_reason(*, error: str | None) -> str | None:
    if not error:
        return None
    normalized = error.strip().casefold()
    if not normalized or normalized in CONTROLLER_FALLBACK_IGNORE_VALUES:
        return None
    mapped = CONTROLLER_FALLBACK_REASON_MAP.get(normalized)
    if mapped:
        return mapped
    if normalized in CONTROLLER_FALLBACK_ERROR_VALUES:
        return "error"
    return "error"


def _resolve_controller_signal_class(*, intent_decomp_set: set[str], booking_signal: bool) -> str | None:
    if booking_signal:
        return "booking"
    if "consult" in intent_decomp_set:
        return "consult"
    if "booking" in intent_decomp_set:
        return "booking"
    if intent_decomp_set & INFO_INTENTS:
        return "info_bundle"
    if "greeting" in intent_decomp_set:
        return "greeting"
    if "out_of_domain" in intent_decomp_set:
        return "out_of_domain"
    return None


def _build_class_controller_result(
    *,
    info_intents: set[str],
    info_meta: dict[str, Any] | None,
    booking_signal: bool,
    class_carryover: dict | None,
    domain_intent: DomainIntent,
    domain_meta: dict | None,
) -> dict[str, Any]:
    anchors_out_hits = int(domain_meta.get("out_hits") or 0) if isinstance(domain_meta, dict) else 0
    anchors_in_hits = int(domain_meta.get("strict_in_hits") or 0) if isinstance(domain_meta, dict) else 0
    in_signals: list[str] = []
    out_signals: list[str] = []
    classes: list[str] = []

    if info_intents:
        in_signals.append("info_intents")
        classes.append("info_bundle")
    if isinstance(info_meta, dict):
        raw_anchor_intents = info_meta.get("anchor_intents")
        if isinstance(raw_anchor_intents, list):
            for item in raw_anchor_intents:
                if isinstance(item, str) and item.strip():
                    in_signals.append(f"info_anchor_{item.strip().casefold()}")
        info_signals = info_meta.get("info_signals")
        if isinstance(info_signals, dict) and info_signals.get("guest"):
            in_signals.append("info_guest")
            classes.append("info_bundle")
    if booking_signal:
        in_signals.append("booking_signal")
        classes.append("booking")
    if anchors_in_hits > 0:
        in_signals.append("anchor_in")
    if anchors_out_hits > 0:
        out_signals.append("anchor_out")

    carryover_class = None
    carryover_info_sections: list[str] = []
    carryover_intents: list[str] = []
    if isinstance(class_carryover, dict):
        carryover_class = class_carryover.get("class")
        if isinstance(carryover_class, str) and carryover_class.strip():
            carryover_class = _normalize_class_name(carryover_class)
            in_signals.append("carryover")
            classes.append(carryover_class)
        raw_sections = class_carryover.get("info_sections")
        if isinstance(raw_sections, list):
            carryover_info_sections = [item for item in raw_sections if isinstance(item, str)]
        raw_intents = class_carryover.get("intents")
        if isinstance(raw_intents, list):
            carryover_intents = [item for item in raw_intents if isinstance(item, str)]

    if domain_intent == DomainIntent.OUT_OF_DOMAIN and not out_signals:
        out_signals.append("domain_out")

    out_of_domain_signal = bool(out_signals and not in_signals)
    if out_of_domain_signal:
        classes.append("out_of_domain")
    classes = list(dict.fromkeys(classes))
    in_signals = list(dict.fromkeys(in_signals))
    out_signals = list(dict.fromkeys(out_signals))
    carryover_intents = list(dict.fromkeys(carryover_intents))
    carryover_info_sections = list(dict.fromkeys(carryover_info_sections))
    return {
        "classes": classes,
        "intents": sorted(info_intents),
        "in_signals": in_signals,
        "out_signals": out_signals,
        "anchors_in_hits": anchors_in_hits,
        "anchors_out_hits": anchors_out_hits,
        "out_of_domain_signal": out_of_domain_signal,
        "carryover_class": carryover_class,
        "carryover_info_sections": carryover_info_sections,
        "carryover_intents": carryover_intents,
    }


def _resolve_class_router_result(
    *,
    info_intents: set[str],
    info_meta: dict[str, Any] | None,
    booking_signal: bool,
    class_carryover: dict | None,
    domain_intent: DomainIntent,
    domain_meta: dict | None,
    router_state: dict | None,
) -> dict[str, Any]:
    result = _build_class_controller_result(
        info_intents=info_intents,
        info_meta=info_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
    )
    out_of_domain_signal = bool(result.get("out_of_domain_signal"))

    controller_output = router_state.get("output") if isinstance(router_state, dict) else None
    controller_used = router_state.get("used") if isinstance(router_state, dict) else False
    controller_error = router_state.get("error") if isinstance(router_state, dict) else None
    controller_fallback = router_state.get("fallback_reason") if isinstance(router_state, dict) else None
    controller_attempted = bool(router_state.get("attempted")) if isinstance(router_state, dict) else False
    controller_fallback_flag = bool(router_state.get("fallback")) if isinstance(router_state, dict) else False
    controller_confidence = router_state.get("confidence") if isinstance(router_state, dict) else None
    controller_sla = router_state.get("sla") if isinstance(router_state, dict) else None
    controller_signal_class = router_state.get("signal_class") if isinstance(router_state, dict) else None
    controller_signal_match = router_state.get("signal_match") if isinstance(router_state, dict) else None
    controller_used_reason = router_state.get("used_reason") if isinstance(router_state, dict) else None

    controller_class = None
    controller_reason = None
    controller_intents: list[str] = []
    controller_goal = None
    if isinstance(controller_output, dict):
        raw_class = controller_output.get("class")
        if isinstance(raw_class, str):
            controller_class = _normalize_class_name(raw_class)
        raw_reason = controller_output.get("reason")
        if isinstance(raw_reason, str):
            controller_reason = raw_reason
        raw_intents = controller_output.get("intents")
        if isinstance(raw_intents, list):
            controller_intents = [item for item in raw_intents if isinstance(item, str)]
        raw_goal = controller_output.get("goal")
        if isinstance(raw_goal, str):
            controller_goal = raw_goal.strip()

    controller_confidence_value = controller_confidence
    controller_low_confidence = bool(
        controller_used
        and isinstance(controller_confidence_value, (int, float))
        and controller_confidence_value < CONTROLLER_CONFIDENCE_THRESHOLD
    )

    controller_fallback_reason = None
    controller_error_normalized = controller_error if isinstance(controller_error, str) else None
    controller_error_normalized = controller_error_normalized.strip() if controller_error_normalized else None
    if controller_error_normalized:
        controller_fallback_reason = _normalize_controller_fallback_reason(error=controller_error_normalized)

    if controller_used and controller_class and not controller_low_confidence:
        result["classes"] = [controller_class]
        info_controller_intents = [intent for intent in controller_intents if intent in INFO_INTENTS]
        if controller_class == "info_bundle":
            if info_controller_intents:
                result["intents"] = sorted(info_controller_intents)
        else:
            result["intents"] = sorted(info_controller_intents)
        controller_fallback_reason = None
    elif controller_used and controller_class and controller_low_confidence:
        # Low confidence: keep deterministic class_router result, but track low confidence explicitly.
        controller_used_reason = "low_confidence"
        controller_used = True
        controller_fallback_reason = None
        controller_fallback_flag = False
    elif not controller_used and isinstance(controller_fallback, str):
        normalized_fallback = _normalize_controller_fallback_reason(error=controller_fallback)
        if normalized_fallback:
            controller_fallback_reason = controller_fallback_reason or normalized_fallback

    if (
        not controller_used
        and not controller_attempted
        and controller_error_normalized in {"skipped", "no_api_key"}
    ):
        fallback_goal = None
        fallback_class = None
        if out_of_domain_signal or "out_of_domain" in result.get("classes", []):
            fallback_goal = "out_of_domain"
            fallback_class = "out_of_domain"
        elif "booking" in result.get("classes", []):
            fallback_goal = "booking"
            fallback_class = "booking"
        elif "consult" in result.get("classes", []):
            fallback_goal = "consult"
            fallback_class = "consult"
        elif "info_bundle" in result.get("classes", []) or "guest_policy" in result.get("classes", []):
            fallback_goal = "info"
            fallback_class = "info_bundle"
        if fallback_goal:
            controller_used = True
            controller_used_reason = "deterministic"
            controller_goal = fallback_goal
            controller_class = fallback_class
            if not isinstance(controller_output, dict):
                controller_output = {}
            controller_output = {**controller_output, "class": controller_class, "goal": controller_goal}
            controller_fallback_reason = None
            controller_fallback_flag = False

    result["controller"] = {
        "used": bool(controller_used),
        "attempted": controller_attempted,
        "fallback": controller_fallback_flag,
        "confidence": controller_confidence,
        "reason": controller_reason,
        "fallback_reason": controller_fallback_reason if not controller_used else None,
        "error": controller_error,
        "output": controller_output,
        "signal_class": controller_signal_class,
        "signal_match": controller_signal_match,
        "used_reason": controller_used_reason,
        "sla": controller_sla,
        "goal": controller_goal,
        "low_confidence": controller_low_confidence,
    }
    result["controller_fallback_reason"] = controller_fallback_reason
    # Backward-compat for downstream callers still keyed on router
    result["router"] = result["controller"]
    result["router_fallback_reason"] = controller_fallback_reason
    return result


def _controller_meta_updates_from_class_router(class_router_result: dict | None) -> dict[str, Any]:
    if not isinstance(class_router_result, dict):
        return {}
    controller_meta = class_router_result.get("controller")
    if not isinstance(controller_meta, dict):
        return {}
    return {
        "controller_used": bool(controller_meta.get("used")),
        "controller_attempted": bool(controller_meta.get("attempted")),
        "controller_fallback": bool(controller_meta.get("fallback")),
        "controller_low_confidence": bool(controller_meta.get("low_confidence")),
        "controller_used_reason": controller_meta.get("used_reason"),
        "controller_confidence": controller_meta.get("confidence"),
        "controller_error": controller_meta.get("error"),
        "controller_goal": controller_meta.get("goal"),
        "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
    }


def _router_observability_updates_from_class_router(class_router_result: dict | None) -> dict[str, Any]:
    if not isinstance(class_router_result, dict):
        return {}
    controller_meta = class_router_result.get("controller")
    if not isinstance(controller_meta, dict):
        return {}
    attempted = bool(controller_meta.get("attempted"))
    reason = "none" if attempted else "not_run"
    return _router_observability_meta(eligible=attempted, reason=reason)


def _is_refusal_flag_active(refusal_flags: dict | None, field: str) -> bool:
    if not isinstance(refusal_flags, dict):
        return False
    payload = refusal_flags.get(field)
    if isinstance(payload, dict):
        return payload.get("value") is True
    if isinstance(payload, bool):
        return payload
    return False


def _detect_name_provided(message_text: str, *, client_slug: str | None) -> bool:
    if not message_text:
        return False
    if classify_confirmation(message_text) in {"yes", "no"}:
        return False
    return bool(_validate_name_slot(message_text, allow_freeform=True, client_slug=client_slug))


def _detect_phone_provided(message_text: str) -> bool:
    if not message_text:
        return False
    match = PHONE_PATTERN.search(message_text)
    if not match:
        return False
    digits = re.sub(r"\D", "", match.group(0))
    return len(digits) >= 10


def _update_refusal_flags(
    manager: dict,
    *,
    message_text: str,
    now: datetime,
    client_slug: str | None,
) -> tuple[dict, dict, list[dict]]:
    detected = detect_refusal_flags(message_text)
    name_initiative = _detect_name_provided(message_text, client_slug=client_slug)
    phone_initiative = _detect_phone_provided(message_text)
    existing = manager.get("refusal_flags")
    existing_flags = dict(existing) if isinstance(existing, dict) else {}
    updated_flags: dict = {}
    events: list[dict] = []

    for field in ("name", "phone"):
        data = existing_flags.get(field)
        payload = dict(data) if isinstance(data, dict) else {}
        explicit_refusal = bool(detected.get(field))
        if explicit_refusal:
            updated_flags[field] = {
                "value": True,
                "source": "explicit_refusal",
                "last_set_at": now.isoformat(),
                "ttl_remaining": REFUSAL_TTL_MESSAGES,
            }
            events.append({"type": "set", "field": field, "source": "explicit_refusal"})
            continue
        if field == "name" and name_initiative:
            if payload.get("value") is True:
                events.append({"type": "cleared", "field": field, "source": "explicit_initiative"})
            continue
        if field == "phone" and phone_initiative:
            if payload.get("value") is True:
                events.append({"type": "cleared", "field": field, "source": "explicit_initiative"})
            continue
        if payload.get("value") is True:
            ttl = payload.get("ttl_remaining")
            if isinstance(ttl, int):
                ttl = max(0, ttl - 1)
                if ttl <= 0:
                    events.append({"type": "cleared", "field": field, "source": "ttl_expired"})
                    continue
                payload["ttl_remaining"] = ttl
            updated_flags[field] = payload

    manager["refusal_flags"] = updated_flags
    return manager, updated_flags, events


def _combine_sidecar(primary: str, sidecar: str | None) -> str:
    if not sidecar:
        return primary
    return f"{sidecar}\n\n{primary}"


def _ensure_question_mark(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith("?"):
        return cleaned
    return f"{cleaned}?"


def _append_followup(primary: str, followup: str | None) -> str:
    if not followup:
        return primary
    return f"{primary}\n\n{followup}"


MULTI_INTENT_LABELS = {
    "booking": "записи",
    "pricing": "цене",
    "duration": "длительности",
    "location": "адресу",
    "hours": "времени",
    "other": "другому вопросу",
}


_POLICY_HANDLERS = {
    "demo_salon": {
        "policy_type": "demo_salon",
        "escalation_gate": _demo_salon_escalation_gate,
        "service_matcher": get_demo_salon_service_decision,
        "truth_gate": get_demo_salon_decision,
        "price_item": get_demo_salon_price_item,
        "price_sidecar": _demo_salon_price_sidecar,
    }
}


def _is_hygiene_context_text(text: str) -> bool:
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    return any(keyword in normalized for keyword in HYGIENE_KEYWORDS)


def find_active_conversation_by_channel_ref(
    db: Session,
    client_id,
    remote_jid: str,
    *,
    branch_id: UUID | None = None,
) -> Conversation | None:
    """Reuse conversation if there is an active handover for this remote_jid."""
    query = (
        db.query(Handover)
        .filter(
            Handover.client_id == client_id,
            Handover.channel_ref == remote_jid,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
    )
    if branch_id is not None:
        query = query.join(Conversation, Conversation.id == Handover.conversation_id).filter(
            Conversation.branch_id == branch_id
        )
    handover = query.first()
    if handover:
        return db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()
    return None


def get_mute_settings(db: Session, client_id) -> tuple[int, int]:
    """Get mute durations from client_settings or use defaults."""
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if settings:
        mute_first = settings.mute_duration_first_minutes or DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = settings.mute_duration_second_hours or DEFAULT_MUTE_DURATION_SECOND_HOURS
    else:
        mute_first = DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = DEFAULT_MUTE_DURATION_SECOND_HOURS

    return mute_first, mute_second


def get_active_handover(db: Session, conversation_id) -> Handover | None:
    """Get latest pending/active handover for conversation."""
    return (
        db.query(Handover)
        .filter(
            Handover.conversation_id == conversation_id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )


def _reuse_active_handover(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message: str,
    source: str,
    intent: str | None = None,
) -> tuple[Handover | None, bool, bool]:
    handover = get_active_handover(db, conversation.id)
    if not handover:
        return None, False, False

    if conversation.state == ConversationState.BOT_ACTIVE.value:
        target_state = ConversationState.MANAGER_ACTIVE if handover.status == "active" else ConversationState.PENDING
        transition_result = transition_state(
            conversation,
            target_state,
            allow_same=True,
            enforce=False,
            handover=handover,
        )
        if transition_result["invalid_transition"]:
            _record_decision_trace(
                conversation,
                {
                    "stage": "state_transition",
                    "decision": "invalid",
                    "meta": {
                        "from": transition_result["from_state"],
                        "to": transition_result["to_state"],
                        "violations": transition_result["violations"],
                    },
                },
            )
        conversation.escalated_at = conversation.escalated_at or datetime.now(timezone.utc)

    telegram_sent = send_telegram_notification(
        db=db,
        handover=handover,
        conversation=conversation,
        user=user,
        message=message,
    )
    _record_decision_trace(
        conversation,
        {
            "stage": "escalation",
            "decision": "reuse_handover",
            "state": conversation.state,
            "intent": intent,
            "source": source,
            "handover_id": str(handover.id),
            "telegram_sent": telegram_sent,
        },
    )
    return handover, True, telegram_sent


def _handle_knowledge_safe_mode_gate(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    saved_message: Message | None,
    message_text: str,
    send_and_save,
) -> WebhookResponse | None:
    if not conversation.branch_id:
        return None
    branch = (
        db.query(Branch)
        .filter(Branch.id == conversation.branch_id)
        .first()
    )
    if not branch or not branch.knowledge_safe_mode:
        return None

    safe_mode_reason = branch.knowledge_safe_mode_reason
    if conversation.state != ConversationState.BOT_ACTIVE.value:
        _record_decision_trace(
            conversation,
            {
                "stage": "knowledge_safe_mode",
                "decision": "pending_state",
                "state": conversation.state,
                "reason": safe_mode_reason,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_wait",
            intent=None,
            source="knowledge_safe_mode",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(MSG_PENDING_WAIT)
        result_message = (
            "Safe-mode pending wait sent"
            if sent
            else "Safe-mode pending wait failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    handover_message = message_text
    _, reused, telegram_sent = _reuse_active_handover(
        db=db,
        conversation=conversation,
        user=user,
        message=handover_message,
        source="knowledge_safe_mode",
        intent="safe_mode",
    )
    if reused:
        _record_decision_trace(
            conversation,
            {
                "stage": "knowledge_safe_mode",
                "decision": "reused",
                "state": conversation.state,
                "telegram_sent": telegram_sent,
                "reason": safe_mode_reason,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_escalation",
            intent=None,
            source="knowledge_safe_mode",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(MSG_ESCALATED)
        result_message = (
            "Safe-mode escalation reused"
            if sent
            else "Safe-mode escalation reuse failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    result = escalate_to_pending(
        db=db,
        conversation=conversation,
        user_message=handover_message,
        trigger_type="knowledge_safe_mode",
        trigger_value=branch.knowledge_tag or str(branch.id),
    )
    if result.ok:
        handover = result.value
        telegram_sent = send_telegram_notification(
            db=db,
            handover=handover,
            conversation=conversation,
            user=user,
            message=handover_message,
        )
        _record_decision_trace(
            conversation,
            {
                "stage": "knowledge_safe_mode",
                "decision": "created",
                "state": conversation.state,
                "telegram_sent": telegram_sent,
                "reason": safe_mode_reason,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_escalation",
            intent=None,
            source="knowledge_safe_mode",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(MSG_ESCALATED)
        result_message = (
            "Safe-mode escalation created"
            if sent
            else "Safe-mode escalation send failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    logger.error("Safe-mode escalation failed: %s", result.error)
    _record_decision_trace(
        conversation,
        {
            "stage": "knowledge_safe_mode",
            "decision": "failed",
            "state": conversation.state,
            "error": result.error,
            "reason": safe_mode_reason,
        },
    )
    _record_message_decision_meta(
        saved_message,
        action="pending_escalation",
        intent=None,
        source="knowledge_safe_mode",
        fast_intent=False,
    )
    bot_response, sent = send_and_save(MSG_ESCALATED)
    result_message = (
        "Safe-mode escalation failed"
        if sent
        else "Safe-mode escalation failed to send"
    )
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )


def should_offer_low_confidence_retry(conversation: Conversation, now: datetime) -> bool:
    """One clarifying question before creating a handover on low confidence."""
    offered_at = conversation.retry_offered_at
    if not offered_at:
        return True

    if offered_at.tzinfo is None:
        offered_at = offered_at.replace(tzinfo=timezone.utc)

    return (now - offered_at) > timedelta(minutes=LOW_CONFIDENCE_RETRY_WINDOW_MINUTES)


async def _process_outbox_rows(
    db: Session,
    rows: list[dict],
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, int]:
    from app.routers.webhook import outbox as outbox_helpers

    return await outbox_helpers._process_outbox_rows(
        db,
        rows,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )


async def _handle_webhook_payload(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    enforce_secret: bool,
    enqueue_only: bool = False,
    skip_persist: bool = False,
    conversation_id: UUID | None = None,
    batch_messages: list[str] | None = None,
    outbox_ids: list[str] | None = None,
    outbox_created_at: datetime | None = None,
) -> WebhookResponse:
    """Shared webhook processing for inbound ChatFlow payloads."""
    logger.info(f"Webhook received: client_slug={payload.client_slug}")
    pipeline_started_at = datetime.now(timezone.utc)
    pipeline_start = time.monotonic()
    pipeline_budget_ms = _get_pipeline_budget_ms()
    pipeline_deadline = pipeline_start + (pipeline_budget_ms / 1000.0)

    def _resolve_trace_conversation(
        *,
        trace_client: Client | None,
        trace_conversation_id: UUID | None,
        trace_message_id: str | None,
        trace_remote_jid: str | None,
    ) -> Conversation | None:
        if trace_conversation_id:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == trace_conversation_id)
                .first()
            )
            if conversation:
                return conversation
        if trace_client and trace_message_id:
            saved_message = _find_message_by_message_id(db, trace_client.id, trace_message_id)
            if saved_message:
                return (
                    db.query(Conversation)
                    .filter(Conversation.id == saved_message.conversation_id)
                    .first()
                )
        if trace_client and trace_remote_jid:
            user = (
                db.query(User)
                .filter(User.client_id == trace_client.id, User.remote_jid == trace_remote_jid)
                .first()
            )
            if user:
                return (
                    db.query(Conversation)
                    .filter(
                        Conversation.client_id == trace_client.id,
                        Conversation.user_id == user.id,
                        Conversation.status == "active",
                    )
                    .first()
                )
        return None

    def _record_early_trace(
        trace_conversation: Conversation | None,
        *,
        stage: str,
        decision: str,
        reason: str,
        meta: dict[str, Any] | None = None,
    ) -> bool:
        if not trace_conversation:
            return False
        trace_payload = {"stage": stage, "decision": decision, "reason": reason}
        if meta:
            trace_payload.update(meta)
        _record_decision_trace(trace_conversation, trace_payload)
        return True

    from . import http as http_helpers

    preflight_context = {"client_slug": payload.client_slug}
    preflight_trace_id = get_trace_id()
    if preflight_trace_id:
        preflight_context["trace_id"] = preflight_trace_id
    with start_span("webhook.preflight", context=preflight_context):
        preflight_response, preflight_payload = http_helpers._run_preflight(
            payload,
            db,
            provided_secret=provided_secret,
            enforce_secret=enforce_secret,
            conversation_id=conversation_id,
            resolve_trace_conversation=_resolve_trace_conversation,
            record_early_trace=_record_early_trace,
        )
    if preflight_response:
        return preflight_response

    client = preflight_payload["client"]
    settings = preflight_payload["settings"]
    body = preflight_payload["body"]
    metadata = preflight_payload["metadata"]
    message_id = preflight_payload["message_id"]
    remote_jid = preflight_payload["remote_jid"]
    message_text = preflight_payload["message_text"]
    message_type = preflight_payload["message_type"]
    has_media = preflight_payload["has_media"]
    is_media_without_text = preflight_payload["is_media_without_text"]
    media_info = preflight_payload["media_info"]
    resolved_branch_id = preflight_payload.get("resolved_branch_id")
    resolved_knowledge_tag = preflight_payload.get("resolved_knowledge_tag")

    if not skip_persist:
        record_inbound_count(payload.client_slug)

    batch_messages_provided = batch_messages is not None
    batch_messages = _coerce_batch_messages(message_text, batch_messages)
    batch_non_booking_message = _select_last_non_booking_message(
        batch_messages,
        client_slug=payload.client_slug,
    )

    timing_context: dict = {
        "client_slug": payload.client_slug,
        "remote_jid": remote_jid,
        "message_id": message_id,
        "pipeline_budget_ms": pipeline_budget_ms,
        "pipeline_deadline": pipeline_deadline,
    }
    trace_id = preflight_trace_id or get_trace_id()
    if trace_id:
        timing_context["trace_id"] = trace_id
    if client and isinstance(client.config, dict):
        timing_context["client_config"] = client.config
    if outbox_ids:
        timing_context["outbox_ids"] = list(outbox_ids)
        timing_context["outbox_id"] = outbox_ids[0]
    if resolved_branch_id:
        timing_context["branch_id"] = str(resolved_branch_id)
    if resolved_knowledge_tag:
        timing_context["knowledge_tag"] = resolved_knowledge_tag
    simulation_context = build_simulation_context(metadata)
    if simulation_context:
        timing_context["simulation"] = dict(simulation_context)
    timing_context["timing_persisted"] = False

    outbound_idempotency_key = message_id or build_inbound_message_id(
        message_id,
        remote_jid,
        metadata.timestamp if metadata else None,
        message_text,
    )

    media_policy = _get_media_policy(client) if media_info else None
    media_decision: MediaDecision | None = None
    saved_message: Message | None = None
    media_redis_client = None
    count_rate_limit = not skip_persist
    if media_info:
        redis_url, socket_timeout_seconds = _get_media_rate_settings()
        media_redis_client = _get_debounce_redis(redis_url, socket_timeout_seconds)

    def _log_timing(stage: str, elapsed_ms: float, extra: dict | None = None) -> None:
        context = dict(timing_context)
        if extra:
            context.update(extra)
        context["stage"] = stage
        context["elapsed_ms"] = round(elapsed_ms, 2)
        for key in ("message_id", "outbox_id", "trace_id"):
            context.setdefault(key, None)
        logger.info("Timing", extra={"context": context})
        timing = timing_context.get("timing")
        if not isinstance(timing, dict):
            timing = {}
        stages = timing.get("stages")
        if not isinstance(stages, dict):
            stages = {}
        stages[stage] = context["elapsed_ms"]
        timing["stages"] = stages
        timing_context["timing"] = timing

    def _persist_timing_snapshot() -> None:
        if not saved_message or timing_context.get("timing_persisted"):
            return
        snapshot = dict(timing_context.get("timing") or {})
        snapshot["pipeline_started_at"] = pipeline_started_at.isoformat()
        snapshot["pipeline_finished_at"] = datetime.now(timezone.utc).isoformat()
        snapshot["pipeline_ms"] = round((time.monotonic() - pipeline_start) * 1000, 2)
        snapshot["pipeline_budget_ms"] = pipeline_budget_ms
        remaining_ms = (pipeline_deadline - time.monotonic()) * 1000
        snapshot["pipeline_budget_remaining_ms"] = round(max(remaining_ms, 0.0), 2)
        _merge_message_timing(saved_message, snapshot)
        timing_context["timing_persisted"] = True

    def _ensure_action_gate() -> None:
        if not saved_message:
            return
        metadata = saved_message.message_metadata if isinstance(saved_message.message_metadata, dict) else {}
        decision_meta = metadata.get("decision_meta") if isinstance(metadata, dict) else {}
        action = decision_meta.get("action") if isinstance(decision_meta, dict) else None
        if action:
            return
        intent_value = getattr(intent, "value", None)
        _record_decision_trace(
            conversation,
            {
                "stage": "action_gate",
                "decision": "error",
                "reason": "missing_action",
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="error",
            intent=intent_value if isinstance(intent_value, str) else None,
            source="action_gate",
            fast_intent=False,
        )
        _update_message_decision_metadata(saved_message, {"action_error": "missing_action"})

    def _record_escalation_metric(trigger: str) -> None:
        record_escalation_count(payload.client_slug, trigger)

    def _send_response(text: str) -> bool:
        send_start = time.monotonic()
        if conversation and is_simulation_context(conversation):
            logger.info(
                "Simulation mode: skipping outbound send",
                extra={
                    "context": {
                        "conversation_id": str(conversation.id),
                        "remote_jid": remote_jid,
                    }
                },
            )
            _log_timing("send_ms", (time.monotonic() - send_start) * 1000, {"send_ok": True})
            return True
        sent = False
        with start_span("webhook.send", context=timing_context) as span:
            instance_id = get_instance_id(
                db,
                client.id,
                branch_id=conversation.branch_id if conversation else None,
                remote_jid=remote_jid,
            )
            if not instance_id:
                logger.warning(f"No instance_id found for client {client.id}, jid={remote_jid}")
                sent = False
            else:
                use_outbox_send = _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=False)
                if use_outbox_send and conversation:
                    outbox_payload = {
                        "schema_version": "outbox.v1",
                        "event_type": "whatsapp.send_text",
                        "idempotency_key": outbound_idempotency_key,
                        "client_id": str(client.id),
                        "branch_id": str(conversation.branch_id) if conversation.branch_id else None,
                        "tenant_context": {
                            "client_id": str(client.id),
                            "branch_id": str(conversation.branch_id) if conversation.branch_id else None,
                            "client_slug": client.name,
                            "instance_id": instance_id,
                            "source": "system",
                        },
                        "conversation_id": str(conversation.id),
                        "channel": "whatsapp",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "payload": {
                            "remote_jid": remote_jid,
                            "text": text,
                            "instance_id": instance_id,
                            "idempotency_key": outbound_idempotency_key,
                        },
                    }
                    enqueue_start = time.monotonic()
                    with start_span("outbox.enqueue", context=timing_context) as enqueue_span:
                        sent = enqueue_outbox_message(
                            db,
                            client_id=client.id,
                            conversation_id=conversation.id,
                            inbound_message_id=outbound_idempotency_key,
                            payload_json=outbox_payload,
                            branch_id=conversation.branch_id,
                        )
                    if enqueue_span is not None:
                        enqueue_span.set_attribute("outbox.enqueued", bool(sent))
                    _log_timing(
                        "outbox_enqueue_ms",
                        (time.monotonic() - enqueue_start) * 1000,
                        {"outbox_enqueued": sent},
                    )
                    if not sent:
                        logger.info(
                            "Outbox send skipped (duplicate)",
                            extra={
                                "context": {
                                    "conversation_id": str(conversation.id),
                                    "remote_jid": remote_jid,
                                    "idempotency_key": outbound_idempotency_key,
                                }
                            },
                        )
                        sent = True
                else:
                    adapter = ChatFlowAdapter()
                    options = MessageOptions(
                        instance_id=instance_id,
                        idempotency_key=outbound_idempotency_key,
                    )
                    result = adapter.send_text(remote_jid, text, options)
                    sent = result.is_ok()
                    if not sent and skip_persist:
                        # Preserve legacy behavior when raise_on_fail=True (skip_persist path).
                        raise RuntimeError(f"ChatFlow delivery failed: {result.error}")
        if span is not None:
            span.set_attribute("send.ok", bool(sent))
        _log_timing("send_ms", (time.monotonic() - send_start) * 1000, {"send_ok": sent})
        return sent

    if skip_persist:
        (
            skip_response,
            conversation,
            user,
            saved_message,
            media_decision,
        ) = await _prepare_skip_persist(
            db=db,
            client=client,
            conversation_id=conversation_id,
            message_id=message_id,
            remote_jid=remote_jid,
            message_text=message_text,
            media_info=media_info,
            media_policy=media_policy,
            media_redis_client=media_redis_client,
            count_rate_limit=count_rate_limit,
            outbox_created_at=outbox_created_at,
            timing_context=timing_context,
            resolve_trace_conversation=_resolve_trace_conversation,
            record_early_trace=_record_early_trace,
        )
        if skip_response:
            return skip_response
    else:
        dedup_start = time.monotonic()
        with start_span("webhook.dedup", context=timing_context) as span:
            dedupe_response, message_id = await _handle_dedup_gate(
                db=db,
                client=client,
                message_id=message_id,
                remote_jid=remote_jid,
                metadata=metadata,
                message_text=message_text,
                conversation_id=conversation_id,
                resolve_trace_conversation=_resolve_trace_conversation,
                record_early_trace=_record_early_trace,
            )
        if span is not None:
            span.set_attribute("dedup.skipped", dedupe_response is not None)
        timing_context["message_id"] = message_id
        _log_timing(
            "dedup_ms",
            (time.monotonic() - dedup_start) * 1000,
            {"dedup_skipped": dedupe_response is not None},
        )
        if dedupe_response:
            return dedupe_response

        # 1. Get or create user
        user = get_or_create_user(db, client.id, remote_jid)

        # 2. Find existing conversation by handover.channel_ref or create new
        conversation = find_active_conversation_by_channel_ref(
            db,
            client.id,
            remote_jid,
            branch_id=resolved_branch_id,
        )
        if not conversation:
            conversation = get_or_create_conversation(
                db,
                client.id,
                user.id,
                "whatsapp",
                branch_id=resolved_branch_id,
            )
        timing_context["conversation_id"] = str(conversation.id)
        if metadata and conversation:
            sim_context = apply_simulation_context(conversation, metadata)
            if sim_context:
                timing_context["simulation"] = dict(sim_context)

        if media_info and media_decision is None and media_policy:
            media_decision = await _evaluate_media_decision(
                media=media_info,
                client_id=client.id,
                remote_jid=remote_jid,
                policy=media_policy,
                redis_client=media_redis_client,
                count_rate_limit=count_rate_limit,
            )

        # 3. Save user message (keep message_id for dedup)
        message_metadata = metadata.model_dump(exclude_none=True) if metadata else {}
        if message_id:
            message_metadata["message_id"] = message_id
        if message_type:
            message_metadata["message_type"] = message_type
        if has_media:
            message_metadata["has_media"] = True
        if media_info:
            media_meta = {
                "type": media_info.media_type,
                "raw_type": media_info.raw_type,
                "mime": media_info.mime,
                "size_bytes": media_info.size_bytes,
                "url": media_info.url,
                "file_name": media_info.file_name,
                "caption": media_info.caption,
                "ptt": media_info.is_ptt,
            }
            if media_decision:
                media_meta["decision"] = _serialize_media_decision(media_decision)
            message_metadata["media"] = media_meta
        saved_message = save_message(
            db,
            conversation.id,
            client.id,
            role="user",
            content=message_text,
            message_metadata=message_metadata,
        )
        _ensure_rag_meta_defaults(saved_message)
        if trace_id and saved_message:
            _update_message_decision_metadata(saved_message, {"trace_id": trace_id})

        if enqueue_only:
            return await _handle_enqueue_only_accept(
                db=db,
                client=client,
                conversation=conversation,
                payload=payload,
                remote_jid=remote_jid,
                message_id=message_id,
                message_text=message_text,
                metadata=metadata,
                saved_message=saved_message,
                media_info=media_info,
                media_policy=media_policy,
                media_decision=media_decision,
            )

    routing = _get_routing_policy(conversation.state)
    context_contract, context_error = build_context_contract(conversation, payload, settings)
    _record_decision_trace(
        conversation,
        {
            "stage": "contract",
            "decision": "context",
            "contract_ok": context_error is None,
            "contract_error": context_error,
            "contract": context_contract,
        },
    )
    decision_plan = build_decision_plan(
        state=conversation.state,
        routing=routing,
        client_slug=payload.client_slug,
    )
    plan_id = decision_plan.plan_id
    for stage in decision_plan.stages:
        _record_decision_trace(
            conversation,
            {
                "stage": "decision_graph",
                "decision": stage,
                "plan_id": plan_id,
            },
        )

    now = datetime.now(timezone.utc)
    sim_now = get_simulation_time(conversation) if conversation else None
    if sim_now:
        now = sim_now

    transcript = None
    asr_meta = None
    asr_inflight_blocked = False
    asr_inflight_set = False
    if media_info and media_policy and _is_placeholder_text(message_text):
        stored_path = None
        if saved_message and isinstance(saved_message.message_metadata, dict):
            stored_path = (saved_message.message_metadata.get("media") or {}).get("storage_path")
        if _is_voice_note(media_info) and conversation.state == ConversationState.BOT_ACTIVE.value:
            context = _get_conversation_context(conversation)
            asr_inflight, inflight_expired = _get_asr_inflight(context, now=now)
            if inflight_expired:
                context = _set_asr_inflight(context, None)
            if asr_inflight:
                asr_inflight_blocked = True
            else:
                context = _set_asr_inflight(
                    context,
                    {
                        "started_at": now.isoformat(),
                        "expires_at": (now + timedelta(seconds=ASR_INFLIGHT_TTL_SECONDS)).isoformat(),
                    },
                )
                asr_inflight_set = True
            if inflight_expired or asr_inflight_set or asr_inflight_blocked:
                _set_conversation_context(conversation, context)
            if asr_inflight_blocked and saved_message:
                _update_message_decision_metadata(saved_message, {"asr_inflight": True})

        if not asr_inflight_blocked:
            transcript, transcript_status, asr_meta = await _maybe_transcribe_voice(
                media=media_info,
                policy=media_policy,
                media_decision=media_decision,
                storage_path=stored_path,
                saved_message=saved_message,
            )
            if saved_message and asr_meta:
                _update_message_asr_metadata(saved_message, asr_meta)
            if transcript:
                message_text = transcript
                if saved_message:
                    saved_message.content = transcript
                    _, _, model, language, _, _, _, _ = _get_transcription_settings()
                    transcript_model = model
                    if asr_meta and asr_meta.get("asr_model"):
                        transcript_model = asr_meta.get("asr_model")
                    updates = {
                        "transcript": transcript,
                        "transcript_model": transcript_model,
                        "transcript_provider": asr_meta.get("asr_provider") if asr_meta else None,
                        "transcribed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if language:
                        updates["transcript_language"] = language
                    _update_message_media_metadata(saved_message, updates)
            elif transcript_status not in {"disabled", "not_voice", "not_allowed", "too_large", "missing_audio"}:
                logger.warning(
                    "Voice transcription skipped",
                    extra={"context": {"status": transcript_status, "conversation_id": str(conversation.id)}},
                )
        if asr_inflight_set:
            context = _get_conversation_context(conversation)
            context = _set_asr_inflight(context, None)
            _set_conversation_context(conversation, context)

    asr_low_confidence = False
    if transcript and media_info and _is_voice_note(media_info):
        asr_low_confidence = _is_asr_low_confidence(transcript, media_info.duration_seconds)

    # 4. Update last_message_at (keep previous for session timeout check)
    from . import _legacy as legacy

    policy_type = _get_policy_type(client, client_slug=payload.client_slug)
    policy_pack = _get_policy_pack(client, client_slug=payload.client_slug)
    policy_pack_missing = not isinstance(policy_pack, dict)
    policy_source = "policy_pack" if not policy_pack_missing else "policy_gate"
    policy_handler = legacy._get_policy_handler(client, client_slug=payload.client_slug)
    hard_law_sections = set(_resolve_hard_law_sections(policy_pack))
    quiet_hours_notice: str | None = None
    evening_greeting: str | None = None
    if conversation.state == ConversationState.BOT_ACTIVE.value:
        quiet_hours_notice = build_quiet_hours_notice(
            now_utc=now,
            client_slug=payload.client_slug,
        )
        evening_greeting = build_evening_greeting(
            now_utc=now,
            client_slug=payload.client_slug,
        )

    _finalize_bot_response = functools.partial(
        _finalize_bot_response_helper,
        conversation=conversation,
        quiet_hours_notice=quiet_hours_notice,
        evening_greeting=evening_greeting,
        now=now,
    )

    def _extract_fact_payload(decision_meta: dict[str, Any]) -> dict[str, Any] | None:
        fact_keys = (
            "fact_source",
            "fact_intents",
            "info_sections",
            "info_combined",
            "question_type",
            "question_type_score",
            "service_query",
            "service_query_source",
            "service_query_score",
            "price_item",
            "duration_item",
            "info_signals",
            "anchor_intents",
            "anchor_hits",
            "anchor_boost",
        )
        facts = {key: decision_meta.get(key) for key in fact_keys if key in decision_meta}
        return facts or None

    def _maybe_apply_fact_guard(
        *,
        decision_meta: dict[str, Any] | None,
        intent: str | None,
        source: str,
        allow_handover: bool,
    ) -> WebhookResponse | None:
        if not FACT_GUARD_ENABLED:
            return None
        if not isinstance(decision_meta, dict):
            return None
        if intent in FACT_GUARD_SKIP_INTENTS:
            return None
        fact_source = decision_meta.get("fact_source")
        if not isinstance(fact_source, str) or not fact_source:
            return None
        fact_payload = {
            "info_sections": decision_meta.get("info_sections"),
            "service_query": decision_meta.get("service_query"),
            "price_item": decision_meta.get("price_item"),
            "duration_item": decision_meta.get("duration_item"),
        }
        has_facts = any(
            (
                isinstance(value, str) and value.strip()
            )
            or (
                isinstance(value, list) and value
            )
            or (
                isinstance(value, dict) and value
            )
            for value in fact_payload.values()
        )
        if has_facts:
            return None
        context = _get_conversation_context(conversation)
        context_manager = _get_context_manager(context)
        clarify_count, _ = _get_clarify_attempt_state(context_manager, FACT_GUARD_INTENT)
        if clarify_count >= FACT_GUARD_MAX_ATTEMPTS:
            _record_context_manager_decision(
                conversation,
                saved_message,
                decision="clarify_limit",
                updates={
                    "clarify_attempt": {"intent": FACT_GUARD_INTENT, "count": clarify_count},
                    "clarify_reason": "fact_guard",
                    "clarify_limit": True,
                },
            )
            return _handle_clarify_limit_escalation(
                db=db,
                conversation=conversation,
                user=user,
                message_text=message_text,
                saved_message=saved_message,
                source="fact_guard",
                allow_handover=allow_handover,
                send_response=_send_response,
                finalize_response=_finalize_bot_response,
            )
        _register_clarify_attempt(
            conversation=conversation,
            saved_message=saved_message,
            intent=FACT_GUARD_INTENT,
            now=now,
            reason="fact_guard",
        )
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "fact_guard",
                "decision": "clarify",
                "state": conversation.state,
                "fact_source": fact_source,
                "source": source,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="reply",
            intent="fact_guard",
            source="fact_guard",
            fast_intent=False,
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "clarify_reason": "fact_guard",
                    "fact_guard": True,
                },
            )
        bot_response, sent = _send_and_save(MSG_FACT_GUARD_CLARIFY)
        result_message = "Fact guard clarify sent" if sent else "Fact guard clarify failed"
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    def _record_contract_traces(*, action_type: str | None = None) -> None:
        decision_meta: dict[str, Any] = {}
        if saved_message and isinstance(saved_message.message_metadata, dict):
            raw_meta = saved_message.message_metadata.get("decision_meta")
            if isinstance(raw_meta, dict):
                decision_meta = raw_meta

        action_value = action_type
        if not action_value:
            meta_action = decision_meta.get("action")
            if isinstance(meta_action, str) and meta_action:
                action_value = meta_action
        if not action_value:
            action_value = "reply"

        fact_source = decision_meta.get("fact_source")
        source = decision_meta.get("source")
        if isinstance(fact_source, str) and fact_source:
            sources = [fact_source]
        elif isinstance(source, str) and source:
            sources = [source]
        else:
            sources = None
        policy_gate = decision_meta.get("policy_gate")
        policy_flags = [policy_gate] if isinstance(policy_gate, str) and policy_gate else None
        facts = _extract_fact_payload(decision_meta)

        fact_payload = {
            "info_sections": decision_meta.get("info_sections"),
            "service_query": decision_meta.get("service_query"),
            "price_item": decision_meta.get("price_item"),
            "duration_item": decision_meta.get("duration_item"),
        }
        has_fact_payload = any(
            (
                isinstance(value, str) and value.strip()
            )
            or (
                isinstance(value, list) and value
            )
            or (
                isinstance(value, dict) and value
            )
            for value in fact_payload.values()
        )
        if facts or (isinstance(fact_source, str) and fact_source):
            _record_decision_trace(
                conversation,
                {
                    "stage": "fact_resolver",
                    "decision": "resolved" if has_fact_payload else "missing",
                    "fact_source": fact_source if isinstance(fact_source, str) else None,
                    "facts": facts,
                },
            )

        fact_contract, fact_error = build_fact_contract(
            facts=facts,
            sources=sources,
            policy_flags=policy_flags,
        )
        _record_decision_trace(
            conversation,
            {
                "stage": "contract",
                "decision": "fact",
                "contract_ok": fact_error is None,
                "contract_error": fact_error,
                "contract": fact_contract,
            },
        )

        action_contract, action_error = build_action_contract(
            action_type=action_value,
            required_next_slots=None,
            escalation_reason=None,
        )
        _record_decision_trace(
            conversation,
            {
                "stage": "contract",
                "decision": "action",
                "contract_ok": action_error is None,
                "contract_error": action_error,
                "contract": action_contract,
            },
        )

        response_contract, response_error = build_response_contract(
            tone=None,
            must_include=None,
            must_not_include=None,
            language=None,
        )
        _record_decision_trace(
            conversation,
            {
                "stage": "contract",
                "decision": "response",
                "contract_ok": response_error is None,
                "contract_error": response_error,
                "contract": response_contract,
            },
        )

    def _detect_language_preference(text: str | None) -> str | None:
        if not text:
            return None
        normalized = _normalize_text(text)
        if not normalized:
            return None
        if any(token in normalized for token in ("қазақша", "казах", "қазақ", "қазак")):
            return "kz"
        if any(token in normalized for token in ("по-русски", "русск")):
            return "ru"
        for char in ("ә", "ғ", "қ", "ң", "ө", "ұ", "ү", "һ", "і"):
            if char in normalized:
                return "kz"
        return None

    def _collect_memory_candidates(context: dict, text: str | None) -> dict[str, dict]:
        candidates: dict[str, dict] = {}
        booking_state = _get_booking_context(context)
        if isinstance(booking_state, dict):
            name_value = booking_state.get("name")
            if isinstance(name_value, str) and name_value.strip():
                candidates["name"] = {
                    "value": name_value.strip(),
                    "source": "booking_slot",
                    "confidence": 1.0,
                }
            service_value = booking_state.get("service")
            if isinstance(service_value, str) and service_value.strip():
                candidates["preferred_service"] = {
                    "value": service_value.strip(),
                    "source": "booking_slot",
                    "confidence": 1.0,
                }
            time_value = booking_state.get("datetime")
            if isinstance(time_value, str) and time_value.strip():
                candidates["preferred_time"] = {
                    "value": time_value.strip(),
                    "source": "booking_slot",
                    "confidence": 1.0,
                }
        language = _detect_language_preference(text)
        if language:
            candidates["language"] = {
                "value": language,
                "source": "language_detect",
                "confidence": 1.0,
            }
        return candidates

    def _upsert_memory_item(
        *,
        items: dict[str, dict],
        key: str,
        payload: dict,
        now: datetime,
        ttl_days: int,
    ) -> bool:
        if not isinstance(key, str) or not key.strip() or not isinstance(payload, dict):
            return False
        value = payload.get("value")
        if not isinstance(value, str) or not value.strip():
            return False
        expires_at = (now + timedelta(days=ttl_days)).isoformat()
        next_item = {
            "value": value.strip(),
            "confidence": float(payload.get("confidence") or 1.0),
            "source": payload.get("source") or "user",
            "updated_at": now.isoformat(),
            "expires_at": expires_at,
        }
        existing = items.get(key) if isinstance(items.get(key), dict) else None
        if existing and existing.get("value") == next_item["value"]:
            items[key] = {**existing, **next_item}
            return True
        items[key] = next_item
        return True

    def _merge_pending_items(
        pending: dict | None,
        candidates: dict[str, dict],
        now: datetime,
    ) -> tuple[dict | None, list[str]]:
        if not candidates:
            return pending, []
        pending = dict(pending) if isinstance(pending, dict) else {}
        items = pending.get("items")
        if not isinstance(items, dict):
            items = {}
        added_keys: list[str] = []
        for key, payload in candidates.items():
            if not isinstance(payload, dict):
                continue
            value = payload.get("value")
            if not isinstance(value, str) or not value.strip():
                continue
            items[key] = {
                "value": value.strip(),
                "source": payload.get("source") or "user",
                "confidence": float(payload.get("confidence") or 1.0),
                "captured_at": now.isoformat(),
            }
            added_keys.append(key)
        if items:
            pending["items"] = items
            pending["expires_at"] = (now + timedelta(hours=MEMORY_PENDING_TTL_HOURS)).isoformat()
            return pending, added_keys
        return None, []

    def _should_prompt_memory_consent(context: dict, response_text: str | None) -> bool:
        if conversation.state != ConversationState.BOT_ACTIVE.value:
            return False
        if not response_text:
            return False
        expected_reply = _get_expected_reply_type(context)
        if expected_reply:
            return False
        booking_state = _get_booking_context(context)
        if isinstance(booking_state, dict) and booking_state.get("active"):
            return False
        normalized = _normalize_text(response_text)
        if "ответьте" in normalized and "да" in normalized and "нет" in normalized:
            return False
        return True

    def _apply_memory_updates(response_text: str | None) -> str | None:
        if not response_text:
            return response_text
        if not MEMORY_PROFILE_ENABLED:
            return response_text
        context = _get_conversation_context(conversation)
        profile, profile_changed = _get_memory_profile(context, now=now)
        pending, pending_expired = _get_memory_pending(context, now=now)
        if pending_expired:
            pending = None
        consent = profile.get("consent") if isinstance(profile.get("consent"), dict) else {}
        consent_status = consent.get("status") or "unknown"
        candidates = _collect_memory_candidates(context, message_text)
        stored_keys: list[str] = []
        pending_keys: list[str] = []
        prompt_consent = False

        if consent_status == "granted":
            items = profile.get("items") if isinstance(profile.get("items"), dict) else {}
            for key, payload in candidates.items():
                if _upsert_memory_item(
                    items=items,
                    key=key,
                    payload=payload,
                    now=now,
                    ttl_days=int(profile.get("ttl_days") or MEMORY_PROFILE_TTL_DAYS),
                ):
                    stored_keys.append(key)
            if pending and isinstance(pending.get("items"), dict):
                for key, payload in pending["items"].items():
                    if _upsert_memory_item(
                        items=items,
                        key=key,
                        payload=payload,
                        now=now,
                        ttl_days=int(profile.get("ttl_days") or MEMORY_PROFILE_TTL_DAYS),
                    ):
                        stored_keys.append(key)
                pending = None
            profile["items"] = items
        elif consent_status == "declined":
            pending = None
        else:
            pending, pending_keys = _merge_pending_items(pending, candidates, now)
            if consent_status == "unknown" and pending_keys and _should_prompt_memory_consent(
                context, response_text
            ):
                consent_status = "asked"
                consent["status"] = "asked"
                consent["asked_at"] = now.isoformat()
                consent["source"] = "explicit"
                consent["prompt_count"] = int(consent.get("prompt_count") or 0) + 1
                prompt_consent = True
                profile_changed = True

        consent["status"] = consent_status
        profile["consent"] = consent
        if stored_keys:
            profile["last_updated_at"] = now.isoformat()
        if profile_changed or stored_keys or pending_expired or pending_keys:
            context = _set_memory_profile(context, profile)
            context = _set_memory_pending(context, pending)
            _set_conversation_context(conversation, context)
        if prompt_consent:
            _record_decision_trace(
                conversation,
                {
                    "stage": "memory_profile",
                    "decision": "consent_prompted",
                    "state": conversation.state,
                    "pending_keys": pending_keys,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {"memory_consent_prompted": True, "memory_pending_keys": pending_keys},
                )
            return f"{response_text}\n\n{MSG_MEMORY_CONSENT}"
        if stored_keys:
            _record_decision_trace(
                conversation,
                {
                    "stage": "memory_profile",
                    "decision": "stored",
                    "state": conversation.state,
                    "stored_keys": sorted(set(stored_keys)),
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {"memory_profile_stored": sorted(set(stored_keys))},
                )
        return response_text

    def _send_and_save(text: str, *, allow_quiet_hours: bool = True) -> tuple[str, bool]:
        final_text = _finalize_bot_response(text, allow_quiet_hours=allow_quiet_hours)
        final_text = _apply_memory_updates(final_text)
        _record_contract_traces()
        save_message(db, conversation.id, client.id, role="assistant", content=final_text)
        sent = _send_response(final_text)
        _persist_timing_snapshot()
        return final_text, sent

    safe_mode_response = _handle_knowledge_safe_mode_gate(
        db=db,
        conversation=conversation,
        user=user,
        saved_message=saved_message,
        message_text=message_text,
        send_and_save=_send_and_save,
    )
    if safe_mode_response:
        return safe_mode_response
    previous_last_message_at = conversation.last_message_at
    conversation.last_message_at = now
    if asr_inflight_blocked:
        _record_decision_trace(
            conversation,
            {
                "stage": "asr_inflight",
                "decision": "wait",
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="asr_inflight",
            intent="asr_inflight",
            source="asr_inflight",
            fast_intent=False,
        )
        bot_response, sent = _send_and_save(MSG_ASR_INFLIGHT_WAIT)
        result_message = "ASR inflight wait sent" if sent else "ASR inflight wait failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )
    context = _get_conversation_context(conversation)
    context_manager = _get_context_manager(context)
    session_memory = _get_session_memory(context)
    session_memory, memory_contract_error = _normalize_session_memory(session_memory)
    if memory_contract_error:
        memory_snapshot = _session_memory_snapshot(session_memory)
        memory_snapshot["memory_keys"] = sorted(
            key for key in session_memory.keys() if isinstance(key, str)
        )
        context = _set_session_memory(context, None)
        _set_conversation_context(conversation, context)
        _record_decision_trace(
            conversation,
            {
                "stage": "session_memory",
                "decision": "contract_error",
                "reason": memory_contract_error,
                **memory_snapshot,
            },
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {"session_memory_contract_error": memory_contract_error},
            )
        session_memory = {}
    else:
        context = _set_session_memory(context, session_memory or None)
        _set_conversation_context(conversation, context)
    session_memory_reset_reason = None
    if session_memory and _is_session_memory_expired(session_memory, now):
        session_memory_reset_reason = "expired"
    elif _should_reset_session_memory(message_text):
        session_memory_reset_reason = "explicit_reset"
    elif session_memory and conversation.state in [
        ConversationState.PENDING.value,
        ConversationState.MANAGER_ACTIVE.value,
    ]:
        session_memory_reset_reason = "handover"
    if session_memory_reset_reason:
        reset_snapshot = _session_memory_snapshot(session_memory)
        reset_snapshot["memory_keys"] = sorted(
            key for key in session_memory.keys() if isinstance(key, str)
        )
        context, context_manager, _reset_snapshot = _reset_session_memory(
            context=context,
            context_manager=context_manager,
            reason=session_memory_reset_reason,
            now=now,
        )
        re_entry_required = session_memory_reset_reason in {"expired", "handover"}
        if re_entry_required:
            context = _set_re_entry_required(
                context,
                reason=session_memory_reset_reason,
                now=now,
            )
        _set_conversation_context(conversation, context)
        _record_decision_trace(
            conversation,
            {
                "stage": "session_memory",
                "decision": "reset",
                "reason": session_memory_reset_reason,
                **reset_snapshot,
            },
        )
        if re_entry_required:
            _record_decision_trace(
                conversation,
                {
                    "stage": "re_entry",
                    "decision": "required",
                    "reason": session_memory_reset_reason,
                },
            )
        if saved_message:
            _update_message_decision_metadata(
                saved_message, {"session_memory_reset": session_memory_reset_reason}
            )
        session_memory = {}
        if session_memory_reset_reason == "explicit_reset" and _is_session_reset_only_message(message_text):
            bot_response = "Ок, давайте новую тему. Чем могу помочь?"
            _record_message_decision_meta(
                saved_message,
                action="smalltalk",
                intent="reset",
                source="session_memory",
                fast_intent=False,
            )
            _record_decision_trace(
                conversation,
                {
                    "stage": "session_memory",
                    "decision": "reset_ack",
                    "reason": session_memory_reset_reason,
                },
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Session reset ack sent" if sent else "Session reset ack failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )
    message_count = _increment_context_message_count(context_manager)
    context_manager, refusal_flags, refusal_events = _update_refusal_flags(
        context_manager,
        message_text=message_text,
        now=now,
        client_slug=payload.client_slug,
    )
    context_manager, class_carryover_event = _prune_class_carryover(
        context_manager,
        message_count=message_count,
    )
    context_manager, carryover_event = _prune_service_carryover(
        context_manager,
        message_count=message_count,
    )
    context_manager, consult_context_event = _prune_consult_context(
        context_manager,
        message_count=message_count,
    )
    context = _set_context_manager(context, context_manager)
    _set_conversation_context(conversation, context)
    if refusal_events:
        _record_context_manager_decision(
            conversation,
            saved_message,
            decision="refusal_flags",
            updates={"refusal_flags": refusal_flags, "refusal_events": refusal_events},
        )
    if class_carryover_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "class_carryover",
                "decision": "expired",
                **class_carryover_event,
            },
        )
    if carryover_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "service_carryover",
                "decision": "expired",
                **carryover_event,
            },
        )
    if consult_context_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "consult_context",
                "decision": "expired",
                **consult_context_event,
            },
        )
    if message_count == SUMMARY_MESSAGE_THRESHOLD:
        _update_compact_summary(
            conversation=conversation,
            saved_message=saved_message,
            reason="message_threshold",
            now=now,
        )
        context = _get_conversation_context(conversation)
    current_goal = context_manager.get("current_goal") if isinstance(context_manager, dict) else None
    consult_context = _get_consult_context(context_manager, message_count=message_count)
    consult_return_prompt = None
    consult_return_reason = None
    consult_return_pending = False
    class_carryover = _get_class_carryover(context_manager, message_count=message_count)
    expected_reply_reason = _get_expected_reply_reason(context)

    expected_reply_state = _apply_expected_reply_contract(
        conversation=conversation,
        saved_message=saved_message,
        message_text=message_text,
        batch_messages=batch_messages,
        context=context,
        context_manager=context_manager,
        now=now,
        current_goal=current_goal,
        class_carryover=class_carryover,
        message_count=message_count,
        policy_type=policy_type,
        policy_pack=policy_pack,
        client_slug=payload.client_slug,
    )
    context = expected_reply_state.context
    context_manager = expected_reply_state.context_manager
    current_goal = expected_reply_state.current_goal
    expected_reply_type = expected_reply_state.expected_reply_type
    intent_queue = expected_reply_state.intent_queue
    expected_reply_matched = expected_reply_state.expected_reply_matched
    expected_reply_shortcircuit = expected_reply_state.expected_reply_shortcircuit
    expected_reply_blocked_by_info = expected_reply_state.expected_reply_blocked_by_info
    memory_expected_reply_type = expected_reply_state.memory_expected_reply_type

    # 4.5 Branch routing (instance_id -> branch, or ask user)
    branch_response = _handle_branch_selection_gate(
        db=db,
        client_id=client.id,
        settings=settings,
        conversation=conversation,
        user=user,
        metadata=metadata,
        message_text=message_text,
        now=now,
        send_and_save=_send_and_save,
    )
    if branch_response:
        return branch_response

    if conversation.branch_id:
        timing_context["branch_id"] = str(conversation.branch_id)
        if "knowledge_tag" not in timing_context:
            branch = (
                db.query(Branch).filter(Branch.id == conversation.branch_id).first()
            )
            if branch and branch.knowledge_tag:
                timing_context["knowledge_tag"] = branch.knowledge_tag

    # 5. Check session timeout - reset mute if no messages for 24h+
    bot_response = None
    sent = False
    result_message = None
    intent = None

    _apply_session_timeout_reset(
        conversation=conversation,
        previous_last_message_at=previous_last_message_at,
        now=now,
    )

    _forward_pending_to_telegram(
        db=db,
        client_id=client.id,
        conversation=conversation,
        metadata=metadata,
        message_text=message_text,
        has_media=has_media,
        media_info=media_info,
        media_decision=media_decision,
        media_policy=media_policy,
        saved_message=saved_message,
        transcript=transcript,
    )

    manager_active_response = _handle_manager_active_gate(
        db=db,
        conversation=conversation,
        saved_message=saved_message,
    )
    if manager_active_response:
        return manager_active_response

    # 8.1 Detect signals early for re-engage and mute decisions.
    reengage_response, batch_messages, reengage_override = _handle_reengage_and_mute_gate(
        db=db,
        client_id=client.id,
        client_slug=payload.client_slug,
        conversation=conversation,
        message_text=message_text,
        batch_messages=batch_messages,
        expected_reply_shortcircuit=expected_reply_shortcircuit,
        now=now,
        send_and_save=_send_and_save,
    )
    if reengage_response:
        return reengage_response

    # 9.01 ASR low-confidence confirmation (bot-active only).
    context = _get_conversation_context(conversation)
    asr_confirmation = _get_asr_confirmation(context)
    if not routing.get("allow_bot_reply"):
        if asr_confirmation:
            context = _set_asr_confirmation(context, None)
            _set_conversation_context(conversation, context)
    else:
        if asr_confirmation:
            if not _is_asr_confirmation_active(asr_confirmation, now):
                context = _set_asr_confirmation(context, None)
                _set_conversation_context(conversation, context)
                asr_confirmation = None
            else:
                decision = classify_confirmation(message_text)
                if decision == "yes":
                    confirmed_text = (asr_confirmation.get("transcript") or "").strip()
                    context = _set_asr_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    if confirmed_text:
                        message_text = confirmed_text
                        if not batch_messages_provided:
                            batch_messages = _coerce_batch_messages(message_text, None)
                    else:
                        bot_response = MSG_ASR_CONFIRM_DECLINED
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "media",
                                "decision": "asr_confirm_missing_transcript",
                                "reason": "empty_transcript",
                                "state": conversation.state,
                            },
                        )
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "ASR confirm missing transcript" if sent else "ASR confirm response failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                elif decision == "no":
                    context = _set_asr_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    bot_response = MSG_ASR_CONFIRM_DECLINED
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "media",
                            "decision": "asr_confirm_declined",
                            "reason": "user_declined",
                            "state": conversation.state,
                        },
                    )
                    bot_response, sent = _send_and_save(bot_response)
                    result_message = "ASR confirm declined" if sent else "ASR confirm decline failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )
                else:
                    context = _set_asr_confirmation(context, None)
                    _set_conversation_context(conversation, context)

    if asr_low_confidence and transcript:
        attempt = int(asr_confirmation.get("attempt", 0)) + 1 if asr_confirmation else 1
        confirmation_payload = {
            "asked_at": now.isoformat(),
            "transcript": transcript.strip(),
            "attempt": attempt,
        }
        context = _set_asr_confirmation(context, confirmation_payload)
        _set_conversation_context(conversation, context)
        bot_response = MSG_ASR_CONFIRM.format(text=confirmation_payload["transcript"])
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {"asr_confirm_requested": True, "asr_low_confidence": True},
            )
        _record_decision_trace(
            conversation,
            {
                "stage": "media",
                "decision": "asr_confirm_requested",
                "reason": "low_confidence",
                "state": conversation.state,
                "attempt": attempt,
            },
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "ASR confirmation requested" if sent else "ASR confirmation send failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    # 9.015 Memory consent confirmation (bot-active only).
    if (
        MEMORY_PROFILE_ENABLED
        and routing.get("allow_bot_reply")
        and conversation.state == ConversationState.BOT_ACTIVE.value
    ):
        context = _get_conversation_context(conversation)
        profile, profile_changed = _get_memory_profile(context, now=now)
        consent = profile.get("consent") if isinstance(profile.get("consent"), dict) else {}
        if consent.get("status") == "asked":
            decision = classify_confirmation(message_text)
            if decision in {"yes", "no"}:
                pending, pending_expired = _get_memory_pending(context, now=now)
                if pending_expired:
                    pending = None
                stored_keys: list[str] = []
                if decision == "yes":
                    items = profile.get("items") if isinstance(profile.get("items"), dict) else {}
                    if pending and isinstance(pending.get("items"), dict):
                        for key, payload in pending["items"].items():
                            if _upsert_memory_item(
                                items=items,
                                key=key,
                                payload=payload,
                                now=now,
                                ttl_days=int(profile.get("ttl_days") or MEMORY_PROFILE_TTL_DAYS),
                            ):
                                stored_keys.append(key)
                    profile["items"] = items
                    consent["status"] = "granted"
                    consent["granted_at"] = now.isoformat()
                    response_text = MSG_MEMORY_CONSENT_ACCEPTED
                else:
                    consent["status"] = "declined"
                    consent["declined_at"] = now.isoformat()
                    response_text = MSG_MEMORY_CONSENT_DECLINED
                profile["consent"] = consent
                if stored_keys:
                    profile["last_updated_at"] = now.isoformat()
                context = _set_memory_profile(context, profile)
                context = _set_memory_pending(context, None)
                _set_conversation_context(conversation, context)
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "memory_profile",
                        "decision": "consent_granted" if decision == "yes" else "consent_declined",
                        "state": conversation.state,
                        "stored_keys": sorted(set(stored_keys)) if stored_keys else None,
                    },
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "memory_consent": decision,
                            "memory_stored": sorted(set(stored_keys)) if stored_keys else None,
                        },
                    )
                bot_response, sent = _send_and_save(response_text)
                result_message = (
                    "Memory consent handled" if sent else "Memory consent response failed"
                )
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

    pending_response = _handle_pending_gate(
        db=db,
        conversation=conversation,
        message_text=message_text,
        saved_message=saved_message,
        now=now,
        send_and_save=_send_and_save,
    )
    if pending_response:
        return pending_response

    # 4.9 Behavioral shield (pre-LAW/policy).
    shield_response = _handle_shield_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        metadata=metadata,
        now=now,
        saved_message=saved_message,
        send_and_save=_send_and_save,
        record_escalation_metric=_record_escalation_metric,
        skip_persist=skip_persist,
    )
    if shield_response:
        return shield_response

    if has_media:
        if not media_info:
            bot_response = MSG_MEDIA_UNSUPPORTED
            if is_media_without_text:
                router_media_meta = _set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="media_only",
                )
                trace_payload = {
                    "stage": "media",
                    "decision": "unsupported",
                    "state": conversation.state,
                }
                trace_payload.update(router_media_meta)
                _record_decision_trace(conversation, trace_payload)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Media unsupported response sent" if sent else "Media response failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

        if media_decision is None and media_policy:
            media_decision = await _evaluate_media_decision(
                media=media_info,
                client_id=client.id,
                remote_jid=remote_jid,
                policy=media_policy,
                redis_client=media_redis_client,
                count_rate_limit=count_rate_limit,
            )

        if media_decision and not media_decision.allowed:
            bot_response = media_decision.response or MSG_MEDIA_UNSUPPORTED
            if is_media_without_text:
                router_media_meta = _set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="media_only",
                )
                trace_payload = {
                    "stage": "media",
                    "decision": "rejected",
                    "state": conversation.state,
                }
                trace_payload.update(router_media_meta)
                _record_decision_trace(conversation, trace_payload)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Media rejected response sent" if sent else "Media response failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

        storage_path = None
        if saved_message and isinstance(saved_message.message_metadata, dict):
            storage_path = (saved_message.message_metadata.get("media") or {}).get("storage_path")

        if media_policy and media_policy.get("store_media") and not storage_path:
            storage_result = await _store_media_locally(
                media=media_info,
                policy=media_policy,
                client_slug=client.name,
                conversation_id=conversation.id,
                message_id=message_id,
            )
            if storage_result.get("stored"):
                storage_path = storage_result.get("path")
            if saved_message:
                update_payload = {
                    "storage_path": storage_result.get("path"),
                    "stored": bool(storage_result.get("stored")),
                    "storage_error": storage_result.get("error"),
                    "size_bytes": storage_result.get("size_bytes") or media_info.size_bytes,
                    "sha256": storage_result.get("sha256"),
                }
                _update_message_media_metadata(saved_message, update_payload)

        media_response = None
        media_escalated = False
        media_text_placeholder = _is_placeholder_text(message_text)
        asr_failed = bool(asr_meta and asr_meta.get("asr_failed"))
        style_request = _is_style_reference_request(
            message_text,
            has_media=media_info.media_type == "photo",
        )
        style_reference_pending = None
        if conversation.state == ConversationState.BOT_ACTIVE.value and media_info.media_type == "photo":
            context = _get_conversation_context(conversation)
            style_reference_pending, style_pending_expired = _get_style_reference_pending(
                context,
                now=now,
            )
            if style_pending_expired:
                context = _set_style_reference_pending(context, None)
                _set_conversation_context(conversation, context)
                style_reference_pending = None
            if style_reference_pending and style_reference_pending.get("reason") == "text_only":
                style_request = True

        if conversation.state == ConversationState.BOT_ACTIVE.value:
            if media_text_placeholder and _is_voice_note(media_info) and asr_failed:
                media_response = MSG_MEDIA_TRANSCRIPT_FAILED
            elif style_request and media_info.media_type == "photo":
                handover_text = message_text.strip()
                if media_text_placeholder:
                    handover_text = "Клиент отправил фото/референс."
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=handover_text,
                    source="media_style",
                    intent="style_reference",
                )
                if reused:
                    result_message = (
                        f"Style reference reuse, telegram={'sent' if telegram_sent else 'failed'}"
                    )
                    media_escalated = True
                    media_response = MSG_MEDIA_STYLE_REFERENCE
                else:
                    _record_escalation_metric("media")
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=handover_text,
                        trigger_type="media",
                        trigger_value="style_reference",
                    )
                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=handover_text,
                        )
                        result_message = (
                            f"Style reference escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        )
                        media_escalated = True
                        media_response = MSG_MEDIA_STYLE_REFERENCE
                    else:
                        bot_response = MSG_AI_ERROR
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "Style reference escalation failed" if sent else "Media escalation response failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                if style_reference_pending:
                    context = _get_conversation_context(conversation)
                    context = _set_style_reference_pending(context, None)
                    _set_conversation_context(conversation, context)
            elif style_request:
                media_response = MSG_STYLE_REFERENCE_NEED_MEDIA
            elif media_text_placeholder:
                if media_info.media_type == "document":
                    media_response = MSG_MEDIA_DOC_RECEIVED
                else:
                    media_response = MSG_MEDIA_RECEIVED
                if media_info.media_type == "photo" and not style_request:
                    pending_payload = {
                        "reason": "photo_only",
                        "created_at": now.isoformat(),
                        "expires_at": (now + timedelta(minutes=STYLE_REFERENCE_PENDING_TTL_MINUTES)).isoformat(),
                        "media": {
                            "media_type": media_info.media_type,
                            "raw_type": media_info.raw_type,
                            "mime": media_info.mime,
                            "size_bytes": media_info.size_bytes,
                            "duration_seconds": media_info.duration_seconds,
                            "url": media_info.url,
                            "file_name": media_info.file_name,
                            "caption": media_info.caption,
                            "ptt": media_info.is_ptt,
                        },
                        "storage_path": storage_path,
                    }
                    context = _get_conversation_context(conversation)
                    context = _set_style_reference_pending(context, pending_payload)
                    _set_conversation_context(conversation, context)
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "style_reference",
                            "decision": "photo_pending",
                            "state": conversation.state,
                        },
                    )

        elif conversation.state == ConversationState.PENDING.value:
            if media_text_placeholder and _is_voice_note(media_info) and asr_failed:
                media_response = MSG_MEDIA_TRANSCRIPT_FAILED
            elif style_request:
                media_response = MSG_STYLE_REFERENCE_NEED_MEDIA
            elif media_text_placeholder:
                media_response = MSG_MEDIA_PENDING_NEED_TEXT

        if (
            (conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value] or media_escalated)
            and conversation.telegram_topic_id
            and not (metadata and metadata.forwarded_to_telegram)
            and (media_policy or {}).get("forward_to_telegram")
        ):
            bot_token, chat_id = get_telegram_credentials(db, client.id)
            if bot_token and chat_id:
                telegram = TelegramService(bot_token)
                caption = _build_media_caption(message_text, media_info)
                forward_result = _send_telegram_media(
                    telegram=telegram,
                    chat_id=chat_id,
                    topic_id=conversation.telegram_topic_id,
                    media=media_info,
                    caption=caption,
                    stored_path=storage_path,
                )
                if forward_result.get("ok"):
                    if metadata:
                        metadata.forwarded_to_telegram = True
                    if saved_message:
                        _update_message_media_metadata(saved_message, {"forwarded_to_telegram": True})
                else:
                    logger.warning(
                        "Media forward to Telegram failed",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                                "error": forward_result.get("description") or forward_result.get("error"),
                            }
                        },
                    )

        if media_response is not None and conversation.state != ConversationState.MANAGER_ACTIVE.value:
            bot_response = media_response
            if is_media_without_text:
                router_media_meta = _set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="media_only",
                )
                trace_payload = {
                    "stage": "media",
                    "decision": "media_only",
                    "state": conversation.state,
                }
                trace_payload.update(router_media_meta)
                _record_decision_trace(conversation, trace_payload)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Media response sent" if sent else "Media response failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    # 9.0 Debounce bursty inputs: only the latest message triggers bot logic.
    (
        debounce_response,
        message_text,
        batch_messages,
        append_user_message,
        now,
    ) = await _handle_debounce_gate(
        db=db,
        client=client,
        conversation=conversation,
        message_text=message_text,
        message_id=message_id,
        remote_jid=remote_jid,
        batch_messages=batch_messages,
        batch_messages_provided=batch_messages_provided,
        payload_client_slug=payload.client_slug,
        now=now,
    )
    if debounce_response:
        return debounce_response

    # 9.02 Pending handover confirmation before other flows.
    handover_response = _handle_handover_confirmation_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        now=now,
        send_and_save=_send_and_save,
        record_escalation_metric=_record_escalation_metric,
    )
    if handover_response:
        return handover_response

    batch_messages = _coerce_batch_messages(message_text, batch_messages)
    booking_messages = batch_messages
    booking_context = None
    booking = None
    booking_active = False
    opt_out_in_batch = any(is_opt_out_message(msg) for msg in booking_messages)
    if reengage_override:
        opt_out_in_batch = False
    bypass_domain_flows = opt_out_in_batch
    if routing["allow_booking_flow"]:
        booking_context = _get_conversation_context(conversation)
        booking = _get_booking_context(booking_context)
        booking_active = bool(booking.get("active"))
        if opt_out_in_batch and booking_active:
            booking_context = _set_booking_context(booking_context, {"active": False})
            booking_context = _clear_service_hint(booking_context)
            _set_conversation_context(conversation, booking_context)
            booking_active = False
    booking_block_meta = None
    if not bypass_domain_flows:
        booking_signal, booking_block_meta = _evaluate_booking_signal(
            booking_messages,
            client_slug=payload.client_slug,
            message_text=message_text,
            relative_base=sim_now,
        )
    else:
        booking_signal = False

    # 6.95 Hard-LAW pre-LLM gate (policy-pack driven).
    hard_law_response = _handle_hard_law_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        policy_pack=policy_pack,
        bypass_domain_flows=bypass_domain_flows,
        routing=routing,
        policy_type=policy_type,
        policy_source=policy_source,
        policy_pack_missing=policy_pack_missing,
        client_slug=payload.client_slug,
        send_and_save=_send_and_save,
        record_policy_count=record_policy_count,
        record_escalation_metric=_record_escalation_metric,
        log_timing=_log_timing,
    )
    if hard_law_response:
        return hard_law_response
    intent_decomp_state = _run_intent_decomposition(
        conversation=conversation,
        saved_message=saved_message,
        message_text=message_text,
        expected_reply_type=expected_reply_type,
        expected_reply_reason=expected_reply_reason,
        intent_queue=intent_queue,
        class_carryover=class_carryover,
        routing=routing,
        bypass_domain_flows=bypass_domain_flows,
        booking_signal=booking_signal,
        booking_block_meta=booking_block_meta,
        booking_context=booking_context,
        booking=booking,
        booking_active=booking_active,
        expected_reply_shortcircuit=expected_reply_shortcircuit,
        context=context,
        context_manager=context_manager,
        current_goal=current_goal,
        consult_context=consult_context,
        message_count=message_count,
        now=now,
        client_slug=payload.client_slug,
        timing_context=timing_context,
    )
    intent_decomp_payload = intent_decomp_state.intent_decomp_payload
    intent_decomp_intents = intent_decomp_state.intent_decomp_intents
    intent_decomp_primary = intent_decomp_state.intent_decomp_primary
    intent_decomp_secondary = intent_decomp_state.intent_decomp_secondary
    intent_decomp_service_query = intent_decomp_state.intent_decomp_service_query
    intent_decomp_multi = intent_decomp_state.intent_decomp_multi
    intent_decomp_used = intent_decomp_state.intent_decomp_used
    intent_decomp_set = intent_decomp_state.intent_decomp_set
    consult_intent = intent_decomp_state.consult_intent
    consult_topic = intent_decomp_state.consult_topic
    consult_question = intent_decomp_state.consult_question
    intent_queue_choice = intent_decomp_state.intent_queue_choice
    pending_intent_queue = intent_decomp_state.pending_intent_queue
    pending_expected_reply_type = intent_decomp_state.pending_expected_reply_type
    intent_queue_expected_next = intent_decomp_state.intent_queue_expected_next
    intent_queue_event = intent_decomp_state.intent_queue_event
    info_class_intents = intent_decomp_state.info_class_intents
    info_class_meta = intent_decomp_state.info_class_meta
    basic_info_message = intent_decomp_state.basic_info_message
    allow_service_carryover = intent_decomp_state.allow_service_carryover
    consult_return_pending = intent_decomp_state.consult_return_pending
    consult_return_reason = intent_decomp_state.consult_return_reason
    consult_return_prompt = intent_decomp_state.consult_return_prompt
    booking_signal = intent_decomp_state.booking_signal
    booking_block_meta = intent_decomp_state.booking_block_meta
    booking_wants_flow = intent_decomp_state.booking_wants_flow
    booking_blocked = intent_decomp_state.booking_blocked
    booking_active = intent_decomp_state.booking_active
    booking_context = intent_decomp_state.booking_context
    booking = intent_decomp_state.booking
    class_carryover = intent_decomp_state.class_carryover
    context = intent_decomp_state.context
    context_manager = intent_decomp_state.context_manager
    current_goal = intent_decomp_state.current_goal
    intent_queue_followup = None
    intent_queue_intents: list[str] = []

    multi_intent_primary = None
    multi_intent_secondary: list[str] = []
    multi_intent_followup = None
    multi_intent_booking_followup = None
    multi_intent_other_followup = None

    opt_out_response = _handle_opt_out_mute_gate(
        db=db,
        client_id=client.id,
        conversation=conversation,
        saved_message=saved_message,
        opt_out_in_batch=opt_out_in_batch,
        booking_signal=booking_signal,
        now=now,
        send_and_save=_send_and_save,
    )
    if opt_out_response:
        return opt_out_response

    # 9.03 Policy escalation gate (policy-pack keywords + intent fallback).
    policy_response = _handle_policy_escalation_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        policy_pack=policy_pack,
        hard_law_sections=hard_law_sections,
        bypass_domain_flows=bypass_domain_flows,
        routing=routing,
        policy_type=policy_type,
        policy_source=policy_source,
        policy_pack_missing=policy_pack_missing,
        booking_wants_flow=booking_wants_flow,
        intent_hints=intent_decomp_intents if policy_pack else None,
        consult_intent=consult_intent,
        current_goal=current_goal,
        multi_intent_other_followup=multi_intent_other_followup,
        client_slug=payload.client_slug,
        send_and_save=_send_and_save,
        record_policy_count=record_policy_count,
        record_escalation_metric=_record_escalation_metric,
        log_timing=_log_timing,
    )
    if policy_response:
        return policy_response

    _record_llm_budget_trace = functools.partial(
        _record_llm_budget_trace_helper,
        conversation=conversation,
        timing_context=timing_context,
    )
    router_state = _build_router_state(
        routing=routing,
        bypass_domain_flows=bypass_domain_flows,
        message_text=message_text,
        booking_wants_flow=booking_wants_flow,
        expected_reply_shortcircuit=expected_reply_shortcircuit,
        expected_reply_type=expected_reply_type,
        class_carryover=class_carryover,
        client_slug=payload.client_slug,
        client_config=client.config if client else None,
        timing_context=timing_context,
        intent_decomp_set=intent_decomp_set,
        booking_signal=booking_signal,
        record_llm_budget_trace=_record_llm_budget_trace,
    )

    early_domain_intent = DomainIntent.UNKNOWN
    early_domain_meta: dict = {}
    early_out_of_domain = False
    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and not bypass_domain_flows
        and message_text
    ):
        early_info_intents, early_info_meta = _detect_info_class_intents(
            message_text,
            intent_decomp_set=intent_decomp_set,
        )
        if not (
            is_greeting_message(message_text)
            or is_thanks_message(message_text)
            or is_acknowledgement_message(message_text)
            or is_low_signal_message(message_text)
            or is_bot_status_question(message_text)
            or is_human_request_message(message_text)
            or is_opt_out_message(message_text)
        ):
            early_domain_intent, _, _, early_domain_meta = classify_domain_with_scores(
                message_text, client.config if client else None
            )
            out_hits = int(early_domain_meta.get("out_hits") or 0)
            strict_in_hits = int(early_domain_meta.get("strict_in_hits") or 0)
            early_in_signals = bool(
                strict_in_hits > 0 or booking_signal or booking_wants_flow or early_info_intents
            )
            early_out_of_domain = bool(out_hits > 0 and not early_in_signals)
            if early_out_of_domain and _is_short_reply(message_text):
                intent_hint = classify_intent(message_text, timing_context=timing_context)
                if intent_hint in {Intent.GREETING, Intent.THANKS, Intent.QUESTION}:
                    if isinstance(timing_context, dict):
                        timing_context["short_intent_hint"] = intent_hint.value
                    early_out_of_domain = False

    expected_reply_off_topic = (
        expected_reply_type == EXPECTED_REPLY_SERVICE
        and expected_reply_matched is False
        and not expected_reply_blocked_by_info
        and message_text
        and (early_out_of_domain or is_frustration_message(message_text))
        and not consult_intent
        and not booking_signal
        and not booking_wants_flow
        and not (
            isinstance(booking_block_meta, dict)
            and booking_block_meta.get("booking_blocked_reason") == "procedure_combo"
        )
    )
    if expected_reply_off_topic:
        bot_response = MSG_EXPECTED_SERVICE_OFF_TOPIC
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "out_of_domain",
                "decision": "expected_reply_off_topic",
                "state": conversation.state,
                "domain_intent": early_domain_intent.value,
                "out_hits": early_domain_meta.get("out_hits"),
                "strict_in_hits": early_domain_meta.get("strict_in_hits"),
                "info_intents": sorted(early_info_intents),
                "expected_reply_type": expected_reply_type,
                "expected_reply_reason": "off_topic",
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="out_of_domain",
            intent="out_of_domain",
            source="domain_router" if early_out_of_domain else "question_contract",
            fast_intent=False,
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "expected_reply_type": expected_reply_type,
                    "expected_reply_matched": False,
                    "expected_reply_reason": "off_topic",
                },
            )
        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        result_message = (
            "Expected reply off-topic response sent"
            if sent
            else "Expected reply off-topic response failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    in_domain_signal = bool(int(early_domain_meta.get("strict_in_hits") or 0) > 0)
    if early_domain_intent == DomainIntent.IN_DOMAIN:
        in_domain_signal = True
    expected_reply_invalid_choice = (
        expected_reply_type == EXPECTED_REPLY_SERVICE
        and expected_reply_matched is False
        and not expected_reply_blocked_by_info
        and message_text
        and not in_domain_signal
        and not consult_intent
        and not booking_signal
        and not booking_wants_flow
        and not (
            isinstance(booking_block_meta, dict)
            and booking_block_meta.get("booking_blocked_reason") == "procedure_combo"
        )
    )
    if expected_reply_invalid_choice:
        semantic_match = semantic_service_match(message_text, payload.client_slug)
        if not semantic_match:
            clarify_intent = current_goal or "info"
            context = _get_conversation_context(conversation)
            context_manager = _get_context_manager(context)
            if _should_escalate_for_clarify(context_manager, clarify_intent):
                clarify_count, _ = _get_clarify_attempt_state(context_manager, clarify_intent)
                clarify_reason = "consult_no_service" if clarify_intent == "consult" else "invalid_choice"
                _record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="clarify_limit",
                    updates={
                        "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                        "clarify_reason": clarify_reason,
                        "clarify_limit": True,
                    },
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "expected_reply_type": expected_reply_type,
                            "expected_reply_matched": False,
                            "expected_reply_reason": "invalid_choice",
                        },
                    )
                if clarify_intent == "consult":
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "consult_flow",
                            "decision": "consult_escalate",
                            "reason": "consult_no_service",
                            "state": conversation.state,
                            "expected_reply_type": expected_reply_type,
                        },
                    )
                    return _handle_clarify_limit_escalation(
                        db=db,
                        conversation=conversation,
                        user=user,
                        message_text=message_text,
                        saved_message=saved_message,
                        source="consult",
                        allow_handover=routing.get("allow_handover_create", False),
                        escalation_intent="consult_no_service",
                        send_response=_send_response,
                        finalize_response=_finalize_bot_response,
                    )
                return _handle_clarify_limit_escalation(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message_text=message_text,
                    saved_message=saved_message,
                    source="question_contract",
                    allow_handover=routing.get("allow_handover_create", False),
                    send_response=_send_response,
                    finalize_response=_finalize_bot_response,
                )
            _register_clarify_attempt(
                conversation=conversation,
                saved_message=saved_message,
                intent=clarify_intent,
                now=now,
                reason="invalid_choice",
            )
            context = _get_conversation_context(conversation)
            context = _set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=EXPECTED_REPLY_SERVICE,
                reason="invalid_choice",
                now=now,
            )
            bot_response = MSG_EXPECTED_SERVICE_OFF_TOPIC
            _reset_low_confidence_retry(conversation)
            _record_decision_trace(
                conversation,
                {
                    "stage": "question_contract",
                    "decision": "invalid_choice",
                    "state": conversation.state,
                    "expected_reply_type": expected_reply_type,
                    "expected_reply_reason": "invalid_choice",
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="reply",
                intent="service_clarify",
                source="question_contract",
                fast_intent=False,
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "expected_reply_type": expected_reply_type,
                        "expected_reply_matched": False,
                        "expected_reply_reason": "invalid_choice",
                    },
                )
            bot_response, sent = _send_and_save(bot_response)
            result_message = (
                "Expected reply invalid choice response sent"
                if sent
                else "Expected reply invalid choice response failed"
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    if early_out_of_domain:
        bot_response = OUT_OF_DOMAIN_RESPONSE
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "out_of_domain",
                "decision": "early_block",
                "state": conversation.state,
                "domain_intent": early_domain_intent.value,
                "out_hits": early_domain_meta.get("out_hits"),
                "strict_in_hits": early_domain_meta.get("strict_in_hits"),
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="out_of_domain",
            intent="out_of_domain",
            source="domain_router",
            fast_intent=False,
        )
        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        result_message = "Out-of-domain early response sent" if sent else "Out-of-domain early response failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    promotions_router_class = None
    router_used = bool(router_state.get("used")) if isinstance(router_state, dict) else False
    router_output = router_state.get("output") if isinstance(router_state, dict) else None
    if isinstance(router_output, dict):
        raw_class = router_output.get("class")
        if isinstance(raw_class, str):
            promotions_router_class = _normalize_class_name(raw_class)
    discount_signal = _looks_like_promotions_request(
        message_text,
        policy_type=policy_type,
        policy_pack=policy_pack,
        client_slug=payload.client_slug,
    )
    promotions_trigger = False
    if router_used and promotions_router_class in {"promotions", "discounts"}:
        promotions_trigger = True
    if discount_signal:
        promotions_trigger = True

    if (
        promotions_trigger
        and routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
    ):
        class_router_result = _resolve_class_router_result(
            info_intents=info_class_intents,
            info_meta=info_class_meta,
            booking_signal=booking_signal,
            class_carryover=class_carryover,
            domain_intent=DomainIntent.UNKNOWN,
            domain_meta=None,
            router_state=router_state,
        )
        if discount_signal:
            class_router_result = dict(class_router_result)
            classes = list(class_router_result.get("classes") or [])
            if "promotions" not in classes and "discounts" not in classes:
                classes.insert(0, "promotions")
            class_router_result["classes"] = classes
            in_signals = list(class_router_result.get("in_signals") or [])
            if "promotions_signal" not in in_signals:
                in_signals.append("promotions_signal")
            class_router_result["in_signals"] = in_signals

        promotion_intent = _detect_promotion_intent(_normalize_text(message_text))
        promo_reply = None
        if promotion_intent == "promotion_birthday":
            promo_reply = format_reply_from_truth(
                "promotions",
                {"promotion_intent": promotion_intent},
                client_slug=payload.client_slug,
            )
        if promo_reply:
            decision = DemoSalonDecision(
                action="reply",
                response=promo_reply,
                intent="promotions",
            )
        else:
            discounts_available = _has_discount_policy_rules(
                policy_pack=policy_pack,
                policy_type=policy_type,
            )
            discounts_reply = (
                _format_discounts_policy_reply(
                    policy_pack=policy_pack,
                    policy_type=policy_type,
                )
                if discounts_available
                else None
            )
            if discounts_reply:
                decision = DemoSalonDecision(
                    action="reply",
                    response=discounts_reply,
                    intent="discounts",
                )
            else:
                decision = DemoSalonDecision(
                    action="escalate",
                    response=MSG_ESCALATED,
                    intent="discounts",
                )

        bot_response = decision.response or MSG_ESCALATED
        followup_intents: list[str] = []
        booking_followup = bool(booking_signal or "booking" in intent_decomp_set)
        if not booking_followup and message_text and _is_booking_request(message_text):
            booking_followup = True
        if booking_followup:
            followup_intents.append("booking")
        for intent_name in ("location", "hours"):
            if intent_name in info_class_intents and intent_name not in followup_intents:
                followup_intents.append(intent_name)
        followup_prompt = None
        queue_set = False
        if followup_intents:
            if expected_reply_type is None and pending_intent_queue is None and not intent_queue_event:
                context = _get_conversation_context(conversation)
                context = _set_intent_queue(context, followup_intents)
                context = _set_expected_reply_type(context, EXPECTED_REPLY_INTENT_CHOICE)
                _set_conversation_context(conversation, context)
                followup_prompt = _format_intent_queue_prompt(followup_intents)
                queue_set = True
            else:
                followup_prompt = _format_multi_intent_followup("discounts", followup_intents)
        if followup_prompt:
            bot_response = _combine_sidecar(bot_response, followup_prompt)

        _reset_low_confidence_retry(conversation)
        record_policy_count(payload.client_slug, "discounts")

        result_message = "Policy discounts reply sent"
        if decision.action == "escalate":
            _, reused, telegram_sent = _reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source=policy_source,
                intent=decision.intent,
            )
            if reused:
                result_message = f"Policy discounts reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == ConversationState.BOT_ACTIVE.value and routing.get("allow_handover_create", False):
                _record_escalation_metric("intent")
                result = escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value=decision.intent or "discounts",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"Policy discounts escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"Policy discounts escalation failed: {result.error}"
            else:
                result_message = "Policy discounts escalation skipped (already pending)"

        router_gate_meta = _set_router_observability(
            saved_message,
            eligible=False,
            reason="policy_gate",
        )
        trace_payload = {
            "stage": "policy_gate",
            "decision": decision.action,
            "intent": decision.intent,
            "state": conversation.state,
            "policy_type": policy_type,
            "policy_gate": "discounts",
            "policy_section": "discounts",
            "source": policy_source,
            "class_router": class_router_result,
        }
        discounts_policy = policy_pack.get("discounts") if isinstance(policy_pack, dict) else None
        risk_level = discounts_policy.get("risk_level") if isinstance(discounts_policy, dict) else None
        if isinstance(risk_level, str) and risk_level:
            trace_payload["risk_level"] = risk_level
        trace_payload.update(router_gate_meta)
        if followup_intents:
            trace_payload["followup_intents"] = followup_intents
        _record_decision_trace(conversation, trace_payload)
        _record_message_decision_meta(
            saved_message,
            action=decision.action,
            intent=decision.intent,
            source=policy_source,
            fast_intent=False,
        )
        if saved_message:
            meta_updates = {
                "class_router": class_router_result,
                "policy_gate": "discounts",
                "policy_section": "discounts",
                "source": policy_source,
            }
            if policy_pack_missing:
                meta_updates["policy_pack_missing"] = True
            if isinstance(risk_level, str) and risk_level:
                meta_updates["risk_level"] = risk_level
            if queue_set:
                meta_updates["intent_queue"] = followup_intents
                meta_updates["expected_reply_type"] = EXPECTED_REPLY_INTENT_CHOICE
            meta_updates.update(_controller_meta_updates_from_class_router(class_router_result))
            _update_message_decision_metadata(saved_message, meta_updates)

        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if intent_queue_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "intent_queue",
                **intent_queue_event,
            },
        )
        if intent_queue_event.get("decision") == "no_match" and intent_queue:
            intent_queue_intents = intent_queue
            intent_queue_followup = _format_intent_queue_prompt(intent_queue)
        if saved_message:
            updates = {"intent_queue_choice": intent_queue_choice}
            if intent_queue_event.get("decision") == "dequeue":
                updates["intent_queue_remaining"] = pending_intent_queue or []
                updates["expected_reply_matched"] = True
                updates["expected_reply_choice"] = intent_queue_choice
                updates["expected_reply_next"] = intent_queue_expected_next
            else:
                updates["intent_queue_missed"] = True
                updates["expected_reply_matched"] = False
            _update_message_decision_metadata(saved_message, updates)

    if (
        intent_queue_choice
        and expected_reply_type == EXPECTED_REPLY_INTENT_CHOICE
        and intent_queue_choice in INFO_INTENTS
        and routing["allow_bot_reply"]
        and not bypass_domain_flows
    ):
        info_service_query = intent_decomp_service_query
        if not info_service_query and intent_queue_choice in {"pricing", "duration"}:
            info_service_query = _extract_service_hint(message_text, payload.client_slug)
        if (
            not info_service_query
            and intent_queue_choice in {"pricing", "duration"}
            and allow_service_carryover
        ):
            carryover = _get_service_carryover(context_manager, message_count=message_count)
            if carryover:
                info_service_query = carryover.get("service_query")

        info_reply, info_meta = _build_info_intent_reply(
            intent_queue_choice,
            service_query=info_service_query,
            client_slug=payload.client_slug,
            message_text=message_text,
        )
        info_reply = info_reply.strip() if isinstance(info_reply, str) else None
        if info_reply:
            guard_response = _maybe_apply_fact_guard(
                decision_meta=info_meta if isinstance(info_meta, dict) else None,
                intent=intent_queue_choice,
                source="intent_queue",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return guard_response
            remaining_queue = (
                pending_intent_queue
                if pending_intent_queue is not None
                else [intent for intent in intent_queue if intent != intent_queue_choice]
            )
            expected_next = EXPECTED_REPLY_INTENT_CHOICE if remaining_queue else None
            context = _get_conversation_context(conversation)
            context = _set_intent_queue(context, remaining_queue or None)
            context = _set_expected_reply_type(context, expected_next)
            _set_conversation_context(conversation, context)
            followup = _format_intent_queue_prompt(remaining_queue)
            bot_response = info_reply
            if followup:
                bot_response = f"{bot_response}\n\n{followup}"
            composer_meta = None
            bot_response, composer_meta = _compose_fact_response(
                bot_response,
                client_slug=payload.client_slug,
                conversation_id=str(conversation.id),
                response_tag="intent_queue",
                conversation_state=conversation.state,
                allow_booking_flow=routing["allow_booking_flow"],
                has_followup=bool(followup),
            )
            bot_response = _maybe_apply_consult_return(
                conversation=conversation,
                saved_message=saved_message,
                bot_response=bot_response,
                consult_return_pending=consult_return_pending,
                consult_return_prompt=consult_return_prompt,
                consult_context=consult_context,
                reason=consult_return_reason or "intent_queue_info",
            )
            _reset_low_confidence_retry(conversation)
            trace_payload = {
                "stage": "intent_queue",
                "decision": "info_reply",
                "state": conversation.state,
                "chosen_intent": intent_queue_choice,
                "remaining_queue": remaining_queue,
                "expected_reply_next": expected_next,
            }
            if isinstance(info_meta, dict) and info_meta:
                trace_payload.update(info_meta)
            if composer_meta:
                trace_payload.update(composer_meta)
            _record_decision_trace(conversation, trace_payload)
            _record_message_decision_meta(
                saved_message,
                action="reply",
                intent=intent_queue_choice,
                source="intent_queue",
                fast_intent=False,
            )
            if saved_message and isinstance(info_meta, dict) and info_meta:
                _update_message_decision_metadata(saved_message, info_meta)
            if saved_message and composer_meta:
                _update_message_decision_metadata(saved_message, composer_meta)
            _maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=[intent_queue_choice],
                info_meta=info_meta,
                message_count=message_count,
                reason="intent_queue",
            )
            _maybe_store_service_carryover(
                conversation=conversation,
                service_meta=info_meta if isinstance(info_meta, dict) else None,
                intent=intent_queue_choice,
                message_count=message_count,
                reason="intent_queue_choice",
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = (
                "Intent queue info reply sent" if sent else "Intent queue info reply failed"
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    if (
        intent_queue_choice == "booking"
        and expected_reply_type == EXPECTED_REPLY_INTENT_CHOICE
        and routing["allow_booking_flow"]
        and not bypass_domain_flows
    ):
        context = _get_conversation_context(conversation)
        context = _set_intent_queue(context, None)
        context_manager = _get_context_manager(context)
        booking_state = _get_booking_context(context)
        booking_state = dict(booking_state)
        if not booking_state.get("active"):
            booking_state["active"] = True
            booking_state["started_at"] = now.isoformat()
        booking_state = _update_booking_from_messages(
            booking_state,
            booking_messages,
            client_slug=payload.client_slug,
        )
        if not booking_state.get("service"):
            service_hint = _get_recent_service_hint(context, now)
            if service_hint:
                booking_state["service"] = service_hint
                context = _clear_service_hint(context)
        if not booking_state.get("service") and allow_service_carryover:
            carryover = _get_service_carryover(context_manager, message_count=message_count)
            if carryover:
                booking_state["service"] = carryover.get("service_query")
        refusal_flags = context_manager.get("refusal_flags") if isinstance(context_manager, dict) else None
        booking_state, prompt = _next_booking_prompt(booking_state, refusal_flags=refusal_flags)
        context = _set_booking_context(context, booking_state)
        _set_conversation_context(conversation, context)
        booking_expected = _expected_reply_for_booking_question(booking_state.get("last_question"))
        if prompt and booking_expected:
            context = _set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=booking_expected,
                reason="booking_prompt",
                now=now,
            )
        _record_decision_trace(
            conversation,
            {
                "stage": "booking",
                "decision": "prompt",
                "state": conversation.state,
                "missing_slot": booking_state.get("last_question"),
                "source": "intent_queue",
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="booking_prompt",
            intent="booking",
            source="intent_queue",
            fast_intent=False,
        )
        bot_response = prompt or MSG_BOOKING_ASK_DATETIME
        bot_response = _maybe_apply_consult_return(
            conversation=conversation,
            saved_message=saved_message,
            bot_response=bot_response,
            consult_return_pending=consult_return_pending,
            consult_return_prompt=consult_return_prompt,
            consult_context=consult_context,
            reason=consult_return_reason or "intent_queue_booking",
        )
        _reset_low_confidence_retry(conversation)
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Intent queue booking prompt sent" if sent else "Intent queue booking prompt failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if (
        intent_decomp_used
        and expected_reply_type is None
        and not intent_queue_event
        and pending_intent_queue is None
        and routing["allow_bot_reply"]
        and routing["allow_truth_gate_reply"]
        and not bypass_domain_flows
        and message_text
    ):
        combined_intents: list[str] = []
        seen_intents: set[str] = set()
        for intent_name in intent_decomp_intents:
            normalized = intent_name.strip().casefold()
            if not normalized or normalized in seen_intents:
                continue
            combined_intents.append(normalized)
            seen_intents.add(normalized)

        truth_gate_intents: list[str] = []
        if "booking" in intent_decomp_set:
            truth_gate_intents = _extract_truth_gate_info_intents(
                message_text,
                policy_handler=policy_handler,
                policy_type=policy_type,
                client_slug=payload.client_slug,
                intent_decomp=intent_decomp_payload,
            )
        for intent_name in truth_gate_intents:
            if intent_name not in seen_intents:
                combined_intents.append(intent_name)
                seen_intents.add(intent_name)

        combined_set = set(combined_intents)
        info_intents = [intent for intent in combined_intents if intent in INFO_INTENTS]
        info_intent_set = set(info_intents)
        should_defer_booking = (
            "booking" in combined_set
            and info_intent_set
            and (len(info_intent_set) >= 2 or len(combined_set) >= 3)
        )
        if should_defer_booking:
            info_service_query = intent_decomp_service_query
            if not info_service_query and {"pricing", "duration"} & info_intent_set:
                info_service_query = _extract_service_hint(message_text, payload.client_slug)
            priority = (
                INFO_INTENT_PRIORITY_SERVICE
                if info_service_query
                else INFO_INTENT_PRIORITY_GENERIC
            )
            answer_intents: list[str] = []
            for intent_name in priority:
                if intent_name in info_intent_set and intent_name not in answer_intents:
                    answer_intents.append(intent_name)
                if len(answer_intents) >= 2:
                    break
            if not answer_intents:
                answer_intents = info_intents[:2]

            replies: list[str] = []
            seen_replies: set[str] = set()
            answered_intents: list[str] = []
            info_meta: dict = {}
            service_meta: dict | None = None
            for intent_name in answer_intents:
                reply, meta = _build_info_intent_reply(
                    intent_name,
                    service_query=info_service_query,
                    client_slug=payload.client_slug,
                    message_text=message_text,
                )
                if isinstance(reply, str):
                    reply = reply.strip()
                    if reply and reply not in seen_replies:
                        replies.append(reply)
                        seen_replies.add(reply)
                        answered_intents.append(intent_name)
                if isinstance(meta, dict) and meta:
                    info_meta.update(meta)
                    service_meta = dict(info_meta)
            if replies:
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=info_meta if info_meta else None,
                    intent="multi_intent_info",
                    source="intent_queue",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
                answered_set = set(answered_intents)
                remaining_queue = [
                    intent for intent in combined_intents if intent not in answered_set
                ]
                context = _get_conversation_context(conversation)
                expected_next = EXPECTED_REPLY_INTENT_CHOICE if remaining_queue else None
                context = _set_intent_queue(context, remaining_queue or None)
                context = _set_expected_reply_type(context, expected_next)
                _set_conversation_context(conversation, context)
                followup = _format_intent_queue_prompt(remaining_queue)
                bot_response = "\n\n".join(replies)
                if followup:
                    bot_response = f"{bot_response}\n\n{followup}"
                _reset_low_confidence_retry(conversation)
                trace_payload = {
                    "stage": "intent_queue",
                    "decision": "defer_booking",
                    "state": conversation.state,
                    "combined_intents": combined_intents,
                    "info_intents": answered_intents,
                    "intent_queue": remaining_queue,
                    "expected_reply_type": expected_next,
                }
                trace_payload.update(info_meta)
                _record_decision_trace(conversation, trace_payload)
                _record_message_decision_meta(
                    saved_message,
                    action="reply",
                    intent="multi_intent_info",
                    source="intent_queue",
                    fast_intent=False,
                )
                if saved_message:
                    updates = {
                        "combined_intents": combined_intents,
                        "info_intents_answered": answered_intents,
                        "intent_queue_reason": "defer_booking",
                        "booking_deferred": True,
                    }
                    if remaining_queue:
                        updates["intent_queue"] = remaining_queue
                        updates["expected_reply_type"] = expected_next
                    if info_meta:
                        updates.update(info_meta)
                    _update_message_decision_metadata(saved_message, updates)
                _maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=answered_intents,
                    info_meta=info_meta,
                    message_count=message_count,
                    reason="intent_queue",
                )
                if service_meta:
                    _maybe_store_service_carryover(
                        conversation=conversation,
                        service_meta=service_meta,
                        intent="multi_intent_info",
                        message_count=message_count,
                        reason="intent_queue",
                    )
                bot_response = _maybe_apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_pending=consult_return_pending,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "intent_queue_defer",
                )
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Intent queue info reply sent" if sent else "Intent queue info reply failed"
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

    if pending_intent_queue is not None:
        context = _get_conversation_context(conversation)
        context = _set_intent_queue(context, pending_intent_queue)
        context = _set_expected_reply_type(context, pending_expected_reply_type)
        _set_conversation_context(conversation, context)
        intent_queue_intents = pending_intent_queue
        if pending_intent_queue:
            intent_queue_followup = _format_intent_queue_prompt(pending_intent_queue)
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "intent_queue": pending_intent_queue,
                    "expected_reply_type": pending_expected_reply_type,
                },
            )
    elif intent_decomp_used and len(intent_decomp_intents) >= 3 and expected_reply_type != EXPECTED_REPLY_INTENT_CHOICE:
        queue = [intent for intent in intent_decomp_intents if intent != intent_decomp_primary]
        if queue:
            context = _get_conversation_context(conversation)
            context = _set_intent_queue(context, queue)
            context = _set_expected_reply_type(context, EXPECTED_REPLY_INTENT_CHOICE)
            _set_conversation_context(conversation, context)
            intent_queue_intents = queue
            intent_queue_followup = _format_intent_queue_prompt(queue)
            _record_decision_trace(
                conversation,
                {
                    "stage": "intent_queue",
                    "decision": "set",
                    "primary_intent": intent_decomp_primary,
                    "intent_queue": queue,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "intent_queue": queue,
                        "expected_reply_type": EXPECTED_REPLY_INTENT_CHOICE,
                    },
                )

    consult_result = _handle_consult_flow(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        client_slug=payload.client_slug,
        policy_type=policy_type,
        policy_pack=policy_pack,
        policy_handler=policy_handler,
        routing=routing,
        bypass_domain_flows=bypass_domain_flows,
        booking_wants_flow=booking_wants_flow,
        booking_active=booking_active,
        booking_signal=booking_signal,
        intent_decomp_set=intent_decomp_set,
        consult_intent=consult_intent,
        consult_topic=consult_topic,
        consult_question=consult_question,
        intent_decomp_payload=intent_decomp_payload,
        intent_decomp_service_query=intent_decomp_service_query,
        info_class_intents=info_class_intents,
        intent_queue_followup=intent_queue_followup,
        current_goal=current_goal,
        expected_reply_type=expected_reply_type,
        consult_context=consult_context,
        message_count=message_count,
        now=now,
        timing_context=timing_context,
        client_config=client.config if client else None,
        send_and_save=_send_and_save,
        record_escalation_metric=_record_escalation_metric,
    )
    consult_intent = consult_result.consult_intent
    consult_topic = consult_result.consult_topic
    consult_question = consult_result.consult_question
    intent_decomp_payload = consult_result.intent_decomp_payload
    if consult_result.response:
        return consult_result.response

    multi_intent_primary = None
    multi_intent_secondary: list[str] = []
    multi_intent_followup = None
    if intent_queue_followup:
        if isinstance(intent_decomp_primary, str):
            multi_intent_primary = intent_decomp_primary
        if intent_queue_intents:
            multi_intent_secondary = list(intent_queue_intents)
        multi_intent_followup = intent_queue_followup
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "multi_intent": True,
                    "primary_intent": multi_intent_primary,
                    "secondary_count": len(multi_intent_secondary),
                    "intent_queue": intent_queue_intents,
                },
            )
    elif (
        routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
        and len(message_text) >= MULTI_INTENT_MIN_CHARS
        and not booking_active
    ):
        multi_intent_payload = intent_decomp_payload
        if not multi_intent_payload:
            multi_intent_payload = detect_multi_intent(
                message_text,
                client_slug=payload.client_slug,
                timing_context=timing_context,
            )
        if isinstance(multi_intent_payload, dict) and multi_intent_payload.get("multi_intent") is True:
            primary = multi_intent_payload.get("primary_intent")
            secondary = multi_intent_payload.get("secondary_intents") or []
            if isinstance(primary, str):
                multi_intent_primary = primary
            if isinstance(secondary, list):
                multi_intent_secondary = [item for item in secondary if isinstance(item, str)]
            if multi_intent_primary:
                multi_intent_followup = _format_multi_intent_followup(
                    multi_intent_primary, multi_intent_secondary
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "multi_intent": True,
                            "primary_intent": multi_intent_primary,
                            "secondary_count": len(multi_intent_secondary),
                        },
                    )
                if booking_blocked:
                    booking_signal = False
                    booking_wants_flow = False

    multi_intent_booking_followup = None
    multi_intent_other_followup = None
    if multi_intent_followup:
        if multi_intent_primary == "booking":
            multi_intent_booking_followup = multi_intent_followup
        else:
            multi_intent_other_followup = multi_intent_followup

    booking_interrupt_response = _handle_booking_interrupt(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        client_slug=payload.client_slug,
        routing=routing,
        bypass_domain_flows=bypass_domain_flows,
        booking_wants_flow=booking_wants_flow,
        consult_intent=consult_intent,
        intent_decomp_used=intent_decomp_used,
        intent_decomp_set=intent_decomp_set,
        intent_decomp_payload=intent_decomp_payload,
        info_class_intents=info_class_intents,
        expected_reply_type=expected_reply_type,
        expected_reply_matched=expected_reply_matched,
        expected_reply_shortcircuit=expected_reply_shortcircuit,
        batch_non_booking_message=batch_non_booking_message,
        booking_messages=booking_messages,
        booking_context=booking_context,
        booking=booking,
        current_goal=current_goal,
        basic_info_message=basic_info_message,
        session_memory_reset_reason=session_memory_reset_reason,
        memory_expected_reply_type=memory_expected_reply_type,
        policy_handler=policy_handler,
        policy_type=policy_type,
        now=now,
        message_count=message_count,
        consult_return_pending=consult_return_pending,
        consult_return_prompt=consult_return_prompt,
        consult_context=consult_context,
        consult_return_reason=consult_return_reason,
        maybe_apply_fact_guard=_maybe_apply_fact_guard,
        send_and_save=_send_and_save,
        send_response=_send_response,
        finalize_response=_finalize_bot_response,
    )
    if booking_interrupt_response:
        return booking_interrupt_response

    booking_result = _handle_booking_flow(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        client_slug=payload.client_slug,
        routing=routing,
        bypass_domain_flows=bypass_domain_flows,
        booking_wants_flow=booking_wants_flow,
        booking_active=booking_active,
        booking_signal=booking_signal,
        booking_messages=booking_messages,
        booking_context=booking_context,
        booking=booking,
        expected_reply_type=expected_reply_type,
        expected_reply_matched=expected_reply_matched,
        basic_info_message=basic_info_message,
        session_memory_reset_reason=session_memory_reset_reason,
        memory_expected_reply_type=memory_expected_reply_type,
        policy_handler=policy_handler,
        policy_pack=policy_pack,
        now=now,
        message_count=message_count,
        multi_intent_booking_followup=multi_intent_booking_followup,
        consult_return_pending=consult_return_pending,
        consult_return_prompt=consult_return_prompt,
        consult_context=consult_context,
        consult_return_reason=consult_return_reason,
        send_and_save=_send_and_save,
        send_response=_send_response,
        finalize_response=_finalize_bot_response,
        log_timing=_log_timing,
        record_escalation_metric=_record_escalation_metric,
    )
    if booking_result.response:
        return booking_result.response
    if booking_result.booking_t0 is not None and not booking_result.booking_logged:
        _log_timing("booking_ms", (time.monotonic() - booking_result.booking_t0) * 1000)


    llm_primary_result = None
    llm_primary_failed = False
    llm_primary_reason = None
    skip_llm_primary = False
    force_truth_gate = False

    # 9.06 Fast intent (smalltalk) before LLM to avoid extra calls.
    fast_decision = None
    if routing["allow_bot_reply"]:
        fast_decision = _detect_fast_intent(
            message_text,
            policy_type=policy_type,
            booking_wants_flow=booking_wants_flow,
            bypass_domain_flows=bypass_domain_flows,
        )

    if fast_decision:
        bot_response = fast_decision.response
        _reset_low_confidence_retry(conversation)

        result_message = "Fast intent reply sent"
        if fast_decision.action == "smalltalk":
            result_message = "Fast intent smalltalk sent"

        _record_decision_trace(
            conversation,
            {
                "stage": "fast_intent",
                "decision": fast_decision.action,
                "intent": fast_decision.intent,
                "state": conversation.state,
                "booking_wants_flow": booking_wants_flow,
                "policy_type": policy_type,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action=fast_decision.action,
            intent=fast_decision.intent,
            source="fast_intent",
            fast_intent=True,
        )
        bot_response, sent = _send_and_save(bot_response)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if (
        expected_reply_shortcircuit
        and routing.get("allow_bot_reply")
        and not bypass_domain_flows
        and current_goal != "booking"
    ):
        carryover_intents = []
        if isinstance(class_carryover, dict):
            carryover_intents = class_carryover.get("intents") or []
        carryover_intents = [
            intent.strip().casefold()
            for intent in carryover_intents
            if isinstance(intent, str) and intent.strip()
        ]
        followup_intent = None
        if "pricing" in carryover_intents:
            followup_intent = "pricing"
        elif "duration" in carryover_intents:
            followup_intent = "duration"
        if followup_intent:
            service_carryover = _get_service_carryover(
                context_manager, message_count=message_count
            )
            service_query = None
            if isinstance(service_carryover, dict):
                service_query = service_carryover.get("service_query")
            if not isinstance(service_query, str) or not service_query.strip():
                service_context = _get_conversation_context(conversation)
                service_query = _get_recent_service_hint(service_context, now)
            if (
                (not isinstance(service_query, str) or not service_query.strip())
                and saved_message
                and isinstance(saved_message.message_metadata, dict)
            ):
                decision_meta = saved_message.message_metadata.get("decision_meta")
                if isinstance(decision_meta, dict):
                    candidate = decision_meta.get("expected_reply_value")
                    if isinstance(candidate, str) and candidate.strip():
                        service_query = candidate.strip()
            reply, reply_meta = _build_info_intent_reply(
                followup_intent,
                service_query=service_query if isinstance(service_query, str) else None,
                client_slug=payload.client_slug,
                message_text=message_text,
                include_info_bundle=False,
            )
            if reply:
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=reply_meta if isinstance(reply_meta, dict) else None,
                    intent=followup_intent,
                    source="expected_reply_followup",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
                bot_response = reply
                composer_meta = None
                bot_response, composer_meta = _compose_fact_response(
                    bot_response,
                    client_slug=payload.client_slug,
                    conversation_id=str(conversation.id),
                    response_tag="expected_reply_followup",
                    conversation_state=conversation.state,
                    allow_booking_flow=routing["allow_booking_flow"],
                    has_followup=bool(multi_intent_other_followup),
                )
                _reset_low_confidence_retry(conversation)
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "info_class",
                        "decision": "reply",
                        "intent": followup_intent,
                        "state": conversation.state,
                        "source": "expected_reply_followup",
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="reply",
                    intent=followup_intent,
                    source="expected_reply_followup",
                    fast_intent=False,
                )
                if saved_message and isinstance(reply_meta, dict):
                    _update_message_decision_metadata(saved_message, reply_meta)
                if saved_message and composer_meta:
                    _update_message_decision_metadata(saved_message, composer_meta)
                bot_response, sent = _send_and_save(bot_response)
                result_message = (
                    "Expected reply followup sent"
                    if sent
                    else "Expected reply followup failed"
                )
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

    info_flow_result = _handle_info_flow(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        client_slug=payload.client_slug,
        routing=routing,
        bypass_domain_flows=bypass_domain_flows,
        booking_wants_flow=booking_wants_flow,
        policy_handler=policy_handler,
        intent_decomp_used=intent_decomp_used,
        intent_decomp_intents=intent_decomp_intents,
        intent_decomp_set=intent_decomp_set,
        intent_decomp_payload=intent_decomp_payload,
        intent_decomp_service_query=intent_decomp_service_query,
        info_class_intents=info_class_intents,
        info_class_meta=info_class_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        router_state=router_state,
        allow_service_carryover=allow_service_carryover,
        context_manager=context_manager,
        current_goal=current_goal,
        message_count=message_count,
        now=now,
        consult_return_pending=consult_return_pending,
        consult_return_prompt=consult_return_prompt,
        consult_context=consult_context,
        consult_return_reason=consult_return_reason,
        multi_intent_other_followup=multi_intent_other_followup,
        maybe_apply_fact_guard=_maybe_apply_fact_guard,
        send_and_save=_send_and_save,
        send_response=_send_response,
        finalize_response=_finalize_bot_response,
    )
    force_truth_gate = info_flow_result.force_truth_gate
    if info_flow_result.response:
        return info_flow_result.response

    if force_truth_gate:
        skip_llm_primary = True
        llm_primary_failed = True
        llm_primary_reason = "forced_truth_gate"

    if routing["allow_bot_reply"] and not skip_llm_primary:
        llm_primary_outcome = _handle_llm_primary(
            db=db,
            conversation=conversation,
            user=user,
            message_text=message_text,
            saved_message=saved_message,
            client_slug=payload.client_slug,
            policy_type=policy_type,
            policy_pack=policy_pack,
            routing=routing,
            append_user_message=append_user_message,
            timing_context=timing_context,
            client_config=client.config if client else None,
            intent=intent,
            multi_intent_other_followup=multi_intent_other_followup,
            send_and_save=_send_and_save,
            record_escalation_metric=_record_escalation_metric,
        )
        if llm_primary_outcome.response:
            return llm_primary_outcome.response
        llm_primary_result = llm_primary_outcome.llm_primary_result
        llm_primary_failed = llm_primary_outcome.llm_primary_failed
        llm_primary_reason = llm_primary_outcome.llm_primary_reason

    if llm_primary_failed and not bypass_domain_flows and policy_handler and _should_run_truth_gate(
        routing, booking_wants_flow
    ):
        truth_gate_response = _handle_truth_gate_fallback(
            db=db,
            conversation=conversation,
            user=user,
            message_text=message_text,
            saved_message=saved_message,
            client_slug=payload.client_slug,
            routing=routing,
            booking_wants_flow=booking_wants_flow,
            policy_handler=policy_handler,
            policy_type=policy_type,
            current_goal=current_goal,
            intent_decomp_used=intent_decomp_used,
            intent_decomp_intents=intent_decomp_intents,
            intent_decomp_payload=intent_decomp_payload,
            llm_primary_reason=llm_primary_reason,
            message_count=message_count,
            now=now,
            consult_return_pending=consult_return_pending,
            consult_return_prompt=consult_return_prompt,
            consult_context=consult_context,
            consult_return_reason=consult_return_reason,
            maybe_apply_fact_guard=_maybe_apply_fact_guard,
            send_and_save=_send_and_save,
            log_timing=_log_timing,
            record_escalation_metric=_record_escalation_metric,
        )
        if truth_gate_response:
            return truth_gate_response

    # 10. Classify intent (expensive). Protect against accidental escalations on short/noisy messages.
    with start_span("webhook.router", context=timing_context) as span:
        intent_routing = _run_class_router_stage(
            conversation=conversation,
            saved_message=saved_message,
            message_text=message_text,
            client_slug=payload.client_slug,
            client_config=client.config if client else None,
            remote_jid=remote_jid,
            timing_context=timing_context,
            info_class_intents=info_class_intents,
            info_class_meta=info_class_meta,
            booking_signal=booking_signal,
            class_carryover=class_carryover,
            router_state=router_state,
            intent_decomp_payload=intent_decomp_payload,
            expected_reply_shortcircuit=expected_reply_shortcircuit,
            log_timing=_log_timing,
        )
    if span is not None:
        span.set_attribute("router.intent", getattr(intent_routing.intent, "value", None))
    signals = intent_routing.signals
    intent = intent_routing.intent
    domain_intent = intent_routing.domain_intent
    domain_meta = intent_routing.domain_meta
    class_router_result = intent_routing.class_router_result
    out_of_domain_signal = intent_routing.out_of_domain_signal
    rag_confident = False

    offline_info_response = _handle_offline_info_class(
        db=db,
        conversation=conversation,
        saved_message=saved_message,
        routing=routing,
        booking_wants_flow=booking_wants_flow,
        bypass_domain_flows=bypass_domain_flows,
        policy_handler=policy_handler,
        class_router_result=class_router_result,
        info_class_meta=info_class_meta,
        multi_intent_other_followup=multi_intent_other_followup,
        message_count=message_count,
        consult_return_pending=consult_return_pending,
        consult_return_prompt=consult_return_prompt,
        consult_context=consult_context,
        consult_return_reason=consult_return_reason,
        client_slug=payload.client_slug,
        maybe_apply_fact_guard=_maybe_apply_fact_guard,
        send_and_save=_send_and_save,
    )
    if offline_info_response:
        return offline_info_response

    # 10.1 Self-healing moved to health_service.check_and_heal_conversations()
    # Call POST /admin/heal periodically to fix broken states

    is_pending_status_question = (
        conversation.state == ConversationState.PENDING.value and is_handover_status_question(message_text)
    )
    context = _get_conversation_context(conversation)
    style_reference_pending, style_pending_expired = _get_style_reference_pending(context, now=now)
    if style_pending_expired:
        context = _set_style_reference_pending(context, None)
        _set_conversation_context(conversation, context)
        style_reference_pending = None
    style_reference = not has_media and _is_style_reference_request(message_text, has_media=False)
    if (
        not has_media
        and style_reference_pending
        and style_reference_pending.get("media")
        and message_text
        and not is_acknowledgement_message(message_text)
    ):
        style_reference = True
    decision = _resolve_action(
        routing=routing,
        state=conversation.state,
        signals=signals,
        is_pending_status_question=is_pending_status_question,
        style_reference=style_reference,
        out_of_domain_signal=out_of_domain_signal,
        rag_confident=rag_confident,
    )
    if saved_message:
        metadata = saved_message.message_metadata if isinstance(saved_message.message_metadata, dict) else {}
        decision_meta = metadata.get("decision_meta") if isinstance(metadata, dict) else {}
        if not (isinstance(decision_meta, dict) and decision_meta.get("action")):
            intent_value = getattr(intent, "value", None)
            _record_message_decision_meta(
                saved_message,
                action=decision.action,
                intent=intent_value if isinstance(intent_value, str) else None,
                source="action_resolve",
                fast_intent=False,
            )
            db.commit()

    if decision.action == "smalltalk":
        bot_response = GREETING_RESPONSE if intent == Intent.GREETING else THANKS_RESPONSE
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "smalltalk",
                "decision": intent.value,
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="smalltalk",
            intent=intent.value,
            source="fast_intent",
            fast_intent=True,
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Greeting response sent" if sent else "Greeting response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    if decision.action == "pending_status":
        bot_response = MSG_PENDING_STATUS
        _record_decision_trace(
            conversation,
            {
                "stage": "pending_status",
                "decision": "status_reply",
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_status",
            intent=intent.value,
            source="pending_status",
            fast_intent=False,
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Pending status response sent" if sent else "Pending status response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    if decision.action == "bot_status":
        bot_response = BOT_STATUS_RESPONSE
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "bot_status",
                "decision": "status_reply",
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="bot_status",
            intent=intent.value,
            source="bot_status",
            fast_intent=False,
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Bot status response sent" if sent else "Bot status response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    if decision.action == "style_reference":
        context = _get_conversation_context(conversation)
        style_reference_pending, style_pending_expired = _get_style_reference_pending(context, now=now)
        if style_pending_expired:
            context = _set_style_reference_pending(context, None)
            _set_conversation_context(conversation, context)
            style_reference_pending = None
        pending_media = (
            style_reference_pending.get("media")
            if isinstance(style_reference_pending, dict)
            else None
        )
        pending_storage_path = (
            style_reference_pending.get("storage_path")
            if isinstance(style_reference_pending, dict)
            else None
        )
        if isinstance(pending_media, dict):
            media_escalated = False
            handover_text = message_text.strip() if message_text else "Клиент уточнил референс."
            _, reused, telegram_sent = _reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=handover_text,
                source="style_reference_pending",
                intent="style_reference",
            )
            if reused:
                media_escalated = True
            else:
                _record_escalation_metric("media")
                result = escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=handover_text,
                    trigger_type="media",
                    trigger_value="style_reference",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=handover_text,
                    )
                    media_escalated = True
                else:
                    bot_response = MSG_AI_ERROR
                    bot_response, sent = _send_and_save(bot_response)
                    result_message = (
                        "Style reference escalation failed"
                        if sent
                        else "Style reference escalation response failed"
                    )
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

            media_policy_local = media_policy or _get_media_policy(client)
            if (
                media_escalated
                and conversation.telegram_topic_id
                and media_policy_local
                and media_policy_local.get("forward_to_telegram")
            ):
                bot_token, chat_id = get_telegram_credentials(db, client.id)
                if bot_token and chat_id:
                    telegram = TelegramService(bot_token)
                    pending_media_info = MediaInfo(
                        raw_type=pending_media.get("raw_type") or "image",
                        media_type=pending_media.get("media_type") or "photo",
                        mime=pending_media.get("mime"),
                        size_bytes=pending_media.get("size_bytes"),
                        duration_seconds=pending_media.get("duration_seconds"),
                        url=pending_media.get("url"),
                        file_name=pending_media.get("file_name"),
                        caption=pending_media.get("caption"),
                        base64_data=None,
                        is_ptt=bool(pending_media.get("ptt")),
                    )
                    caption = _build_media_caption(message_text, pending_media_info)
                    _send_telegram_media(
                        telegram=telegram,
                        chat_id=chat_id,
                        topic_id=conversation.telegram_topic_id,
                        media=pending_media_info,
                        caption=caption,
                        stored_path=pending_storage_path,
                    )

            context = _set_style_reference_pending(context, None)
            _set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "style_reference",
                    "decision": "escalate_with_media",
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="style_reference",
                intent=intent.value,
                source="style_reference",
                fast_intent=False,
            )
            bot_response, sent = _send_and_save(MSG_MEDIA_STYLE_REFERENCE)
            result_message = (
                "Style reference pending media escalated"
                if sent
                else "Style reference pending media response failed"
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

        pending_payload = {
            "reason": "text_only",
            "requested_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=STYLE_REFERENCE_PENDING_TTL_MINUTES)).isoformat(),
        }
        context = _set_style_reference_pending(context, pending_payload)
        _set_conversation_context(conversation, context)
        bot_response = MSG_STYLE_REFERENCE_NEED_MEDIA
        _record_decision_trace(
            conversation,
            {
                "stage": "style_reference",
                "decision": "need_media",
                "state": conversation.state,
                "pending": "text_only",
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="style_reference",
            intent=intent.value,
            source="style_reference",
            fast_intent=False,
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Style reference prompt sent" if sent else "Style reference prompt failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if decision.action == "out_of_domain":
        bot_response = OUT_OF_DOMAIN_RESPONSE
        _reset_low_confidence_retry(conversation)
        ood_source = "router_low_confidence" if signals.is_low_signal else "domain_router"
        ood_decision = "router_low_confidence" if signals.is_low_signal else "fallback"
        _record_decision_trace(
            conversation,
            {
                "stage": "out_of_domain",
                "decision": ood_decision,
                "state": conversation.state,
                "rag_confident": rag_confident,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="out_of_domain",
            intent="out_of_domain",
            source=ood_source,
            fast_intent=False,
        )
        _record_knowledge_backlog(
            db,
            client_id=client.id,
            conversation_id=conversation.id,
            message=saved_message,
            user_text=message_text,
            miss_type="out_of_domain",
        )
        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        result_message = "Out-of-domain response sent" if sent else "Out-of-domain response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 10. Handle based on intent and state
    if decision.action == "escalate":
        handover_message = message_text
        if intent == Intent.HUMAN_REQUEST:
            handover_message = select_handover_user_message(db, conversation.id, message_text)

        _, reused, telegram_sent = _reuse_active_handover(
            db=db,
            conversation=conversation,
            user=user,
            message=handover_message,
            source="intent_escalation",
            intent=intent.value,
        )

        if reused:
            bot_response = MSG_ESCALATED
            _record_message_decision_meta(
                saved_message,
                action="escalate",
                intent=intent.value,
                source="intent_escalation",
                fast_intent=False,
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = (
                f"Escalation reused ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"
            )
        else:
            # Escalate using state_service (atomic transition)
            _record_escalation_metric("intent")
            result = escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=handover_message,
                trigger_type="intent",
                trigger_value=intent.value,
            )

            if result.ok:
                handover = result.value
                # Send notification to Telegram
                telegram_sent = send_telegram_notification(
                    db=db,
                    handover=handover,
                    conversation=conversation,
                    user=user,
                    message=handover_message,
                )
                bot_response = MSG_ESCALATED
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "escalation",
                        "decision": "created",
                        "state": conversation.state,
                        "intent": intent.value,
                        "telegram_sent": telegram_sent,
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="escalate",
                    intent=intent.value,
                    source="intent_escalation",
                    fast_intent=False,
                )
                bot_response, sent = _send_and_save(bot_response)
                result_message = f"Escalated ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"
            else:
                logger.error(f"Escalation failed: {result.error}")
                # Fallback: respond normally
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "escalation",
                        "decision": "failed",
                        "state": conversation.state,
                        "intent": intent.value,
                        "error": result.error_code,
                    },
                )
                ai_response_outcome = _handle_ai_response_action(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message_text=message_text,
                    saved_message=saved_message,
                    client_slug=payload.client_slug,
                    client_id=client.id,
                    client_config=client.config if client else None,
                    routing=routing,
                    intent=intent,
                    llm_primary_result=None,
                    append_user_message=append_user_message,
                    timing_context=timing_context,
                    intent_decomp_payload=intent_decomp_payload,
                    class_router_result=class_router_result,
                    expected_reply_shortcircuit=expected_reply_shortcircuit,
                    out_of_domain_signal=out_of_domain_signal,
                    booking_signal=booking_signal,
                    info_class_intents=info_class_intents,
                    current_goal=current_goal,
                    now=now,
                    send_and_save=_send_and_save,
                    send_response=_send_response,
                    finalize_response=_finalize_bot_response,
                )
                if ai_response_outcome.response:
                    return ai_response_outcome.response
                bot_response = ai_response_outcome.bot_response
                result_message = (
                    ai_response_outcome.result_message
                    or f"Escalation failed ({result.error_code}), responded normally"
                )

    elif decision.action == "pending_escalation":
        bot_response = MSG_PENDING_ESCALATION if intent == Intent.FRUSTRATION else MSG_PENDING_STATUS
        _record_decision_trace(
            conversation,
            {
                "stage": "escalation",
                "decision": "skipped_pending",
                "state": conversation.state,
                "intent": intent.value,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_escalation",
            intent=intent.value,
            source="intent_escalation",
            fast_intent=False,
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Escalation skipped (pending), status response sent" if sent else "Pending status response failed"

    elif decision.action == "rejection":
        # Client rejects help
        if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
            handover = get_active_handover(db, conversation.id)
            if handover:
                manager_resolve(db, conversation, handover, manager_id="system", manager_name="system")
            bot_response = MSG_MUTED_TEMP
            _record_decision_trace(
                conversation,
                {
                    "stage": "rejection",
                    "decision": "cancel_handover",
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="rejection",
                intent=intent.value,
                source="rejection",
                fast_intent=False,
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Request cancelled, bot reactivated"
        else:
            mute_first, mute_second = get_mute_settings(db, client.id)
            if conversation.no_count == 0:
                # First rejection: mute (default 30 min)
                conversation.bot_muted_until = now + timedelta(minutes=mute_first)
                conversation.no_count = 1
                bot_response = MSG_MUTED_TEMP
                trace_decision = "muted_first"
            else:
                # Second rejection: mute (default 24 hours)
                conversation.bot_muted_until = now + timedelta(hours=mute_second)
                conversation.no_count += 1
                bot_response = MSG_MUTED_LONG
                trace_decision = "muted_second"

            _record_decision_trace(
                conversation,
                {
                    "stage": "rejection",
                    "decision": trace_decision,
                    "state": conversation.state,
                    "no_count": conversation.no_count,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="rejection",
                intent=intent.value,
                source="rejection",
                fast_intent=False,
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = f"Muted (rejection #{conversation.no_count})"

    elif decision.action == "ai_response":
        ai_response_outcome = _handle_ai_response_action(
            db=db,
            conversation=conversation,
            user=user,
            message_text=message_text,
            saved_message=saved_message,
            client_slug=payload.client_slug,
            client_id=client.id,
            client_config=client.config if client else None,
            routing=routing,
            intent=intent,
            llm_primary_result=llm_primary_result,
            append_user_message=append_user_message,
            timing_context=timing_context,
            intent_decomp_payload=intent_decomp_payload,
            class_router_result=class_router_result,
            expected_reply_shortcircuit=expected_reply_shortcircuit,
            out_of_domain_signal=out_of_domain_signal,
            booking_signal=booking_signal,
            info_class_intents=info_class_intents,
            current_goal=current_goal,
            now=now,
            send_and_save=_send_and_save,
            send_response=_send_response,
            finalize_response=_finalize_bot_response,
        )
        if ai_response_outcome.response:
            return ai_response_outcome.response
        bot_response = ai_response_outcome.bot_response
        result_message = ai_response_outcome.result_message
        llm_primary_failed = ai_response_outcome.llm_primary_failed
        llm_primary_reason = ai_response_outcome.llm_primary_reason

    else:
        _record_decision_trace(
            conversation,
            {
                "stage": "routing",
                "decision": "unknown_state",
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="unknown_state",
            intent=intent.value,
            source="routing",
            fast_intent=False,
        )
        result_message = f"Unknown state: {conversation.state}"

    _ensure_action_gate()
    _persist_timing_snapshot()
    db.commit()

    return WebhookResponse(
        success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
    )
