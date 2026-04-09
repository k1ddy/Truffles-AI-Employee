from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal

from app.schemas.webhook import WebhookResponse

PolicyTimeoutBookingSpecialistBoundaryMode = Literal[
    "specialist_followup",
    "master_info_interrupt",
]


@dataclass(frozen=True)
class PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks:
    get_conversation_context: Callable[..., dict[str, Any]]
    set_booking_context: Callable[..., dict[str, Any]]
    set_expected_reply_context: Callable[..., dict[str, Any]]
    set_conversation_context: Callable[..., None]
    apply_policy_guard_override: Callable[..., None]
    sync_policy_plan_audit: Callable[..., None]
    record_decision_trace: Callable[..., None]
    record_message_decision_meta: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]
    format_specialist_followup_prompt: Callable[..., str]
    send_and_save: Callable[..., tuple[str, bool]]
    commit: Callable[..., None]
    handle_booking_interrupt: Callable[..., WebhookResponse | None]


@dataclass(frozen=True)
class PolicyTimeoutBookingSpecialistBoundaryRuntimeInput:
    mode: PolicyTimeoutBookingSpecialistBoundaryMode
    conversation: Any
    saved_message: Any
    now: datetime
    policy_core_mode: str
    policy_core_degrade_reason: str
    reason_code: str
    guard_reason: str
    booking_state: dict[str, Any] | None
    collect_slot: str
    timeout_booking_service_query: str | None = None
    expected_reply_type: str | None = None
    specialist_name: str | None = None
    specialist_id: str | None = None
    same_name_collision: bool = False
    active_question_relation: str | None = None
    trace_decision: str | None = None
    pending_question_owner: str | None = None
    expected_reply_reason: str | None = None
    recovery_tag: str | None = None
    retry_path: str | None = None
    base_prompt: str | None = None
    question_like: bool = False
    result_message_sent: str | None = None
    result_message_failed: str | None = None
    interrupt_kwargs: dict[str, Any] | None = None


def _normalize_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _build_timeout_booking_state(
    runtime_input: PolicyTimeoutBookingSpecialistBoundaryRuntimeInput,
) -> dict[str, Any]:
    booking_state = dict(runtime_input.booking_state) if isinstance(runtime_input.booking_state, dict) else {}
    if runtime_input.timeout_booking_service_query and not booking_state.get("service"):
        booking_state["service"] = runtime_input.timeout_booking_service_query
    if not booking_state.get("active"):
        booking_state["active"] = True
        booking_state["started_at"] = runtime_input.now.isoformat()
    booking_state["last_question"] = runtime_input.collect_slot
    specialist_name = _normalize_optional_text(runtime_input.specialist_name)
    specialist_id = _normalize_optional_text(runtime_input.specialist_id)
    if specialist_name:
        booking_state["specialist_name"] = specialist_name
    if specialist_id:
        booking_state["specialist_id"] = specialist_id
    if runtime_input.same_name_collision:
        booking_state.pop("name", None)
    return booking_state


