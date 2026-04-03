from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal

from app.schemas.webhook import WebhookResponse

PolicyTimeoutDegradeBoundaryMode = Literal[
    "generic_clarify",
    "booking_retry",
    "pending_slot_question",
]


@dataclass(frozen=True)
class PolicyTimeoutDegradeBoundaryRuntimeHooks:
    get_conversation_context: Callable[..., dict[str, Any]]
    get_context_manager: Callable[..., dict[str, Any]]
    timeout_degrade_retry_status: Callable[..., tuple[int, bool]]
    set_expected_reply_context: Callable[..., dict[str, Any]]
    record_context_manager_decision: Callable[..., None]
    apply_policy_guard_override: Callable[..., None]
    sync_policy_plan_audit: Callable[..., None]
    record_decision_trace: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]
    handle_clarify_limit_escalation: Callable[..., WebhookResponse]
    register_clarify_attempt: Callable[..., int]
    record_message_decision_meta: Callable[..., None]
    send_and_save: Callable[..., tuple[str, bool]]
    commit: Callable[..., None]


@dataclass(frozen=True)
class PolicyTimeoutDegradeBoundaryRuntimeInput:
    mode: PolicyTimeoutDegradeBoundaryMode
    db: Any
    conversation: Any
    user: Any
    saved_message: Any
    message_text: str | None
    allow_handover: bool
    now: datetime
    policy_core_mode: str
    policy_core_degrade_reason: str
    retry_intent: str
    retry_reason: str
    retry_limit: int
    retry_limit_decision: str
    retry_limit_reason: str
    escalation_intent: str
    escalation_fallback_message: str
    retry_path: str | None = None
    retry_count: int | None = None
    limit_missing_slot: str | None = None
    limit_pending_question_act: str | None = None
    limit_pending_question_target: str | None = None
    continue_decision: str | None = None
    continue_missing_slot: str | None = None
    continue_response_text: str | None = None
    continue_result_message_sent: str | None = None
    continue_result_message_failed: str | None = None
    continue_message_action: str | None = None
    continue_message_intent: str | None = None
    continue_message_source: str | None = None
    continue_expected_reply_type: str | None = None
    continue_expected_reply_reason: str | None = None
    continue_pending_question_decision: str | None = None
    continue_pending_question_act: str | None = None
    continue_pending_question_target: str | None = None
    continue_recovery: str | None = None
    continue_guard_reason_code: str | None = None
    continue_guard_reason: str | None = None
    send_response: Any = None
    finalize_response: Any = None


@dataclass(frozen=True)
class PolicyTimeoutDegradeBoundaryResult:
    response: WebhookResponse | None = None
    retry_count: int | None = None


def _retry_meta_updates(
    *,
    retry_count: int,
    retry_limit: int,
    retry_path: str | None,
    exhausted: bool = False,
) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "policy_core_timeout_retry_count": retry_count,
        "policy_core_timeout_retry_limit": retry_limit,
    }
    if exhausted:
        updates["policy_core_timeout_retry_exhausted"] = True
    if isinstance(retry_path, str) and retry_path.strip():
        updates["policy_core_timeout_retry_path"] = retry_path.strip()
    return updates


