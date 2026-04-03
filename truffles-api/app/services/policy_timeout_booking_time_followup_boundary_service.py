from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from app.core import DialogStateService
from app.schemas.webhook import WebhookResponse

_DIALOG_STATE_SERVICE = DialogStateService()


@dataclass(frozen=True)
class PolicyTimeoutBookingTimeFollowupBoundaryRuntimeHooks:
    get_conversation_context: Callable[..., dict[str, Any]]
    set_booking_context: Callable[..., dict[str, Any]]
    set_expected_reply_context: Callable[..., dict[str, Any]]
    get_context_manager: Callable[..., dict[str, Any]]
    sync_canonical_dialog_state: Callable[..., dict[str, Any]]
    set_context_manager: Callable[..., dict[str, Any]]
    get_canonical_dialog_state: Callable[..., dict[str, Any]]
    sync_session_memory_interaction_state: Callable[..., tuple[dict[str, Any], dict[str, Any]]]
    set_conversation_context: Callable[..., None]
    record_session_memory_update: Callable[..., None]
    apply_policy_guard_override: Callable[..., None]
    sync_policy_plan_audit: Callable[..., None]
    record_decision_trace: Callable[..., None]
    record_message_decision_meta: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]
    build_response: Callable[..., str]
    combine_sidecar: Callable[..., str]
    maybe_apply_consult_return: Callable[..., str]
    reset_low_confidence_retry: Callable[..., None]
    send_and_save: Callable[..., tuple[str, bool]]
    commit: Callable[..., None]


@dataclass(frozen=True)
class PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput:
    conversation: Any
    saved_message: Any
    now: datetime
    message_count: int
    branch_id: Any
    policy_core_mode: str
    policy_core_degrade_reason: str
    reason_code: str
    guard_reason: str
    booking_state: dict[str, Any]
    collect_slot: str
    current_booking_datetime: str
    alternate_booking_datetime: str
    expected_reply_type: str
    expected_reply_reason: str
    interaction_target: str = "time"
    interaction_relation: str = "ask_about_requested_slot"
    interaction_owner: str = "llm_policy_core:ask_about_requested_slot"
    pending_question_owner: str = "booking_time_availability_followup"
    recovery_tag: str = "timeout_active_name_time_availability_followup"
    retry_path: str = "booking_time_availability_followup"
    message_action: str = "collect"
    message_intent: str = "booking"
    message_source: str = "llm_policy_core"
    style_signal: bool = False
    has_media: bool = False
    style_sidecar_message: str | None = None
    consult_return_pending: bool = False
    consult_return_prompt: str | None = None
    consult_context: dict[str, Any] | None = None
    consult_return_reason: str | None = None
    result_message_sent: str | None = None
    result_message_failed: str | None = None


