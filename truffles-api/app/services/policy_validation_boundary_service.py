from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal

from app.schemas.webhook import WebhookResponse

PolicyValidationBoundaryMode = Literal[
    "fact_guard",
    "clarify",
    "collect_prompt",
    "pending_question_guidance",
    "service_grounded_booking",
]


@dataclass(frozen=True)
class PolicyValidationBoundaryRuntimeHooks:
    classify_policy_core_degrade_reason: Callable[..., Any]
    sync_semantic_arbiter_meta: Callable[..., None]
    sync_policy_plan_audit: Callable[..., None]
    backfill_policy_degraded_referent_evidence: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]
    apply_policy_guard_override: Callable[..., None]
    record_decision_trace: Callable[..., None]
    record_message_decision_meta: Callable[..., None]
    get_conversation_context: Callable[..., dict[str, Any]]
    get_context_manager: Callable[..., dict[str, Any]]
    get_clarify_attempt_state: Callable[..., tuple[int, str | None]]
    record_context_manager_decision: Callable[..., None]
    handle_clarify_limit_escalation: Callable[..., WebhookResponse]
    register_clarify_attempt: Callable[..., int]
    set_booking_context: Callable[..., dict[str, Any]]
    set_service_hint: Callable[..., dict[str, Any]]
    set_expected_reply_context: Callable[..., dict[str, Any]]
    set_conversation_context: Callable[..., None]
    expected_reply_for_booking_question: Callable[..., str | None]
    booking_prompt_for_expected_reply_type: Callable[..., str | None]
    reset_low_confidence_retry: Callable[..., None]
    combine_sidecar: Callable[..., str]
    maybe_apply_consult_return: Callable[..., str]
    send_and_save: Callable[..., tuple[str, bool]]
    commit: Callable[..., None]


@dataclass(frozen=True)
class PolicyValidationBoundaryRuntimeInput:
    mode: PolicyValidationBoundaryMode
    validation_error: str
    guard_reason: str
    trace_decision: str
    conversation: Any
    saved_message: Any
    now: datetime
    llm_policy_core_meta: dict[str, Any] | None
    msg_fact_guard_clarify: str
    booking_state: dict[str, Any] | None = None
    policy_slot_state_validated: dict[str, str] | None = None
    trace_source: str | None = None
    mark_override_reason_missing: bool = False
    collect_slot: str | None = None
    requested_slot: str | None = None
    pending_question_act: str | None = None
    pending_question_target: str | None = None
    msg_booking_pending_question_time_guidance: str | None = None
    msg_style_reference_need_media: str | None = None
    message_text: str | None = None
    has_media: bool = False
    pending_style_reference_signal: bool = False
    consult_return_pending: bool = False
    consult_return_prompt: str | None = None
    consult_context: dict[str, Any] | None = None
    consult_return_reason: str | None = None
    policy_core_degrade_reason_override: str | None = None
    service_query: str | None = None
    service_query_source: str | None = None
    db: Any = None
    user: Any = None
    allow_handover: bool = False
    escalation_source: str | None = None
    clarify_intent: str | None = None
    clarify_max_attempts: int = 0
    fact_source: str | None = None
    fact_evidence_refs: list[str] | None = None
    send_response: Callable[..., Any] | None = None
    finalize_response: Callable[..., Any] | None = None


def _policy_validation_degrade_reason(validation_error: str) -> str:
    return f"policy_validation:{validation_error}"


