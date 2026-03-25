from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from app.services.owner_resolver import (
    TimeoutOwnerBoundaryInput,
    TimeoutOwnerBoundaryResolution,
    resolve_timeout_owner_boundary,
)


@dataclass(frozen=True)
class TimeoutOwnerBoundaryRuntimeHooks:
    set_booking_context: Callable[..., dict[str, Any]]
    set_expected_reply_context: Callable[..., dict[str, Any]]
    get_booking_context: Callable[..., dict[str, Any]]
    get_expected_reply_type: Callable[..., str | None]
    get_expected_reply_reason: Callable[..., str | None]
    get_context_manager: Callable[..., dict[str, Any]]
    sync_canonical_dialog_state: Callable[..., dict[str, Any]]
    set_context_manager: Callable[..., dict[str, Any]]
    get_canonical_dialog_state: Callable[..., dict[str, Any]]
    sync_session_memory_interaction_state: Callable[..., tuple[dict[str, Any], dict[str, Any]]]
    set_conversation_context: Callable[..., None]
    apply_policy_guard_override: Callable[..., None]
    sync_policy_plan_audit: Callable[..., None]
    record_decision_trace: Callable[..., None]
    record_message_decision_meta: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]
    send_and_save: Callable[..., tuple[str, bool]]


@dataclass(frozen=True)
class TimeoutOwnerBoundaryApplyResult:
    bot_response: str
    result_message: str


@dataclass(frozen=True)
class TimeoutOwnerBoundaryApplyOverrides:
    decision_meta_updates: dict[str, Any] | None = None
    result_message_sent: str | None = None
    result_message_failed: str | None = None


@dataclass(frozen=True)
class TimeoutOwnerBoundaryRuntimeInput:
    resolution_input: TimeoutOwnerBoundaryInput
    conversation: Any
    saved_message: Any
    context: dict[str, Any]
    now: datetime
    message_count: int
    branch_id: Any
    consult_context: dict[str, Any] | None
    policy_core_mode: str | None
    policy_core_degrade_reason: str | None
    boundary_state_source: str
    derive_pending_question_contract: bool = False
    overrides: TimeoutOwnerBoundaryApplyOverrides | None = None


def _build_timeout_owner_boundary_retry_path(source: str) -> str:
    if source == "matched_expected_reply":
        return "booking_owner_boundary_collect"
    if source == "slot_fill_followup":
        return "booking_slot_fill_followup"
    return "booking_resume_collect_boundary"


def _build_timeout_owner_boundary_result_message(
    *,
    source: str,
    sent: bool,
    overrides: TimeoutOwnerBoundaryApplyOverrides | None = None,
) -> str:
    if overrides:
        if sent and overrides.result_message_sent:
            return overrides.result_message_sent
        if not sent and overrides.result_message_failed:
            return overrides.result_message_failed
    if source == "matched_expected_reply":
        return (
            "Policy core timeout owner-boundary collect response sent"
            if sent
            else "Policy core timeout owner-boundary collect response failed"
        )
    if source == "slot_fill_followup":
        return (
            "Policy core timeout booking slot-fill follow-up response sent"
            if sent
            else "Policy core timeout booking slot-fill follow-up response failed"
        )
    return (
        "Policy core timeout resume-boundary collect response sent"
        if sent
        else "Policy core timeout resume-boundary collect response failed"
    )


def _derive_timeout_owner_boundary_pending_question_contract(
    *,
    source: str | None,
    expected_reply_type: str | None,
    booking_state: dict[str, Any] | None,
    filled_slots: Any,
) -> dict[str, str] | None:
    if source != "matched_expected_reply":
        return None
    if expected_reply_type != "time":
        return None
    if not isinstance(booking_state, dict):
        return None
    if booking_state.get("last_question") != "datetime":
        return None
    normalized_filled_slots = {
        raw_slot.strip().casefold()
        for raw_slot in (filled_slots or ())
        if isinstance(raw_slot, str) and raw_slot.strip()
    }
    if "datetime" not in normalized_filled_slots:
        return None
    return {
        "pending_question_act": "slot_constraint",
        "pending_question_target": "time",
        "pending_question_interaction": "slot_constraint",
        "pending_question_owner": "question_contract",
    }