def handle_policy_timeout_degrade_boundary(
    *,
    runtime_input: PolicyTimeoutDegradeBoundaryRuntimeInput,
    hooks: PolicyTimeoutDegradeBoundaryRuntimeHooks,
) -> PolicyTimeoutDegradeBoundaryResult:
    if runtime_input.mode == "pending_slot_question":
        if runtime_input.retry_count is None:
            raise ValueError("pending_slot_question mode requires retry_count")

        if (
            isinstance(runtime_input.continue_expected_reply_type, str)
            and runtime_input.continue_expected_reply_type.strip()
        ):
            context = hooks.get_conversation_context(runtime_input.conversation)
            hooks.set_expected_reply_context(
                conversation=runtime_input.conversation,
                saved_message=runtime_input.saved_message,
                context=context,
                expected_reply_type=runtime_input.continue_expected_reply_type.strip(),
                reason=(
                    runtime_input.continue_expected_reply_reason.strip()
                    if isinstance(runtime_input.continue_expected_reply_reason, str)
                    and runtime_input.continue_expected_reply_reason.strip()
                    else "booking_slot_guidance"
                ),
                now=runtime_input.now,
            )

        hooks.apply_policy_guard_override(
            final_action="collect",
            final_tool_action="collect",
            reason_code=runtime_input.continue_guard_reason_code or "timeout_degrade",
            reason=runtime_input.continue_guard_reason or "policy_core_timeout_pending_question",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "policy_core_guard",
                "decision": runtime_input.continue_decision or "timeout_pending_slot_question",
                "state": getattr(runtime_input.conversation, "state", None),
                "mode": runtime_input.policy_core_mode,
                "reason": runtime_input.policy_core_degrade_reason,
                "missing_slot": runtime_input.continue_missing_slot,
            },
        )
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "pending_question_interaction",
                "decision": (
                    runtime_input.continue_pending_question_decision or "booking_slot_guidance"
                ),
                "state": getattr(runtime_input.conversation, "state", None),
                "source": "policy_core_guard",
                "recovery": runtime_input.continue_recovery or "timeout_pending_slot_question",
                "pending_question_act": (
                    runtime_input.continue_pending_question_act or "ask_about_requested_slot"
                ),
                "pending_question_target": (
                    runtime_input.continue_pending_question_target or "time"
                ),
                "requested_slot": runtime_input.continue_missing_slot,
                "expected_reply_type": runtime_input.continue_expected_reply_type,
            },
        )
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="collect",
            intent=runtime_input.continue_message_intent or "booking",
            source=runtime_input.continue_message_source or "booking_slot_guidance",
            fast_intent=False,
        )
        if runtime_input.saved_message:
            metadata_updates = _retry_meta_updates(
                retry_count=runtime_input.retry_count,
                retry_limit=runtime_input.retry_limit,
                retry_path=runtime_input.retry_path,
            )
            metadata_updates.update(
                {
                    "pending_question_act": (
                        runtime_input.continue_pending_question_act or "ask_about_requested_slot"
                    ),
                    "pending_question_target": (
                        runtime_input.continue_pending_question_target or "time"
                    ),
                    "pending_question_interaction": (
                        runtime_input.continue_pending_question_act or "ask_about_requested_slot"
                    ),
                    "pending_question_owner": (
                        runtime_input.continue_pending_question_decision
                        or "booking_slot_guidance"
                    ),
                    "expected_reply_type": runtime_input.continue_expected_reply_type,
                    "expected_reply_reason": (
                        runtime_input.continue_expected_reply_reason
                        or "booking_slot_guidance"
                    ),
                    "expected_reply_matched": False,
                    "expected_reply_blocked_by_info": True,
                    "policy_core_guard_recovery": (
                        runtime_input.continue_recovery or "timeout_pending_slot_question"
                    ),
                }
            )
            hooks.update_message_decision_metadata(
                runtime_input.saved_message,
                metadata_updates,
            )
        bot_response, sent = hooks.send_and_save(runtime_input.continue_response_text or "")
        hooks.commit()
        result_message = (
            runtime_input.continue_result_message_sent
            if sent and runtime_input.continue_result_message_sent
            else runtime_input.continue_result_message_failed
            if not sent and runtime_input.continue_result_message_failed
            else "Policy core timeout pending-slot-question response sent"
            if sent
            else "Policy core timeout pending-slot-question response failed"
        )
        return PolicyTimeoutDegradeBoundaryResult(
            response=WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=getattr(runtime_input.conversation, "id", None),
                bot_response=bot_response,
            ),
            retry_count=runtime_input.retry_count,
        )

    context = hooks.get_conversation_context(runtime_input.conversation)
    context_manager = hooks.get_context_manager(context)
    retry_count, retry_exhausted = hooks.timeout_degrade_retry_status(
        context_manager,
        intent=runtime_input.retry_intent,
    )

    if retry_exhausted:
        hooks.record_context_manager_decision(
            runtime_input.conversation,
            runtime_input.saved_message,
            decision="clarify_limit",
            updates={
                "clarify_attempt": {
                    "intent": runtime_input.retry_intent,
                    "count": retry_count,
                },
                "clarify_reason": runtime_input.retry_reason,
                "clarify_limit": True,
            },
        )
        hooks.apply_policy_guard_override(
            final_action="handoff",
            final_tool_action="handoff",
            reason_code="timeout_degrade",
            reason=runtime_input.retry_limit_reason,
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        trace_payload: dict[str, Any] = {
            "stage": "policy_core_guard",
            "decision": runtime_input.retry_limit_decision,
            "state": getattr(runtime_input.conversation, "state", None),
            "mode": runtime_input.policy_core_mode,
            "reason": runtime_input.policy_core_degrade_reason,
            "retry_count": retry_count,
            "retry_limit": runtime_input.retry_limit,
        }
        if isinstance(runtime_input.limit_missing_slot, str) and runtime_input.limit_missing_slot.strip():
            trace_payload["missing_slot"] = runtime_input.limit_missing_slot.strip()
        if (
            isinstance(runtime_input.limit_pending_question_act, str)
            and runtime_input.limit_pending_question_act.strip()
        ):
            trace_payload["pending_question_act"] = runtime_input.limit_pending_question_act.strip()
        if (
            isinstance(runtime_input.limit_pending_question_target, str)
            and runtime_input.limit_pending_question_target.strip()
        ):
            trace_payload["pending_question_target"] = runtime_input.limit_pending_question_target.strip()
        hooks.record_decision_trace(runtime_input.conversation, trace_payload)
        if runtime_input.saved_message:
            hooks.update_message_decision_metadata(
                runtime_input.saved_message,
                _retry_meta_updates(
                    retry_count=retry_count,
                    retry_limit=runtime_input.retry_limit,
                    retry_path=runtime_input.retry_path,
                    exhausted=True,
                ),
            )
        return PolicyTimeoutDegradeBoundaryResult(
            response=hooks.handle_clarify_limit_escalation(
                db=runtime_input.db,
                conversation=runtime_input.conversation,
                user=runtime_input.user,
                message_text=runtime_input.message_text or runtime_input.escalation_fallback_message,
                saved_message=runtime_input.saved_message,
                source="policy_core_guard",
                allow_handover=runtime_input.allow_handover,
                escalation_intent=runtime_input.escalation_intent,
                send_response=runtime_input.send_response,
                finalize_response=runtime_input.finalize_response,
            )
        )

    retry_count = hooks.register_clarify_attempt(
        conversation=runtime_input.conversation,
        saved_message=runtime_input.saved_message,
        intent=runtime_input.retry_intent,
        now=runtime_input.now,
        reason=runtime_input.retry_reason,
    )

    if runtime_input.mode == "generic_clarify":
        hooks.apply_policy_guard_override(
            final_action="collect",
            final_tool_action="collect",
            reason_code="timeout_degrade",
            reason="policy_core_timeout_degrade_clarify",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "policy_core_guard",
                "decision": "timeout_clarify",
                "state": getattr(runtime_input.conversation, "state", None),
                "mode": runtime_input.policy_core_mode,
                "reason": runtime_input.policy_core_degrade_reason,
                "retry_count": retry_count,
                "retry_limit": runtime_input.retry_limit,
            },
        )
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="collect",
            intent=runtime_input.continue_message_intent or "policy_core_guard",
            source=runtime_input.continue_message_source or "llm_policy_core",
            fast_intent=False,
        )
        if runtime_input.saved_message:
            hooks.update_message_decision_metadata(
                runtime_input.saved_message,
                _retry_meta_updates(
                    retry_count=retry_count,
                    retry_limit=runtime_input.retry_limit,
                    retry_path=runtime_input.retry_path,
                ),
            )
        bot_response, sent = hooks.send_and_save(runtime_input.continue_response_text or "")
        hooks.commit()
        result_message = (
            runtime_input.continue_result_message_sent
            if sent and runtime_input.continue_result_message_sent
            else runtime_input.continue_result_message_failed
            if not sent and runtime_input.continue_result_message_failed
            else "Policy core timeout degrade clarify sent"
            if sent
            else "Policy core timeout degrade clarify failed"
        )
        return PolicyTimeoutDegradeBoundaryResult(
            response=WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=getattr(runtime_input.conversation, "id", None),
                bot_response=bot_response,
            ),
            retry_count=retry_count,
        )

    if runtime_input.saved_message:
        hooks.update_message_decision_metadata(
            runtime_input.saved_message,
            _retry_meta_updates(
                retry_count=retry_count,
                retry_limit=runtime_input.retry_limit,
                retry_path=runtime_input.retry_path,
            ),
        )
    if isinstance(runtime_input.continue_decision, str) and runtime_input.continue_decision.strip():
        trace_payload = {
            "stage": "policy_core_guard",
            "decision": runtime_input.continue_decision.strip(),
            "state": getattr(runtime_input.conversation, "state", None),
            "mode": runtime_input.policy_core_mode,
            "reason": runtime_input.policy_core_degrade_reason,
            "retry_count": retry_count,
            "retry_limit": runtime_input.retry_limit,
        }
        if (
            isinstance(runtime_input.continue_missing_slot, str)
            and runtime_input.continue_missing_slot.strip()
        ):
            trace_payload["missing_slot"] = runtime_input.continue_missing_slot.strip()
        hooks.record_decision_trace(runtime_input.conversation, trace_payload)
    return PolicyTimeoutDegradeBoundaryResult(retry_count=retry_count)


__all__ = [
    "PolicyTimeoutDegradeBoundaryResult",
    "PolicyTimeoutDegradeBoundaryRuntimeHooks",
    "PolicyTimeoutDegradeBoundaryRuntimeInput",
    "handle_policy_timeout_degrade_boundary",
]
