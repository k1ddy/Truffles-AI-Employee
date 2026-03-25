from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal

from app.schemas.webhook import WebhookResponse

PolicyTimeoutRecoveryMode = Literal[
    "style_reference_need_media",
    "fact_fallback",
    "info_fallback",
]


@dataclass(frozen=True)
class PolicyTimeoutRecoveryBoundaryRuntimeHooks:
    get_conversation_context: Callable[..., dict[str, Any]]
    set_style_reference_pending: Callable[..., dict[str, Any]]
    set_conversation_context: Callable[..., None]
    set_expected_reply_context: Callable[..., dict[str, Any]]
    apply_policy_guard_override: Callable[..., None]
    sync_policy_plan_audit: Callable[..., None]
    record_decision_trace: Callable[..., None]
    record_message_decision_meta: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]
    send_and_save: Callable[..., tuple[str, bool]]
    commit: Callable[..., None]


@dataclass(frozen=True)
class PolicyTimeoutRecoveryBoundaryRuntimeInput:
    mode: PolicyTimeoutRecoveryMode
    conversation: Any
    saved_message: Any
    now: datetime
    policy_core_mode: str
    policy_core_degrade_reason: str
    response_text: str
    style_reference_pending_payload: dict[str, Any] | None = None
    fallback_intent: str | None = None
    expected_reply_type: str | None = None
    expected_reply_reason: str | None = None
    info_sections: list[str] | None = None
    resolver_id: Any = None
    resolver_confidence: Any = None