def _base_saved_message_updates(
    *,
    runtime_input: PolicyValidationBoundaryRuntimeInput,
    policy_core_mode: str,
    policy_core_degrade_reason: str,
    policy_core_failure: Any,
) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "policy_core_mode": policy_core_mode,
        "policy_core_degrade_reason": policy_core_degrade_reason,
        "policy_core_failure": policy_core_failure,
    }
    if runtime_input.mode in {"collect_prompt", "pending_question_guidance"}:
        updates["llm_policy_core_guard"] = runtime_input.trace_decision
        updates["policy_core_guard_slot_override"] = runtime_input.collect_slot
        if isinstance(runtime_input.requested_slot, str) and runtime_input.requested_slot.strip():
            updates["policy_core_guard_requested_slot"] = runtime_input.requested_slot.strip()
    if runtime_input.mark_override_reason_missing:
        updates["llm_policy_override_reason_missing_detected"] = True
    if runtime_input.validation_error == "semantic_owner_post_hoc_override_blocked":
        updates["policy_semantic_override_blocked"] = True
        updates["policy_semantic_override_block_reason"] = "single_semantic_owner_hard_lock"
    if isinstance(runtime_input.llm_policy_core_meta, dict):
        updates["llm_policy_core"] = runtime_input.llm_policy_core_meta
    return updates


def build_policy_validation_booking_recovery(
    *,
    booking_state: dict[str, Any] | None,
    collect_slot: str | None,
    now: datetime,
    expected_reply_for_booking_question: Callable[..., str | None],
    policy_slot_state_validated: dict[str, str] | None = None,
    service_query: str | None = None,
) -> tuple[dict[str, Any], str | None] | None:
    if not isinstance(collect_slot, str) or not collect_slot.strip():
        return None

    recovered_booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    if isinstance(service_query, str) and service_query.strip() and not recovered_booking_state.get("service"):
        recovered_booking_state["service"] = service_query.strip()
    if not recovered_booking_state.get("active"):
        recovered_booking_state["active"] = True
        recovered_booking_state["started_at"] = now.isoformat()
    for slot_key, value in (policy_slot_state_validated or {}).items():
        if not recovered_booking_state.get(slot_key):
            recovered_booking_state[slot_key] = value
    normalized_collect_slot = collect_slot.strip()
    recovered_booking_state["last_question"] = normalized_collect_slot
    expected_reply_slot = expected_reply_for_booking_question(normalized_collect_slot)
    return recovered_booking_state, expected_reply_slot


def _build_booking_context(
    *,
    runtime_input: PolicyValidationBoundaryRuntimeInput,
    hooks: PolicyValidationBoundaryRuntimeHooks,
    expected_reply_reason: str,
) -> tuple[dict[str, Any], str | None]:
    recovery = build_policy_validation_booking_recovery(
        booking_state=runtime_input.booking_state,
        collect_slot=runtime_input.collect_slot,
        now=runtime_input.now,
        expected_reply_for_booking_question=hooks.expected_reply_for_booking_question,
        policy_slot_state_validated=runtime_input.policy_slot_state_validated,
    )
    if recovery is None:
        booking_state = dict(runtime_input.booking_state) if isinstance(runtime_input.booking_state, dict) else {}
        return booking_state, None
    booking_state, expected_reply_slot = recovery
    context = hooks.get_conversation_context(runtime_input.conversation)
    context = hooks.set_booking_context(context, booking_state)
    if expected_reply_slot:
        context = hooks.set_expected_reply_context(
            conversation=runtime_input.conversation,
            saved_message=runtime_input.saved_message,
            context=context,
            expected_reply_type=expected_reply_slot,
            reason=expected_reply_reason,
            now=runtime_input.now,
        )
    hooks.set_conversation_context(runtime_input.conversation, context)
    return booking_state, expected_reply_slot


def _build_service_grounded_booking_context(
    *,
    runtime_input: PolicyValidationBoundaryRuntimeInput,
    hooks: PolicyValidationBoundaryRuntimeHooks,
) -> tuple[dict[str, Any], str | None]:
    recovery = build_policy_validation_booking_recovery(
        booking_state=runtime_input.booking_state,
        collect_slot=runtime_input.collect_slot,
        now=runtime_input.now,
        expected_reply_for_booking_question=hooks.expected_reply_for_booking_question,
        service_query=runtime_input.service_query,
    )
    if recovery is None:
        booking_state = dict(runtime_input.booking_state) if isinstance(runtime_input.booking_state, dict) else {}
        return booking_state, None
    booking_state, expected_reply_slot = recovery
    context = hooks.get_conversation_context(runtime_input.conversation)
    context = hooks.set_booking_context(context, booking_state)
    if (
        isinstance(runtime_input.service_query, str)
        and runtime_input.service_query.strip()
    ):
        context = hooks.set_service_hint(
            context,
            runtime_input.service_query.strip(),
            runtime_input.now,
        )
    if expected_reply_slot:
        context = hooks.set_expected_reply_context(
            conversation=runtime_input.conversation,
            saved_message=runtime_input.saved_message,
            context=context,
            expected_reply_type=expected_reply_slot,
            reason="policy_core_invalid_schema_service_grounded_booking",
            now=runtime_input.now,
        )
    hooks.set_conversation_context(runtime_input.conversation, context)
    return booking_state, expected_reply_slot