def apply_timeout_owner_boundary_resolution(
    *,
    conversation: Any,
    saved_message: Any,
    context: dict[str, Any],
    resolution: TimeoutOwnerBoundaryResolution,
    now: datetime,
    message_count: int,
    branch_id: Any,
    consult_context: dict[str, Any] | None,
    policy_core_mode: str | None,
    policy_core_degrade_reason: str | None,
    pending_question_contract: dict[str, str] | None,
    boundary_state_source: str,
    overrides: TimeoutOwnerBoundaryApplyOverrides | None = None,
    hooks: TimeoutOwnerBoundaryRuntimeHooks,
) -> TimeoutOwnerBoundaryApplyResult:
    context = hooks.set_booking_context(
        context,
        resolution.booking_state,
    )
    context = hooks.set_expected_reply_context(
        conversation=conversation,
        saved_message=saved_message,
        context=context,
        expected_reply_type=resolution.expected_reply_type,
        reason=resolution.expected_reply_reason,
        now=now,
    )
    context_manager = hooks.sync_canonical_dialog_state(
        hooks.get_context_manager(context),
        booking_state=hooks.get_booking_context(context),
        expected_reply_type=hooks.get_expected_reply_type(context),
        expected_reply_reason=hooks.get_expected_reply_reason(context),
        message_count=message_count,
        branch_id=branch_id,
        consult_context=consult_context,
        interaction_owner=resolution.execution_owner,
    )
    context = hooks.set_context_manager(context, context_manager)
    interaction_state_payload = hooks.get_canonical_dialog_state(context_manager).get(
        "interaction_state"
    )
    context, _session_memory = hooks.sync_session_memory_interaction_state(
        context,
        interaction_state=(
            interaction_state_payload if isinstance(interaction_state_payload, dict) else None
        ),
        now=now,
    )
    hooks.set_conversation_context(conversation, context)
    hooks.apply_policy_guard_override(
        final_action="collect",
        final_tool_action="collect",
        reason_code="timeout_degrade",
        reason=resolution.expected_reply_reason,
    )
    hooks.sync_policy_plan_audit(emit_trace=True)
    hooks.record_decision_trace(
        conversation,
        {
            "stage": "owner_resolver",
            "decision": "timeout_owner_boundary_match",
            "reason_code": resolution.reason_code,
            "execution_owner": resolution.execution_owner,
            "source": resolution.source,
        },
    )
    if resolution.source == "resume_contract":
        hooks.record_decision_trace(
            conversation,
            {
                "stage": "boundary_state",
                "decision": "resume_collect",
                "state": getattr(conversation, "state", None),
                "mode": policy_core_mode,
                "reason": policy_core_degrade_reason,
                "source": boundary_state_source,
                "missing_slot": resolution.missing_slot,
            },
        )
    hooks.record_decision_trace(
        conversation,
        {
            "stage": "policy_core_guard",
            "decision": resolution.trace_decision,
            "state": getattr(conversation, "state", None),
            "mode": policy_core_mode,
            "reason": policy_core_degrade_reason,
            "owner_reason_code": resolution.reason_code,
            "missing_slot": resolution.missing_slot,
            "filled_slots": list(resolution.filled_slots),
        },
    )
    if pending_question_contract:
        hooks.record_decision_trace(
            conversation,
            {
                "stage": "pending_question_interaction",
                "decision": pending_question_contract["pending_question_act"],
                "state": getattr(conversation, "state", None),
                "source": pending_question_contract["pending_question_owner"],
                "pending_question_act": pending_question_contract["pending_question_act"],
                "pending_question_target": pending_question_contract["pending_question_target"],
                "expected_reply_type": resolution.expected_reply_type,
            },
        )
    hooks.record_message_decision_meta(
        saved_message,
        action="booking_prompt",
        intent="booking",
        source="policy_core_guard",
        fast_intent=False,
    )
    if saved_message:
        meta_updates = {
            "expected_reply_type": resolution.expected_reply_type,
            "expected_reply_reason": resolution.expected_reply_reason,
            "policy_core_guard_recovery": resolution.recovery,
            "policy_core_timeout_retry_path": _build_timeout_owner_boundary_retry_path(
                resolution.source
            ),
            "booking_slot_fill_applied": list(resolution.filled_slots),
            "owner_resolution_reason_code": resolution.reason_code,
            "interaction_owner": resolution.execution_owner,
            "timeout_owner_boundary_source": resolution.source,
        }
        if pending_question_contract:
            meta_updates.update(pending_question_contract)
        if overrides and overrides.decision_meta_updates:
            meta_updates.update(overrides.decision_meta_updates)
        hooks.update_message_decision_metadata(saved_message, meta_updates)
    bot_response, sent = hooks.send_and_save(resolution.prompt)
    return TimeoutOwnerBoundaryApplyResult(
        bot_response=bot_response,
        result_message=_build_timeout_owner_boundary_result_message(
            source=resolution.source,
            sent=sent,
            overrides=overrides,
        ),
    )


def resolve_and_apply_timeout_owner_boundary(
    *,
    runtime_input: TimeoutOwnerBoundaryRuntimeInput,
    hooks: TimeoutOwnerBoundaryRuntimeHooks,
) -> TimeoutOwnerBoundaryApplyResult | None:
    resolution = resolve_timeout_owner_boundary(runtime_input.resolution_input)
    if resolution is None:
        return None
    pending_question_contract = None
    if runtime_input.derive_pending_question_contract:
        pending_question_contract = _derive_timeout_owner_boundary_pending_question_contract(
            source=resolution.source,
            expected_reply_type=resolution.expected_reply_type,
            booking_state=resolution.booking_state,
            filled_slots=resolution.filled_slots,
        )
    return apply_timeout_owner_boundary_resolution(
        conversation=runtime_input.conversation,
        saved_message=runtime_input.saved_message,
        context=runtime_input.context,
        resolution=resolution,
        now=runtime_input.now,
        message_count=runtime_input.message_count,
        branch_id=runtime_input.branch_id,
        consult_context=runtime_input.consult_context,
        policy_core_mode=runtime_input.policy_core_mode,
        policy_core_degrade_reason=runtime_input.policy_core_degrade_reason,
        pending_question_contract=pending_question_contract,
        boundary_state_source=runtime_input.boundary_state_source,
        overrides=runtime_input.overrides,
        hooks=hooks,
    )


__all__ = [
    "TimeoutOwnerBoundaryApplyOverrides",
    "TimeoutOwnerBoundaryApplyResult",
    "TimeoutOwnerBoundaryInput",
    "TimeoutOwnerBoundaryRuntimeHooks",
    "TimeoutOwnerBoundaryRuntimeInput",
    "apply_timeout_owner_boundary_resolution",
    "resolve_and_apply_timeout_owner_boundary",
]