def handle_policy_timeout_booking_time_followup_boundary(
    *,
    runtime_input: PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput,
    hooks: PolicyTimeoutBookingTimeFollowupBoundaryRuntimeHooks,
) -> WebhookResponse:
    context = hooks.get_conversation_context(runtime_input.conversation)
    context = hooks.set_booking_context(context, runtime_input.booking_state)
    context = hooks.set_expected_reply_context(
        conversation=runtime_input.conversation,
        saved_message=runtime_input.saved_message,
        context=context,
        expected_reply_type=runtime_input.expected_reply_type,
        reason=runtime_input.expected_reply_reason,
        now=runtime_input.now,
    )
    timeout_followup_manager = hooks.sync_canonical_dialog_state(
        hooks.get_context_manager(context),
        booking_state=runtime_input.booking_state,
        expected_reply_type=runtime_input.expected_reply_type,
        expected_reply_reason=runtime_input.expected_reply_reason,
        message_count=runtime_input.message_count,
        branch_id=runtime_input.branch_id,
        consult_context=(
            runtime_input.consult_context
            if isinstance(runtime_input.consult_context, dict)
            else None
        ),
        interaction_target=runtime_input.interaction_target,
        interaction_relation=runtime_input.interaction_relation,
        interaction_owner=runtime_input.interaction_owner,
    )
    context = hooks.set_context_manager(context, timeout_followup_manager)
    interaction_state_payload = _DIALOG_STATE_SERVICE.project_context_session_memory_interaction_state(
        context,
        context_manager_key="context_manager",
    )
    context, timeout_followup_memory = hooks.sync_session_memory_interaction_state(
        context,
        interaction_state=interaction_state_payload if isinstance(interaction_state_payload, dict) else None,
        now=runtime_input.now,
    )
    hooks.set_conversation_context(runtime_input.conversation, context)
    hooks.record_session_memory_update(
        runtime_input.conversation,
        runtime_input.saved_message,
        memory=timeout_followup_memory,
        reason="question_set",
    )
    hooks.apply_policy_guard_override(
        final_action="collect",
        final_tool_action="collect",
        reason_code=runtime_input.reason_code,
        reason=runtime_input.guard_reason,
    )
    hooks.sync_policy_plan_audit(emit_trace=True)
    hooks.record_decision_trace(
        runtime_input.conversation,
        {
            "stage": "policy_core_guard",
            "decision": "timeout_active_name_time_availability_followup",
            "state": getattr(runtime_input.conversation, "state", None),
            "mode": runtime_input.policy_core_mode,
            "reason": runtime_input.policy_core_degrade_reason,
            "missing_slot": runtime_input.collect_slot,
            "current_datetime": runtime_input.current_booking_datetime,
            "alternate_datetime": runtime_input.alternate_booking_datetime,
        },
    )
    hooks.record_decision_trace(
        runtime_input.conversation,
        {
            "stage": "pending_question_interaction",
            "decision": "booking_time_availability_followup",
            "state": getattr(runtime_input.conversation, "state", None),
            "source": "policy_core_guard",
            "pending_question_act": runtime_input.interaction_relation,
            "pending_question_target": runtime_input.interaction_target,
            "active_question_relation": runtime_input.interaction_relation,
            "requested_slot": runtime_input.collect_slot,
            "expected_reply_type": runtime_input.expected_reply_type,
            "current_datetime": runtime_input.current_booking_datetime,
            "alternate_datetime": runtime_input.alternate_booking_datetime,
        },
    )
    hooks.record_message_decision_meta(
        runtime_input.saved_message,
        action=runtime_input.message_action,
        intent=runtime_input.message_intent,
        source=runtime_input.message_source,
        fast_intent=False,
    )
    if runtime_input.saved_message:
        hooks.update_message_decision_metadata(
            runtime_input.saved_message,
            {
                "pending_question_act": runtime_input.interaction_relation,
                "pending_question_target": runtime_input.interaction_target,
                "pending_question_interaction": runtime_input.interaction_relation,
                "pending_question_owner": runtime_input.pending_question_owner,
                "active_question_relation": runtime_input.interaction_relation,
                "current_datetime": runtime_input.current_booking_datetime,
                "alternate_datetime": runtime_input.alternate_booking_datetime,
                "expected_reply_type": runtime_input.expected_reply_type,
                "expected_reply_reason": runtime_input.expected_reply_reason,
                "policy_core_guard_recovery": runtime_input.recovery_tag,
                "policy_core_timeout_retry_path": runtime_input.retry_path,
            },
        )
    bot_response = hooks.build_response(
        current_slot=runtime_input.current_booking_datetime,
        alternate_slot=runtime_input.alternate_booking_datetime,
    )
    if runtime_input.style_signal and not runtime_input.has_media and runtime_input.style_sidecar_message:
        bot_response = hooks.combine_sidecar(runtime_input.style_sidecar_message, bot_response)
    bot_response = hooks.maybe_apply_consult_return(
        conversation=runtime_input.conversation,
        saved_message=runtime_input.saved_message,
        bot_response=bot_response,
        consult_return_pending=runtime_input.consult_return_pending,
        consult_return_prompt=runtime_input.consult_return_prompt,
        consult_context=runtime_input.consult_context,
        reason=runtime_input.consult_return_reason or runtime_input.expected_reply_reason,
    )
    hooks.reset_low_confidence_retry(runtime_input.conversation)
    bot_response, sent = hooks.send_and_save(bot_response)
    hooks.commit()
    return WebhookResponse(
        success=True,
        message=(
            runtime_input.result_message_sent
            if sent and runtime_input.result_message_sent
            else runtime_input.result_message_failed
            if not sent and runtime_input.result_message_failed
            else "Policy core timeout active-name time-availability follow-up response sent"
            if sent
            else "Policy core timeout active-name time-availability follow-up response failed"
        ),
        conversation_id=getattr(runtime_input.conversation, "id", None),
        bot_response=bot_response,
    )


__all__ = [
    "PolicyTimeoutBookingTimeFollowupBoundaryRuntimeHooks",
    "PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput",
    "handle_policy_timeout_booking_time_followup_boundary",
]