def handle_policy_validation_boundary(
    *,
    runtime_input: PolicyValidationBoundaryRuntimeInput,
    hooks: PolicyValidationBoundaryRuntimeHooks,
) -> WebhookResponse:
    if runtime_input.mode == "fact_guard":
        context = hooks.get_conversation_context(runtime_input.conversation)
        manager = hooks.get_context_manager(context)
        clarify_count, _ = hooks.get_clarify_attempt_state(
            manager,
            runtime_input.clarify_intent,
        )
        if clarify_count >= runtime_input.clarify_max_attempts:
            hooks.record_context_manager_decision(
                runtime_input.conversation,
                runtime_input.saved_message,
                decision="clarify_limit",
                updates={
                    "clarify_attempt": {
                        "intent": runtime_input.clarify_intent,
                        "count": clarify_count,
                    },
                    "clarify_reason": "fact_guard",
                    "clarify_limit": True,
                    "fact_guard_reason": runtime_input.guard_reason,
                },
            )
            return hooks.handle_clarify_limit_escalation(
                db=runtime_input.db,
                conversation=runtime_input.conversation,
                user=runtime_input.user,
                message_text=runtime_input.message_text or "",
                saved_message=runtime_input.saved_message,
                source=runtime_input.escalation_source or "fact_guard",
                allow_handover=runtime_input.allow_handover,
                send_response=runtime_input.send_response,
                finalize_response=runtime_input.finalize_response,
            )
        hooks.register_clarify_attempt(
            conversation=runtime_input.conversation,
            saved_message=runtime_input.saved_message,
            intent=runtime_input.clarify_intent,
            now=runtime_input.now,
            reason="fact_guard",
        )
        hooks.reset_low_confidence_retry(runtime_input.conversation)
        hooks.record_decision_trace(
            runtime_input.conversation,
            {
                "stage": "fact_guard",
                "decision": f"clarify_{runtime_input.guard_reason}",
                "state": getattr(runtime_input.conversation, "state", None),
                "fact_source": runtime_input.fact_source or None,
                "fact_guard_reason": runtime_input.guard_reason,
                "fact_evidence_refs": list(runtime_input.fact_evidence_refs or []),
                "source": runtime_input.trace_source,
            },
        )
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="reply",
            intent="fact_guard",
            source="fact_guard",
            fast_intent=False,
        )
        if runtime_input.saved_message:
            hooks.update_message_decision_metadata(
                runtime_input.saved_message,
                {
                    "clarify_reason": "fact_guard",
                    "fact_guard": True,
                    "fact_guard_reason": runtime_input.guard_reason,
                    "fact_evidence_refs": list(runtime_input.fact_evidence_refs or []),
                },
            )
        bot_response, sent = hooks.send_and_save(runtime_input.msg_fact_guard_clarify)
        result_message = "Fact guard clarify sent" if sent else "Fact guard clarify failed"
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=getattr(runtime_input.conversation, "id", None),
            bot_response=bot_response,
        )

    policy_core_mode = "degraded_fallback"
    policy_core_degrade_reason = (
        runtime_input.policy_core_degrade_reason_override
        if isinstance(runtime_input.policy_core_degrade_reason_override, str)
        and runtime_input.policy_core_degrade_reason_override.strip()
        else _policy_validation_degrade_reason(runtime_input.validation_error)
    )
    policy_core_failure = hooks.classify_policy_core_degrade_reason(policy_core_degrade_reason)

    if isinstance(runtime_input.llm_policy_core_meta, dict):
        runtime_input.llm_policy_core_meta["validated"] = False
        runtime_input.llm_policy_core_meta["validation_error"] = runtime_input.validation_error
        if runtime_input.mark_override_reason_missing:
            runtime_input.llm_policy_core_meta["override_reason_missing_detected"] = True
        hooks.sync_semantic_arbiter_meta()
        hooks.sync_policy_plan_audit()

    hooks.backfill_policy_degraded_referent_evidence()

    if runtime_input.saved_message:
        hooks.update_message_decision_metadata(
            runtime_input.saved_message,
            _base_saved_message_updates(
                runtime_input=runtime_input,
                policy_core_mode=policy_core_mode,
                policy_core_degrade_reason=policy_core_degrade_reason,
                policy_core_failure=policy_core_failure,
            ),
        )

    hooks.apply_policy_guard_override(
        final_action="collect",
        final_tool_action="collect",
        reason_code="contract_validation_failure",
        reason=runtime_input.guard_reason,
    )
    hooks.sync_policy_plan_audit(emit_trace=True)

    trace_payload: dict[str, Any] = {
        "stage": "policy_core_guard",
        "decision": runtime_input.trace_decision,
        "state": getattr(runtime_input.conversation, "state", None),
        "mode": policy_core_mode,
        "reason": policy_core_degrade_reason,
        "validation_error": runtime_input.validation_error,
    }
    if runtime_input.mode in {"collect_prompt", "pending_question_guidance", "service_grounded_booking"}:
        trace_payload["missing_slot"] = runtime_input.collect_slot
        trace_payload["requested_slot"] = runtime_input.requested_slot
    if runtime_input.mode == "service_grounded_booking":
        trace_payload["service_query"] = runtime_input.service_query
        trace_payload["service_query_source"] = runtime_input.service_query_source
    if isinstance(runtime_input.trace_source, str) and runtime_input.trace_source.strip():
        trace_payload["source"] = runtime_input.trace_source.strip().casefold()
    hooks.record_decision_trace(runtime_input.conversation, trace_payload)

    if runtime_input.mode == "clarify":
        hooks.record_message_decision_meta(
            runtime_input.saved_message,
            action="collect",
            intent="policy_core_guard",
            source="llm_policy_core",
            fast_intent=False,
        )
        bot_response, sent = hooks.send_and_save(runtime_input.msg_fact_guard_clarify)
        result_message = (
            f"Policy core {runtime_input.validation_error} clarify sent"
            if sent
            else f"Policy core {runtime_input.validation_error} clarify failed"
        )
    else:
        if runtime_input.mode == "service_grounded_booking":
            _booking_state, expected_reply_slot = _build_service_grounded_booking_context(
                runtime_input=runtime_input,
                hooks=hooks,
            )
            hooks.record_message_decision_meta(
                runtime_input.saved_message,
                action="collect",
                intent="booking",
                source="policy_core_guard",
                fast_intent=False,
            )
            if runtime_input.saved_message:
                hooks.update_message_decision_metadata(
                    runtime_input.saved_message,
                    {
                        "service_query": runtime_input.service_query,
                        "service_query_source": runtime_input.service_query_source,
                        "expected_reply_type": expected_reply_slot,
                        "expected_reply_reason": "policy_core_invalid_schema_service_grounded_booking",
                        "policy_core_guard_recovery": runtime_input.trace_decision,
                    },
                )
            bot_response = hooks.booking_prompt_for_expected_reply_type(expected_reply_slot)
            if not bot_response:
                bot_response = runtime_input.msg_fact_guard_clarify
            bot_response, sent = hooks.send_and_save(bot_response)
            result_message = (
                "Policy core invalid-schema service-grounded booking prompt sent"
                if sent
                else "Policy core invalid-schema service-grounded booking prompt failed"
            )
        else:
            expected_reply_reason = (
                "policy_core_degraded_collect"
                if runtime_input.mode == "collect_prompt"
                else "booking_slot_guidance"
            )
            _booking_state, expected_reply_slot = _build_booking_context(
                runtime_input=runtime_input,
                hooks=hooks,
                expected_reply_reason=expected_reply_reason,
            )
            if runtime_input.mode == "collect_prompt":
                hooks.record_message_decision_meta(
                    runtime_input.saved_message,
                    action="collect",
                    intent="booking",
                    source="policy_core_guard",
                    fast_intent=False,
                )
                bot_response = hooks.booking_prompt_for_expected_reply_type(expected_reply_slot)
                if not bot_response:
                    bot_response = runtime_input.msg_fact_guard_clarify
                hooks.reset_low_confidence_retry(runtime_input.conversation)
                bot_response, sent = hooks.send_and_save(bot_response)
                result_message = (
                    f"Policy core {runtime_input.validation_error} booking prompt sent"
                    if sent
                    else f"Policy core {runtime_input.validation_error} booking prompt failed"
                )
            else:
                hooks.record_decision_trace(
                    runtime_input.conversation,
                    {
                        "stage": "pending_question_interaction",
                        "decision": "booking_slot_guidance",
                        "state": getattr(runtime_input.conversation, "state", None),
                        "source": "policy_core_guard",
                        "pending_question_act": runtime_input.pending_question_act,
                        "pending_question_target": runtime_input.pending_question_target or "time",
                        "requested_slot": runtime_input.collect_slot,
                        "expected_reply_type": expected_reply_slot,
                        "validation_error": runtime_input.validation_error,
                    },
                )
                hooks.record_message_decision_meta(
                    runtime_input.saved_message,
                    action="collect",
                    intent="booking",
                    source="booking_slot_guidance",
                    fast_intent=False,
                )
                if runtime_input.saved_message:
                    hooks.update_message_decision_metadata(
                        runtime_input.saved_message,
                        {
                            "pending_question_act": runtime_input.pending_question_act,
                            "pending_question_target": runtime_input.pending_question_target or "time",
                            "pending_question_interaction": runtime_input.pending_question_act,
                            "pending_question_owner": "booking_slot_guidance",
                            "expected_reply_type": expected_reply_slot,
                            "expected_reply_reason": "booking_slot_guidance",
                            "expected_reply_matched": False,
                            "expected_reply_blocked_by_info": True,
                            "policy_core_guard_recovery": runtime_input.trace_decision,
                        },
                    )
                bot_response = runtime_input.msg_booking_pending_question_time_guidance
                if (
                    runtime_input.pending_style_reference_signal
                    and runtime_input.msg_style_reference_need_media
                    and not runtime_input.has_media
                ):
                    bot_response = hooks.combine_sidecar(
                        runtime_input.msg_style_reference_need_media,
                        bot_response,
                    )
                bot_response = hooks.maybe_apply_consult_return(
                    conversation=runtime_input.conversation,
                    saved_message=runtime_input.saved_message,
                    bot_response=bot_response,
                    consult_return_pending=runtime_input.consult_return_pending,
                    consult_return_prompt=runtime_input.consult_return_prompt,
                    consult_context=runtime_input.consult_context,
                    reason=runtime_input.consult_return_reason or "booking_slot_guidance",
                )
                hooks.reset_low_confidence_retry(runtime_input.conversation)
                bot_response, sent = hooks.send_and_save(bot_response)
                result_message = (
                    f"Policy core {runtime_input.validation_error} pending-slot guidance sent"
                    if sent
                    else f"Policy core {runtime_input.validation_error} pending-slot guidance failed"
                )

    hooks.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=getattr(runtime_input.conversation, "id", None),
        bot_response=bot_response,
    )


__all__ = [
    "build_policy_validation_booking_recovery",
    "PolicyValidationBoundaryRuntimeHooks",
    "PolicyValidationBoundaryRuntimeInput",
    "handle_policy_validation_boundary",
]
