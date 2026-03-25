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

from app.core import DialogStateService, TurnExecutor, TurnPlanner
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
from app.models import (
    Branch,
    Client,
    ClientSettings,
    Conversation,
    Handover,
    MarketingCampaign,
    MarketingCampaignDelivery,
    Message,
    OutboxMessage,
    Specialist,
    User,
)
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
    _is_booking_slot_signal,
    _is_booking_time_service_decision,
    _is_datetime_grounded_for_prompt,
    _looks_like_booking_reschedule_request,
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
    CANONICAL_DIALOG_STATE_KEY,
    _build_compact_summary_text,
    _build_consult_return_prompt,
    _get_asr_confirmation,
    _get_asr_inflight,
    _get_canonical_dialog_state,
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
    _project_canonical_referent,
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
    _sync_canonical_dialog_state,
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
    _handle_sla_collect_only_gate,
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
    _looks_like_services_overview_message,
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
    _pack_escalation_gate,
    _pack_price_sidecar,
    _resolve_hard_law_sections,
    _should_escalate_to_pending,
    _should_run_booking_flow,
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
from app.routers.webhook.runtime_primitives import (
    INFO_ANCHOR_GROUPS,
    INFO_INTENT_PRIORITY_GENERIC,
    INFO_INTENT_PRIORITY_SERVICE,
    INFO_INTENTS,
    INFO_NON_SERVICE_INTENTS,
    INFO_SERVICE_DEPENDENT_INTENTS,
    MSG_AI_ERROR,
    MSG_BOOKING_ASK_DATETIME,
    MSG_BOOKING_ASK_NAME,
    MSG_BOOKING_ASK_SERVICE,
    MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE,
    MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP,
    MSG_BOOKING_TIMEOUT_PENDING_QUESTION_TIME,
    MSG_DELIVERY_FAILED,
    MSG_EXPECTED_SERVICE_OFF_TOPIC,
    QUESTION_WORD_PREFIXES,
    SERVICE_CARRYOVER_TTL_MESSAGES,
    SESSION_MEMORY_SHORT_TOKENS,
)
from app.routers.webhook.session_memory import (
    _clear_session_memory_expected_reply,
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
    _sync_session_memory_interaction_state,
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
    _update_message_signal_snapshot,
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
    _current_openai_api_key,
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
from app.services.booking_signal_service import (
    extract_relative_date_token as _extract_relative_date_token,
)
from app.services.booking_signal_service import (
    has_daypart_stem as _has_daypart_stem,
)
from app.services.booking_signal_service import (
    has_pending_time_question_marker as _has_pending_time_question_marker,
)
from app.services.booking_signal_service import (
    looks_like_time_preference_statement as _looks_like_time_preference_statement,
)
from app.services.booking_signal_service import (
    match_booking_hour_fallback as _match_booking_hour_fallback,
)
from app.services.booking_signal_service import (
    pick_daypart_token as _pick_daypart_token,
)
from app.services.booking_transition_owner import (
    BOOKING_TRANSITION_OWNER_V1,
    apply_tool_transition_owner,
    normalize_phone_digits,
    resolve_user_phone_for_tool,
    sync_user_profile_from_booking_args,
)
from app.services.capabilities_runtime import build_runtime_capabilities, set_runtime_capabilities
from app.services.capability_manifest_service import (
    build_requested_fact_scopes,
    resolve_fact_scope_decision,
    resolve_handoff_policy_decision,
    resolve_tool_protocol_decision,
)
from app.services.chatflow_service import get_instance_id
from app.services.conversation_service import get_or_create_conversation, get_or_create_user
from app.services.escalation_service import get_telegram_credentials
from app.services.expected_reply_contract import (
    resolve_services_overview_contract_update,
    resolve_tool_expected_reply_contract,
)
from app.services.integration_guardrails_service import (
    REASON_INBOUND_WITHOUT_OUTBOUND,
    report_integration_incident,
)
from app.services.intent_service import (
    ANSWER_INTERPRETER_TIMEOUT_SECONDS,
    CONTROLLER_TIMEOUT_SECONDS,
    POLICY_CORE_CONFIDENCE_THRESHOLD,
    POLICY_CORE_TIMEOUT_SECONDS,
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    classify_intent,
    extract_customer_name_hint_llm,
    extract_service_query_hint_llm,
    extract_specialist_hint_llm,
    interpret_expected_reply,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
    is_rejection,
    is_strong_out_of_domain,
    route_dialogue_controller,
    route_llm_policy_core,
    should_escalate,
)
from app.services.knowledge_registry_service import get_current_published
from app.services.knowledge_runtime import (
    build_runtime_truth,
    set_runtime_truth,
    should_allow_truth_fallback,
)
from app.services.knowledge_validation import (
    MINIMUM_DATA_CONTRACT_VERSION,
    MinimumDataContractStatus,
    evaluate_minimum_data_contract,
)
from app.services.message_service import generate_bot_response, save_message, select_handover_user_message
from app.services.outbox_service import build_inbound_message_id
from app.services.owner_resolver import (
    build_owner_resolution_input,
    build_semantic_contract_view,
    extract_specialist_preference,
    resolve_interaction_owner,
    should_preserve_active_name_time_availability_followup_owner,
    should_preserve_service_choice_specialist_availability_followup_owner,
    should_preserve_specialist_availability_followup_owner,
    should_preserve_specialist_followup_owner,
)
from app.services.timeout_owner_boundary_service import (
    TimeoutOwnerBoundaryApplyOverrides,
    TimeoutOwnerBoundaryInput,
    TimeoutOwnerBoundaryRuntimeHooks,
    TimeoutOwnerBoundaryRuntimeInput,
    resolve_and_apply_timeout_owner_boundary,
)
from app.services.policy_validation_boundary_service import (
    PolicyValidationBoundaryRuntimeHooks,
    PolicyValidationBoundaryRuntimeInput,
    handle_policy_validation_boundary,
)
from app.services.policy_timeout_degrade_boundary_service import (
    PolicyTimeoutDegradeBoundaryRuntimeHooks,
    PolicyTimeoutDegradeBoundaryRuntimeInput,
    handle_policy_timeout_degrade_boundary,
)
from app.services.policy_timeout_recovery_boundary_service import (
    PolicyTimeoutRecoveryBoundaryRuntimeHooks,
    PolicyTimeoutRecoveryBoundaryRuntimeInput,
    handle_policy_timeout_recovery_boundary,
)
from app.services.policy_timeout_booking_specialist_boundary_service import (
    PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks,
    PolicyTimeoutBookingSpecialistBoundaryRuntimeInput,
    handle_policy_timeout_booking_specialist_boundary,
)
from app.services.policy_timeout_booking_time_followup_boundary_service import (
    PolicyTimeoutBookingTimeFollowupBoundaryRuntimeHooks,
    PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput,
    handle_policy_timeout_booking_time_followup_boundary,
)
from app.services.policy_core_guard_orchestration_service import (
    PolicyCoreGuardOrchestrationRuntimeHooks,
    PolicyCoreGuardOrchestrationRuntimeInput,
    handle_policy_core_guard_orchestration,
)
from app.services.pack_runtime_service import (
    PackDecision,
    _detect_promotion_intent,
    _format_service_not_found_reply,
    _has_duration_signal,
    _has_parking_signal,
    _has_price_signal,
    _match_service,
    _matches_service_request_lexicon,
    build_capability_question_contract,
    build_evening_greeting,
    build_quiet_hours_notice,
    compose_multi_truth_reply,
    format_reply_from_truth,
    get_pack_decision,
    get_pack_price_item,
    get_pack_service_decision,
    get_pack_service_hint,
    get_signal_lexicon_list,
    get_system_lexicon_list,
    has_walkin_without_booking_signal,
    is_timeout_fact_fallback_candidate,
    load_system_lexicons,
    load_yaml_truth,
    resolve_master_intent,
    semantic_question_type,
    semantic_service_match,
)
from app.services.pack_runtime_service import (
    _normalize_text as _normalize_service_text,
)
from app.services.signal_manifest_service import get_booking_text_tokens
from app.services.handover_owner_service import (
    ActiveHandoverReuseRuntimeHooks,
    PendingEscalationNotificationRuntimeHooks,
    _create_pending_escalation_with_notification as _handover_owner_create_pending_escalation_with_notification,
    _reuse_active_handover as _handover_owner_reuse_active_handover,
    escalate_to_pending,
    get_active_handover as _handover_owner_get_active_handover,
    manager_resolve,
    resolve_active_handover_rejection,
    send_telegram_notification,
)
from app.services.state_machine import ConversationState
from app.services.state_service import (
    PendingResumeBoundaryRuntimeHooks as ResumeBoundaryRuntimeHooks,
    _derive_pending_booking_resume_boundary_payload as _state_service_derive_pending_booking_resume_boundary_payload,
    _derive_pending_resume_reason as _state_service_derive_pending_resume_reason,
    _resolve_pending_resume_boundary_activation as _resolve_resume_boundary_activation,
    _resolve_resolved_handoff_resume_boundary_restore as _resolve_resolved_resume_boundary_restore,
    _resolve_pending_resume_session_memory_policy as _resolve_resume_session_memory_policy,
    _resolve_pending_timeout_resume_boundary_payload as _resolve_resume_timeout_boundary_payload,
    apply_simulation_context,
    build_simulation_context,
    get_simulation_time,
    is_simulation_context,
    transition_state,
)
from app.services.telegram_service import TelegramService
from app.services.transport_adapter import TransportSendRequest, resolve_transport_adapter

# Backward-compatible exports for tests and legacy imports.
get_demo_salon_decision = get_pack_decision
get_demo_salon_service_decision = get_pack_service_decision
get_demo_salon_price_item = get_pack_price_item
get_demo_salon_service_hint = get_pack_service_hint
_should_run_demo_truth_gate = _should_run_truth_gate


def _normalize_message_text(message_text: str | None) -> str:
    return (message_text or "").strip()


_SPECIALIST_SURFACE_HINT_TOKEN_RE = re.compile(
    r"^[A-ZА-ЯЁӘІҢҒҚҮҰӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҚқҮүҰұӨөҺһ'’\\-]{1,47}$"
)


def _compact_signal_snapshot(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _has_lateness_signal(message_text: str | None, *, client_slug: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    phrases = get_signal_lexicon_list(client_slug, "lateness_phrases")
    for phrase in phrases:
        if not isinstance(phrase, str):
            continue
        token = normalize_for_matching(phrase)
        if token and token in normalized:
            return True
    return any(marker in normalized for marker in ("опозд", "опаздыв", "задерж"))


def _extract_pack_index_meta(client_config: dict | None) -> dict[str, Any] | None:
    if not isinstance(client_config, dict):
        return None
    pack_index = client_config.get("pack_index")
    if not isinstance(pack_index, dict):
        return None
    meta = _compact_signal_snapshot(
        {
            "schema_version": pack_index.get("schema_version"),
            "hash": pack_index.get("hash"),
            "version_id": pack_index.get("version_id"),
            "compiled_at": pack_index.get("compiled_at"),
            "source": pack_index.get("source"),
        }
    )
    return meta or None


def _extract_compiled_pack_meta(client_config: dict | None) -> dict[str, Any] | None:
    if not isinstance(client_config, dict):
        return None
    compiled_pack = client_config.get("compiled_pack")
    if not isinstance(compiled_pack, dict):
        return None
    meta = _compact_signal_snapshot(
        {
            "schema_version": compiled_pack.get("schema_version"),
            "hash": compiled_pack.get("hash"),
            "version_id": compiled_pack.get("version_id"),
            "compiled_at": compiled_pack.get("compiled_at"),
            "source": compiled_pack.get("source"),
        }
    )
    return meta or None


def _detect_fast_intent(
    message_text: str,
    *,
    policy_type: str | None,
    booking_wants_flow: bool,
    bypass_domain_flows: bool,
) -> PackDecision | None:
    if not message_text or booking_wants_flow or bypass_domain_flows:
        return None

    from . import _legacy as legacy

    if legacy.is_greeting_message(message_text):
        return PackDecision(action="smalltalk", response=legacy.GREETING_RESPONSE, intent="greeting")
    if legacy.is_thanks_message(message_text):
        return PackDecision(action="smalltalk", response=legacy.THANKS_RESPONSE, intent="thanks")
    if legacy.is_acknowledgement_message(message_text):
        return PackDecision(action="smalltalk", response=legacy.ACKNOWLEDGEMENT_RESPONSE, intent="ack")
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
    is_human_request = is_human_request_message(message_text)

    if is_human_request:
        intent = Intent.HUMAN_REQUEST
        legacy.logger.info("Intent shortcut: human_request (lexicon)")
    elif intent_hint == Intent.GREETING:
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

    if intent_hint in {Intent.GREETING, Intent.THANKS, Intent.QUESTION} and intent != Intent.HUMAN_REQUEST:
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
    in_domain_override: bool = False,
    out_of_domain_signal: bool,
    rag_confident: bool = False,
    llm_first_firebreak: bool = False,
) -> DecisionOutcome:
    from . import _legacy as legacy

    if routing["allow_bot_reply"] and (signals.is_greeting or signals.is_thanks):
        return DecisionOutcome("smalltalk")
    if routing["allow_bot_reply"] and state == legacy.ConversationState.PENDING.value and is_pending_status_question:
        return DecisionOutcome("pending_status")
    if routing["allow_bot_reply"] and signals.is_status_question:
        return DecisionOutcome("bot_status")
    if routing["allow_bot_reply"] and style_reference:
        return DecisionOutcome("style_reference")
    if routing["allow_bot_reply"] and in_domain_override:
        return DecisionOutcome("ai_response")
    firebreak_reasons = _llm_first_firebreak_semantic_reasons(
        routing=routing,
        signals=signals,
        out_of_domain_signal=out_of_domain_signal,
        rag_confident=rag_confident,
        llm_first_firebreak=llm_first_firebreak,
    )
    if firebreak_reasons:
        return DecisionOutcome("ai_response")
    if routing["allow_bot_reply"] and (out_of_domain_signal or signals.is_low_signal) and not rag_confident:
        return DecisionOutcome("out_of_domain")
    if legacy._should_escalate_to_pending(routing, signals.intent):
        return DecisionOutcome("escalate")
    if legacy.should_escalate(signals.intent) and not routing["allow_handover_create"]:
        return DecisionOutcome("pending_escalation")
    if legacy.is_rejection(signals.intent):
        return DecisionOutcome("rejection")
    if routing["allow_bot_reply"]:
        return DecisionOutcome("ai_response")
    return DecisionOutcome("unknown_state")


def _llm_first_firebreak_semantic_reasons(
    *,
    routing: dict[str, bool],
    signals: DecisionSignals,
    out_of_domain_signal: bool,
    rag_confident: bool,
    llm_first_firebreak: bool,
) -> list[str]:
    from . import _legacy as legacy

    if not llm_first_firebreak or not routing.get("allow_bot_reply", False):
        return []

    reasons: list[str] = []
    if (out_of_domain_signal or signals.is_low_signal) and not rag_confident:
        reasons.append("out_of_domain_signal" if out_of_domain_signal else "low_signal")
    if legacy._should_escalate_to_pending(routing, signals.intent):
        reasons.append("escalate_to_pending_intent")
    if legacy.should_escalate(signals.intent) and not routing.get("allow_handover_create", False):
        reasons.append("pending_without_handover_create")
    if legacy.is_rejection(signals.intent):
        reasons.append("rejection_intent")
    return reasons


def is_handover_status_question(text: str) -> bool:
    """Detect 'did you forward / when manager replies' questions in pending state."""
    if not text:
        return False

    normalized = text.strip().casefold()
    keywords = get_system_lexicon_list("handover_status_keywords")
    return bool(keywords) and any(k in normalized for k in keywords)


def _should_block_expected_reply_by_info(
    *,
    expected_reply_type: str | None,
    message_text: str | None,
    client_slug: str | None,
) -> bool:
    from . import _legacy as legacy

    if expected_reply_type not in {
        legacy.EXPECTED_REPLY_SERVICE,
        legacy.EXPECTED_REPLY_TIME,
        legacy.EXPECTED_REPLY_NAME,
    }:
        return False
    if not message_text:
        return False
    normalized_message = legacy._normalize_service_text(message_text)
    info_query = legacy._looks_like_info_query(message_text, client_slug=client_slug)
    price_signal = legacy._has_price_signal(normalized_message, message_text)
    duration_signal = legacy._has_duration_signal(normalized_message, message_text)
    style_reference_signal = _is_style_reference_request(message_text, has_media=False)
    tokens = normalized_message.split()
    question_like = "?" in message_text
    if not question_like and tokens:
        question_like = any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)
    location_question_signal = bool(
        question_like
        and _has_explicit_location_or_hours_request(
            message_text,
            client_slug=client_slug,
            strict=True,
        )
    )
    verification_signal = _looks_like_booking_verification_request(message_text)
    reschedule_signal = _looks_like_booking_reschedule_request(
        message_text,
        client_slug=client_slug,
    )
    media_offer_terms = get_system_lexicon_list("style_reference_media_terms")
    media_offer_verbs = get_system_lexicon_list("style_reference_send_terms")
    media_offer_signal = bool(
        style_reference_signal
        or (
            media_offer_terms
            and media_offer_verbs
            and any(term in normalized_message for term in media_offer_terms)
            and any(term in normalized_message for term in media_offer_verbs)
        )
    )
    explicit_info_interrupt = bool(
        price_signal
        or duration_signal
        or style_reference_signal
        or location_question_signal
        or verification_signal
        or reschedule_signal
        or media_offer_signal
    )
    expected_reply_candidate = None
    if expected_reply_type == legacy.EXPECTED_REPLY_TIME:
        expected_reply_candidate = _validate_expected_reply_value(
            expected_reply_type=expected_reply_type,
            value=message_text,
            client_slug=client_slug,
        )
    question_like_time_slot_constraint = bool(
        expected_reply_type == legacy.EXPECTED_REPLY_TIME
        and _is_question_like_time_slot_constraint_candidate(
            message_text=message_text,
            candidate_value=expected_reply_candidate,
        )
    )
    blocked = bool(
        info_query
        or explicit_info_interrupt
    )
    if not blocked and expected_reply_type in {
        legacy.EXPECTED_REPLY_TIME,
        legacy.EXPECTED_REPLY_NAME,
    }:
        if question_like:
            blocked = True
    if (
        blocked
        and expected_reply_type == legacy.EXPECTED_REPLY_TIME
    ):
        booking_signal = _is_booking_request(message_text, client_slug=client_slug)
        has_clock_time_signal = bool(
            re.search(r"\b(?:[01]?\d|2[0-3])[:.][0-5]\d\b", message_text)
            or TIME_HOUR_PATTERN.search(message_text)
            or _match_booking_hour_fallback(message_text)
        )
        try:
            has_datetime_signal = bool(
                legacy._extract_datetime(message_text, client_slug=client_slug)
            )
        except TypeError:
            # Some tests patch _extract_datetime with a positional-only stub.
            has_datetime_signal = bool(legacy._extract_datetime(message_text))
        has_daypart_candidate = bool(
            isinstance(expected_reply_candidate, str)
            and expected_reply_candidate.strip()
            and _has_daypart_stem(
                legacy.normalize_for_matching(expected_reply_candidate)
            )
        )
        if (
            isinstance(expected_reply_candidate, str)
            and expected_reply_candidate.strip()
            and not explicit_info_interrupt
            and (
                has_datetime_signal
                or booking_signal
                or has_daypart_candidate
                or question_like_time_slot_constraint
            )
            and (
                not question_like
                or booking_signal
                or has_clock_time_signal
                or has_daypart_candidate
                or question_like_time_slot_constraint
            )
        ):
            # Accept grounded booking-time replies like "на 3 часа" even when
            # duration markers are present in wording.
            return False
        if not has_datetime_signal:
            return blocked
        if (
            question_like
            and has_datetime_signal
            and not explicit_info_interrupt
            and (booking_signal or has_clock_time_signal)
        ):
            # Accept explicit booking-time questions like "Можно на 18:30?"
            # while still blocking info/price/duration interruptions.
            return False
        if question_like:
            return True
        # Keep info interrupts (address/hours/price/duration) in the info path
        # even when the message also contains a time-like token.
        return bool(info_query or price_signal or duration_signal)
    return blocked


def _is_question_like_time_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
) -> bool:
    from . import _legacy as legacy

    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if not isinstance(candidate_value, str) or not candidate_value.strip():
        return False
    normalized_message = legacy._normalize_service_text(message_text)
    tokens = normalized_message.split()
    question_like = "?" in message_text
    if not question_like and tokens:
        question_like = any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)
    if not question_like:
        return False
    has_clock_time_signal = bool(
        legacy.TIME_PATTERN.search(message_text)
        or legacy.TIME_HOUR_PATTERN.search(message_text)
        or _match_booking_hour_fallback(message_text)
        or legacy.TIME_PATTERN.search(candidate_value)
        or legacy.TIME_HOUR_PATTERN.search(candidate_value)
        or _match_booking_hour_fallback(candidate_value)
    )
    if has_clock_time_signal:
        return False
    return True


def _is_daypart_only_time_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
) -> bool:
    from . import _legacy as legacy

    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if not isinstance(candidate_value, str) or not candidate_value.strip():
        return False
    candidate_token = _pick_daypart_token(candidate_value)
    if not isinstance(candidate_token, str) or not candidate_token.strip():
        return False
    normalized_candidate = legacy.normalize_for_matching(candidate_value)
    normalized_token = legacy.normalize_for_matching(candidate_token)
    if not normalized_candidate or normalized_candidate != normalized_token:
        return False
    has_clock_time_signal = bool(
        legacy.TIME_PATTERN.search(message_text)
        or legacy.TIME_HOUR_PATTERN.search(message_text)
        or _match_booking_hour_fallback(message_text)
        or legacy.TIME_PATTERN.search(candidate_value)
        or legacy.TIME_HOUR_PATTERN.search(candidate_value)
        or _match_booking_hour_fallback(candidate_value)
    )
    if has_clock_time_signal:
        return False
    return True


def _extract_question_like_daypart_exact_time_fill(
    message_text: str | None,
) -> str | None:
    if not isinstance(message_text, str) or not message_text.strip():
        return None
    if not _pick_daypart_token(message_text):
        return None
    match = _match_booking_hour_fallback(message_text)
    if not match:
        return None
    try:
        hour = int(match.get("hour") or 0)
    except (TypeError, ValueError):
        return None
    minute = str(match.get("minute") or "00").strip() or "00"
    return f"{hour:02d}:{minute}"


