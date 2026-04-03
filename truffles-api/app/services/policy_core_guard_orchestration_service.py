from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from app.schemas.webhook import WebhookResponse

PolicyCoreGuardOrchestrationMode = Literal[
    "handoff_policy_blocked_safe_reply",
    "guard_handoff_safe",
    "pending_hold",
    "timeout_booking_completion",
    "degraded_collect_reschedule_handoff",
    "degraded_collect",
]


@dataclass(frozen=True)
class PolicyCoreGuardOrchestrationRuntimeHooks:
    apply_policy_guard_override: Callable[..., None]
    sync_policy_plan_audit: Callable[..., None]
    record_decision_trace: Callable[..., None]
    record_message_decision_meta: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]
    send_and_save: Callable[..., tuple[str | None, bool]]
    reuse_active_handover: Callable[..., tuple[Any, bool, bool]]
    create_pending_escalation_with_notification: Callable[..., Any]
    record_escalation_metric: Callable[..., None]
    timeout_booking_completion_override: Callable[..., tuple[str, str]]
    commit: Callable[..., None]


@dataclass(frozen=True)
class PolicyCoreGuardOrchestrationRuntimeInput:
    mode: PolicyCoreGuardOrchestrationMode
    conversation: Any
    saved_message: Any
    policy_core_mode: str | None
    policy_core_degrade_reason: str | None
    user: Any = None
    message_text: str | None = None
    allow_handover: bool = False
    reason_code: str | None = None
    capability_reason: str | None = None
    handover_message: str | None = None
    collect_slot: str | None = None
    original_collect_slot: str | None = None
    info_query_override: bool = False
    collect_prompt: str | None = None
    collect_action: str | None = None
    collect_intent: str | None = None
    completion_action: str | None = None
    completion_filled_slots: tuple[str, ...] = ()
    completion_response: WebhookResponse | None = None
    response_text: str | None = None
    error_response_text: str | None = None


def _conversation_id(conversation: Any) -> Any:
    return getattr(conversation, "id", None)


def _require_user(runtime_input: PolicyCoreGuardOrchestrationRuntimeInput) -> Any:
    if runtime_input.user is None:
        raise ValueError(f"{runtime_input.mode} requires user")
    return runtime_input.user


def _require_handover_message(runtime_input: PolicyCoreGuardOrchestrationRuntimeInput) -> str:
    if isinstance(runtime_input.handover_message, str) and runtime_input.handover_message.strip():
        return runtime_input.handover_message
    raise ValueError(f"{runtime_input.mode} requires handover_message")


def _build_handoff_trace(
    *,
    runtime_input: PolicyCoreGuardOrchestrationRuntimeInput,
    decision: str,
) -> dict[str, Any]:
    trace_payload: dict[str, Any] = {
        "stage": "policy_core_guard",
        "decision": decision,
        "state": getattr(runtime_input.conversation, "state", None),
        "mode": runtime_input.policy_core_mode,
        "reason": runtime_input.policy_core_degrade_reason,
    }
    if runtime_input.collect_slot is not None:
        trace_payload["missing_slot"] = runtime_input.collect_slot
    if runtime_input.original_collect_slot is not None:
        trace_payload["missing_slot_original"] = runtime_input.original_collect_slot
    if runtime_input.info_query_override:
        trace_payload["info_query_override"] = True
    return trace_payload