def handle_policy_timeout_booking_specialist_boundary(
    *,
    runtime_input: PolicyTimeoutBookingSpecialistBoundaryRuntimeInput,
    hooks: PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks,
) -> WebhookResponse | None:
    booking_state = _build_timeout_booking_state(runtime_input)
    specialist_name = _normalize_optional_text(runtime_input.specialist_name)
    specialist_id = _normalize_optional_text(runtime_input.specialist_id)

    if runtime_input.mode == "specialist_followup":
        context = hooks.get_conversation_context(runtime_input.conversation)
        context = hooks.set_booking_context(context, booking_state)
        expected_reply_type = _normalize_optional_text(runtime_input.expected_reply_type)
        expected_reply_reason = (
            _normalize_optional_text(runtime_input.expected_reply_reason)
            or runtime_input.guard_reason
        )
        trace_decision = (
            _normalize_optional_text(runtime_input.trace_decision)
            or "timeout_specialist_followup"
        )
        pending_question_owner = (
            _normalize_optional_text(runtime_input.pending_question_owner)
            or runtime_input.guard_reason
        )
        recovery_tag = (
            _normalize_optional_text(runtime_input.recovery_tag)
            or "timeout_specialist_followup"
        )
        if expected_reply_type:
            context = hooks.set_expected_reply_context(
                conversation=runtime_input.conversation,
                saved_message=runtime_input.saved_message,
                context=context,
                expected_reply_type=expected_reply_type,
                reason=expected_reply_reason,
                now=runtime_input.now,
            )
        hooks.set_conversation_context(runtime_input.conversation, context)
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
                "decision": trace_decision,
                "state": getattr(runtime_input.conversation, "state", None),
                "mode": runtime_input.policy_core_mode,
                "reason": runtime_input.policy_core_degrade_reason,
                "missing_slot": runtime_input.collect_slot,
            },
        )
        pending_trace: dict[str, Any] = {
            "stage": "pending_question_interaction",
            "decision": "booking_specialist_followup",
            "state": getattr(runtime_input.conversation, "state", None),
            "source": "policy_core_guard",
            "pending_question_target": "specialist",
            "requested_slot": runtime_input.collect_slot,
            "expected_reply_type": expected_reply_type,
        }
        if specialist_name:
            pending_trace["specialist_name"] = specialist_name
        if runtime_input.active_question_relation:
            pending_trace["active_question_relation"] = runtime_input.active_question_relation
        hooks.record_decision_trace(runtime_input.conversation, pending_trace)
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="collect",
            intent="booking",
            source="policy_core_guard",
            fast_intent=False,
        )
        if runtime_input.saved_message:
            metadata_updates: dict[str, Any] = {
                "pending_question_target": "specialist",
                "pending_question_interaction": "specialist_followup",
                "pending_question_owner": pending_question_owner,
                "expected_reply_type": expected_reply_type,
                "expected_reply_reason": expected_reply_reason,
                "policy_core_guard_recovery": recovery_tag,
            }
            if _normalize_optional_text(runtime_input.retry_path):
                metadata_updates["policy_core_timeout_retry_path"] = _normalize_optional_text(
                    runtime_input.retry_path
                )
            if specialist_name:
                metadata_updates["specialist_name"] = specialist_name
            if specialist_id:
                metadata_updates["specialist_id"] = specialist_id
            if runtime_input.active_question_relation:
                metadata_updates["active_question_relation"] = runtime_input.active_question_relation
            hooks.update_message_decision_metadata(runtime_input.saved_message, metadata_updates)
        bot_response = hooks.format_specialist_followup_prompt(
            specialist_name=specialist_name,
            base_prompt=runtime_input.base_prompt or "",
            question_like=runtime_input.question_like,
        )
        bot_response, sent = hooks.send_and_save(bot_response)
        hooks.commit()
        return WebhookResponse(
            success=True,
            message=(
                runtime_input.result_message_sent
                if sent
                else runtime_input.result_message_failed
            )
            or "Policy core timeout specialist boundary response sent",
            conversation_id=getattr(runtime_input.conversation, "id", None),
            bot_response=bot_response,
        )

    hooks.apply_policy_guard_override(
        final_action="fact",
        final_tool_action="info",
        reason_code=runtime_input.reason_code,
        reason=runtime_input.guard_reason,
    )
    hooks.sync_policy_plan_audit(emit_trace=True)
    decision_trace: dict[str, Any] = {
        "stage": "policy_core_guard",
        "decision": _normalize_optional_text(runtime_input.trace_decision)
        or "timeout_master_info_interrupt",
        "state": getattr(runtime_input.conversation, "state", None),
        "mode": runtime_input.policy_core_mode,
        "reason": runtime_input.policy_core_degrade_reason,
        "missing_slot": runtime_input.collect_slot,
        "pending_question_target": "specialist",
    }
    if runtime_input.active_question_relation:
        decision_trace["active_question_relation"] = runtime_input.active_question_relation
    hooks.record_decision_trace(runtime_input.conversation, decision_trace)
    if runtime_input.saved_message:
        metadata_updates = {
            "policy_core_guard_recovery": _normalize_optional_text(runtime_input.recovery_tag)
            or "timeout_master_info_interrupt",
        }
        if _normalize_optional_text(runtime_input.retry_path):
            metadata_updates["policy_core_timeout_retry_path"] = _normalize_optional_text(
                runtime_input.retry_path
            )
        if runtime_input.active_question_relation:
            metadata_updates["active_question_relation"] = runtime_input.active_question_relation
        hooks.update_message_decision_metadata(runtime_input.saved_message, metadata_updates)
    interrupt_kwargs = dict(runtime_input.interrupt_kwargs or {})
    interrupt_kwargs["booking"] = booking_state
    interrupt_kwargs.setdefault("pending_question_target", "specialist")
    return hooks.handle_booking_interrupt(**interrupt_kwargs)


__all__ = [
    "PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks",
    "PolicyTimeoutBookingSpecialistBoundaryRuntimeInput",
    "handle_policy_timeout_booking_specialist_boundary",
]