def handle_policy_timeout_recovery_boundary(
    *,
    runtime_input: PolicyTimeoutRecoveryBoundaryRuntimeInput,
    hooks: PolicyTimeoutRecoveryBoundaryRuntimeHooks,
) -> WebhookResponse:
    if runtime_input.mode == "style_reference_need_media":
        context = hooks.get_conversation_context(runtime_input.conversation)
        context = hooks.set_style_reference_pending(
            context,
            runtime_input.style_reference_pending_payload or {},
        )
        hooks.set_conversation_context(runtime_input.conversation, context)
        hooks.apply_policy_guard_override(
            final_action="style_reference",
            final_tool_action="style_reference",
            reason_code="timeout_degrade",
            reason="policy_core_timeout_style_reference_need_media",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        pending_value = None
        pending_payload = runtime_input.style_reference_pending_payload
        if isinstance(pending_payload, dict):
            raw_reason = pending_payload.get("reason")
            if isinstance(raw_reason, str) and raw_reason.strip():
                pending_value = raw_reason.strip()
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "policy_core_guard",
                "decision": "timeout_style_reference_need_media",
                "state": getattr(runtime_input.conversation, "state", None),
                "mode": runtime_input.policy_core_mode,
                "reason": runtime_input.policy_core_degrade_reason,
                "pending": pending_value,
            },
        )
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "style_reference",
                "decision": "need_media",
                "state": getattr(runtime_input.conversation, "state", None),
                "pending": pending_value,
                "source": "policy_core_guard",
            },
        )
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="style_reference",
            intent="style_reference",
            source="policy_core_guard",
            fast_intent=False,
        )
        if runtime_input.saved_message:
            hooks.update_message_decision_metadata(
                runtime_input.saved_message,
                {
                    "policy_core_guard_recovery": "style_reference_need_media",
                },
            )
        bot_response, sent = hooks.send_and_save(runtime_input.response_text)
        hooks.commit()
        result_message = (
            "Policy core timeout degrade style reference prompt sent"
            if sent
            else "Policy core timeout degrade style reference prompt failed"
        )
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=getattr(runtime_input.conversation, "id", None),
            bot_response=bot_response,
        )

    if runtime_input.mode == "fact_fallback":
        context = hooks.get_conversation_context(runtime_input.conversation)
        if (
            isinstance(runtime_input.expected_reply_type, str)
            and runtime_input.expected_reply_type.strip()
        ):
            context = hooks.set_expected_reply_context(
                conversation=runtime_input.conversation,
                saved_message=runtime_input.saved_message,
                context=context,
                expected_reply_type=runtime_input.expected_reply_type.strip(),
                reason=(
                    runtime_input.expected_reply_reason.strip()
                    if isinstance(runtime_input.expected_reply_reason, str)
                    and runtime_input.expected_reply_reason.strip()
                    else "policy_core_timeout_fact_fallback"
                ),
                now=runtime_input.now,
            )
            hooks.set_conversation_context(runtime_input.conversation, context)
        hooks.apply_policy_guard_override(
            final_action="fact",
            final_tool_action="pack.fact_fallback",
            reason_code="timeout_degrade",
            reason="policy_core_timeout_fact_fallback",
        )
        hooks.sync_policy_plan_audit(emit_trace=True)
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "policy_core_guard",
                "decision": "timeout_fact_fallback",
                "state": getattr(runtime_input.conversation, "state", None),
                "mode": runtime_input.policy_core_mode,
                "reason": runtime_input.policy_core_degrade_reason,
                "resolver_id": runtime_input.resolver_id,
                "resolver_confidence": runtime_input.resolver_confidence,
                "intent": runtime_input.fallback_intent,
                "info_sections": (
                    runtime_input.info_sections
                    if isinstance(runtime_input.info_sections, list)
                    else []
                ),
            },
        )
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="reply",
            intent=runtime_input.fallback_intent or "policy_core_guard",
            source="llm_policy_core",
            fast_intent=False,
        )
        if runtime_input.saved_message:
            meta_updates: dict[str, Any] = {
                "policy_core_guard_info_query": True,
                "policy_core_guard_recovery": "pack_fact_fallback",
                "resolver_confidence": runtime_input.resolver_confidence,
            }
            if isinstance(runtime_input.info_sections, list):
                meta_updates["info_sections"] = runtime_input.info_sections
            if (
                isinstance(runtime_input.expected_reply_type, str)
                and runtime_input.expected_reply_type.strip()
            ):
                meta_updates["expected_reply_type"] = runtime_input.expected_reply_type.strip()
                if (
                    isinstance(runtime_input.expected_reply_reason, str)
                    and runtime_input.expected_reply_reason.strip()
                ):
                    meta_updates["expected_reply_reason"] = runtime_input.expected_reply_reason.strip()
            hooks.update_message_decision_metadata(runtime_input.saved_message, meta_updates)
        bot_response, sent = hooks.send_and_save(runtime_input.response_text)
        hooks.commit()
        result_message = (
            "Policy core timeout degrade factual fallback sent"
            if sent
            else "Policy core timeout degrade factual fallback failed"
        )
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=getattr(runtime_input.conversation, "id", None),
            bot_response=bot_response,
        )

    context = hooks.get_conversation_context(runtime_input.conversation)
    if (
        isinstance(runtime_input.expected_reply_type, str)
        and runtime_input.expected_reply_type.strip()
        and isinstance(runtime_input.expected_reply_reason, str)
        and runtime_input.expected_reply_reason.strip()
    ):
        context = hooks.set_expected_reply_context(
            conversation=runtime_input.conversation,
            saved_message=runtime_input.saved_message,
            context=context,
            expected_reply_type=runtime_input.expected_reply_type.strip(),
            reason=runtime_input.expected_reply_reason.strip(),
            now=runtime_input.now,
        )
        hooks.set_conversation_context(runtime_input.conversation, context)
    hooks.apply_policy_guard_override(
        final_action="fact",
        final_tool_action="catalog.service_query",
        reason_code="timeout_degrade",
        reason="policy_core_timeout_info_fallback",
    )
    hooks.sync_policy_plan_audit(emit_trace=True)
    hooks.record_decision_trace(
        runtime_input.conversation,
        {
            "stage": "policy_core_guard",
            "decision": "timeout_info_fallback",
            "state": getattr(runtime_input.conversation, "state", None),
            "mode": runtime_input.policy_core_mode,
            "reason": runtime_input.policy_core_degrade_reason,
            "tool_recovery": "services_overview",
            "info_sections": ["services_overview"],
        },
    )
    hooks.record_message_decision_meta(
        runtime_input.saved_message,
        action="reply",
        intent="catalog.service_query",
        source="llm_policy_core",
        fast_intent=False,
    )
    if runtime_input.saved_message:
        meta_updates: dict[str, Any] = {
            "policy_core_guard_info_query": True,
            "policy_core_guard_recovery": "services_overview",
            "info_sections": ["services_overview"],
        }
        if (
            isinstance(runtime_input.expected_reply_type, str)
            and runtime_input.expected_reply_type.strip()
            and isinstance(runtime_input.expected_reply_reason, str)
            and runtime_input.expected_reply_reason.strip()
        ):
            meta_updates["expected_reply_type"] = runtime_input.expected_reply_type.strip()
            meta_updates["expected_reply_reason"] = runtime_input.expected_reply_reason.strip()
        hooks.update_message_decision_metadata(runtime_input.saved_message, meta_updates)
    bot_response, sent = hooks.send_and_save(runtime_input.response_text)
    hooks.commit()
    result_message = (
        "Policy core timeout degrade info fallback sent"
        if sent
        else "Policy core timeout degrade info fallback failed"
    )
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=getattr(runtime_input.conversation, "id", None),
        bot_response=bot_response,
    )


__all__ = [
    "PolicyTimeoutRecoveryBoundaryRuntimeHooks",
    "PolicyTimeoutRecoveryBoundaryRuntimeInput",
    "handle_policy_timeout_recovery_boundary",
]