def _run_handoff_mode(
    *,
    runtime_input: PolicyCoreGuardOrchestrationRuntimeInput,
    hooks: PolicyCoreGuardOrchestrationRuntimeHooks,
    source: str,
    intent: str,
    trigger_value: str,
    trace_decision: str,
    guard_reason: str,
    result_message_reused: str,
    result_message_created: str,
    result_message_failed: str,
    result_message_skipped: str,
    message_meta_intent: str,
    message_meta_source: str,
) -> WebhookResponse:
    user = _require_user(runtime_input)
    handover_message = _require_handover_message(runtime_input)
    _handover, reused, telegram_sent = hooks.reuse_active_handover(
        conversation=runtime_input.conversation,
        user=user,
        message=handover_message,
        source=source,
        intent=intent,
    )
    if reused:
        bot_response = runtime_input.response_text or ""
        result_message = (
            f"{result_message_reused}, telegram={'sent' if telegram_sent else 'failed'}"
        )
    elif getattr(runtime_input.conversation, "state", None) == "bot_active" and runtime_input.allow_handover:
        hooks.record_escalation_metric("intent")
        escalation_notification_result = hooks.create_pending_escalation_with_notification(
            conversation=runtime_input.conversation,
            user=user,
            user_message=handover_message,
            trigger_type="intent",
            trigger_value=trigger_value,
        )
        if getattr(escalation_notification_result, "ok", False):
            telegram_sent = bool(getattr(escalation_notification_result, "telegram_sent", False))
            bot_response = runtime_input.response_text or ""
            result_message = (
                f"{result_message_created}, telegram={'sent' if telegram_sent else 'failed'}"
            )
        else:
            bot_response = runtime_input.error_response_text or runtime_input.response_text or ""
            result_message = result_message_failed
    else:
        bot_response = runtime_input.response_text or ""
        result_message = result_message_skipped

    hooks.apply_policy_guard_override(
        final_action="handoff",
        final_tool_action="handoff",
        reason_code=runtime_input.reason_code,
        reason=guard_reason,
    )
    hooks.sync_policy_plan_audit(emit_trace=True)
    hooks.record_decision_trace(
        runtime_input.conversation,
        _build_handoff_trace(runtime_input=runtime_input, decision=trace_decision),
    )
    hooks.record_message_decision_meta(
        runtime_input.saved_message,
        action="handoff",
        intent=message_meta_intent,
        source=message_meta_source,
        fast_intent=False,
    )
    bot_response, sent = hooks.send_and_save(bot_response)
    if not sent:
        result_message = f"{result_message}; response_send=failed"
    hooks.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=_conversation_id(runtime_input.conversation),
        bot_response=bot_response,
    )