def _is_declarative_time_window_slot_constraint_candidate(
    *,
    message_text: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if _is_question_like_message(message_text):
        return False
    return bool(
        re.search(
            r"\b(?:с|со|между)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:до|по|и|-|–|—)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b",
            message_text,
            re.IGNORECASE,
        )
    )


def _is_declarative_partial_date_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
    client_slug: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if not isinstance(candidate_value, str) or not candidate_value.strip():
        return False
    if _is_question_like_message(message_text):
        return False
    if _is_declarative_time_window_slot_constraint_candidate(message_text=message_text):
        return False
    if _is_datetime_grounded_for_prompt(candidate_value, client_slug=client_slug):
        return False
    normalized_message = normalize_for_matching(message_text)
    if not normalized_message or _extract_relative_date_token(message_text) != WEEKEND_RELATIVE_DAY_TOKEN:
        return False
    extracted_value = _extract_datetime(message_text, client_slug=client_slug)
    if not isinstance(extracted_value, str) or not extracted_value.strip():
        return False
    normalized_candidate = normalize_for_matching(candidate_value)
    normalized_extracted = normalize_for_matching(extracted_value)
    if not normalized_candidate or not normalized_extracted:
        return False
    return normalized_candidate == normalized_extracted


def _is_time_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
    client_slug: str | None,
) -> bool:
    return _is_question_like_time_slot_constraint_candidate(
        message_text=message_text,
        candidate_value=candidate_value,
    ) or _is_daypart_only_time_slot_constraint_candidate(
        message_text=message_text,
        candidate_value=candidate_value,
    ) or _is_declarative_partial_date_slot_constraint_candidate(
        message_text=message_text,
        candidate_value=candidate_value,
        client_slug=client_slug,
    )


def _derive_timeout_active_name_time_availability_followup_slots(
    *,
    message_text: str | None,
    client_slug: str | None,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    booking_state: dict[str, Any] | None,
) -> tuple[str, str] | None:
    if expected_reply_type != EXPECTED_REPLY_NAME:
        return None
    if expected_reply_matched is True or not expected_reply_blocked_by_info:
        return None
    normalized_reason = (
        expected_reply_reason.strip().casefold()
        if isinstance(expected_reply_reason, str) and expected_reply_reason.strip()
        else None
    )
    if normalized_reason not in {
        "booking_prompt",
        "booking_time_availability_followup",
        "policy_core_timeout_owner_boundary",
    }:
        return None
    if not isinstance(booking_state, dict):
        return None
    raw_last_question = booking_state.get("last_question")
    normalized_last_question = (
        raw_last_question.strip().casefold()
        if isinstance(raw_last_question, str) and raw_last_question.strip()
        else None
    )
    if normalized_last_question not in {None, "name"}:
        return None
    current_slot = (
        booking_state.get("datetime")
        if isinstance(booking_state.get("datetime"), str) and booking_state.get("datetime").strip()
        else None
    )
    if not _is_datetime_grounded_for_prompt(current_slot, client_slug=client_slug):
        return None
    if not _is_question_like_message(message_text):
        return None
    alternate_slot = _extract_question_like_daypart_exact_time_fill(message_text)
    if not alternate_slot:
        alternate_slot = _extract_datetime(message_text or "", client_slug=client_slug)
    if not isinstance(alternate_slot, str) or not alternate_slot.strip():
        return None
    return current_slot.strip(), alternate_slot.strip()


def _is_question_like_message(message_text: str | None) -> bool:
    from . import _legacy as legacy

    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if "?" in message_text:
        return True
    normalized_message = legacy._normalize_service_text(message_text)
    tokens = normalized_message.split()
    return bool(tokens) and any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)


def _format_specialist_followup_prompt(
    *,
    specialist_name: str | None,
    base_prompt: str,
    question_like: bool,
) -> str:
    prompt = (base_prompt or "").strip()
    if not prompt or not question_like:
        return prompt
    if not isinstance(specialist_name, str) or not specialist_name.strip():
        return prompt
    specialist_token = specialist_name.strip()
    return f"Понял, ориентир по специалисту — {specialist_token}. {prompt}"


def _specialist_availability_followup_prompt(*, requested_slot: str | None) -> str:
    slot_token = (
        requested_slot.strip().casefold()
        if isinstance(requested_slot, str) and requested_slot.strip()
        else None
    )
    if slot_token == "name":
        return MSG_BOOKING_ASK_NAME
    return MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP


def _build_specialist_availability_followup_response(
    *,
    service_query: str | None,
    client_slug: str | None,
    message_text: str | None,
    requested_slot: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    prompt = _specialist_availability_followup_prompt(requested_slot=requested_slot)
    normalized_service = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if not normalized_service:
        return prompt, None
    info_reply, info_meta = _build_info_intent_reply(
        "master",
        service_query=normalized_service,
        client_slug=client_slug,
        message_text=message_text,
    )
    if not isinstance(info_reply, str) or not info_reply.strip():
        return prompt, info_meta if isinstance(info_meta, dict) else None
    return (
        _combine_sidecar(info_reply.strip(), prompt),
        info_meta if isinstance(info_meta, dict) else None,
    )


def _build_active_name_time_availability_followup_response(
    *,
    current_slot: str | None,
    alternate_slot: str | None,
) -> str:
    prompt = MSG_BOOKING_ASK_NAME
    current_token = (
        current_slot.strip() if isinstance(current_slot, str) and current_slot.strip() else None
    )
    alternate_token = (
        alternate_slot.strip()
        if isinstance(alternate_slot, str) and alternate_slot.strip()
        else None
    )
    if alternate_token and current_token and alternate_token != current_token:
        return _combine_sidecar(
            (
                f"Сейчас в заявке отмечено {current_token}. "
                f"Слот {alternate_token} не меняю автоматически: если хотите проверить "
                "или выбрать его вместо текущего, скажите об этом отдельно."
            ),
            prompt,
        )
    if current_token and alternate_token == current_token:
        return _combine_sidecar(
            (
                f"Сейчас в заявке отмечено {current_token}. "
                "Если хотите оставить именно это время и продолжить запись, скажите об этом."
            ),
            prompt,
        )
    if current_token:
        return _combine_sidecar(
            (
                f"Сейчас в заявке отмечено {current_token}. "
                "Если хотите продолжить запись на это время, скажите об этом."
            ),
            prompt,
        )
    if alternate_token:
        return _combine_sidecar(
            (
                f"Слот {alternate_token} не меняю автоматически: если хотите проверить "
                "или выбрать его отдельно, скажите об этом."
            ),
            prompt,
        )
    return _combine_sidecar(
        "Если хотите проверить другое время отдельно от текущей заявки, скажите об этом.",
        prompt,
    )


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
        is_short_reply = legacy._is_short_reply(message_text)
        if (
            not is_short_reply
            and last_question_type == legacy.EXPECTED_REPLY_TIME
            and legacy._extract_datetime(message_text)
        ):
            is_short_reply = True
        if (
            (not memory_active_goal or not current_goal or memory_active_goal == current_goal)
            and last_question_type
            in {
                legacy.EXPECTED_REPLY_SERVICE,
                legacy.EXPECTED_REPLY_TIME,
                legacy.EXPECTED_REPLY_NAME,
            }
            and is_short_reply
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
    matched_expected_reply_type: str | None = None
    matched_booking_followup_state: dict[str, Any] | None = None
    matched_booking_followup_prompt: str | None = None
    matched_booking_followup_expected: str | None = None
    matched_booking_filled_slots: tuple[str, ...] = ()
    expected_reply_text = (
        legacy._select_expected_reply_message(
            batch_messages,
            expected_reply_type=expected_reply_type,
            client_slug=client_slug,
        )
        or message_text
    )
    if (
        expected_reply_type
        in {
            legacy.EXPECTED_REPLY_SERVICE,
            legacy.EXPECTED_REPLY_TIME,
            legacy.EXPECTED_REPLY_NAME,
        }
        and message_text
        and is_human_request_message(message_text)
    ):
        context = legacy._set_expected_reply_type(context, None)
        context, memory_payload, memory_cleared = legacy._clear_session_memory_expected_reply(
            context,
            expected_reply_type=expected_reply_type,
            now=now,
        )
        legacy._set_conversation_context(conversation, context)
        legacy._record_decision_trace(
            conversation,
            {
                "stage": "question_contract",
                "decision": "bypass",
                "expected_reply_type": expected_reply_type,
                "expected_reply_bypassed": "human_request",
            },
        )
        if memory_cleared:
            legacy._record_session_memory_update(
                conversation,
                saved_message,
                memory=memory_payload,
                reason="expected_reply_bypass",
            )
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "expected_reply_type": None,
                    "expected_reply_matched": False,
                    "expected_reply_bypassed": "human_request",
                    "session_memory_expected_reply_cleared": memory_cleared,
                },
            )
        context = legacy._get_conversation_context(conversation)
        context_manager = legacy._get_context_manager(context)
        return ExpectedReplyState(
            context=context,
            context_manager=context_manager,
            expected_reply_type=None,
            intent_queue=legacy._get_intent_queue(context),
            expected_reply_matched=False,
            expected_reply_shortcircuit=False,
            expected_reply_blocked_by_info=False,
            memory_expected_reply_type=memory_expected_reply_type,
            current_goal=current_goal,
        )
    booking_verification_bypass = bool(
        expected_reply_type
        in {
            legacy.EXPECTED_REPLY_SERVICE,
            legacy.EXPECTED_REPLY_TIME,
            legacy.EXPECTED_REPLY_NAME,
        }
        and message_text
        and _looks_like_booking_verification_request(message_text)
    )
    if booking_verification_bypass:
        context = legacy._set_expected_reply_type(context, None)
        context, memory_payload, memory_cleared = legacy._clear_session_memory_expected_reply(
            context,
            expected_reply_type=expected_reply_type,
            now=now,
        )
        legacy._set_conversation_context(conversation, context)
        legacy._record_decision_trace(
            conversation,
            {
                "stage": "question_contract",
                "decision": "bypass",
                "expected_reply_type": expected_reply_type,
                "expected_reply_bypassed": "booking_verification",
            },
        )
        if memory_cleared:
            legacy._record_session_memory_update(
                conversation,
                saved_message,
                memory=memory_payload,
                reason="expected_reply_bypass",
            )
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "expected_reply_type": None,
                    "expected_reply_matched": False,
                    "expected_reply_bypassed": "booking_verification",
                    "session_memory_expected_reply_cleared": memory_cleared,
                },
            )
        context = legacy._get_conversation_context(conversation)
        context_manager = legacy._get_context_manager(context)
        return ExpectedReplyState(
            context=context,
            context_manager=context_manager,
            expected_reply_type=None,
            intent_queue=legacy._get_intent_queue(context),
            expected_reply_matched=False,
            expected_reply_shortcircuit=False,
            expected_reply_blocked_by_info=False,
            memory_expected_reply_type=memory_expected_reply_type,
            current_goal=current_goal,
        )
    if expected_reply_type in {
        legacy.EXPECTED_REPLY_SERVICE,
        legacy.EXPECTED_REPLY_TIME,
        legacy.EXPECTED_REPLY_NAME,
    }:
        booking_context = legacy._get_booking_context(context)
        deterministic_available = False
        deterministic_value = None
        normalization_flags: list[str] = []
        if message_text:
            expected_reply_blocked_by_info = _should_block_expected_reply_by_info(
                expected_reply_type=expected_reply_type,
                message_text=message_text,
                client_slug=client_slug,
            )
        expected_reply_text = expected_reply_text or ""
        if expected_reply_text:
            (
                deterministic_available,
                deterministic_value,
                normalization_flags,
            ) = _match_expected_reply_candidates(
                expected_reply_type=expected_reply_type,
                message_text=expected_reply_text,
                client_slug=client_slug,
            )
        deterministic_matched = False
        answer_result = None
        answer_confidence = 0.0
        answer_slot = ""
        answer_detected_slot = ""
        answer_value = ""
        answer_error = "blocked_by_info"
        answer_interpreter_attempted = False
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
            last_question = booking_context.get("last_question")
            if expected_reply_type == legacy.EXPECTED_REPLY_SERVICE:
                prompt_hint = (
                    MSG_BOOKING_ASK_SERVICE
                    if last_question == "service"
                    else MSG_EXPECTED_SERVICE_OFF_TOPIC
                )
            elif expected_reply_type == legacy.EXPECTED_REPLY_TIME:
                prompt_hint = MSG_BOOKING_ASK_DATETIME
            elif expected_reply_type == legacy.EXPECTED_REPLY_NAME:
                prompt_hint = MSG_BOOKING_ASK_NAME
            elif expected_reply_type == legacy.EXPECTED_REPLY_PHONE:
                prompt_hint = legacy.MSG_BOOKING_ASK_PHONE

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
                answer_interpreter_attempted = True
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
                    answer_detected_slot = answer_payload.get("detected_slot") or answer_slot
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
                    "answer_detected_slot": answer_detected_slot,
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
                    "detected_slot": answer_detected_slot,
                    "value": answer_value,
                    "confidence": answer_confidence,
                    "error": answer_error,
                },
            )
        blocked_question_like = False
        if expected_reply_blocked_by_info and message_text:
            normalized_message = legacy._normalize_service_text(message_text)
            tokens = normalized_message.split()
            blocked_question_like = "?" in message_text
            if not blocked_question_like and tokens:
                blocked_question_like = any(
                    tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES
                )
        if blocked_question_like:
            deterministic_available = False
            deterministic_value = None
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
        use_llm_slot = _is_booking_confirm_enabled()
        if not deterministic_matched and deterministic_available:
            should_use_deterministic = (
                not use_llm_slot
                or not answer_interpreter_attempted
                or not answer_result_ok
            )
            if (
                expected_reply_type == legacy.EXPECTED_REPLY_TIME
                and isinstance(deterministic_value, str)
            ):
                deterministic_has_time = bool(
                    legacy.TIME_PATTERN.search(deterministic_value)
                    or legacy.TIME_HOUR_PATTERN.search(deterministic_value)
                )
                if not deterministic_has_time:
                    should_use_deterministic = True
            if should_use_deterministic:
                deterministic_matched = True
                if expected_slot_key:
                    answer_slot = expected_slot_key
                if isinstance(deterministic_value, str) and deterministic_value.strip():
                    answer_value = deterministic_value
                if not use_llm_slot:
                    answer_used = False
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
        alternate_slot_captured = False
        alternate_slot_key = None
        alternate_slot_value = None
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
                # Guard against fabricated time slots: for datetime replies we only
                # accept LLM slot values when the user text had a deterministic
                # datetime signal in this turn.
                if expected_reply_type == legacy.EXPECTED_REPLY_TIME and not deterministic_available:
                    answer_value_validated = False
                    slot_validation_error = "time_not_grounded"
                    answer_error = "time_not_grounded"
                else:
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
                answer_detected_slot = ""
                answer_value = ""
        if (
            not matched
            and answer_error == "slot_mismatch"
        ):
            alternate_slot_key, alternate_slot_value = _resolve_alternate_booking_slot_capture(
                expected_reply_type=expected_reply_type,
                detected_slot=answer_detected_slot,
                answer_value=answer_value,
                message_text=message_text,
                client_slug=client_slug,
            )
            alternate_reply_type = _expected_reply_type_for_slot_key(alternate_slot_key)
            if alternate_reply_type and isinstance(alternate_slot_value, str):
                if not isinstance(booking_context, dict) or not booking_context:
                    booking_context = {
                        "active": True,
                        "started_at": now.isoformat(),
                    }
                    context = legacy._set_booking_context(context, booking_context)
                context = legacy._apply_expected_reply_slot(
                    context,
                    expected_reply_type=alternate_reply_type,
                    value=alternate_slot_value,
                )
                legacy._set_conversation_context(conversation, context)
                context, memory = legacy._update_session_memory_on_answer(
                    context,
                    expected_reply_type=alternate_reply_type,
                    value=alternate_slot_value,
                    now=now,
                )
                legacy._set_conversation_context(conversation, context)
                legacy._record_session_memory_update(
                    conversation,
                    saved_message,
                    memory=memory,
                    reason="alternate_slot_captured",
                )
                alternate_slot_captured = True
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "slot_validate",
                        "decision": "alternate_slot_captured",
                        "expected_reply_type": expected_reply_type,
                        "slot": alternate_slot_key,
                        "value": alternate_slot_value,
                        "detected_slot": answer_detected_slot,
                    },
                )
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
                "answer_detected_slot": answer_detected_slot,
                "answer_value": answer_value,
                "answer_error": answer_error,
                "slot_confidence": slot_confidence,
                "slot_source": slot_source,
                "slot_validation_error": slot_validation_error,
                "slot_confirmation_required": slot_confirmation_required,
                "alternate_slot_captured": alternate_slot_captured,
                "alternate_slot": alternate_slot_key,
                "alternate_value": alternate_slot_value,
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
        if matched and not slot_confirmation_required and isinstance(expected_reply_type, str):
            matched_expected_reply_type = expected_reply_type
            if expected_slot_key:
                matched_booking_filled_slots = (expected_slot_key,)
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
            next_expected = None
            if intent_queue:
                context = _set_intent_queue(context, None)
                intent_queue = None
                legacy._record_decision_trace(
                    conversation,
                    {
                        "stage": "intent_queue",
                        "decision": "reset_for_booking_reply",
                        "expected_reply_type": expected_reply_type,
                    },
                )
                if saved_message:
                    legacy._update_message_decision_metadata(
                        saved_message,
                        {"intent_queue_cleared": "booking_expected_reply"},
                    )
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
        if matched and expected_reply_blocked_by_info:
            # The message contained info-like signals but still produced a valid
            # expected-reply slot match; treat it as a successful answer to avoid
            # false "expected_reply_deferred" observability noise.
            expected_reply_blocked_by_info = False
            if answer_meta.get("answer_error") == "blocked_by_info":
                answer_meta["answer_error"] = "none"
        pending_question_slot_constraint = bool(
            matched
            and expected_reply_type == legacy.EXPECTED_REPLY_TIME
            and _is_time_slot_constraint_candidate(
                message_text=message_text,
                candidate_value=value if isinstance(value, str) and value.strip() else answer_value,
                client_slug=client_slug,
            )
        )
        if pending_question_slot_constraint:
            current_expected_reply = legacy._get_expected_reply_type(
                legacy._get_conversation_context(conversation)
            )
            _record_decision_trace(
                conversation,
                {
                    "stage": "pending_question_interaction",
                    "decision": "slot_constraint",
                    "state": conversation.state,
                    "source": "question_contract",
                    "pending_question_act": "slot_constraint",
                    "pending_question_target": "time",
                    "expected_reply_type": current_expected_reply or expected_reply_type,
                },
            )
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message,
                    {
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "pending_question_interaction": "slot_constraint",
                        "pending_question_owner": "question_contract",
                    },
                )
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
                    eligible=True,
                    reason="none",
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
        if matched_expected_reply_type:
            followup_context = legacy._get_conversation_context(conversation)
            followup_booking_state = legacy._get_booking_context(followup_context)
            (
                matched_booking_followup_state,
                matched_booking_followup_expected,
                matched_booking_followup_prompt,
            ) = _derive_booking_followup_contract(
                expected_reply_type=matched_expected_reply_type,
                booking_state=followup_booking_state,
                merged_slots=None,
                client_slug=client_slug,
            )
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
        matched_expected_reply_type=matched_expected_reply_type,
        matched_booking_followup_state=matched_booking_followup_state,
        matched_booking_followup_prompt=matched_booking_followup_prompt,
        matched_booking_followup_expected=matched_booking_followup_expected,
        matched_booking_filled_slots=matched_booking_filled_slots,
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
    booking_slot_signal: bool,
    booking_context: dict | None,
    booking: dict | None,
    booking_active: bool,
    expected_reply_shortcircuit: bool,
    expected_reply_blocked_by_info: bool,
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

    remaining_budget_ms = _remaining_pipeline_budget_ms(timing_context)
    critical_booking_turn = bool(
        booking_signal or booking_active or expected_reply_shortcircuit or booking_slot_signal
    )
    booking_expected_reply_turn = bool(
        expected_reply_type
        in {
            legacy.EXPECTED_REPLY_SERVICE,
            legacy.EXPECTED_REPLY_TIME,
            legacy.EXPECTED_REPLY_NAME,
        }
        and (booking_signal or booking_slot_signal or expected_reply_shortcircuit)
        and not expected_reply_blocked_by_info
        and (
            not expected_reply_reason
            or expected_reply_reason
            in {
                "booking_prompt",
                "booking_interrupt",
                "booking_confirm_reject",
                "booking_prompt_media_ack",
            }
        )
    )
    direct_booking_request = bool(
        message_text and _is_booking_request(message_text, client_slug=client_slug)
    )
    if booking_expected_reply_turn and message_text and _looks_like_info_query(
        message_text,
        client_slug=client_slug,
    ):
        booking_expected_reply_turn = False
    intent_decomp_skipped_reason = None
    intent_decomp_budget_required_ms = WEBHOOK_MULTI_INTENT_MIN_BUDGET_MS

    controller_reserve_ms = 0.0
    if (
        routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
        and not expected_reply_shortcircuit
        and _current_openai_api_key()
    ):
        controller_reserve_ms = max(float(CONTROLLER_TIMEOUT_SECONDS) * 1000, 0.0)
        controller_reserve_ms += max(float(POLICY_CORE_TIMEOUT_SECONDS) * 1000, 0.0)
        if expected_reply_type in {
            legacy.EXPECTED_REPLY_SERVICE,
            legacy.EXPECTED_REPLY_TIME,
            legacy.EXPECTED_REPLY_NAME,
        }:
            controller_reserve_ms += max(float(ANSWER_INTERPRETER_TIMEOUT_SECONDS) * 1000, 0.0)
    if critical_booking_turn and _current_openai_api_key():
        intent_decomp_budget_required_ms = max(
            intent_decomp_budget_required_ms,
            WEBHOOK_BOOKING_CRITICAL_PATH_RESERVE_MS,
        )
        controller_reserve_ms = max(
            controller_reserve_ms,
            WEBHOOK_BOOKING_CRITICAL_PATH_RESERVE_MS,
        )

    allow_intent_decomp = bool(routing["allow_bot_reply"] and not bypass_domain_flows and message_text)
    if allow_intent_decomp and booking_expected_reply_turn:
        allow_intent_decomp = False
        intent_decomp_skipped_reason = "booking_expected_reply_turn"
        meta_updates = {"intent_decomp_skipped_reason": intent_decomp_skipped_reason}
        trace_payload = {
            "stage": "intent_decomposition",
            "decision": "skipped",
            "reason": intent_decomp_skipped_reason,
        }
        if isinstance(expected_reply_type, str) and expected_reply_type.strip():
            meta_updates["intent_decomp_expected_reply_type"] = expected_reply_type.strip()
            trace_payload["expected_reply_type"] = expected_reply_type.strip()
        if isinstance(expected_reply_reason, str) and expected_reply_reason.strip():
            meta_updates["intent_decomp_expected_reply_reason"] = expected_reply_reason.strip()
            trace_payload["expected_reply_reason"] = expected_reply_reason.strip()
        if saved_message:
            legacy._update_message_decision_metadata(saved_message, meta_updates)
        legacy._record_decision_trace(conversation, trace_payload)

    if (
        allow_intent_decomp
        and critical_booking_turn
        and remaining_budget_ms is not None
        and remaining_budget_ms <= intent_decomp_budget_required_ms
    ):
        allow_intent_decomp = False
        intent_decomp_skipped_reason = "booking_critical_path_budget_reserved"
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "intent_decomp_skipped_reason": intent_decomp_skipped_reason,
                    "intent_decomp_budget_remaining_ms": round(remaining_budget_ms, 2),
                    "intent_decomp_budget_required_ms": round(intent_decomp_budget_required_ms, 2),
                },
            )
        legacy._record_decision_trace(
            conversation,
            {
                "stage": "intent_decomposition",
                "decision": "skipped",
                "reason": intent_decomp_skipped_reason,
                "budget_remaining_ms": round(remaining_budget_ms, 2),
                "budget_required_ms": round(intent_decomp_budget_required_ms, 2),
            },
        )

    if allow_intent_decomp:
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
        info_class_intents, info_class_meta = _detect_info_class_intents(
            message_text,
            intent_decomp_set=intent_decomp_set,
            client_slug=client_slug,
        )
        if legacy._matches_guest_policy_lexicon(message_text, client_slug=client_slug):
            if not isinstance(info_class_meta, dict):
                info_class_meta = {}
            info_signals = info_class_meta.get("info_signals")
            if not isinstance(info_signals, dict):
                info_signals = {}
            info_signals["guest"] = True
            info_class_meta["info_signals"] = info_signals
    openai_key_missing = not _current_openai_api_key()
    if not info_class_intents and isinstance(class_carryover, dict):
        use_carryover_intents = bool(
            expected_reply_shortcircuit and current_goal != "booking"
        )
        if not use_carryover_intents and legacy._looks_like_carryover_followup(message_text):
            use_carryover_intents = True
        if use_carryover_intents:
            carryover_intents = class_carryover.get("intents")
            if isinstance(carryover_intents, list):
                for intent_name in carryover_intents:
                    if isinstance(intent_name, str) and intent_name.strip():
                        info_class_intents.add(intent_name.strip().casefold())
            if not info_class_intents:
                carryover_sections = class_carryover.get("info_sections")
                if isinstance(carryover_sections, list):
                    for section_name in carryover_sections:
                        if not isinstance(section_name, str) or not section_name.strip():
                            continue
                        normalized_section = section_name.strip().casefold()
                        if normalized_section in INFO_INTENTS:
                            info_class_intents.add(normalized_section)
    info_signals = (
        info_class_meta.get("info_signals")
        if isinstance(info_class_meta, dict)
        else None
    )
    guest_policy_signal = bool(
        isinstance(info_signals, dict) and info_signals.get("guest")
    )
    carryover_followup = legacy._looks_like_carryover_followup(message_text)
    hours_followup = legacy._looks_like_hours_followup(message_text)
    expected_reply_followup = bool(
        expected_reply_shortcircuit and current_goal != "booking"
    )
    normalized_carryover = normalize_for_matching(message_text) if message_text else ""
    service_request_signal = bool(
        normalized_carryover
        and client_slug
        and _matches_service_request_lexicon(normalized_carryover, client_slug)
    )
    explicit_service_signal = bool(
        message_text
        and _has_explicit_service_signal(
            message_text,
            client_slug=client_slug,
            intent_decomp_payload=intent_decomp_payload,
        )
    )
    guest_lexicon_hit = bool(
        message_text
        and client_slug
        and _matches_guest_policy_lexicon(message_text, client_slug=client_slug)
    )
    if explicit_service_signal and guest_policy_signal and not guest_lexicon_hit:
        guest_policy_signal = False
        if isinstance(info_signals, dict):
            info_signals["guest"] = False
            info_class_meta["info_signals"] = info_signals
    basic_info_message = bool(
        {"location", "hours"} & info_class_intents
        or (
            isinstance(info_signals, dict)
            and (info_signals.get("parking") or info_signals.get("guest"))
        )
    )
    allow_service_carryover = bool(
        (carryover_followup or expected_reply_followup)
        and not basic_info_message
        and not service_request_signal
        and not explicit_service_signal
    )
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
                get_pack_service_hint(message_text, client_slug=client_slug)
            )
            short_noisy_followup = not has_digits and "?" not in message_text and not has_service_hint
    preserve_info_carryover = bool(
        (carryover_followup or hours_followup or (openai_key_missing and short_noisy_followup))
        and not explicit_service_signal
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
        existing_service_carryover = _get_service_carryover(
            context_manager, message_count=message_count
        )
        if (
            (basic_info_message or class_carryover or existing_service_carryover)
            and not preserve_info_carryover
            and not force_keep_info_carryover
        ):
            if service_request_signal:
                carryover_reason = "service_request"
            elif explicit_service_signal:
                carryover_reason = "explicit_service"
            else:
                carryover_reason = "basic_info_lock" if basic_info_message else "no_followup"
            if saved_message:
                _update_message_decision_metadata(
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
    consult_context_active = bool(
        isinstance(consult_context, dict)
        and (
            consult_context.get("topic")
            or consult_context.get("question")
            or consult_context.get("questions")
        )
    )
    consult_booking_signal = bool(booking_signal)
    if not consult_booking_signal and message_text:
        consult_booking_signal = _is_booking_request(
            message_text,
            client_slug=client_slug,
        )
    if (
        consult_context_active
        and not consult_intent
        and (consult_interrupt_intents or consult_booking_signal)
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
                            "canonical_state_owner": carryover.get("canonical_state_owner"),
                            "projection_source": carryover.get("projection_source"),
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
                        "canonical_state_owner": carryover.get("canonical_state_owner"),
                        "projection_source": carryover.get("projection_source"),
                    },
                )
    intent_decomp_has_booking = "booking" in intent_decomp_set
    intent_decomp_info = intent_decomp_set & legacy.BOOKING_INFO_QUESTION_TYPES
    booking_slot_override = booking_slot_signal and (
        not intent_decomp_used or not intent_decomp_set or intent_decomp_set <= {"other"}
    )
    preserve_booking_signal_on_expected_service_turn = bool(
        booking_expected_reply_turn
        and expected_reply_type == EXPECTED_REPLY_SERVICE
        and direct_booking_request
    )
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
            elif (
                intent_decomp_used
                and intent_decomp_set
                and intent_decomp_set != {"other"}
                and not booking_slot_override
            ):
                booking_block_meta = {
                    "booking_blocked_reason": "intent_decomp_no_booking",
                }
            elif not intent_decomp_used and not booking_slot_override:
                if preserve_booking_signal_on_expected_service_turn:
                    legacy._record_decision_trace(
                        conversation,
                        {
                            "stage": "booking_gate",
                            "decision": "booking_expected_reply_turn_preserved",
                            "expected_reply_type": expected_reply_type,
                            "reason": "direct_booking_request",
                        },
                    )
                    if saved_message:
                        legacy._update_message_decision_metadata(
                            saved_message,
                            {"booking_expected_reply_turn_preserved": True},
                        )
                else:
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
    if message_text and is_human_request_message(message_text):
        if booking_signal or booking_wants_flow:
            booking_signal = False
            booking_wants_flow = False
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "booking_gate",
                    "decision": "booking_bypass_human_request",
                    "booking_bypassed_reason": "human_request",
                },
            )
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message,
                    {"booking_bypassed_reason": "human_request"},
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
            context = legacy._set_booking_context(context, booking_state)
            legacy._set_conversation_context(conversation, context)
            booking_active = False
            booking = booking_state
        booking_signal = False
        booking_wants_flow = False
    booking_blocked = bool(booking_block_meta)

    if saved_message:
        intent_snapshot = _compact_signal_snapshot(
            {
                "used": intent_decomp_used,
                "intents": intent_decomp_intents,
                "primary": intent_decomp_primary,
                "secondary": intent_decomp_secondary,
                "multi_intent": intent_decomp_multi,
                "service_query": intent_decomp_service_query,
                "consult_intent": consult_intent,
                "consult_topic": consult_topic,
                "consult_question": consult_question,
            }
        )
        info_snapshot = _compact_signal_snapshot(
            {
                "intents": sorted(info_class_intents),
                "signals": info_signals if isinstance(info_signals, dict) else None,
                "guest_policy_signal": guest_policy_signal,
                "basic_info_message": basic_info_message,
            }
        )
        booking_snapshot = _compact_signal_snapshot(
            {
                "signal": booking_signal,
                "slot_signal": booking_slot_signal,
                "blocked": booking_blocked,
                "blocked_reason": (
                    booking_block_meta.get("booking_blocked_reason")
                    if isinstance(booking_block_meta, dict)
                    else None
                ),
                "active": booking_active,
                "wants_flow": booking_wants_flow,
                "expected_reply_type": expected_reply_type,
                "expected_reply_reason": expected_reply_reason,
                "expected_reply_shortcircuit": expected_reply_shortcircuit,
            }
        )
        _update_message_signal_snapshot(
            saved_message,
            _compact_signal_snapshot(
                {
                    "intent_decomp": intent_snapshot,
                    "info_class": info_snapshot,
                    "booking": booking_snapshot,
                }
            ),
        )

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
    expected_reply_blocked_by_info: bool,
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
    booking_interrupt_controller_eligible = bool(
        booking_wants_flow and expected_reply_blocked_by_info
    )
    controller_should_attempt = bool(
        routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
        and (not booking_wants_flow or booking_interrupt_controller_eligible)
        and not expected_reply_shortcircuit
        and _current_openai_api_key()
    )
    controller_budget_remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if (
        controller_should_attempt
        and controller_budget_remaining_ms is not None
        and controller_budget_remaining_ms <= WEBHOOK_CONTROLLER_MIN_BUDGET_MS
    ):
        controller_should_attempt = False
        controller_state["error"] = "budget_reserved"
        controller_state["fallback_reason"] = "budget_reserved"
        controller_state["used_reason"] = "budget_guard"
        controller_state["budget_remaining_ms"] = round(controller_budget_remaining_ms, 2)
        controller_state["budget_required_ms"] = round(WEBHOOK_CONTROLLER_MIN_BUDGET_MS, 2)
        controller_state["output"] = legacy._build_controller_meta_output(
            error="budget_exceeded"
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
    explicit_service_signal = _has_explicit_service_signal(
        message_text,
        client_slug=client_slug,
        intent_decomp_payload=intent_decomp_payload,
    )
    class_router_result = legacy._resolve_class_router_result(
        info_intents=info_class_intents,
        info_meta=info_class_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        router_state=router_state,
        explicit_service_signal=explicit_service_signal,
    )
    out_of_domain_signal = class_router_result["out_of_domain_signal"]
    in_signals = class_router_result.get("in_signals") or []
    if not in_signals and message_text and not expected_reply_shortcircuit:
        fallback_info_intents, fallback_info_meta = _detect_info_class_intents(
            message_text,
            intent_decomp_set=set(),
            client_slug=client_slug,
        )
        if fallback_info_intents:
            class_router_result = legacy._resolve_class_router_result(
                info_intents=fallback_info_intents,
                info_meta=fallback_info_meta,
                booking_signal=booking_signal,
                class_carryover=class_carryover,
                domain_intent=domain_intent,
                domain_meta=domain_meta,
                router_state=router_state,
                explicit_service_signal=explicit_service_signal,
            )
            out_of_domain_signal = class_router_result["out_of_domain_signal"]
            in_signals = class_router_result.get("in_signals") or []
    controller_booking_hint = False
    controller_meta_hint = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_output_hint = (
        controller_meta_hint.get("output") if isinstance(controller_meta_hint, dict) else None
    )
    if isinstance(controller_output_hint, dict):
        controller_goal_hint = controller_output_hint.get("goal")
        controller_class_hint = controller_output_hint.get("class")
        controller_booking_hint = (
            isinstance(controller_goal_hint, str)
            and controller_goal_hint.strip().casefold() in {"booking", "reschedule", "cancel_request"}
        ) or (
            isinstance(controller_class_hint, str)
            and controller_class_hint.strip().casefold() == "booking"
        )
    if (
        conversation.state == legacy.ConversationState.BOT_ACTIVE.value
        and intent == Intent.OTHER
        and not expected_reply_shortcircuit
        and not in_signals
        and not out_of_domain_signal
        and not controller_booking_hint
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
        "explicit_service_signal": explicit_service_signal,
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
        intent_value = getattr(signals.intent, "value", None)
        domain_snapshot = _compact_signal_snapshot(
            {
                "intent": getattr(domain_intent, "value", None),
                "in_score": domain_in_score,
                "out_score": domain_out_score,
                "in_hits": domain_meta.get("in_hits"),
                "out_hits": domain_meta.get("out_hits"),
                "strict_in_hits": domain_meta.get("strict_in_hits"),
                "matched_in": domain_meta.get("matched_in"),
                "matched_out": domain_meta.get("matched_out"),
                "matched_strict_in": domain_meta.get("matched_strict_in"),
                "in_threshold": domain_meta.get("in_threshold"),
                "out_threshold": domain_meta.get("out_threshold"),
                "margin": domain_meta.get("margin"),
                "in_hit_threshold": domain_meta.get("in_hit_threshold"),
                "out_hit_threshold": domain_meta.get("out_hit_threshold"),
                "strict_in_hit_threshold": domain_meta.get("strict_in_hit_threshold"),
                "anchors_in": domain_meta.get("anchors_in"),
                "anchors_out": domain_meta.get("anchors_out"),
                "strict_in_anchors": domain_meta.get("strict_in_anchors"),
            }
        )
        controller_snapshot = _compact_signal_snapshot(
            {
                "used": controller_used,
                "attempted": controller_attempted,
                "fallback": controller_fallback,
                "low_confidence": controller_low_confidence,
                "confidence": controller_confidence,
                "goal": controller_goal,
                "error": controller_error,
                "fallback_reason": class_router_result.get("controller_fallback_reason"),
            }
        )
        class_router_snapshot = _compact_signal_snapshot(
            {
                "classes": class_router_result.get("classes"),
                "intents": class_router_result.get("intents"),
                "in_signals": class_router_result.get("in_signals"),
                "out_signals": class_router_result.get("out_signals"),
                "explicit_service_signal": explicit_service_signal,
                "out_of_domain_signal": out_of_domain_signal,
                "router_fallback_reason": class_router_result.get("router_fallback_reason"),
                "controller": controller_snapshot or None,
            }
        )
        signal_snapshot = _compact_signal_snapshot(
            {
                "intent_signals": _compact_signal_snapshot(
                    {
                        "intent": intent_value,
                        "is_greeting": signals.is_greeting,
                        "is_thanks": signals.is_thanks,
                        "is_ack": signals.is_ack,
                        "is_low_signal": signals.is_low_signal,
                        "is_status_question": signals.is_status_question,
                    }
                ),
                "domain_router": domain_snapshot,
                "class_router": class_router_snapshot,
                "pack_index": _extract_pack_index_meta(client_config),
                "compiled_pack": _extract_compiled_pack_meta(client_config),
            }
        )
        _update_message_signal_snapshot(saved_message, signal_snapshot)

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
BOOK_SLOT_TOOL_ACTION = "calendar.book_slot"
DEFAULT_MANAGER_REQUEST_MESSAGE = "Клиент запросил менеджера."
DEFAULT_BOOKING_CLARIFY_MESSAGE = "Клиент ожидает уточнение по записи."
WEEKEND_RELATIVE_DAY_TOKEN = "в субботу"
_CARRYOVER_CAPACITY_LEAD_PREFIX = "скольк"
_CARRYOVER_CAPACITY_TOKENS = ("мест",)
_KAZAKH_LANGUAGE_HINT_TOKENS = ("қазақша", "казах", "қазақ", "қазак")
_RUSSIAN_LANGUAGE_HINT_TOKENS = ("по-русски", "русск")
_MEMORY_CONSENT_REPLY_TOKENS = ("ответьте", "да", "нет")
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
WEBHOOK_PIPELINE_BUDGET_DEFAULT_MS = 18000
WEBHOOK_BOOKING_CRITICAL_PATH_RESERVE_DEFAULT_MS = 4500.0
WEBHOOK_MULTI_INTENT_MIN_BUDGET_DEFAULT_MS = 2200.0
WEBHOOK_CONTROLLER_MIN_BUDGET_DEFAULT_MS = 2600.0
WEBHOOK_SECONDARY_LLM_MIN_BUDGET_DEFAULT_MS = 1200.0


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


def _get_positive_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return value


WEBHOOK_BOOKING_CRITICAL_PATH_RESERVE_MS = _get_positive_float_env(
    "WEBHOOK_BOOKING_CRITICAL_PATH_RESERVE_MS",
    WEBHOOK_BOOKING_CRITICAL_PATH_RESERVE_DEFAULT_MS,
)
WEBHOOK_MULTI_INTENT_MIN_BUDGET_MS = _get_positive_float_env(
    "WEBHOOK_MULTI_INTENT_MIN_BUDGET_MS",
    WEBHOOK_MULTI_INTENT_MIN_BUDGET_DEFAULT_MS,
)
WEBHOOK_CONTROLLER_MIN_BUDGET_MS = _get_positive_float_env(
    "WEBHOOK_CONTROLLER_MIN_BUDGET_MS",
    WEBHOOK_CONTROLLER_MIN_BUDGET_DEFAULT_MS,
)
WEBHOOK_SECONDARY_LLM_MIN_BUDGET_MS = _get_positive_float_env(
    "WEBHOOK_SECONDARY_LLM_MIN_BUDGET_MS",
    WEBHOOK_SECONDARY_LLM_MIN_BUDGET_DEFAULT_MS,
)


def _remaining_pipeline_budget_ms(timing_context: dict | None) -> float | None:
    if not isinstance(timing_context, dict):
        return None
    deadline = timing_context.get("pipeline_deadline")
    if deadline is None:
        return None
    try:
        remaining = (float(deadline) - time.monotonic()) * 1000.0
    except (TypeError, ValueError):
        return None
    return max(remaining, 0.0)


def _should_skip_secondary_llm_stage(
    *,
    timing_context: dict | None,
    min_remaining_ms: float,
) -> tuple[bool, float | None]:
    remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if remaining_ms is None:
        return False, None
    return remaining_ms <= max(float(min_remaining_ms), 0.0), remaining_ms


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _semantic_arbitration_enabled() -> bool:
    return _is_env_enabled(
        os.environ.get("LLM_POLICY_CORE_SEMANTIC_ARBITRATION"),
        default=True,
    )


def _single_semantic_owner_hard_lock_enabled() -> bool:
    # Single semantic owner is a contract invariant for runtime-core.
    return True


def _llm_first_firebreak_enabled() -> bool:
    return _is_env_enabled(
        os.environ.get("LLM_POLICY_CORE_LLM_FIRST_FIREBREAK"),
        default=False,
    )


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
    re.compile(r"\b(прислать|отправить|скинуть)\s+(фото|картин\w+|референс\w*)\b"),
    re.compile(r"\b(send|share|upload)\s+(a\s+)?(photo|picture|reference)\b"),
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


_OBSERVABILITY_REASONS_PROTECTED = {
    "law_gate",
    "policy_gate",
    "pending",
    "guard_not_eligible",
    "expected_reply_deferred",
    "none",
}


def _contains_any_text_token(text: str | None, tokens: tuple[str, ...]) -> bool:
    if not isinstance(text, str) or not text:
        return False
    return any(token in text for token in tokens)


def _contains_all_text_tokens(text: str | None, tokens: tuple[str, ...]) -> bool:
    if not isinstance(text, str) or not text:
        return False
    return all(token in text for token in tokens)


def _pad_surface_token(value: str | None) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return " ".join(("", value, ""))


def _set_policy_core_tool_observability(message: Message | None) -> None:
    if not message:
        return
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    if decision_meta.get("controller_attempted") is True:
        return
    router_reason = (
        decision_meta.get("router_skipped_reason").strip().lower()
        if isinstance(decision_meta.get("router_skipped_reason"), str)
        else ""
    )
    controller_reason = (
        decision_meta.get("controller_skipped_reason").strip().lower()
        if isinstance(decision_meta.get("controller_skipped_reason"), str)
        else ""
    )
    if (
        router_reason in _OBSERVABILITY_REASONS_PROTECTED
        or controller_reason in _OBSERVABILITY_REASONS_PROTECTED
    ):
        return
    updates: dict[str, Any] = {}
    if decision_meta.get("router_eligible") is not True:
        updates["router_eligible"] = True
    if decision_meta.get("controller_eligible") is not True:
        updates["controller_eligible"] = True
    if router_reason in {"", "not_run"}:
        updates["router_skipped_reason"] = "policy_core_tool"
    if controller_reason in {"", "not_run"}:
        updates["controller_skipped_reason"] = "policy_core_tool"
    if updates:
        _update_message_decision_metadata(message, updates)


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


MARKETING_REPLY_CONTEXT_LOOKBACK_HOURS = 72
MARKETING_REPLY_CONTEXT_AMBIGUITY_WINDOW_HOURS = 6
MARKETING_REPLY_CONTEXT_ATTACHABLE_STATUSES = {"queued", "sent", "delivered", "pending"}


def _record_marketing_reply_context_skip(conversation: Conversation, *, reason: str) -> None:
    _record_decision_trace(
        conversation,
        {
            "stage": "marketing_reply_context",
            "decision": "skipped",
            "reason": reason,
        },
    )


def _maybe_attach_marketing_reply_context(
    db: Session,
    *,
    conversation: Conversation | None,
    saved_message: Message | None,
    now: datetime,
) -> dict[str, Any] | None:
    if not conversation or not saved_message:
        return None

    # Keep marketing context scoped to the current inbound only.
    context = _get_conversation_context(conversation)
    if "marketing_context" in context:
        context.pop("marketing_context", None)
        _set_conversation_context(conversation, context)

    inbound_text = str(getattr(saved_message, "content", "") or "").strip()
    if not inbound_text:
        _record_marketing_reply_context_skip(conversation, reason="empty_text")
        return None
    if _is_placeholder_text(inbound_text):
        _record_marketing_reply_context_skip(conversation, reason="placeholder_text")
        return None

    lookback_start = now - timedelta(hours=MARKETING_REPLY_CONTEXT_LOOKBACK_HOURS)
    rows_result = (
        db.query(MarketingCampaignDelivery)
        .join(MarketingCampaign, MarketingCampaign.id == MarketingCampaignDelivery.campaign_id)
        .filter(
            MarketingCampaignDelivery.client_id == conversation.client_id,
            MarketingCampaignDelivery.conversation_id == conversation.id,
            MarketingCampaignDelivery.created_at >= lookback_start,
        )
        .order_by(MarketingCampaignDelivery.created_at.desc(), MarketingCampaignDelivery.id.desc())
        .limit(2)
        .all()
    )
    rows = rows_result if isinstance(rows_result, list) else []
    if not rows:
        _record_marketing_reply_context_skip(conversation, reason="no_recent_delivery")
        return None

    eligible_rows: list[tuple[MarketingCampaignDelivery, MarketingCampaign, str]] = []
    for row in rows:
        delivery = row
        campaign: MarketingCampaign | None = None
        if isinstance(row, (tuple, list)):
            delivery = row[0]
            if len(row) > 1 and hasattr(row[1], "id"):
                campaign = row[1]
        if campaign is None:
            campaign = (
                db.query(MarketingCampaign)
                .filter(MarketingCampaign.id == getattr(delivery, "campaign_id", None))
                .first()
            )
        if not campaign:
            continue

        outbox_status = ""
        if isinstance(row, (tuple, list)) and len(row) > 2 and isinstance(row[2], str):
            outbox_status = row[2].strip().upper()
        else:
            outbox_id = getattr(delivery, "outbox_id", None)
            if outbox_id:
                outbox_row = db.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).first()
                candidate_status = getattr(outbox_row, "status", None)
                if isinstance(candidate_status, str):
                    outbox_status = candidate_status.strip().upper()
        if campaign.client_id != conversation.client_id:
            continue
        created_at = getattr(delivery, "created_at", None)
        if isinstance(created_at, datetime) and created_at < lookback_start:
            continue
        status_before = (delivery.status or "queued").strip().lower() or "queued"
        if status_before not in MARKETING_REPLY_CONTEXT_ATTACHABLE_STATUSES:
            continue
        if outbox_status == "FAILED":
            continue
        eligible_rows.append((delivery, campaign, status_before))

    if not eligible_rows:
        _record_marketing_reply_context_skip(conversation, reason="no_eligible_delivery")
        return None

    if len(eligible_rows) > 1:
        latest_created_at = getattr(eligible_rows[0][0], "created_at", None)
        second_created_at = getattr(eligible_rows[1][0], "created_at", None)
        if isinstance(latest_created_at, datetime) and isinstance(second_created_at, datetime):
            ambiguity_window = timedelta(hours=MARKETING_REPLY_CONTEXT_AMBIGUITY_WINDOW_HOURS)
            if (latest_created_at - second_created_at) <= ambiguity_window:
                _record_marketing_reply_context_skip(
                    conversation,
                    reason="ambiguous_recent_deliveries",
                )
                return None

    delivery, campaign, status_before = eligible_rows[0]

    if status_before not in MARKETING_REPLY_CONTEXT_ATTACHABLE_STATUSES:
        _record_marketing_reply_context_skip(conversation, reason="non_attachable_status")
        return None

    delivery.status = "replied"
    delivery.updated_at = now
    db.add(delivery)

    marketing_context = {
        "campaign_id": str(campaign.id),
        "campaign_name": campaign.name,
        "delivery_id": str(delivery.id),
        "status_before": status_before,
        "attached_at": now.isoformat(),
    }

    _update_message_decision_metadata(
        saved_message,
        {
            "marketing_reply_context": True,
            "marketing_campaign_id": str(campaign.id),
            "marketing_campaign_name": campaign.name,
            "marketing_delivery_id": str(delivery.id),
            "marketing_delivery_status_before": status_before,
        },
    )
    _record_decision_trace(
        conversation,
        {
            "stage": "marketing_reply_context",
            "decision": "linked",
            "campaign_id": str(campaign.id),
            "delivery_id": str(delivery.id),
            "status_before": status_before,
        },
    )
    context = _get_conversation_context(conversation)
    context["marketing_context"] = marketing_context
    _set_conversation_context(conversation, context)
    return marketing_context


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
    "Передал менеджеру — сообщения уходят администратору. Пока ждём ответ, могу помочь с услугами, ценами и записью. "
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
MSG_PENDING_LOW_CONFIDENCE = (
    "Я уже передал менеджеру — он скоро подключится. "
    "Пока ждём, уточните: услуги/цены или запись/адрес."
)
MSG_PENDING_ESCALATION = (
    "Я уже передал менеджеру — сообщения уходят администратору. "
    "Пока ждём ответ, могу помочь с услугами, ценами и записью."
)
MSG_PENDING_STATUS = (
    "Да, передал. Сейчас менеджер ещё не взял заявку. "
    "Пока ждём ответ, могу помочь с услугами, ценами и записью."
)
MSG_PENDING_RESCHEDULE = (
    "Перенос записи подтверждает администратор. Передам ваш запрос. "
    "Пока ждём ответ, могу помочь с услугами, ценами и записью."
)
MSG_PENDING_COMPLAINT = (
    "Жаль, что так вышло. Передам администратору, разберутся. "
    "Пока ждём ответ, могу помочь с услугами, ценами и записью."
)
MSG_PENDING_WAIT = "Менеджер подключится. Пока ждём ответ, могу помочь с услугами, ценами и записью."
MSG_PENDING_SLA_PING = (
    "Напоминаю: менеджер ещё не подключился. "
    "Если всё актуально — напишите детали, я передам администратору."
)
MSG_PENDING_AUTO_CLOSE = "Закрываю ожидание. Если всё ещё актуально — напишите, я помогу."
MSG_PENDING_ACK = "Хорошо. Напишите, что именно нужно: цена/запись/адрес/мастер."
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
    "Пока ждём ответ, могу помочь с услугами, ценами и записью. "
    "Чтобы ускорить, напишите услугу, дату/время и имя."
)
MSG_STYLE_REFERENCE_NEED_MEDIA = (
    "Да, конечно. Можем ориентироваться на фото/референс. Пришлите фото и кратко опишите запрос — "
    "я передам администратору для подтверждения."
)
MSG_STYLE_REFERENCE_NEED_MEDIA_BOOKING = (
    "Да, конечно. Можем ориентироваться на фото/референс. "
    "Пришлите фото и кратко опишите пожелание."
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
MEMORY_POLICY_RETRIEVAL_MAX_ITEMS = max(
    int(os.environ.get("MEMORY_POLICY_RETRIEVAL_MAX_ITEMS", "4")),
    1,
)
MEMORY_POLICY_RETRIEVAL_MAX_VALUE_CHARS = max(
    int(os.environ.get("MEMORY_POLICY_RETRIEVAL_MAX_VALUE_CHARS", "120")),
    40,
)
MEMORY_POLICY_RETRIEVAL_MIN_TOKEN_LEN = max(
    int(os.environ.get("MEMORY_POLICY_RETRIEVAL_MIN_TOKEN_LEN", "2")),
    1,
)
MEMORY_POLICY_RETRIEVAL_BLOCKED_KEYS = {"phone", "customer_phone", "contact_phone"}

MSG_BOOKING_ASK_PHONE = "Подскажите, пожалуйста, номер телефона для подтверждения записи."
MSG_BOOKING_ASK_REFERENCE = (
    "Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи."
)
MSG_BOOKING_ASK_ALL = "Чтобы записать, пожалуйста, напишите: услуга, точная дата, точное время, имя, контактный номер."
MSG_BOOKING_SLOT_LOCK_STUB = "Я помогаю только по вопросам салона и записи."
MSG_BOOKING_CANCELLED = "Хорошо, если передумаете — пишите."
MSG_BOOKING_REENGAGE = "Хотите продолжить запись? Если да — напишите услугу."

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
EXPECTED_REPLY_PHONE = "phone"
EXPECTED_REPLY_INTENT_CHOICE = "intent_choice"

CLARIFY_MAX_ATTEMPTS = 2
REFUSAL_TTL_MESSAGES = 10
SUMMARY_MESSAGE_THRESHOLD = 12
FACT_GUARD_ENABLED = True
FACT_GUARD_INTENT = "fact_guard"
FACT_GUARD_SKIP_INTENTS = {"service_clarify", "duration_or_price_clarify"}
FACT_GUARD_MAX_ATTEMPTS = 1
FACT_GUARD_BLOCKED_TOOL_DECISIONS = {
    "missing_slot",
    "not_found",
    "branch_missing",
    "provider_unavailable",
    "error",
    "contract_invalid",
    "verifier_blocked",
    "service_not_found",
}
MSG_FACT_GUARD_CLARIFY = "Подскажите, пожалуйста, что именно вас интересует?"

ROUTING_MATRIX = {
    ConversationState.BOT_ACTIVE.value: {
        "allow_booking_flow": True,
        "allow_truth_gate_reply": True,
        "allow_handover_create": True,
        "allow_bot_reply": True,
    },
    ConversationState.PENDING.value: {
        "allow_booking_flow": True,
        "allow_truth_gate_reply": True,
        "allow_handover_create": False,
        "allow_bot_reply": True,
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

TIME_PATTERN = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)")
TIME_HOUR_PATTERN = re.compile(r"\b(?:в|к)\s*(?:[01]?\d|2[0-3])\b", re.IGNORECASE)
TIME_ONLY_AMPM_PATTERN = re.compile(r"^\d{1,2}(?:am|pm)$", re.IGNORECASE)
TIME_ONLY_ALLOWED_TOKENS = {
    "в",
    "во",
    "к",
    "ко",
    "на",
    "около",
    "примерно",
    "после",
    "до",
    "ну",
    "э",
    "м",
}
TIME_ONLY_ALLOWED_PREFIXES = ("час", "мин", "вечер", "утр", "дн", "ноч")
DATE_PATTERN = re.compile(
    r"\b(?:сегодня|сегодняш\w*|завтра|завтраш\w*|послезавтра|послезавтраш\w*|понедель\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскрес\w*|выходн\w*|утром|днем|днём|вечером)\b",
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
    if expected_reply_type == EXPECTED_REPLY_TIME:
        exact_daypart_fill = _extract_question_like_daypart_exact_time_fill(message_text)
        if exact_daypart_fill:
            return True, exact_daypart_fill, ["question_like_daypart_exact_time"]
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
    if expected_reply_type == EXPECTED_REPLY_PHONE:
        return "phone"
    return None


def _booking_prompt_for_expected_reply_type(expected_reply_type: str | None) -> str | None:
    if expected_reply_type == EXPECTED_REPLY_SERVICE:
        return MSG_BOOKING_ASK_SERVICE
    if expected_reply_type == EXPECTED_REPLY_TIME:
        return MSG_BOOKING_ASK_DATETIME
    if expected_reply_type == EXPECTED_REPLY_NAME:
        return MSG_BOOKING_ASK_NAME
    if expected_reply_type == EXPECTED_REPLY_PHONE:
        return MSG_BOOKING_ASK_PHONE
    return None


PENDING_QUESTION_ACT_VALUES = {
    "fill_requested_slot",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
}
PENDING_QUESTION_TARGET_VALUES = {
    "time",
    "specialist",
}
ACTIVE_QUESTION_RELATION_VALUES = {
    "fill_requested_slot",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
    "referent_followup",
    "generic_info_interrupt",
    "specialist_availability_interrupt",
    "specialist_availability_followup",
    "tool_result_followup_specialist_missing",
}


def _normalize_pending_question_act(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().casefold()
    if token in PENDING_QUESTION_ACT_VALUES:
        return token
    return None


def _normalize_pending_question_target(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().casefold()
    if token in PENDING_QUESTION_TARGET_VALUES:
        return token
    return None


def _normalize_active_question_relation(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().casefold()
    if token in ACTIVE_QUESTION_RELATION_VALUES:
        return token
    return None


def _is_time_pending_question_guidance_act(
    pending_question_act: str | None,
    pending_question_target: str | None,
) -> bool:
    if pending_question_act not in {"ask_about_requested_slot", "slot_compare"}:
        return False
    return pending_question_target in {None, "time"}


def _expected_reply_type_for_slot_key(slot_key: str | None) -> str | None:
    if slot_key == "service":
        return EXPECTED_REPLY_SERVICE
    if slot_key == "datetime":
        return EXPECTED_REPLY_TIME
    if slot_key == "name":
        return EXPECTED_REPLY_NAME
    if slot_key == "phone":
        return EXPECTED_REPLY_PHONE
    return None


def _derive_booking_followup_prompt(
    *,
    expected_reply_type: str | None,
    booking_state: dict | None,
    merged_slots: dict[str, str] | None,
    client_slug: str | None,
) -> tuple[str | None, str | None]:
    followup_state, derived_expected, prompt = _derive_booking_followup_contract(
        expected_reply_type=expected_reply_type,
        booking_state=booking_state,
        merged_slots=merged_slots,
        client_slug=client_slug,
    )
    del followup_state
    return derived_expected, prompt


def _derive_booking_followup_contract(
    *,
    expected_reply_type: str | None,
    booking_state: dict | None,
    merged_slots: dict[str, str] | None,
    client_slug: str | None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if expected_reply_type not in {
        EXPECTED_REPLY_SERVICE,
        EXPECTED_REPLY_TIME,
        EXPECTED_REPLY_NAME,
        EXPECTED_REPLY_PHONE,
    }:
        return None, None, None
    followup_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    if followup_state.get("active") is not True:
        followup_state["active"] = True
    if isinstance(merged_slots, dict):
        for slot_key in BOOKING_SLOT_ORDER:
            slot_value = merged_slots.get(slot_key)
            if not isinstance(slot_value, str) or not slot_value.strip():
                continue
            normalized_slot = slot_value.strip()
            if slot_key == "datetime":
                followup_state[slot_key] = normalized_slot
            elif not followup_state.get(slot_key):
                followup_state[slot_key] = normalized_slot
    followup_state, prompt = _next_booking_prompt(
        followup_state,
        client_slug=client_slug,
    )
    derived_expected = _expected_reply_for_booking_question(followup_state.get("last_question"))
    if derived_expected not in {
        EXPECTED_REPLY_SERVICE,
        EXPECTED_REPLY_TIME,
        EXPECTED_REPLY_NAME,
        EXPECTED_REPLY_PHONE,
    }:
        return None, None, None
    return (
        followup_state,
        derived_expected,
        prompt or _booking_prompt_for_expected_reply_type(derived_expected),
    )


def _derive_timeout_completed_booking_state(
    *,
    matched_expected_reply_type: str | None,
    booking_state: dict[str, Any] | None,
    filled_slots: Any,
    client_slug: str | None,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    if matched_expected_reply_type not in {
        EXPECTED_REPLY_SERVICE,
        EXPECTED_REPLY_TIME,
        EXPECTED_REPLY_NAME,
        EXPECTED_REPLY_PHONE,
    }:
        return None, ()
    if not isinstance(booking_state, dict):
        return None, ()
    normalized_filled_slots = tuple(
        slot_key.strip()
        for slot_key in (filled_slots or ())
        if isinstance(slot_key, str) and slot_key.strip()
    )
    if not normalized_filled_slots:
        return None, ()
    completed_booking_state = dict(booking_state)
    if completed_booking_state.get("active") is not True:
        completed_booking_state["active"] = True
    if _booking_has_reference(completed_booking_state):
        return None, ()
    if not _plan_has_complete_booking_slots(
        completed_booking_state,
        client_slug=client_slug,
    ):
        return None, ()
    return completed_booking_state, normalized_filled_slots


def _timeout_booking_completion_override(action: str | None) -> tuple[str, str]:
    normalized_action = (
        action.strip().casefold() if isinstance(action, str) and action.strip() else ""
    )
    if normalized_action in {"escalate", "handoff", "pending_escalation"}:
        return "escalate", "handoff"
    if normalized_action in {"booking_confirm", "booking_prompt", "check_booking_prompt"}:
        return normalized_action, "collect"
    if normalized_action == "reply":
        return "reply", "reply"
    return "booking_prompt", "collect"


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
    if expected_reply_type == EXPECTED_REPLY_PHONE:
        return normalize_phone_digits(cleaned)
    return None


def _resolve_alternate_booking_slot_capture(
    *,
    expected_reply_type: str | None,
    detected_slot: str | None,
    answer_value: str | None,
    message_text: str | None,
    client_slug: str | None,
) -> tuple[str | None, str | None]:
    expected_slot_key = _expected_reply_slot_key(expected_reply_type)
    normalized_detected_slot = (
        detected_slot.strip() if isinstance(detected_slot, str) and detected_slot.strip() else None
    )
    if (
        expected_slot_key not in BOOKING_SLOT_ORDER
        or normalized_detected_slot not in BOOKING_SLOT_ORDER
        or normalized_detected_slot == expected_slot_key
    ):
        return None, None
    alternate_reply_type = _expected_reply_type_for_slot_key(normalized_detected_slot)
    if alternate_reply_type is None:
        return None, None
    candidate_values: list[str] = []
    for raw_candidate in (answer_value, message_text):
        if isinstance(raw_candidate, str) and raw_candidate.strip():
            cleaned_candidate = raw_candidate.strip()
            if cleaned_candidate not in candidate_values:
                candidate_values.append(cleaned_candidate)
    for candidate_value in candidate_values:
        validated_value = _validate_expected_reply_value(
            expected_reply_type=alternate_reply_type,
            value=candidate_value,
            client_slug=client_slug,
        )
        if validated_value:
            return normalized_detected_slot, validated_value
    return None, None


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


def _merge_lang_phrase_maps(*maps: dict[str, Any] | None) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for mapping in maps:
        if not isinstance(mapping, dict):
            continue
        for lang_key, phrases in mapping.items():
            if not isinstance(phrases, list):
                continue
            bucket = merged.setdefault(lang_key, [])
            for phrase in phrases:
                if not isinstance(phrase, str):
                    continue
                cleaned = phrase.strip()
                if cleaned and cleaned not in bucket:
                    bucket.append(cleaned)
    return merged


def _collect_booking_request_lexicon(client_slug: str | None) -> dict[str, list[str]]:
    system_lexicons = load_system_lexicons()
    system_booking = (
        system_lexicons.get("booking_request") if isinstance(system_lexicons, dict) else None
    )
    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    synonyms = domain_pack.get("synonyms") if isinstance(domain_pack, dict) else None
    domain_booking = (
        synonyms.get("booking") if isinstance(synonyms, dict) else None
    )
    return _merge_lang_phrase_maps(system_booking, domain_booking)


def _matches_booking_request_lexicon(
    message_text: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    lexicon = _collect_booking_request_lexicon(client_slug)
    if not lexicon:
        return False
    for lang_key in ("ru", "kk", "en"):
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


def _has_explicit_service_signal(
    message_text: str | None,
    *,
    client_slug: str | None,
    intent_decomp_payload: dict[str, Any] | None,
) -> bool:
    from . import _legacy as legacy

    if not message_text:
        return False
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", message_text)
    normalized = _normalize_service_text(cleaned_text)
    if not normalized:
        return False
    if isinstance(intent_decomp_payload, dict):
        raw_query = intent_decomp_payload.get("service_query")
        raw_source = intent_decomp_payload.get("service_query_source")
        if (
            isinstance(raw_query, str)
            and raw_query.strip()
            and raw_source != "context"
        ):
            return True
    if client_slug:
        if _match_service(normalized, client_slug):
            return True
        if _matches_service_request_lexicon(normalized, client_slug):
            return True
        # Guard location/hours/parking info questions from false service-semantic hits.
        info_intents, _ = _detect_info_class_intents(
            cleaned_text,
            intent_decomp_set=set(),
            client_slug=client_slug,
        )
        if {"location", "hours", "parking"} & info_intents:
            return False
        if legacy._extract_service_hint(cleaned_text, client_slug):
            return True
    return False


def _is_booking_request(text: str, *, client_slug: str | None) -> bool:
    if _matches_booking_request_lexicon(text, client_slug=client_slug):
        return True
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    booking_keywords = get_system_lexicon_list("booking_keywords")
    if booking_keywords and _contains_any(normalized, booking_keywords):
        return True
    desire_keywords = get_system_lexicon_list("booking_desire_keywords")
    need_or_desire_signal = bool(desire_keywords and _contains_any(normalized, desire_keywords))
    if not need_or_desire_signal or not client_slug:
        return False
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", text)
    normalized_service = _normalize_service_text(cleaned_text)
    if not normalized_service:
        return False
    if not (
        _match_service(normalized_service, client_slug)
        or _matches_service_request_lexicon(normalized_service, client_slug)
    ):
        return False
    try:
        has_datetime_signal = bool(
            _extract_datetime(
                cleaned_text,
                client_slug=client_slug,
            )
        )
    except TypeError:
        # Some tests patch _extract_datetime with a positional-only stub.
        has_datetime_signal = bool(_extract_datetime(cleaned_text))
    if not has_datetime_signal:
        return False
    info_intents, _ = _detect_info_class_intents(
        cleaned_text,
        intent_decomp_set=set(),
        client_slug=client_slug,
    )
    return not bool({"location", "hours", "parking"} & info_intents)


def _is_booking_cancel(text: str, *, policy_pack: dict | None) -> bool:
    return _detect_booking_cancel(text, policy_pack=policy_pack)


def _extract_service_hint(text: str, client_slug: str | None) -> str | None:
    if not text:
        return None
    if not isinstance(client_slug, str):
        return None
    slug = client_slug.strip()
    if not slug:
        return None
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", text).strip()
    if not cleaned_text:
        return None
    normalized_text = _normalize_text(cleaned_text)
    booking_like = _is_booking_request(cleaned_text, client_slug=slug)
    if not booking_like:
        booking_like = bool(
            TIME_PATTERN.search(cleaned_text)
            or TIME_HOUR_PATTERN.search(cleaned_text)
            or DATE_PATTERN.search(cleaned_text)
            or DATE_NUMERIC_PATTERN.search(cleaned_text)
            or DATE_MONTH_PATTERN.search(cleaned_text)
        )
    domain_intent, _, _, domain_meta = classify_domain_with_scores(cleaned_text, None)
    strict_in_hits = int(domain_meta.get("strict_in_hits") or 0)
    if (
        domain_intent == DomainIntent.OUT_OF_DOMAIN
        and strict_in_hits <= 0
        and not booking_like
    ):
        return None
    match = semantic_service_match(cleaned_text, slug)
    if not match or match.action != "match":
        fallback = get_pack_service_hint(cleaned_text, client_slug=slug)
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
    iso_date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    explicit_date_match = (
        iso_date_match
        or DATE_NUMERIC_PATTERN.search(text)
        or DATE_MONTH_PATTERN.search(text)
    )
    time_match = TIME_PATTERN.search(text) or TIME_HOUR_PATTERN.search(text)
    if explicit_date_match and time_match and explicit_date_match.start() <= time_match.start():
        combined_value = text[explicit_date_match.start() : time_match.end()].strip(" ,.")
        if combined_value:
            return combined_value
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


def _looks_like_time_only_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    time_only_phrases = get_system_lexicon_list("time_only_request_phrases")
    if time_only_phrases and _contains_any(normalized, time_only_phrases):
        return True
    tokens = _tokenize_for_matching(normalized)
    if not tokens:
        return False
    has_time_token = False
    has_time_marker = bool(TIME_PATTERN.search(message_text) or TIME_HOUR_PATTERN.search(message_text))
    for token in tokens:
        if token.isdigit():
            if len(token) <= 2:
                has_time_token = True
                continue
            if has_time_marker and len(token) in (3, 4):
                has_time_token = True
                continue
            return False
        if TIME_ONLY_AMPM_PATTERN.fullmatch(token):
            has_time_token = True
            continue
        if token in TIME_ONLY_ALLOWED_TOKENS:
            continue
        if any(token.startswith(prefix) for prefix in TIME_ONLY_ALLOWED_PREFIXES):
            has_time_marker = True
            continue
        return False
    return has_time_token


def _count_pending_time_question_markers(normalized_message: str | None) -> int:
    if not isinstance(normalized_message, str) or not normalized_message.strip():
        return 0
    markers = get_booking_text_tokens("pending_time_question_markers")
    if not markers:
        return 0
    normalized = normalized_message.strip()
    return sum(1 for marker in markers if marker and marker in normalized)


def _has_timeout_slot_question_info_lock_surface(
    *,
    message_text: str | None,
    client_slug: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if not _is_question_like_message(message_text):
        return False
    normalized_message = normalize_for_matching(message_text)
    if not normalized_message:
        return False
    if _count_pending_time_question_markers(normalized_message) < 2:
        return False
    if _validate_expected_reply_value(
        expected_reply_type=EXPECTED_REPLY_TIME,
        value=message_text,
        client_slug=client_slug,
    ):
        return False
    return True


def _is_timeout_pending_time_slot_question(
    *,
    message_text: str | None,
    client_slug: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    booking_service: str | None,
    intent_decomp_payload: dict[str, Any] | None,
    now: datetime,
) -> bool:
    if (
        expected_reply_type != EXPECTED_REPLY_TIME
        or not isinstance(message_text, str)
        or not message_text.strip()
        or expected_reply_matched is True
        or not expected_reply_blocked_by_info
    ):
        return False
    normalized_message = normalize_for_matching(message_text)
    if not normalized_message:
        return False
    time_preference_statement = _looks_like_time_preference_statement(
        message_text,
        normalized_text=normalized_message,
    )
    question_like = "?" in message_text
    if not question_like:
        tokens = normalized_message.split()
        if tokens:
            question_like = any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)
    if not question_like and not time_preference_statement:
        return False
    time_only_request = _looks_like_time_only_request(message_text)
    # Keep the first-time requested-slot row alive when the question is phrased
    # as "в какое время..." and still carries pending-slot markers.
    if time_only_request and not _has_pending_time_question_marker(normalized_message):
        return False
    if _validate_expected_reply_value(
        expected_reply_type=expected_reply_type,
        value=message_text,
        client_slug=client_slug,
    ):
        return False
    normalized_service_message = _normalize_service_text(message_text)
    if _has_price_signal(normalized_service_message, message_text):
        return False
    if (
        _has_duration_signal(normalized_service_message, message_text)
        and not time_preference_statement
    ):
        return False
    if _has_explicit_location_or_hours_request(
        message_text,
        client_slug=client_slug,
        strict=True,
    ):
        return False
    if _is_style_reference_request(message_text, has_media=False):
        return False
    if _looks_like_booking_verification_request(message_text):
        return False
    if _looks_like_booking_reschedule_request(
        message_text,
        client_slug=client_slug,
    ):
        return False
    try:
        if _extract_datetime(
            message_text,
            client_slug=client_slug,
            relative_base=now,
        ):
            return False
    except TypeError:
        if _extract_datetime(message_text, client_slug=client_slug):
            return False
    master_resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=client_slug,
        service_query=booking_service,
        intent_decomp=intent_decomp_payload,
    )
    if master_resolution.explicit:
        return False
    return bool(
        time_preference_statement
        or
        _has_daypart_stem(normalized_message)
        or _has_pending_time_question_marker(normalized_message)
    )


def _is_timeout_master_info_interrupt_candidate(
    *,
    message_text: str | None,
    client_slug: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    booking_service: str | None,
    intent_decomp_payload: dict[str, Any] | None,
) -> bool:
    if (
        expected_reply_type != EXPECTED_REPLY_NAME
        or not isinstance(message_text, str)
        or not message_text.strip()
        or expected_reply_matched is True
        or not expected_reply_blocked_by_info
    ):
        return False
    master_resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=client_slug,
        service_query=booking_service,
        intent_decomp=intent_decomp_payload if isinstance(intent_decomp_payload, dict) else None,
        force_master_intent=False,
    )
    return bool(master_resolution.explicit)


def _is_timeout_active_time_specialist_interrupt_candidate(
    *,
    message_text: str | None,
    client_slug: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    booking_service: str | None,
    intent_decomp_payload: dict[str, Any] | None,
) -> bool:
    if (
        expected_reply_type != EXPECTED_REPLY_TIME
        or not isinstance(message_text, str)
        or not message_text.strip()
        or expected_reply_matched is True
        or not expected_reply_blocked_by_info
    ):
        return False
    master_resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=client_slug,
        service_query=booking_service,
        intent_decomp=intent_decomp_payload if isinstance(intent_decomp_payload, dict) else None,
        force_master_intent=False,
    )
    return bool(master_resolution.explicit)


BOOKING_INFO_QUESTION_TYPES = {"pricing", "hours", "duration", "location", "parking", "master"}
TOOL_INFO_SECTION_MAP = {
    "catalog.location": ["location"],
    "catalog.portfolio": ["portfolio"],
    "calendar.list_slots": ["hours"],
}
LLM_PLAN_ALLOWED_OUTCOMES = {"fact", "collect", "handoff"}
LLM_PLAN_ALLOWED_TOOL_ACTIONS = {
    "info",
    "consult",
    "booking",
    "handoff",
    "collect",
    "calendar.list_slots",
    "calendar.book_slot",
    "calendar.get_booking",
    "calendar.reschedule",
    "calendar.cancel",
    "catalog.service_query",
    "catalog.location",
    "catalog.portfolio",
}
LLM_POLICY_CORE_ALLOWED_ACTIONS = LLM_PLAN_ALLOWED_OUTCOMES
LLM_POLICY_CORE_ALLOWED_TOOL_ACTIONS = LLM_PLAN_ALLOWED_TOOL_ACTIONS
LLM_POLICY_CORE_LOW_CONFIDENCE_TOOL_ALLOWLIST = {
    "calendar.list_slots",
    "calendar.get_booking",
    "calendar.reschedule",
    "catalog.service_query",
    "catalog.location",
    "catalog.portfolio",
    "info",
    "consult",
    "collect",
}
POLICY_OVERRIDE_REASON_CODES = {
    "safety_policy_block",
    "contract_validation_failure",
    "required_slot_missing",
    "tool_unavailable",
    "timeout_degrade",
    "idempotency_replay_guard",
}
POLICY_OVERRIDE_REASON_DEFAULT = "contract_validation_failure"
SEMANTIC_ARBITER_CONTRACT_VERSION = "v1"
POLICY_TIMEOUT_DEGRADE_CLARIFY_INTENT = "policy_timeout_degrade"
POLICY_TIMEOUT_PENDING_SLOT_QUESTION_INTENT = "policy_timeout_pending_slot_question"
POLICY_TIMEOUT_DEGRADE_MAX_RETRIES = max(
    int(os.environ.get("POLICY_TIMEOUT_DEGRADE_MAX_RETRIES", "1")),
    0,
)
POLICY_TIMEOUT_DEGRADE_FACT_MIN_CONFIDENCE = max(
    min(float(os.environ.get("POLICY_TIMEOUT_DEGRADE_FACT_MIN_CONFIDENCE", "0.58")), 1.0),
    0.0,
)
LLM_POLICY_CORE_ENABLED = _is_env_enabled(
    os.environ.get("LLM_POLICY_CORE_ENABLED"), default=True
)
POLICY_CORE_RESCUE_MATRIX_ENABLED = _is_env_enabled(
    os.environ.get("POLICY_CORE_RESCUE_MATRIX"), default=True
)
POLICY_CORE_RESCUE_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_RESCUE_TIMEOUT_SECONDS", "2.4")),
    0.2,
)
POLICY_CORE_RESCUE_ERROR_CODES = {
    "deadline_exceeded",
    "timeout",
    "invalid_json",
    "invalid_schema",
    "empty_response",
    "connection_error",
    "service_unavailable",
    "rate_limit",
}
CONSULT_INTERRUPT_INTENTS = {"booking", "pricing", "duration", "location", "hours"}
CLASS_CARRYOVER_KEY = "class_carryover"
CLASS_CARRYOVER_TTL_MESSAGES = 4
CLASS_CARRYOVER_CLASSES = {"info_bundle"}
SERVICE_CARRYOVER_KEY = "service_carryover"
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
SESSION_MEMORY_RESET_PHRASES = (
    "новый вопрос",
    "другая тема",
    "начнем сначала",
    "начнём сначала",
    "начнем заново",
    "начнём заново",
    "давай сначала",
)
BOOKING_VERIFICATION_PATTERNS = (
    re.compile(r"\bпров\w*\b.*\b(запис|брон|бронир)\w*"),
    re.compile(r"\bподтверд\w*\b.*\b(запис|брон|бронир)\w*"),
    re.compile(r"\bподтверд\w*\b.*\b(дат|врем)\w*"),
    re.compile(r"\b(жду|ожидаю|не получил\w*)\b.*\b(подтвержд|ответ)\w*"),
    re.compile(r"\b(check|verify|confirm)\b.*\b(booking|appointment|reservation)\b"),
)
BOOKING_VERIFICATION_HANDOFF_INTENTS = {
    "check_booking",
    "confirm_booking",
    "verify_booking",
    "booking_confirmation",
}
TOOL_VERIFIER_APPOINTMENT_ID_ACTIONS = {
    "calendar.book_slot",
    "calendar.get_booking",
    "calendar.reschedule",
    "calendar.cancel",
}
TOOL_VERIFIER_REFERENCE_ACTIONS = {
    "calendar.get_booking",
    "calendar.reschedule",
    "calendar.cancel",
}
TOOL_VERIFIER_STRICT_DECISION_ACTIONS = {
    "calendar.list_slots",
    "calendar.book_slot",
    "calendar.get_booking",
    "calendar.reschedule",
    "calendar.cancel",
    "catalog.service_query",
    "catalog.location",
    "catalog.portfolio",
}
TOOL_VERIFIER_SUCCESS_DECISIONS: dict[str, set[str]] = {
    # catalog.service_query can legitimately return truth/info fallbacks while still being a successful tool outcome.
    "catalog.service_query": {
        "ok",
        "promotions",
        "duration",
        "services_overview",
        "truth_fallback",
        "presence_fallback",
        "price_item_fallback",
        "not_found_fallback",
        "service_not_found",
    },
}
TOOL_VERIFIER_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "calendar.book_slot": ("service_query", "start_at"),
    "calendar.reschedule": ("appointment_id", "start_at"),
    "calendar.cancel": ("appointment_id",),
}
TOOL_VERIFIER_SLOT_BY_FIELD: dict[str, str] = {
    "service_query": "service",
    "start_at": "datetime",
    "customer_name": "name",
    "appointment_id": "booking_reference",
}
TOOL_VERIFIER_BOOKING_CONFIRM_TEXT_MARKERS = (
    "запись создана",
    "запись подтверждена",
    "вы записаны",
    "запись оформлена",
)
TOOL_VERIFIER_BOOKING_CONFIRM_STATUS = {"confirmed", "booked"}


def _is_booking_verification_handoff_intent(policy_intent: str | None, policy_tool_action: str | None) -> bool:
    intent = str(policy_intent or "").strip().casefold()
    tool_action = str(policy_tool_action or "").strip().casefold()
    if intent in BOOKING_VERIFICATION_HANDOFF_INTENTS:
        return True
    if tool_action == "calendar.get_booking" and intent in {"check_booking", "verify_booking"}:
        return True
    if tool_action == "calendar.book_slot" and intent in {"confirm_booking", "booking_confirmation"}:
        return True
    return False


def _looks_like_booking_verification_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in BOOKING_VERIFICATION_PATTERNS)


def _looks_like_promo_code_request(message_text: str | None, *, client_slug: str | None = None) -> bool:
    if not message_text:
        return False
    normalized = _normalize_service_text(message_text).replace("-", " ")
    if not normalized:
        return False
    promo_code_terms = get_signal_lexicon_list(client_slug, "promotion_promo_code_terms")
    if not promo_code_terms:
        return False
    return any(token in normalized for token in promo_code_terms)


def _format_discounts_reply_for_message(
    *,
    message_text: str | None,
    policy_pack: dict | None,
    policy_type: str | None,
    client_slug: str | None = None,
    promo_code_request: bool | None = None,
) -> str | None:
    reply = _format_discounts_policy_reply(
        policy_pack=policy_pack,
        policy_type=policy_type,
    )
    if not (isinstance(reply, str) and reply.strip()):
        return None
    if promo_code_request is None:
        promo_code_request = _looks_like_promo_code_request(
            message_text,
            client_slug=client_slug,
        )
    if not promo_code_request:
        return reply
    discounts_policy = policy_pack.get("discounts") if isinstance(policy_pack, dict) else None
    promo_code = None
    if isinstance(discounts_policy, dict):
        for key in ("promo_code", "promoCode", "special_promo_code", "code"):
            raw = discounts_policy.get(key)
            if isinstance(raw, str) and raw.strip():
                promo_code = raw.strip()
                break
    if promo_code:
        return f"Сейчас действует промокод {promo_code}. {reply}"
    return f"Специальный промокод в правилах не указан. {reply}"


def _resolve_policy_check_confirm_mode(policy_intent: str | None) -> str | None:
    intent = str(policy_intent or "").strip().casefold()
    if intent in {"check_booking", "verify_booking"}:
        return "check"
    if intent in {"confirm_booking", "booking_confirmation"}:
        return "confirm"
    return None


def _validate_policy_check_confirm_contract(
    *,
    policy_intent: str | None,
    policy_action: str | None,
    policy_tool_action: str | None,
) -> str | None:
    mode = _resolve_policy_check_confirm_mode(policy_intent)
    if mode is None:
        return None
    action = str(policy_action or "").strip().casefold()
    tool_action = str(policy_tool_action or "").strip().casefold()
    if action == "handoff" and tool_action == "handoff":
        return None
    if mode == "check":
        if tool_action != "calendar.get_booking":
            return "check_confirm_tool_mismatch"
        if action not in {"fact", "collect"}:
            return "check_confirm_action_mismatch"
        return None
    if tool_action != "calendar.book_slot":
        return "check_confirm_tool_mismatch"
    if action not in {"fact", "collect"}:
        return "check_confirm_action_mismatch"
    return None


def _detect_tool_contract_error(
    *,
    tool_action: str | None,
    tool_ok: bool,
    response_text: str | None,
    decision_meta: dict[str, Any] | None,
) -> str | None:
    if not isinstance(decision_meta, dict):
        return "decision_meta_missing"
    tool_decision = str(decision_meta.get("tool_decision") or "").strip().casefold()
    if not tool_decision:
        return "tool_decision_missing"
    enforce_decision_match = tool_action in TOOL_VERIFIER_STRICT_DECISION_ACTIONS
    if enforce_decision_match:
        allowed_success_decisions = TOOL_VERIFIER_SUCCESS_DECISIONS.get(tool_action or "", {"ok"})
        if tool_ok and tool_decision not in allowed_success_decisions:
            return "tool_decision_mismatch"
        if not tool_ok and tool_decision in allowed_success_decisions:
            return "tool_decision_mismatch"
    if tool_ok and not (isinstance(response_text, str) and response_text.strip()):
        return "tool_response_missing"
    if not tool_action or tool_action not in TOOL_VERIFIER_APPOINTMENT_ID_ACTIONS:
        return None
    if tool_decision == "ok":
        appointment_id = decision_meta.get("appointment_id")
        if not (isinstance(appointment_id, str) and appointment_id.strip()):
            return "appointment_id_missing"
    if tool_action == "calendar.book_slot":
        response_token = normalize_for_matching(response_text)
        if response_token and any(
            marker in response_token for marker in TOOL_VERIFIER_BOOKING_CONFIRM_TEXT_MARKERS
        ):
            status_raw = decision_meta.get("appointment_status")
            if status_raw is not None:
                status_token = str(status_raw).strip().casefold()
                if status_token not in TOOL_VERIFIER_BOOKING_CONFIRM_STATUS:
                    return "booking_confirmation_status_mismatch"
    return None


def _detect_tool_state_guard_error(
    *,
    tool_action: str | None,
    tool_decision: str | None,
    conversation_state: str | None,
) -> str | None:
    if tool_action not in {"calendar.book_slot", "calendar.reschedule", "calendar.cancel"}:
        return None
    if (tool_decision or "").strip().casefold() != "ok":
        return None
    if conversation_state not in {
        ConversationState.PENDING.value,
        ConversationState.MANAGER_ACTIVE.value,
    }:
        return None
    return "state_guard_blocked"


def _verify_policy_tool_args_contract(
    *,
    tool_action: str,
    tool_args: dict[str, Any],
    validate_tool_args_contract: Callable[..., tuple[str | None, str | None]],
) -> tuple[str | None, str | None]:
    contract_error, error_field = validate_tool_args_contract(
        tool_action=tool_action,
        tool_args=tool_args,
    )
    if contract_error:
        return contract_error, error_field
    required_fields = TOOL_VERIFIER_REQUIRED_FIELDS.get(tool_action, ())
    for field_name in required_fields:
        value = tool_args.get(field_name)
        if not (isinstance(value, str) and value.strip()):
            return "tool_args_required_missing", field_name
    return None, None


def _normalize_plan_refs(refs: list[str] | None) -> list[str]:
    if not refs:
        return []
    cleaned: list[str] = []
    for item in refs:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if value:
            cleaned.append(value.casefold())
    return cleaned


def _normalize_plan_slot_state(slot_state: dict[str, str] | None) -> dict[str, str]:
    if not isinstance(slot_state, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, value in slot_state.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        normalized_key = key.strip().casefold()
        if normalized_key not in BOOKING_SLOT_ORDER:
            continue
        value = value.strip()
        if value:
            cleaned[normalized_key] = value
    return cleaned


def _normalize_plan_questions(open_questions: list[str] | None) -> list[str]:
    return _normalize_plan_refs(open_questions)


def _plan_outcome_matches_action(outcome: str | None, tool_action: str | None) -> bool:
    if not outcome or not tool_action:
        return False
    if outcome == "handoff":
        return tool_action == "handoff"
    if outcome == "fact":
        return tool_action in {"info", "consult"} or tool_action.startswith("calendar.") or tool_action.startswith(
            "catalog."
        )
    if outcome == "collect":
        return tool_action in {"collect", "booking", "info"} or tool_action.startswith(
            "calendar."
        ) or tool_action.startswith("catalog.")
    return False


def _normalize_policy_override_reason_code(reason_code: str | None) -> str:
    if not isinstance(reason_code, str):
        return POLICY_OVERRIDE_REASON_DEFAULT
    normalized = reason_code.strip().casefold()
    if normalized in POLICY_OVERRIDE_REASON_CODES:
        return normalized
    return POLICY_OVERRIDE_REASON_DEFAULT


def _audit_policy_override_reason_code(reason_code: object | None) -> str | None:
    if not isinstance(reason_code, str):
        return None
    normalized = reason_code.strip().casefold()
    if normalized in POLICY_OVERRIDE_REASON_CODES:
        return normalized
    return None


def _build_policy_plan_audit(
    *,
    plan_action: str | None,
    plan_tool_action: str | None,
    final_action: str | None,
    final_tool_action: str | None,
    override_events: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    action_changed = bool(
        isinstance(plan_action, str)
        and plan_action
        and (not isinstance(final_action, str) or plan_action != final_action)
    )
    tool_action_changed = bool(
        isinstance(plan_tool_action, str)
        and plan_tool_action
        and (not isinstance(final_tool_action, str) or plan_tool_action != final_tool_action)
    )
    override_applied = bool(action_changed or tool_action_changed)

    cleaned_events: list[dict[str, Any]] = []
    override_reason_codes: list[str] = []
    event_missing_reason = False
    for event in override_events or []:
        if not isinstance(event, dict):
            continue
        reason_code = _audit_policy_override_reason_code(event.get("reason_code"))
        if reason_code is None:
            event_missing_reason = True
        cleaned_event: dict[str, Any] = {"reason_code": reason_code}
        for key in ("reason", "from_action", "from_tool_action", "to_action", "to_tool_action"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                cleaned_event[key] = value.strip()
        cleaned_events.append(cleaned_event)
        if reason_code not in override_reason_codes:
            override_reason_codes.append(reason_code)

    override_reason_missing = bool(
        override_applied
        and (
            not cleaned_events
            or not override_reason_codes
            or event_missing_reason
        )
    )

    return {
        "plan_action": plan_action,
        "plan_tool_action": plan_tool_action,
        "final_action": final_action,
        "final_tool_action": final_tool_action,
        "action_changed": action_changed,
        "tool_action_changed": tool_action_changed,
        "override_applied": override_applied,
        "override_reason_code": (
            override_reason_codes[-1] if override_reason_codes else None
        ),
        "override_reason_codes": override_reason_codes,
        "override_reason_missing": override_reason_missing,
        "override_events": cleaned_events,
    }


def _normalize_semantic_refs(refs: list[str] | None) -> list[str]:
    if not refs:
        return []
    cleaned: list[str] = []
    for item in refs:
        if not isinstance(item, str):
            continue
        token = item.strip().casefold()
        if token and token not in cleaned:
            cleaned.append(token)
    return cleaned


def _normalize_semantic_reason_codes(reason_codes: list[str] | None) -> list[str]:
    if not reason_codes:
        return []
    cleaned: list[str] = []
    for item in reason_codes:
        normalized = _audit_policy_override_reason_code(item)
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def _normalize_semantic_entity_refs(entity_refs: list[Any] | None) -> list[dict[str, Any]]:
    if not isinstance(entity_refs, list):
        return []
    cleaned: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in entity_refs:
        normalized_entry: dict[str, Any] = {}
        if isinstance(item, str):
            token = item.strip()
            if token:
                normalized_entry["entity_id"] = token
        elif isinstance(item, dict):
            entity_id = item.get("entity_id")
            if not isinstance(entity_id, str) or not entity_id.strip():
                fallback_id = item.get("id")
                if isinstance(fallback_id, str) and fallback_id.strip():
                    entity_id = fallback_id
            if isinstance(entity_id, str) and entity_id.strip():
                normalized_entry["entity_id"] = entity_id.strip()
            entity_type = item.get("entity_type")
            if not isinstance(entity_type, str) or not entity_type.strip():
                fallback_type = item.get("type")
                if isinstance(fallback_type, str) and fallback_type.strip():
                    entity_type = fallback_type
            if isinstance(entity_type, str) and entity_type.strip():
                normalized_entry["entity_type"] = entity_type.strip().casefold()
            source_ref = item.get("source_ref")
            if isinstance(source_ref, str) and source_ref.strip():
                normalized_entry["source_ref"] = source_ref.strip()
            confidence = item.get("confidence")
            if isinstance(confidence, (int, float)):
                normalized_entry["confidence"] = max(0.0, min(float(confidence), 1.0))
        if not normalized_entry:
            continue
        dedupe_key = (
            str(normalized_entry.get("entity_id") or ""),
            str(normalized_entry.get("entity_type") or ""),
            str(normalized_entry.get("source_ref") or ""),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        cleaned.append(normalized_entry)
    return cleaned


def _normalize_semantic_slots(slots: dict[str, str] | None) -> dict[str, str]:
    if not isinstance(slots, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key in BOOKING_SLOT_ORDER:
        value = slots.get(key)
        if isinstance(value, str) and value.strip():
            cleaned[key] = value.strip()
    return cleaned


def _build_semantic_arbiter_contract(
    *,
    intent: str | None,
    action: str | None,
    tool_action: str | None,
    pack_refs: list[str] | None,
    slots: dict[str, str] | None,
    confidence: float | None,
    reason: str | None,
    goal: str | None,
    open_questions: list[str] | None,
    needs_manager: bool,
    risk_signals: list[str] | None,
    entity_refs: list[Any] | None,
    subject_kind: str | None,
    capability: str | None,
    temporal_scope: str | None,
    resolution_mode: str | None,
    pending_question_act: str | None,
    pending_question_target: str | None,
    active_question_relation: str | None,
    resolver_id: str | None,
    resolver_version: str | None,
    override_reason_codes: list[str] | None,
) -> dict[str, Any]:
    confidence_value: float | None = None
    if isinstance(confidence, (int, float)):
        confidence_value = max(0.0, min(float(confidence), 1.0))
    resolver_id_token = (
        resolver_id.strip()
        if isinstance(resolver_id, str) and resolver_id.strip()
        else None
    )
    resolver_version_token = (
        resolver_version.strip()
        if isinstance(resolver_version, str) and resolver_version.strip()
        else None
    )
    subject_kind_token = (
        subject_kind.strip().casefold()
        if isinstance(subject_kind, str) and subject_kind.strip()
        else None
    )
    capability_token = (
        capability.strip().casefold()
        if isinstance(capability, str) and capability.strip()
        else None
    )
    temporal_scope_token = (
        temporal_scope.strip().casefold()
        if isinstance(temporal_scope, str) and temporal_scope.strip()
        else None
    )
    resolution_mode_token = (
        resolution_mode.strip().casefold()
        if isinstance(resolution_mode, str) and resolution_mode.strip()
        else None
    )
    pending_question_act_token = (
        pending_question_act.strip().casefold()
        if isinstance(pending_question_act, str) and pending_question_act.strip()
        else None
    )
    pending_question_target_token = (
        pending_question_target.strip().casefold()
        if isinstance(pending_question_target, str) and pending_question_target.strip()
        else None
    )
    active_question_relation_token = (
        active_question_relation.strip().casefold()
        if isinstance(active_question_relation, str) and active_question_relation.strip()
        else None
    )
    return {
        "intent_class": intent or None,
        "action_class": action or None,
        "tool_action": tool_action or None,
        "fact_refs": _normalize_semantic_refs(pack_refs),
        "entity_refs": _normalize_semantic_entity_refs(entity_refs),
        "subject_kind": subject_kind_token,
        "capability": capability_token,
        "temporal_scope": temporal_scope_token,
        "resolution_mode": resolution_mode_token,
        "pending_question_act": pending_question_act_token,
        "pending_question_target": pending_question_target_token,
        "active_question_relation": active_question_relation_token,
        "slot_candidates": _normalize_semantic_slots(slots),
        "confidence": confidence_value,
        "abstain_reason": reason or None,
        "goal": goal or None,
        "open_questions": _normalize_semantic_refs(open_questions),
        "needs_manager": bool(needs_manager),
        "risk_signals": _normalize_semantic_refs(risk_signals),
        "resolver_id": resolver_id_token,
        "resolver_version": resolver_version_token,
        "override_reason_codes": _normalize_semantic_reason_codes(override_reason_codes),
    }


def _normalize_semantic_followup_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token:
        return None
    return token.casefold()


def _resolve_semantic_referent(
    *,
    subject_kind: str | None,
    explicit_value: str | None,
    explicit_source: str | None,
    context_manager: dict | None,
    message_count: int,
    booking_state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_subject_kind = _normalize_semantic_followup_token(subject_kind)
    referent_key_map = {
        "service": "service",
        "specialist": "master",
        "booking": "booking_ref",
        "branch": "branch",
    }
    referent_key = referent_key_map.get(normalized_subject_kind)
    resolution: dict[str, Any] = {
        "subject_kind": normalized_subject_kind,
        "referent_key": referent_key,
        "decision": "not_applicable" if not referent_key else "missing",
    }
    explicit_token = explicit_value.strip() if isinstance(explicit_value, str) and explicit_value.strip() else None
    explicit_source_token = (
        explicit_source.strip().casefold()
        if isinstance(explicit_source, str) and explicit_source.strip()
        else "policy_payload"
    )
    if explicit_token:
        resolution.update(
            {
                "decision": "resolved",
                "resolved_referent": explicit_token,
                "referent_source": explicit_source_token,
            }
        )
        return resolution
    if not referent_key:
        return resolution

    manager = context_manager if isinstance(context_manager, dict) else {}
    projection = _project_canonical_referent(
        manager,
        referent_key=referent_key,
        message_count=message_count,
    )
    if isinstance(projection, dict):
        resolved_value = projection.get("value")
        if isinstance(resolved_value, str) and resolved_value.strip():
            resolution.update(
                {
                    "decision": "resolved",
                    "resolved_referent": resolved_value.strip(),
                    "referent_source": (
                        str(projection.get("source")).strip().casefold()
                        if isinstance(projection.get("source"), str) and projection.get("source").strip()
                        else str(projection.get("projection_source") or referent_key).strip().casefold()
                    ),
                    "projection_source": projection.get("projection_source"),
                    "canonical_state_owner": projection.get("canonical_state_owner"),
                    "age": projection.get("age"),
                    "ttl": projection.get("ttl"),
                    "remaining": projection.get("remaining"),
                }
            )
            return resolution

    canonical_state = _get_canonical_dialog_state(manager)
    if referent_key == "service":
        pending_question_contract = (
            canonical_state.get("pending_question_contract")
            if isinstance(canonical_state, dict)
            else None
        )
        if isinstance(pending_question_contract, dict):
            pending_slot = _normalize_semantic_followup_token(
                pending_question_contract.get("slot")
            )
            pending_value = pending_question_contract.get("value")
            if (
                pending_slot == "service"
                and isinstance(pending_value, str)
                and pending_value.strip()
            ):
                resolution.update(
                    {
                        "decision": "resolved",
                        "resolved_referent": pending_value.strip(),
                        "referent_source": "pending_question_contract",
                        "projection_source": "canonical_dialog_state",
                        "canonical_state_owner": canonical_state.get("owner_id"),
                    }
                )
                return resolution

    if referent_key == "service" and isinstance(booking_state, dict):
        booking_service = booking_state.get("service")
        if isinstance(booking_service, str) and booking_service.strip():
            resolution.update(
                {
                    "decision": "resolved",
                    "resolved_referent": booking_service.strip(),
                    "referent_source": "booking_state",
                }
            )
            return resolution

    if referent_key == "booking_ref":
        booking_reference = _extract_booking_reference_id(booking_state)
        if isinstance(booking_reference, str) and booking_reference.strip():
            resolution.update(
                {
                    "decision": "resolved",
                    "resolved_referent": booking_reference.strip(),
                    "referent_source": "booking_state",
                }
            )
            return resolution

    if referent_key == "service":
        carryover = _get_service_carryover(manager, message_count=message_count)
        if isinstance(carryover, dict):
            carryover_service = carryover.get("service_query")
            if isinstance(carryover_service, str) and carryover_service.strip():
                resolution.update(
                    {
                        "decision": "resolved",
                        "resolved_referent": carryover_service.strip(),
                        "referent_source": (
                            str(carryover.get("service_query_source")).strip().casefold()
                            if isinstance(carryover.get("service_query_source"), str)
                            and carryover.get("service_query_source").strip()
                            else "service_carryover"
                        ),
                        "projection_source": carryover.get("projection_source"),
                        "canonical_state_owner": carryover.get("canonical_state_owner"),
                        "age": carryover.get("age"),
                        "ttl": carryover.get("ttl"),
                        "remaining": carryover.get("remaining"),
                    }
                )
                return resolution

    return resolution


def _extract_fact_evidence_refs(decision_meta: dict[str, Any] | None) -> list[str]:
    if not isinstance(decision_meta, dict):
        return []

    refs: list[str] = []

    def _extend_refs(value: Any) -> None:
        if isinstance(value, str):
            normalized = _normalize_semantic_refs([value])
        elif isinstance(value, list):
            normalized = _normalize_semantic_refs([item for item in value if isinstance(item, str)])
        else:
            normalized = []
        for ref in normalized:
            if ref not in refs:
                refs.append(ref)

    def _extend_tool_args(tool_args: dict[str, Any] | None) -> None:
        if not isinstance(tool_args, dict):
            return
        _extend_refs(tool_args.get("info_refs"))
        _extend_refs(tool_args.get("consult_refs"))
        _extend_refs(tool_args.get("info_ref"))
        _extend_refs(tool_args.get("consult_ref"))
        for keyed_value in (
            tool_args.get("service_query"),
            tool_args.get("price_item"),
            tool_args.get("duration_item"),
        ):
            if isinstance(keyed_value, str) and keyed_value.strip():
                _extend_refs([keyed_value])

    for key in (
        "fact_refs",
        "pack_refs",
        "info_sections",
        "consult_topic",
        "consult_topic_id",
        "service_query",
        "price_item",
        "duration_item",
    ):
        _extend_refs(decision_meta.get(key))

    _extend_tool_args(decision_meta.get("tool_args"))

    llm_policy_core = decision_meta.get("llm_policy_core")
    if isinstance(llm_policy_core, dict):
        payload = llm_policy_core.get("payload")
        if isinstance(payload, dict):
            _extend_refs(payload.get("pack_refs"))
            _extend_refs(payload.get("consult_topic"))
            _extend_tool_args(payload.get("tool_args"))

    return refs


def _fact_guard_reason(decision_meta: dict[str, Any] | None) -> str | None:
    if not isinstance(decision_meta, dict):
        return None

    fact_source = str(decision_meta.get("fact_source") or "").strip().casefold()
    tool_action = str(decision_meta.get("tool_action") or "").strip().casefold()
    tool_decision = str(decision_meta.get("tool_decision") or "").strip().casefold()
    if not fact_source and not tool_action:
        return None
    if tool_action.startswith("calendar."):
        return None
    if tool_decision in FACT_GUARD_BLOCKED_TOOL_DECISIONS:
        return None

    evidence_refs = _extract_fact_evidence_refs(decision_meta)
    if not evidence_refs:
        return "missing_evidence_refs"

    fact_payload = (
        decision_meta.get("fact_refs"),
        decision_meta.get("info_sections"),
        decision_meta.get("consult_topic"),
        decision_meta.get("service_query"),
        decision_meta.get("price_item"),
        decision_meta.get("duration_item"),
    )
    has_fact_payload = any(
        (isinstance(value, str) and value.strip())
        or (isinstance(value, list) and value)
        or (isinstance(value, dict) and value)
        for value in fact_payload
    )
    if not has_fact_payload:
        return "missing_fact_payload"
    return None


def _build_semantic_arbiter_audit(
    *,
    plan_contract: dict[str, Any] | None,
    final_contract: dict[str, Any] | None,
    override_events: list[dict[str, Any]] | None,
    intent_override_events: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    plan_action = (
        plan_contract.get("action_class")
        if isinstance(plan_contract, dict)
        else None
    )
    final_action = (
        final_contract.get("action_class")
        if isinstance(final_contract, dict)
        else None
    )
    plan_tool_action = (
        plan_contract.get("tool_action")
        if isinstance(plan_contract, dict)
        else None
    )
    final_tool_action = (
        final_contract.get("tool_action")
        if isinstance(final_contract, dict)
        else None
    )
    plan_intent = (
        plan_contract.get("intent_class")
        if isinstance(plan_contract, dict)
        else None
    )
    final_intent = (
        final_contract.get("intent_class")
        if isinstance(final_contract, dict)
        else None
    )
    action_changed = bool(
        isinstance(plan_action, str)
        and plan_action
        and (not isinstance(final_action, str) or final_action != plan_action)
    )
    tool_action_changed = bool(
        isinstance(plan_tool_action, str)
        and plan_tool_action
        and (not isinstance(final_tool_action, str) or final_tool_action != plan_tool_action)
    )
    intent_changed = bool(
        isinstance(plan_intent, str)
        and plan_intent
        and (not isinstance(final_intent, str) or final_intent != plan_intent)
    )
    override_reason_codes: list[str] = []
    for event in override_events or []:
        if not isinstance(event, dict):
            continue
        reason_code = _audit_policy_override_reason_code(event.get("reason_code"))
        if reason_code and reason_code not in override_reason_codes:
            override_reason_codes.append(reason_code)
    intent_override_reason_codes: list[str] = []
    for event in intent_override_events or []:
        if not isinstance(event, dict):
            continue
        reason_code = _audit_policy_override_reason_code(event.get("reason_code"))
        if reason_code and reason_code not in intent_override_reason_codes:
            intent_override_reason_codes.append(reason_code)
    return {
        "action_changed": action_changed,
        "tool_action_changed": tool_action_changed,
        "intent_changed": intent_changed,
        "override_reason_codes": override_reason_codes,
        "intent_override_reason_codes": intent_override_reason_codes,
        "intent_override_count": len(intent_override_events or []),
    }


def _derive_policy_info_refs(
    *,
    policy_intent: str | None,
    policy_capability: str | None = None,
    message_text: str | None,
    client_slug: str | None,
    service_query: str | None = None,
) -> list[str]:
    derived: list[str] = []

    def _append_ref(ref: str) -> None:
        if ref in INFO_INTENTS and ref not in derived:
            derived.append(ref)

    for raw_ref in (policy_capability, policy_intent):
        if not isinstance(raw_ref, str):
            continue
        normalized_ref = raw_ref.strip().casefold()
        if normalized_ref:
            _append_ref(normalized_ref)

    if isinstance(message_text, str) and message_text.strip():
        fallback_intents, _ = _detect_info_class_intents(
            message_text,
            intent_decomp_set=set(),
            client_slug=client_slug,
            service_query=service_query,
        )

        # Always keep fallback info refs deterministic to avoid cross-process drift.
        fallback_refs = sorted(
            (ref for ref in fallback_intents if ref in INFO_INTENTS),
            key=lambda ref: (
                INFO_INTENT_PRIORITY_GENERIC.index(ref)
                if ref in INFO_INTENT_PRIORITY_GENERIC
                else len(INFO_INTENT_PRIORITY_GENERIC),
                ref,
            ),
        )

        for ref in fallback_refs:
            _append_ref(ref)

    return derived


def _resolve_policy_collect_interrupt_arbitration(
    *,
    policy_tool_action: str | None,
    policy_intent: str | None,
    policy_subject_kind: str | None = None,
    policy_capability: str | None = None,
    policy_pack_refs: list[str] | None,
    policy_tool_args: dict[str, Any] | None = None,
    policy_entity_refs: list[dict[str, Any]] | None = None,
    policy_pending_question_act: str | None = None,
    policy_pending_question_target: str | None = None,
    policy_temporal_scope: str | None = None,
    policy_resolution_mode: str | None = None,
    policy_active_question_relation: str | None = None,
    message_text: str | None,
    client_slug: str | None,
    service_query: str | None = None,
    booking_state: dict[str, Any] | None = None,
    booking_wants_flow: bool,
    booking_active: bool,
    policy_goal: str | None,
    expected_reply_type: str | None = None,
    expected_reply_matched: bool | None = None,
) -> tuple[str | None, list[str], str | None]:
    normalized_tool_action = (
        policy_tool_action.strip().casefold()
        if isinstance(policy_tool_action, str) and policy_tool_action.strip()
        else ""
    )
    booking_scope = bool(
        booking_wants_flow
        or booking_active
        or (
            isinstance(policy_goal, str)
            and policy_goal.strip().casefold() == "booking"
        )
    )
    if not booking_scope or normalized_tool_action != "collect":
        return policy_tool_action, [], None
    if bool(expected_reply_matched):
        # Preserve active collect ownership whenever question_contract already
        # matched on this turn. The local expected_reply_type may already be
        # cleared after shortcircuit, so the matched signal is the stable
        # contract boundary here.
        return policy_tool_action, [], None
    if _should_preserve_specialist_availability_followup_owner(
        policy_goal=policy_goal,
        policy_collect_slot=None,
        policy_pending_question_target=policy_pending_question_target,
        policy_subject_kind=policy_subject_kind,
        policy_capability=policy_capability,
        policy_temporal_scope=policy_temporal_scope,
        policy_active_question_relation=policy_active_question_relation,
    ):
        return policy_tool_action, [], None
    specialist_name, specialist_id = _extract_semantic_specialist_preference(
        tool_args=policy_tool_args,
        entity_refs=policy_entity_refs,
    )
    if _should_preserve_specialist_followup_owner(
        policy_goal=policy_goal,
        policy_collect_slot=None,
        policy_pending_question_target=policy_pending_question_target,
        policy_subject_kind=policy_subject_kind,
        policy_capability=policy_capability,
        policy_resolution_mode=policy_resolution_mode,
        policy_active_question_relation=policy_active_question_relation,
        expected_reply_type=expected_reply_type,
        specialist_name=specialist_name,
        specialist_id=specialist_id,
    ):
        # Named specialist follow-ups are booking-state operations.
        # Keep them in collect ownership and let the dedicated specialist
        # follow-up owner resume the active pending question.
        return policy_tool_action, [], None

    effective_service_query = service_query
    if not isinstance(effective_service_query, str) or not effective_service_query.strip():
        if isinstance(booking_state, dict):
            booking_service = booking_state.get("service")
            if isinstance(booking_service, str) and booking_service.strip():
                effective_service_query = booking_service.strip()

    info_refs: list[str] = []
    for ref in policy_pack_refs or []:
        if isinstance(ref, str) and ref in INFO_INTENTS and ref not in info_refs:
            info_refs.append(ref)
    for ref in _derive_policy_info_refs(
        policy_intent=policy_intent,
        policy_capability=policy_capability,
        message_text=message_text,
        client_slug=client_slug,
        service_query=effective_service_query,
    ):
        if ref in INFO_INTENTS and ref not in info_refs:
            info_refs.append(ref)

    preserve_active_time_slot_question = _should_preserve_active_time_slot_question_owner(
        policy_goal=policy_goal,
        policy_pending_question_act=policy_pending_question_act,
        policy_pending_question_target=policy_pending_question_target,
        policy_active_question_relation=policy_active_question_relation,
    )
    if preserve_active_time_slot_question and not _should_admit_active_time_duration_info_interrupt(
        policy_goal=policy_goal,
        policy_capability=policy_capability,
        policy_pending_question_act=policy_pending_question_act,
        policy_pending_question_target=policy_pending_question_target,
        policy_active_question_relation=policy_active_question_relation,
        message_text=message_text,
        info_refs=info_refs,
    ):
        return policy_tool_action, [], None
    if not info_refs:
        return policy_tool_action, [], None
    return "info", info_refs, "policy_collect_info_interrupt_owner"


def _resolve_active_time_collect_service_info_interrupt_query(
    *,
    policy_tool_action: str | None,
    policy_collect_slot: str | None,
    policy_intent: str | None,
    policy_subject_kind: str | None,
    policy_resolution_mode: str | None,
    message_text: str | None,
    client_slug: str | None,
    service_query: str | None,
    booking_state: dict[str, Any] | None,
    booking_wants_flow: bool,
    booking_active: bool,
    policy_goal: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
) -> str | None:
    def _clean(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    normalized_tool_action = (
        policy_tool_action.strip().casefold()
        if isinstance(policy_tool_action, str) and policy_tool_action.strip()
        else None
    )
    if normalized_tool_action != "collect":
        return None
    normalized_collect_slot = (
        policy_collect_slot.strip().casefold()
        if isinstance(policy_collect_slot, str) and policy_collect_slot.strip()
        else None
    )
    if normalized_collect_slot not in {None, "service"}:
        return None
    booking_scope = bool(
        booking_wants_flow
        or booking_active
        or (
            isinstance(policy_goal, str)
            and policy_goal.strip().casefold() == "booking"
        )
    )
    if not booking_scope or bool(expected_reply_matched):
        return None
    if _normalize_semantic_followup_token(expected_reply_type) != _normalize_semantic_followup_token(
        EXPECTED_REPLY_TIME
    ):
        return None
    if _normalize_semantic_followup_token(policy_intent) != "info":
        return None
    if _normalize_semantic_followup_token(policy_subject_kind) != "service":
        return None
    if _normalize_semantic_followup_token(policy_resolution_mode) != "clarify_missing_subject":
        return None

    effective_service_query = _clean(service_query)
    if not effective_service_query and isinstance(booking_state, dict):
        effective_service_query = _clean(booking_state.get("service"))
    if not effective_service_query:
        return None

    if not _looks_like_services_overview_message(message_text, client_slug=client_slug):
        return None

    return effective_service_query


def _derive_service_clarify_info_sections(*sources: Any) -> list[str]:
    sections: list[str] = []
    for source in sources:
        if not isinstance(source, (list, tuple, set)):
            continue
        for item in source:
            if not isinstance(item, str):
                continue
            normalized = item.strip().casefold()
            if normalized in INFO_INTENTS and normalized not in sections:
                sections.append(normalized)
    return sections


def _should_collect_service_for_info(policy_info_set: set[str]) -> bool:
    return bool(policy_info_set & INFO_SERVICE_DEPENDENT_INTENTS) and not bool(
        policy_info_set & INFO_NON_SERVICE_INTENTS
    )


def _validate_plan_slot_value(
    slot_key: str,
    value: str,
    *,
    client_slug: str | None,
) -> str | None:
    if slot_key == "service":
        return _validate_service_slot(value, allow_freeform=True, client_slug=client_slug)
    if slot_key == "datetime":
        return _validate_datetime_slot(value, allow_freeform=True, client_slug=client_slug)
    if slot_key == "name":
        return _validate_name_slot(value, allow_freeform=True, client_slug=client_slug)
    return None


def _select_plan_collect_slot(
    *,
    open_questions: list[str],
    pack_refs: list[str],
    tool_action: str | None,
    goal: str | None,
) -> str | None:
    for slot_key in BOOKING_SLOT_ORDER:
        if slot_key in open_questions:
            return slot_key
    if tool_action == "info" and {"pricing", "duration"} & set(pack_refs):
        return "service"
    if goal and goal.strip().casefold() == "booking":
        return "service"
    return None


def _merge_booking_plan_slots(
    *,
    booking_state: dict[str, Any] | None,
    plan_slots: dict[str, str],
) -> dict[str, str]:
    merged: dict[str, str] = {}
    if isinstance(booking_state, dict):
        for slot_key in BOOKING_SLOT_ORDER:
            value = booking_state.get(slot_key)
            if isinstance(value, str) and value.strip():
                merged[slot_key] = value.strip()
    for slot_key in BOOKING_SLOT_ORDER:
        value = plan_slots.get(slot_key)
        if isinstance(value, str) and value.strip():
            merged[slot_key] = value.strip()
    return merged


def _booking_slot_is_complete(
    *,
    slot_key: str,
    value: Any,
    client_slug: str | None,
) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if slot_key != "datetime":
        return True
    return _is_datetime_grounded_for_prompt(value, client_slug=client_slug)


def _plan_has_complete_booking_slots(
    slot_state: dict[str, str],
    *,
    client_slug: str | None,
) -> bool:
    return all(
        _booking_slot_is_complete(
            slot_key=slot_key,
            value=slot_state.get(slot_key),
            client_slug=client_slug,
        )
        for slot_key in BOOKING_SLOT_ORDER
    )


def _first_missing_booking_slot(
    slot_state: dict[str, Any] | None,
    *,
    client_slug: str | None,
) -> str | None:
    if not isinstance(slot_state, dict):
        return "service"
    for slot_key in BOOKING_SLOT_ORDER:
        if not _booking_slot_is_complete(
            slot_key=slot_key,
            value=slot_state.get(slot_key),
            client_slug=client_slug,
        ):
            return slot_key
    return None


def _collect_policy_active_slots(
    *,
    primary_slot_state: dict[str, Any] | None,
    fallback_slot_state: dict[str, Any] | None,
    client_slug: str | None,
) -> list[str]:
    active_slots: list[str] = []
    for slot_key in BOOKING_SLOT_ORDER:
        value = None
        for candidate_state in (primary_slot_state, fallback_slot_state):
            if not isinstance(candidate_state, dict):
                continue
            candidate_value = candidate_state.get(slot_key)
            if isinstance(candidate_value, str) and candidate_value.strip():
                value = candidate_value.strip()
                break
        if _booking_slot_is_complete(
            slot_key=slot_key,
            value=value,
            client_slug=client_slug,
        ):
            active_slots.append(slot_key)
    return active_slots


def _booking_has_reference(booking_state: dict[str, Any] | None) -> bool:
    if not isinstance(booking_state, dict):
        return False
    for key in ("appointment_id", "booking_id", "external_booking_id"):
        value = booking_state.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _extract_booking_reference_id(booking_state: dict[str, Any] | None) -> str | None:
    if not isinstance(booking_state, dict):
        return None
    for key in ("appointment_id", "booking_id", "external_booking_id"):
        raw_value = booking_state.get(key)
        if not isinstance(raw_value, str) or not raw_value.strip():
            continue
        reference_uuid = _coerce_uuid(raw_value.strip())
        if reference_uuid:
            return str(reference_uuid)
    return None


def _extract_tool_result_appointment_id(decision_meta: dict[str, Any] | None) -> str | None:
    if not isinstance(decision_meta, dict):
        return None
    raw_value = decision_meta.get("appointment_id")
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    appointment_uuid = _coerce_uuid(raw_value.strip())
    if not appointment_uuid:
        return None
    return str(appointment_uuid)


def _normalize_specialist_tool_args(tool_args: dict[str, Any] | None) -> None:
    if not isinstance(tool_args, dict):
        return
    raw_specialist_id = tool_args.get("specialist_id")
    if not isinstance(raw_specialist_id, str) or not raw_specialist_id.strip():
        return
    if isinstance(tool_args.get("specialist_name"), str) and tool_args.get("specialist_name").strip():
        return
    specialist_token = raw_specialist_id.strip()
    specialist_uuid = _coerce_uuid(specialist_token)
    if specialist_uuid:
        tool_args["specialist_id"] = str(specialist_uuid)
        return
    # LLM can place master name into specialist_id; preserve semantics by moving it to specialist_name.
    tool_args["specialist_name"] = specialist_token
    tool_args.pop("specialist_id", None)


def _decode_semantic_specialist_entity_id(entity_id: Any) -> tuple[str | None, str | None]:
    specialist_name, specialist_id = extract_specialist_preference(
        entity_refs=[{"entity_id": entity_id, "entity_type": "specialist"}],
    )
    return specialist_name, specialist_id


def _extract_semantic_specialist_preference(
    *,
    tool_args: dict[str, Any] | None,
    entity_refs: list[dict[str, Any]] | None,
) -> tuple[str | None, str | None]:
    return extract_specialist_preference(
        tool_args=tool_args,
        entity_refs=entity_refs,
    )


def _should_preserve_specialist_followup_owner(
    *,
    policy_goal: str | None,
    policy_collect_slot: str | None,
    policy_pending_question_target: str | None,
    policy_subject_kind: str | None,
    policy_capability: str | None,
    policy_resolution_mode: str | None,
    policy_active_question_relation: str | None,
    expected_reply_type: str | None,
    specialist_name: str | None,
    specialist_id: str | None,
) -> bool:
    semantic_view = build_semantic_contract_view(
        entity_refs=[],
        subject_kind=policy_subject_kind,
        capability=policy_capability,
        resolution_mode=policy_resolution_mode,
        pending_question_target=policy_pending_question_target,
        active_question_relation=policy_active_question_relation,
        tool_args={
            "specialist_name": specialist_name,
            "specialist_id": specialist_id,
        },
    )
    return should_preserve_specialist_followup_owner(
        semantic_view=semantic_view,
        policy_goal=policy_goal,
        policy_collect_slot=policy_collect_slot,
        expected_reply_type=expected_reply_type,
    )


def _should_preserve_specialist_availability_followup_owner(
    *,
    policy_goal: str | None,
    policy_collect_slot: str | None,
    policy_pending_question_target: str | None,
    policy_subject_kind: str | None,
    policy_capability: str | None,
    policy_temporal_scope: str | None,
    policy_active_question_relation: str | None,
) -> bool:
    semantic_view = build_semantic_contract_view(
        subject_kind=policy_subject_kind,
        capability=policy_capability,
        temporal_scope=policy_temporal_scope,
        pending_question_target=policy_pending_question_target,
        active_question_relation=policy_active_question_relation,
    )
    return should_preserve_specialist_availability_followup_owner(
        semantic_view=semantic_view,
        policy_goal=policy_goal,
        policy_collect_slot=policy_collect_slot,
    )


def _should_preserve_service_choice_specialist_availability_followup_owner(
    *,
    policy_goal: str | None,
    policy_collect_slot: str | None,
    expected_reply_type: str | None,
    policy_resolution_mode: str | None,
    policy_pending_question_act: str | None,
    policy_pending_question_target: str | None,
    policy_subject_kind: str | None,
    policy_capability: str | None,
    policy_temporal_scope: str | None,
    policy_active_question_relation: str | None,
) -> bool:
    semantic_view = build_semantic_contract_view(
        subject_kind=policy_subject_kind,
        capability=policy_capability,
        temporal_scope=policy_temporal_scope,
        resolution_mode=policy_resolution_mode,
        pending_question_act=policy_pending_question_act,
        pending_question_target=policy_pending_question_target,
        active_question_relation=policy_active_question_relation,
    )
    return should_preserve_service_choice_specialist_availability_followup_owner(
        semantic_view=semantic_view,
        policy_goal=policy_goal,
        policy_collect_slot=policy_collect_slot,
        expected_reply_type=expected_reply_type,
    )


def _should_preserve_active_name_time_availability_followup_owner(
    *,
    policy_goal: str | None,
    policy_collect_slot: str | None,
    expected_reply_type: str | None,
    policy_resolution_mode: str | None,
    policy_pending_question_act: str | None,
    policy_pending_question_target: str | None,
    policy_subject_kind: str | None,
    policy_capability: str | None,
    policy_temporal_scope: str | None,
    policy_active_question_relation: str | None,
) -> bool:
    semantic_view = build_semantic_contract_view(
        subject_kind=policy_subject_kind,
        capability=policy_capability,
        temporal_scope=policy_temporal_scope,
        resolution_mode=policy_resolution_mode,
        pending_question_act=policy_pending_question_act,
        pending_question_target=policy_pending_question_target,
        active_question_relation=policy_active_question_relation,
    )
    return should_preserve_active_name_time_availability_followup_owner(
        semantic_view=semantic_view,
        policy_goal=policy_goal,
        policy_collect_slot=policy_collect_slot,
        expected_reply_type=expected_reply_type,
    )


def _should_preserve_active_time_slot_question_owner(
    *,
    policy_goal: str | None,
    policy_pending_question_act: str | None,
    policy_pending_question_target: str | None,
    policy_active_question_relation: str | None,
) -> bool:
    normalized_goal = (
        policy_goal.strip().casefold()
        if isinstance(policy_goal, str) and policy_goal.strip()
        else None
    )
    if normalized_goal != "booking":
        return False
    pending_question_target = _normalize_pending_question_target(policy_pending_question_target)
    if pending_question_target != "time":
        return False
    pending_question_act = _normalize_pending_question_act(policy_pending_question_act)
    if pending_question_act not in {None, "ask_about_requested_slot", "slot_constraint", "slot_compare"}:
        return False
    relation_token = _normalize_active_question_relation(policy_active_question_relation)
    return relation_token in {"ask_about_requested_slot", "slot_constraint", "slot_compare"}


def _should_admit_active_time_duration_info_interrupt(
    *,
    policy_goal: str | None,
    policy_capability: str | None,
    policy_pending_question_act: str | None,
    policy_pending_question_target: str | None,
    policy_active_question_relation: str | None,
    message_text: str | None,
    info_refs: list[str] | None,
) -> bool:
    if not _should_preserve_active_time_slot_question_owner(
        policy_goal=policy_goal,
        policy_pending_question_act=policy_pending_question_act,
        policy_pending_question_target=policy_pending_question_target,
        policy_active_question_relation=policy_active_question_relation,
    ):
        return False
    normalized_info_refs = {
        ref.strip().casefold()
        for ref in info_refs or []
        if isinstance(ref, str) and ref.strip()
    }
    if "duration" not in normalized_info_refs:
        return False
    normalized_capability = (
        policy_capability.strip().casefold()
        if isinstance(policy_capability, str) and policy_capability.strip()
        else None
    )
    if normalized_capability != "duration":
        if not isinstance(message_text, str) or not message_text.strip():
            return False
        normalized_service_message = _normalize_service_text(message_text)
        if not _has_duration_signal(normalized_service_message, message_text):
            return False
    normalized_message = (
        normalize_for_matching(message_text)
        if isinstance(message_text, str) and message_text.strip()
        else None
    )
    if normalized_message and _looks_like_time_preference_statement(
        message_text,
        normalized_text=normalized_message,
    ):
        return False
    return True


def _resolve_specialist_name_hint_with_trace(
    *,
    db: Session,
    message_text: str | None,
    client_slug: str | None,
    timing_context: dict | None,
    conversation: Any,
    saved_message: Any,
    tool_action: str | None,
) -> str | None:
    def _record_branch_catalog_hint(
        specialist_name_hint: str,
        *,
        match_mode: str = "exact",
    ) -> str:
        hint_meta = {
            "specialist_hint_attempted": False,
            "specialist_hint_ok": True,
            "specialist_hint_error": None,
            "specialist_hint_source": "branch_catalog",
        }
        if match_mode != "exact":
            hint_meta["specialist_hint_match_mode"] = match_mode
        if saved_message:
            _update_message_decision_metadata(saved_message, hint_meta)
        trace_payload = {
            "stage": "specialist_hint",
            "decision": "ok",
            "tool_action": tool_action,
            "attempted": False,
            "confidence": 1.0,
            "error": None,
            "source": "branch_catalog",
            "specialist_name": specialist_name_hint,
        }
        if match_mode != "exact":
            trace_payload["match_mode"] = match_mode
        _record_decision_trace(conversation, trace_payload)
        return specialist_name_hint

    def _extract_surface_specialist_name_hint() -> str | None:
        if not isinstance(message_text, str) or not message_text.strip():
            return None
        person_terms = {
            normalize_for_matching(term)
            for term in get_signal_lexicon_list(client_slug, "master_query_person_terms")
            if isinstance(term, str) and term.strip()
        }
        # Keep the runtime lexicon as the primary source, but retain the
        # inflected booking forms needed for the bounded followup recovery.
        person_terms.update(
            {
                "мастер",
                "мастеру",
                "мастера",
                "специалист",
                "специалисту",
                "специалиста",
            }
        )
        person_terms.discard("")
        raw_tokens = [
            token.strip(" \t\n\r.,!?;:()[]{}\"'`«»")
            for token in str(message_text or "").split()
        ]
        normalized_tokens = [normalize_for_matching(token) for token in raw_tokens]
        for idx, normalized_token in enumerate(normalized_tokens[:-1]):
            if normalized_token not in person_terms:
                continue
            candidate = raw_tokens[idx + 1]
            if not candidate or not _SPECIALIST_SURFACE_HINT_TOKEN_RE.match(candidate):
                continue
            validated_candidate = _validate_name_slot(
                candidate,
                allow_freeform=True,
                client_slug=client_slug,
            )
            if validated_candidate:
                return validated_candidate
        return None

    if not isinstance(message_text, str) or not message_text.strip():
        return None
    branch_id = getattr(conversation, "branch_id", None)
    if branch_id:
        normalized_message = normalize_for_matching(message_text)
        if normalized_message:
            specialist_matches: list[str] = []
            specialist_prefix_matches: list[str] = []
            normalized_message_tokens = {
                token for token in normalized_message.split() if isinstance(token, str) and token
            }
            specialists = (
                db.query(Specialist)
                .filter(
                    Specialist.branch_id == branch_id,
                    Specialist.is_active == True,
                )
                .all()
            )
            padded_message = _pad_surface_token(normalized_message)
            for specialist in specialists:
                specialist_name = getattr(specialist, "name", None)
                if not isinstance(specialist_name, str) or not specialist_name.strip():
                    continue
                normalized_specialist_name = normalize_for_matching(specialist_name)
                if not normalized_specialist_name:
                    continue
                if _pad_surface_token(normalized_specialist_name) not in padded_message:
                    specialist_name_tokens = [
                        token
                        for token in normalized_specialist_name.split()
                        if isinstance(token, str) and token
                    ]
                    if len(specialist_name_tokens) >= 2 and specialist_name_tokens[0] in normalized_message_tokens:
                        specialist_prefix_matches.append(specialist_name.strip())
                    continue
                specialist_matches.append(specialist_name.strip())
            if len(specialist_matches) == 1:
                return _record_branch_catalog_hint(specialist_matches[0])
            unique_prefix_matches = list(dict.fromkeys(specialist_prefix_matches))
            if not specialist_matches and len(unique_prefix_matches) == 1:
                return _record_branch_catalog_hint(
                    unique_prefix_matches[0],
                    match_mode="first_name_unique",
                )
    skip_hint_stage, hint_budget_remaining_ms = _should_skip_secondary_llm_stage(
        timing_context=timing_context,
        min_remaining_ms=WEBHOOK_SECONDARY_LLM_MIN_BUDGET_MS,
    )
    if skip_hint_stage:
        specialist_name_hint = _extract_surface_specialist_name_hint()
        if isinstance(specialist_name_hint, str) and specialist_name_hint.strip():
            hint_meta = {
                "specialist_hint_attempted": False,
                "specialist_hint_ok": True,
                "specialist_hint_error": None,
                "specialist_hint_source": "message_surface",
            }
            if saved_message:
                _update_message_decision_metadata(saved_message, hint_meta)
            _record_decision_trace(
                conversation,
                {
                    "stage": "specialist_hint",
                    "decision": "ok",
                    "tool_action": tool_action,
                    "attempted": False,
                    "confidence": 1.0,
                    "error": None,
                    "source": "message_surface",
                    "specialist_name": specialist_name_hint,
                },
            )
            return specialist_name_hint
        hint_meta = {
            "specialist_hint_attempted": False,
            "specialist_hint_ok": False,
            "specialist_hint_error": "budget_reserved",
        }
        if isinstance(hint_budget_remaining_ms, (int, float)):
            hint_meta["specialist_hint_budget_remaining_ms"] = round(
                hint_budget_remaining_ms, 2
            )
        if saved_message:
            _update_message_decision_metadata(saved_message, hint_meta)
        _record_decision_trace(
            conversation,
            {
                "stage": "specialist_hint",
                "decision": "skipped",
                "tool_action": tool_action,
                "reason": "budget_reserved",
                "budget_remaining_ms": (
                    round(hint_budget_remaining_ms, 2)
                    if isinstance(hint_budget_remaining_ms, (int, float))
                    else None
                ),
                "budget_required_ms": round(WEBHOOK_SECONDARY_LLM_MIN_BUDGET_MS, 2),
            },
        )
        return None

    specialist_hint = extract_specialist_hint_llm(
        message_text,
        client_slug=client_slug,
        timing_context=timing_context,
    )
    specialist_name_hint = None
    if isinstance(specialist_hint, dict):
        candidate = specialist_hint.get("specialist_name")
        if isinstance(candidate, str) and candidate.strip():
            specialist_name_hint = candidate.strip()
        hint_meta = {
            "specialist_hint_attempted": bool(specialist_hint.get("attempted")),
            "specialist_hint_ok": bool(specialist_hint.get("ok")),
            "specialist_hint_confidence": specialist_hint.get("confidence"),
            "specialist_hint_error": specialist_hint.get("error"),
            "specialist_hint_language": specialist_hint.get("language"),
            "specialist_hint_source": "llm",
        }
        if saved_message:
            _update_message_decision_metadata(saved_message, hint_meta)
        _record_decision_trace(
            conversation,
            {
                "stage": "specialist_hint",
                "decision": "ok" if specialist_name_hint else "empty",
                "tool_action": tool_action,
                "attempted": bool(specialist_hint.get("attempted")),
                "confidence": specialist_hint.get("confidence"),
                "error": specialist_hint.get("error"),
                "language": specialist_hint.get("language"),
                "source": "llm",
            },
        )
    return specialist_name_hint


def _normalize_booking_start_at_tool_arg(
    tool_args: dict[str, Any] | None,
    *,
    fallback_datetime: str | None,
    now: datetime,
) -> bool:
    if not isinstance(tool_args, dict):
        return False
    raw_start_at = tool_args.get("start_at")
    if not isinstance(raw_start_at, str) or not raw_start_at.strip():
        return False
    parsed_start_at = None
    normalized_start_at = raw_start_at.strip()
    try:
        parsed_start_at = datetime.fromisoformat(normalized_start_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        parsed_start_at = None
    if parsed_start_at is None:
        return False
    if parsed_start_at.tzinfo is None:
        parsed_start_at = parsed_start_at.replace(tzinfo=timezone.utc)
    now_ref = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    # Reject stale absolute datetimes emitted by the planner and rebase to current turn slot.
    if parsed_start_at >= (now_ref - timedelta(hours=12)):
        return False
    if not isinstance(fallback_datetime, str) or not fallback_datetime.strip():
        return False
    tool_args["start_at"] = fallback_datetime.strip()
    return True


def _collect_plan_consult_refs(client_slug: str | None) -> tuple[list[str], str | None]:
    from app.services.consult_pack_service import load_consult_playbook

    playbook, error = load_consult_playbook(client_slug)
    if error or not playbook:
        return [], error or "consult_playbook_missing"
    refs = [topic.id for topic in playbook.topics if getattr(topic, "id", None)]
    return refs, None


def _normalize_class_name(class_name: str) -> str:
    normalized = class_name.strip()
    if normalized.casefold() in {"info", "info_bundle"}:
        return "info_bundle"
    return normalized


def _preflight_booking_block(
    *,
    message_text: str | None,
    client_config: dict | None,
    booking_active: bool,
) -> dict | None:
    if booking_active or not message_text:
        return None
    if (
        is_greeting_message(message_text)
        or is_thanks_message(message_text)
        or is_acknowledgement_message(message_text)
        or is_low_signal_message(message_text)
    ):
        return {"booking_blocked_reason": "intent_signal"}
    domain_intent, in_score, out_score, _ = classify_domain_with_scores(
        message_text,
        client_config,
    )
    strong_out, _ = is_strong_out_of_domain(
        message_text,
        domain_intent,
        in_score,
        out_score,
        client_config,
    )
    if strong_out:
        return {"booking_blocked_reason": "out_of_domain_signal"}
    return None


def _should_suppress_booking_slot_signal(
    *,
    message_text: str | None,
    class_carryover: dict | None,
    client_slug: str | None,
) -> bool:
    if not message_text:
        return False
    if not isinstance(class_carryover, dict):
        return False
    if class_carryover.get("class") != "info_bundle":
        return False
    info_sections = class_carryover.get("info_sections")
    if not info_sections:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    if not tokens or len(tokens) > SESSION_MEMORY_SHORT_TOKENS:
        return False
    if "?" in message_text:
        return False
    if any(ch.isdigit() for ch in message_text):
        return False
    if _has_explicit_service_signal(
        message_text,
        client_slug=client_slug,
        intent_decomp_payload=None,
    ):
        return False
    return True


def _evaluate_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None,
    message_text: str | None,
    relative_base: datetime | None = None,
) -> tuple[bool, dict | None]:
    if not messages:
        return False, None
    if any(_is_booking_request(message, client_slug=client_slug) for message in messages):
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
        if _looks_like_info_query(message_text, client_slug=client_slug):
            return False, {"booking_blocked_reason": "info_question"}
        normalized = normalize_for_matching(message_text)
        procedure_combo_any = get_signal_lexicon_list(client_slug, "procedure_combo_require_any")
        procedure_combo_all = get_signal_lexicon_list(client_slug, "procedure_combo_require_all")
        if (
            normalized
            and procedure_combo_any
            and procedure_combo_all
            and _contains_any(normalized, procedure_combo_any)
            and _contains_any(normalized, procedure_combo_all)
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

def _looks_like_hours_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    phrases = get_system_lexicon_list("hours_followup_phrases")
    return bool(phrases) and _contains_any(normalized, phrases)


def _has_explicit_location_or_hours_request(
    message_text: str | None,
    *,
    client_slug: str | None,
    strict: bool = False,
) -> bool:
    if not message_text:
        return False
    _info_intents, info_meta = _detect_info_class_intents(
        message_text,
        intent_decomp_set=set(),
        client_slug=client_slug,
    )
    anchor_intents: set[str] = set()
    if isinstance(info_meta, dict):
        raw_anchor_intents = info_meta.get("anchor_intents")
        if isinstance(raw_anchor_intents, list):
            anchor_intents = {
                intent.strip().casefold()
                for intent in raw_anchor_intents
                if isinstance(intent, str) and intent.strip()
            }
    info_signals = info_meta.get("info_signals") if isinstance(info_meta, dict) else None
    master_signal = bool(isinstance(info_signals, dict) and info_signals.get("master"))
    if isinstance(info_signals, dict):
        if info_signals.get("location_address_hint"):
            return True

    if {"location", "hours", "parking"} & anchor_intents:
        # strict mode must not treat weak anchor matches as explicit location/hours
        # when the same message is primarily about specialists/masters.
        if strict and master_signal:
            return False
        return True

    return False


def _looks_like_carryover_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    if not tokens:
        return False
    followup_phrases = get_system_lexicon_list("carryover_followup_phrases")
    if followup_phrases and _contains_any(normalized, followup_phrases):
        return True
    if (
        tokens[0].startswith(_CARRYOVER_CAPACITY_LEAD_PREFIX)
        and _contains_any_text_token(normalized, _CARRYOVER_CAPACITY_TOKENS)
    ):
        return True
    if len(tokens) <= SESSION_MEMORY_SHORT_TOKENS:
        pricing_groups = INFO_ANCHOR_GROUPS.get("pricing", [])
        if pricing_groups and _count_anchor_hits(tokens, pricing_groups) > 0:
            return True
    lead_tokens = set(get_system_lexicon_list("carryover_followup_lead_tokens"))
    question_phrases = get_system_lexicon_list("carryover_followup_question_phrases")
    if lead_tokens and question_phrases and tokens[0] in lead_tokens:
        if _contains_any(normalized, question_phrases):
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
    "budget_reserved": "budget_reserved",
    "no_api_key": "no_api_key",
    "prompt_missing": "prompt_missing",
    "empty_message": "empty_message",
    "empty_response": "empty_response",
    "invalid_class": "invalid_class",
    "unsupported_temperature": "unsupported_temperature",
}
CONTROLLER_FALLBACK_ERROR_VALUES = {"controller_failed", "error"}
CONTROLLER_FALLBACK_REASONS = set(CONTROLLER_FALLBACK_REASON_MAP.values()) | {"error"}
POLICY_CORE_INFO_RESCUE_REASON_PREFIXES = (
    "policy_error:",
    "policy_validation:",
    "llm_degraded:",
)
POLICY_CORE_RETRYABLE_ERROR_CODES = {
    "timeout",
    "connection_error",
    "service_unavailable",
    "rate_limit",
    "deadline_exceeded",
    "budget_exceeded",
}
POLICY_STYLE_REFERENCE_HINT_INTENTS = {"style_reference", "ask_photo", "send_photo"}


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


def _policy_core_reason_supports_info_rescue(reason: str | None) -> bool:
    classification = _classify_policy_core_degrade_reason(reason)
    return bool(classification.get("info_rescue_eligible"))


def _is_timeout_degrade_failure(failure: dict[str, Any] | None) -> bool:
    if not isinstance(failure, dict):
        return False
    category = failure.get("category")
    code = failure.get("code")
    if not (isinstance(category, str) and isinstance(code, str)):
        return False
    normalized_code = code.strip().casefold()
    if category in {"llm_degraded", "policy_error"}:
        return normalized_code in {"timeout", "deadline_exceeded", "budget_exceeded"}
    return False


def _timeout_degrade_retry_status(
    context_manager: dict[str, Any] | None,
    *,
    intent: str = POLICY_TIMEOUT_DEGRADE_CLARIFY_INTENT,
) -> tuple[int, bool]:
    manager = context_manager if isinstance(context_manager, dict) else {}
    retry_count, _ = _get_clarify_attempt_state(
        manager,
        intent,
    )
    retry_count = max(0, int(retry_count))
    exhausted = retry_count >= POLICY_TIMEOUT_DEGRADE_MAX_RETRIES
    return retry_count, exhausted


def _is_retryable_policy_core_error_code(code: str | None) -> bool:
    if not isinstance(code, str):
        return False
    normalized = code.strip().casefold()
    if not normalized:
        return False
    if normalized in POLICY_CORE_RETRYABLE_ERROR_CODES:
        return True
    if normalized.startswith("http_5"):
        return True
    return False


def _supports_policy_core_llm_rescue(error: str | None) -> bool:
    if not isinstance(error, str):
        return False
    normalized = error.strip().casefold()
    if not normalized:
        return False
    return normalized in POLICY_CORE_RESCUE_ERROR_CODES


def _is_policy_core_rescue_critical_turn(
    *,
    conversation_state: str | None,
    expected_reply_type: str | None,
    expected_reply_blocked_by_info: bool,
    info_class_intents: set[str] | list[str] | tuple[str, ...] | None,
    booking_wants_flow: bool,
    message_text: str | None,
    intent_decomp_set: set[str],
    consult_intent: bool,
    client_slug: str | None,
) -> bool:
    if info_class_intents:
        return False
    expected_reply_active = bool(
        expected_reply_type in {EXPECTED_REPLY_SERVICE, EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME}
        and not expected_reply_blocked_by_info
    )
    pending_flow = conversation_state in {
        ConversationState.PENDING.value,
        ConversationState.MANAGER_ACTIVE.value,
    }
    booking_flow = bool(
        booking_wants_flow
        and message_text
        and _is_booking_request(message_text, client_slug=client_slug)
        and not (intent_decomp_set & INFO_INTENTS)
        and not consult_intent
    )
    return bool(expected_reply_active or pending_flow or booking_flow)


def _should_use_expected_reply_collect_fast_path(
    *,
    message_text: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    intent_decomp_set: set[str],
    info_class_intents: set[str] | list[str] | tuple[str, ...] | None,
    booking_wants_flow: bool,
    booking_slot_signal: bool,
    consult_intent: bool,
    booking_reference_present: bool,
    booking_slots_complete: bool,
    refusal_flags: dict[str, bool] | None,
    client_slug: str | None,
) -> bool:
    fast_path_enabled = str(
        os.environ.get("POLICY_CORE_EXPECTED_REPLY_COLLECT_FAST_PATH", "0")
    ).strip().lower() in {"1", "true", "yes", "on"}
    if not fast_path_enabled:
        return False
    if expected_reply_type not in {EXPECTED_REPLY_SERVICE, EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME}:
        return False
    if expected_reply_matched is not False or expected_reply_blocked_by_info:
        return False
    normalized_text = message_text.strip() if isinstance(message_text, str) else ""
    if not normalized_text:
        return False
    if not booking_wants_flow or consult_intent:
        return False
    if info_class_intents:
        return False
    verification_text_signal = _looks_like_booking_verification_request(normalized_text)
    allow_intent_override = False
    if (
        verification_text_signal
        and expected_reply_type in {EXPECTED_REPLY_NAME, EXPECTED_REPLY_TIME}
        and not booking_reference_present
    ):
        allow_intent_override = True
    if intent_decomp_set != {"other"}:
        verification_intents = {
            "check_booking",
            "verify_booking",
            "confirm_booking",
            "booking_confirmation",
        }
        allow_verification_collect = bool(
            intent_decomp_set
            and intent_decomp_set <= verification_intents
            and expected_reply_type in {EXPECTED_REPLY_NAME, EXPECTED_REPLY_TIME}
            and not booking_reference_present
        )
        allow_booking_collect = bool(
            intent_decomp_set == {"booking"}
            and expected_reply_type in {EXPECTED_REPLY_SERVICE, EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME}
            and not booking_reference_present
            and (
                not booking_slots_complete
                or expected_reply_type in {EXPECTED_REPLY_NAME, EXPECTED_REPLY_TIME}
            )
        )
        if not (allow_verification_collect or allow_booking_collect):
            return False
        allow_intent_override = True
    if booking_slot_signal and not allow_intent_override:
        return False
    if _looks_like_info_query(normalized_text, client_slug=client_slug):
        return False
    if expected_reply_type == EXPECTED_REPLY_TIME and isinstance(client_slug, str) and client_slug.strip():
        normalized_service = _normalize_service_text(normalized_text)
        if normalized_service and (
            _match_service(normalized_service, client_slug)
            or _matches_service_request_lexicon(normalized_service, client_slug)
        ):
            return False
    if is_human_request_message(normalized_text) or is_frustration_message(normalized_text):
        return False
    if isinstance(refusal_flags, dict) and any(bool(value) for value in refusal_flags.values()):
        return False
    return True


def _build_expected_reply_collect_fast_policy_result(
    *,
    expected_reply_type: str | None,
    booking_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    collect_slot = _expected_reply_slot_key(expected_reply_type)
    if collect_slot not in {"service", "datetime", "name"}:
        return None
    slot_state: dict[str, str] = {}
    if isinstance(booking_state, dict):
        for slot_key in BOOKING_SLOT_ORDER:
            value = booking_state.get(slot_key)
            if isinstance(value, str) and value.strip():
                slot_state[slot_key] = value.strip()
    payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "confidence": 1.0,
        "reason": "expected_reply_pending_collect_fast_path",
        "goal": "booking",
        "slots": slot_state,
        "next_question": collect_slot,
        "open_questions": [collect_slot],
        "needs_manager": False,
        "risk_signals": [],
    }
    return {
        "ok": True,
        "payload": payload,
        "error": None,
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
        "compact_input_used": False,
        "compact_retry_used": False,
    }


def _should_attempt_policy_core_llm_rescue(
    *,
    policy_result: dict[str, Any] | None,
    conversation_state: str | None,
    expected_reply_type: str | None,
    expected_reply_blocked_by_info: bool,
    info_class_intents: set[str] | list[str] | tuple[str, ...] | None,
    booking_wants_flow: bool,
    message_text: str | None,
    intent_decomp_set: set[str],
    consult_intent: bool,
    client_slug: str | None,
) -> bool:
    if not POLICY_CORE_RESCUE_MATRIX_ENABLED:
        return False
    if not isinstance(policy_result, dict):
        return False
    if policy_result.get("ok") or not policy_result.get("attempted"):
        return False
    if not _supports_policy_core_llm_rescue(policy_result.get("error")):
        return False
    return _is_policy_core_rescue_critical_turn(
        conversation_state=conversation_state,
        expected_reply_type=expected_reply_type,
        expected_reply_blocked_by_info=expected_reply_blocked_by_info,
        info_class_intents=info_class_intents,
        booking_wants_flow=booking_wants_flow,
        message_text=message_text,
        intent_decomp_set=intent_decomp_set,
        consult_intent=consult_intent,
        client_slug=client_slug,
    )


def _build_policy_core_rescue_timing_context(
    *,
    base_timing_context: dict | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    timeout_seconds = max(float(timeout_seconds), 0.1)
    rescue_context: dict[str, Any] = {
        "pipeline_budget_ms": int(timeout_seconds * 1000),
        "pipeline_deadline": time.monotonic() + timeout_seconds,
        "timing": {},
    }
    if not isinstance(base_timing_context, dict):
        return rescue_context
    for key in (
        "trace_id",
        "client_slug",
        "conversation_id",
        "message_id",
        "branch_id",
        "outbox_id",
    ):
        value = base_timing_context.get(key)
        if value is not None:
            rescue_context[key] = value
    simulation = base_timing_context.get("simulation")
    if isinstance(simulation, dict):
        rescue_context["simulation"] = dict(simulation)
    return rescue_context


def _classify_policy_core_degrade_reason(reason: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "category": "none",
        "code": "none",
        "retryable": False,
        "info_rescue_eligible": False,
        "severity": "none",
    }
    if not isinstance(reason, str):
        return result

    normalized = reason.strip().casefold()
    if not normalized:
        return result

    category = "runtime"
    code = normalized
    if normalized == "guard_not_eligible":
        category = "guard"
    elif normalized == "envelope_missing":
        category = "runtime"
    elif ":" in normalized:
        prefix, suffix = normalized.split(":", 1)
        prefix = prefix.strip()
        suffix = suffix.strip() or "unknown"
        if prefix in {"policy_error", "policy_validation", "llm_degraded"}:
            category = prefix
            code = suffix

    info_rescue_eligible = category in {"policy_error", "policy_validation", "llm_degraded"}

    retryable = False
    if category in {"policy_error", "llm_degraded"}:
        retryable = _is_retryable_policy_core_error_code(code)
    elif category == "runtime":
        retryable = code == "envelope_missing"

    if category == "guard":
        severity = "low"
    elif category == "policy_validation":
        severity = "high"
    elif category == "policy_error":
        severity = "medium" if retryable else "high"
    elif category == "llm_degraded":
        severity = "medium" if retryable else "high"
    else:
        severity = "medium" if retryable else "low"

    result.update(
        {
            "category": category,
            "code": code,
            "retryable": retryable,
            "info_rescue_eligible": info_rescue_eligible,
            "severity": severity,
        }
    )
    return result


def _policy_has_style_reference_hint(
    *,
    policy_intent: str | None,
    policy_reason: str | None,
) -> bool:
    if isinstance(policy_intent, str):
        normalized_intent = policy_intent.strip().casefold()
        if normalized_intent in POLICY_STYLE_REFERENCE_HINT_INTENTS:
            return True
        if "style" in normalized_intent:
            return True
    if isinstance(policy_reason, str):
        normalized_reason = policy_reason.strip().casefold()
        if normalized_reason.startswith("style_reference"):
            return True
        if "style" in normalized_reason:
            return True
    return False


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
    explicit_service_signal: bool,
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
    if explicit_service_signal:
        in_signals.append("explicit_service")
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
    explicit_service_signal: bool,
) -> dict[str, Any]:
    result = _build_class_controller_result(
        info_intents=info_intents,
        info_meta=info_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        explicit_service_signal=explicit_service_signal,
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


def _controller_meta_updates_from_router_state(router_state: dict | None) -> dict[str, Any]:
    if not isinstance(router_state, dict):
        return {}
    controller_output = router_state.get("output")
    controller_goal = controller_output.get("goal") if isinstance(controller_output, dict) else None
    controller_confidence = router_state.get("confidence")
    controller_used = bool(router_state.get("used"))
    controller_low_confidence = bool(
        controller_used
        and isinstance(controller_confidence, (int, float))
        and controller_confidence < CONTROLLER_CONFIDENCE_THRESHOLD
    )
    controller_fallback_reason = router_state.get("fallback_reason")
    if isinstance(controller_fallback_reason, str):
        normalized = controller_fallback_reason.strip().casefold()
        if not normalized or normalized == "skipped":
            controller_fallback_reason = None
    else:
        controller_fallback_reason = None
    return {
        "controller_used": controller_used,
        "controller_attempted": bool(router_state.get("attempted")),
        "controller_fallback": bool(router_state.get("fallback")),
        "controller_low_confidence": controller_low_confidence,
        "controller_used_reason": router_state.get("used_reason"),
        "controller_confidence": controller_confidence,
        "controller_error": router_state.get("error"),
        "controller_goal": controller_goal,
        "controller_fallback_reason": controller_fallback_reason,
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


def _detect_explicit_name_provided(message_text: str, *, client_slug: str | None) -> bool:
    if not message_text:
        return False
    if classify_confirmation(message_text) in {"yes", "no"}:
        return False
    return bool(_validate_name_slot(message_text, allow_freeform=False, client_slug=client_slug))


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


def _should_append_followup_prompt(primary: str | None, followup: str | None) -> bool:
    if not followup:
        return False
    followup_normalized = normalize_for_matching(followup)
    if not followup_normalized:
        return False
    primary_normalized = normalize_for_matching(primary or "")
    return followup_normalized not in primary_normalized


MULTI_INTENT_LABELS = {
    "booking": "записи",
    "pricing": "цене",
    "duration": "длительности",
    "location": "адресу",
    "hours": "времени",
    "other": "другому вопросу",
}


_DEFAULT_POLICY_HANDLER = {
    "escalation_gate": _pack_escalation_gate,
    "service_matcher": get_pack_service_decision,
    "truth_gate": get_pack_decision,
    "price_item": get_pack_price_item,
    "price_sidecar": _pack_price_sidecar,
}


_POLICY_HANDLERS = {
    "default": _DEFAULT_POLICY_HANDLER,
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


get_active_handover = _handover_owner_get_active_handover


def _reuse_active_handover(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message: str,
    source: str,
    intent: str | None = None,
) -> tuple[Handover | None, bool, bool]:
    return _handover_owner_reuse_active_handover(
        db=db,
        conversation=conversation,
        user=user,
        message=message,
        source=source,
        intent=intent,
        hooks=ActiveHandoverReuseRuntimeHooks(
            get_active_handover=get_active_handover,
            transition_state=transition_state,
            send_telegram_notification=send_telegram_notification,
            record_decision_trace=_record_decision_trace,
        ),
    )


def _create_pending_escalation_with_notification(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    user_message: str,
    trigger_type: str,
    trigger_value: str | None = None,
):
    return _handover_owner_create_pending_escalation_with_notification(
        db=db,
        conversation=conversation,
        user=user,
        user_message=user_message,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        hooks=PendingEscalationNotificationRuntimeHooks(
            escalate_to_pending=escalate_to_pending,
            send_telegram_notification=send_telegram_notification,
        ),
    )


def _has_pending_booking_resume_contract(context: dict[str, Any] | None) -> bool:
    return _derive_pending_booking_resume_boundary_payload(context) is not None


def _derive_pending_booking_resume_reason(context: dict[str, Any] | None) -> str | None:
    return _state_service_derive_pending_resume_reason(context)


def _derive_pending_booking_resume_boundary_payload(
    context: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    return _state_service_derive_pending_booking_resume_boundary_payload(
        context, now=now, prompt_builder=_booking_prompt_for_expected_reply_type
    )


def _build_minimum_data_contract_status(
    db: Session,
    *,
    branch_id: UUID | None,
) -> MinimumDataContractStatus:
    if not branch_id:
        return MinimumDataContractStatus(ready=True, missing_fields=[])
    published = get_current_published(db, branch_id=branch_id)
    if not published or not isinstance(published.payload_json, dict):
        return MinimumDataContractStatus(ready=False, missing_fields=["knowledge_published"])
    return evaluate_minimum_data_contract(published.payload_json)


def _record_minimum_data_contract_meta(
    saved_message: Message | None,
    status: MinimumDataContractStatus,
) -> None:
    if not saved_message:
        return
    _update_message_decision_metadata(
        saved_message,
        {
            "minimum_data_contract": {
                "version": MINIMUM_DATA_CONTRACT_VERSION,
                "ready": status.ready,
                "missing_fields": status.missing_fields,
            }
        },
    )


def _handle_minimum_data_safe_mode_gate(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    saved_message: Message | None,
    message_text: str,
    status: MinimumDataContractStatus,
    guard_only: bool = False,
    send_and_save,
) -> WebhookResponse | None:
    if status.ready or not status.missing_fields:
        return None
    if not conversation.branch_id:
        return None
    if guard_only:
        _record_decision_trace(
            conversation,
            {
                "stage": "minimum_data_safe_mode",
                "decision": "guard_only",
                "state": conversation.state,
                "reason": "minimum_data_contract",
                "missing_fields": status.missing_fields,
            },
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {"minimum_data_guard_only": True},
            )
        return None

    missing_fields = status.missing_fields
    if conversation.state != ConversationState.BOT_ACTIVE.value:
        _record_decision_trace(
            conversation,
            {
                "stage": "minimum_data_safe_mode",
                "decision": "pending_state",
                "state": conversation.state,
                "reason": "minimum_data_contract",
                "missing_fields": missing_fields,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_wait",
            intent=None,
            source="minimum_data_safe_mode",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(MSG_PENDING_WAIT)
        result_message = (
            "Minimum data safe-mode pending wait sent"
            if sent
            else "Minimum data safe-mode pending wait failed"
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
        source="minimum_data_safe_mode",
        intent="safe_mode",
    )
    if reused:
        _record_decision_trace(
            conversation,
            {
                "stage": "minimum_data_safe_mode",
                "decision": "reused",
                "state": conversation.state,
                "telegram_sent": telegram_sent,
                "reason": "minimum_data_contract",
                "missing_fields": missing_fields,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_escalation",
            intent=None,
            source="minimum_data_safe_mode",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(MSG_ESCALATED)
        result_message = (
            "Minimum data safe-mode escalation reused"
            if sent
            else "Minimum data safe-mode escalation reuse failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    escalation_notification_result = _create_pending_escalation_with_notification(
        db=db,
        conversation=conversation,
        user=user,
        user_message=handover_message,
        trigger_type="minimum_data_contract",
        trigger_value=str(conversation.branch_id),
    )
    if escalation_notification_result.ok:
        handover = escalation_notification_result.handover
        handover_reopened = escalation_notification_result.handover_reopened
        telegram_sent = escalation_notification_result.telegram_sent
        _record_decision_trace(
            conversation,
            {
                "stage": "minimum_data_safe_mode",
                "decision": "created",
                "state": conversation.state,
                "telegram_sent": telegram_sent,
                "reason": "minimum_data_contract",
                "missing_fields": missing_fields,
                "handover_reopened": handover_reopened,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_escalation",
            intent=None,
            source="minimum_data_safe_mode",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(MSG_ESCALATED)
        result_message = (
            "Minimum data safe-mode escalation created"
            if sent
            else "Minimum data safe-mode escalation send failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    logger.error("Minimum data safe-mode escalation failed: %s", result.error)
    _record_decision_trace(
        conversation,
        {
            "stage": "minimum_data_safe_mode",
            "decision": "failed",
            "state": conversation.state,
            "error": result.error,
            "reason": "minimum_data_contract",
            "missing_fields": missing_fields,
        },
    )
    _record_message_decision_meta(
        saved_message,
        action="pending_escalation",
        intent=None,
        source="minimum_data_safe_mode",
        fast_intent=False,
    )
    bot_response, sent = send_and_save(MSG_ESCALATED)
    result_message = (
        "Minimum data safe-mode escalation failed"
        if sent
        else "Minimum data safe-mode escalation failed to send"
    )
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )


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

    escalation_notification_result = _create_pending_escalation_with_notification(
        db=db,
        conversation=conversation,
        user=user,
        user_message=handover_message,
        trigger_type="knowledge_safe_mode",
        trigger_value=branch.knowledge_tag or str(branch.id),
    )
    if escalation_notification_result.ok:
        handover = escalation_notification_result.handover
        handover_reopened = escalation_notification_result.handover_reopened
        telegram_sent = escalation_notification_result.telegram_sent
        _record_decision_trace(
            conversation,
            {
                "stage": "knowledge_safe_mode",
                "decision": "created",
                "state": conversation.state,
                "telegram_sent": telegram_sent,
                "reason": safe_mode_reason,
                "handover_reopened": handover_reopened,
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
    from app.core import consultant_runtime

    return await consultant_runtime.handle_webhook_payload(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=enforce_secret,
        enqueue_only=enqueue_only,
        skip_persist=skip_persist,
        conversation_id=conversation_id,
        batch_messages=batch_messages,
        outbox_ids=outbox_ids,
        outbox_created_at=outbox_created_at,
    )