def handle_policy_core_guard_orchestration(
    *,
    runtime_input: PolicyCoreGuardOrchestrationRuntimeInput,
    hooks: PolicyCoreGuardOrchestrationRuntimeHooks,
) -> WebhookResponse:
    if runtime_input.mode == "handoff_policy_blocked_safe_reply":
        hooks.apply_policy_guard_override(
            final_action="collect",
            final_tool_action="collect",
            reason_code="safety_policy_block",
            reason="handoff_policy_blocked",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "policy_core_guard",
                "decision": "handoff_blocked_by_policy",
                "state": getattr(runtime_input.conversation, "state", None),
                "mode": runtime_input.policy_core_mode,
                "reason": runtime_input.policy_core_degrade_reason,
                "capability_reason": runtime_input.capability_reason,
            },
        )
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="collect",
            intent="policy_core_guard",
            source="llm_policy_core",
            fast_intent=False,
        )
        bot_response, sent = hooks.send_and_save(runtime_input.response_text or "")
        hooks.commit()
        return WebhookResponse(
            success=True,
            message=(
                "Policy core handoff blocked by capability policy"
                if sent
                else "Policy core handoff blocked by capability policy; response_send=failed"
            ),
            conversation_id=_conversation_id(runtime_input.conversation),
            bot_response=bot_response,
        )

    if runtime_input.mode == "guard_handoff_safe":
        return _run_handoff_mode(
            runtime_input=runtime_input,
            hooks=hooks,
            source="policy_core_degraded",
            intent="policy_core_guard",
            trigger_value="policy_core_guard",
            trace_decision="handoff_safe",
            guard_reason="policy_core_guard_handoff_safe",
            result_message_reused="Policy core degraded handoff reused",
            result_message_created="Policy core degraded handoff",
            result_message_failed="Policy core degraded handoff failed",
            result_message_skipped="Policy core degraded handoff skipped (already pending)",
            message_meta_intent="policy_core_guard",
            message_meta_source="llm_policy_core",
        )

    if runtime_input.mode == "pending_hold":
        if getattr(runtime_input.conversation, "state", None) == "pending":
            bot_response = runtime_input.response_text or ""
            bot_response, sent = hooks.send_and_save(bot_response)
            result_message = (
                "Policy core degraded pending hold response sent"
                if sent
                else "Policy core degraded pending hold response failed"
            )
        else:
            bot_response = None
            result_message = "Policy core degraded manager-active hold"
        hooks.apply_policy_guard_override(
            final_action="handoff",
            final_tool_action="handoff",
            reason_code=runtime_input.reason_code,
            reason="policy_core_guard_pending_hold",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "policy_core_guard",
                "decision": "pending_hold",
                "state": getattr(runtime_input.conversation, "state", None),
                "mode": runtime_input.policy_core_mode,
                "reason": runtime_input.policy_core_degrade_reason,
            },
        )
        if runtime_input.saved_message:
            hooks.update_message_decision_metadata(
                runtime_input.saved_message,
                {
                    "pending_action": "policy_core_degraded_hold",
                    "pending_guard": "policy_core_degraded",
                },
            )
        hooks.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=_conversation_id(runtime_input.conversation),
            bot_response=bot_response,
        )

    if runtime_input.mode == "timeout_booking_completion":
        if runtime_input.completion_response is None:
            raise ValueError("timeout_booking_completion mode requires completion_response")
        if runtime_input.saved_message:
            hooks.update_message_decision_metadata(
                runtime_input.saved_message,
                {
                    "policy_core_guard_recovery": "timeout_completed_booking_continuity",
                    "policy_core_timeout_retry_path": "booking_completion_continuity",
                    "booking_slot_fill_applied": list(runtime_input.completion_filled_slots),
                },
            )
        override_action, override_tool_action = hooks.timeout_booking_completion_override(
            runtime_input.completion_action
        )
        hooks.apply_policy_guard_override(
            final_action=override_action,
            final_tool_action=override_tool_action,
            reason_code="timeout_degrade",
            reason="policy_core_timeout_booking_completion",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        hooks.commit()
        return runtime_input.completion_response

    if runtime_input.mode == "degraded_collect_reschedule_handoff":
        return _run_handoff_mode(
            runtime_input=runtime_input,
            hooks=hooks,
            source="policy_core_degraded_collect",
            intent="reschedule",
            trigger_value="reschedule",
            trace_decision="degraded_collect_reschedule_handoff",
            guard_reason="policy_core_degraded_reschedule_handoff",
            result_message_reused="Policy core degraded collect reschedule handoff reused",
            result_message_created="Policy core degraded collect reschedule handoff",
            result_message_failed="Policy core degraded collect reschedule handoff failed",
            result_message_skipped=(
                "Policy core degraded collect reschedule handoff skipped (already pending)"
            ),
            message_meta_intent="reschedule",
            message_meta_source="booking_verification",
        )

    if runtime_input.mode == "degraded_collect":
        hooks.apply_policy_guard_override(
            final_action="collect",
            final_tool_action="collect",
            reason_code=runtime_input.reason_code,
            reason="policy_core_degraded_collect_guard",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        hooks.record_decision_trace(
            runtime_input.conversation,
            _build_handoff_trace(runtime_input=runtime_input, decision="degraded_collect"),
        )
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="collect",
            intent=runtime_input.collect_intent or "policy_core_guard",
            source="llm_policy_core",
            fast_intent=False,
        )
        bot_response, sent = hooks.send_and_save(runtime_input.collect_prompt or "")
        hooks.commit()
        return WebhookResponse(
            success=True,
            message=(
                "Policy core degraded collect response sent"
                if sent
                else "Policy core degraded collect response failed"
            ),
            conversation_id=_conversation_id(runtime_input.conversation),
            bot_response=bot_response,
        )

    raise ValueError(f"unsupported_policy_core_guard_orchestration_mode:{runtime_input.mode}")


__all__ = [
    "PolicyCoreGuardOrchestrationRuntimeHooks",
    "PolicyCoreGuardOrchestrationRuntimeInput",
    "handle_policy_core_guard_orchestration",
]
