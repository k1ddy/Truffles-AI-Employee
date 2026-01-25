"""Decision trace/meta helpers for webhook processing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.logging_config import get_logger
from app.models import Conversation, Message
from app.schemas.webhook import TraceContract

logger = get_logger("webhook")

DECISION_TRACE_KEY = "decision_trace"
DECISION_TRACE_MAX = 40
DECISION_TRACE_CRITICAL_STAGES = {
    "action_gate",
    "booking",
    "booking_confirm",
    "booking_commit",
    "booking_interrupt",
    "consult_flow",
    "consult_return",
    "contract_error",
    "escalation",
    "fast_intent",
    "knowledge_safe_mode",
    "multi_truth",
    "out_of_domain",
    "outbox_payload_guard",
    "pending_resume",
    "pending_guard",
    "pending_sla",
    "pending_wait",
    "policy_gate",
    "question_contract",
    "re_entry",
    "service_matcher",
    "service_semantic_matcher",
    "smalltalk",
    "session_memory",
    "state_transition",
    "truth_gate",
}
DECISION_TRACE_PRIORITY_STAGES = {
    "booking_interrupt",
    "multi_truth",
}
DECISION_TRACE_PINNED_STAGES = {
    "booking_commit",
}

DECISION_STAGE_ORDER_SNAPSHOT = [
    "preflight",
    "outbox_payload_guard",
    "outbox",
    "contract",
    "decision_graph",
    "knowledge_safe_mode",
    "session_memory",
    "re_entry",
    "class_carryover",
    "service_carryover",
    "consult_context",
    "question_contract",
    "branch_selection",
    "shield",
    "policy_gate",
    "routing",
    "rejection",
    "pending_sla",
    "pending_resume",
    "pending_guard",
    "pending_status",
    "pending_wait",
    "media",
    "debounce",
    "handover_confirmation",
    "intent_decomposition",
    "class_router",
    "intent",
    "carryover_guard",
    "booking_gate",
    "complaint_guard",
    "out_of_domain",
    "consult_flow",
    "intent_queue",
    "booking",
    "consult",
    "clarify_guard",
    "booking_interrupt",
    "service_matcher",
    "truth_gate",
    "multi_truth",
    "service_semantic_matcher",
    "time_only_guard",
    "info_class",
    "fast_intent",
    "llm_guard",
    "ai_response",
    "rewrite",
    "budget_gate",
    "llm_degradation",
    "context_manager",
    "consult_return",
    "escalation",
    "state_transition",
    "action_gate",
]


def _is_critical_trace(payload: dict[str, Any]) -> bool:
    stage = payload.get("stage")
    if stage in DECISION_TRACE_CRITICAL_STAGES:
        return True
    if stage == "question_contract" and payload.get("decision") in {"matched", "missed"}:
        return True
    if payload.get("contract_error") or payload.get("trace_contract_error"):
        return True
    if stage == "contract" and payload.get("contract_ok") is False:
        return True
    return False


def _retain_decision_trace(trace_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(trace_list) <= DECISION_TRACE_MAX:
        return trace_list

    pinned_indices: list[int] = []
    if DECISION_TRACE_PINNED_STAGES:
        for stage in DECISION_TRACE_PINNED_STAGES:
            for idx in range(len(trace_list) - 1, -1, -1):
                if trace_list[idx].get("stage") == stage:
                    pinned_indices.append(idx)
                    break
    pinned_set = set(pinned_indices)
    if len(pinned_indices) >= DECISION_TRACE_MAX:
        logger.warning(
            "Decision trace pinned retention exceeded limit",
            extra={
                "context": {
                    "pinned_count": len(pinned_indices),
                    "trace_max": DECISION_TRACE_MAX,
                }
            },
        )
        keep_indices = set(pinned_indices[-DECISION_TRACE_MAX:])
        return [item for idx, item in enumerate(trace_list) if idx in keep_indices]

    priority_indices: list[int] = []
    critical_indices: list[int] = []
    normal_indices: list[int] = []
    for idx, item in enumerate(trace_list):
        if idx in pinned_set:
            continue
        stage = item.get("stage")
        if stage in DECISION_TRACE_PRIORITY_STAGES:
            priority_indices.append(idx)
        elif _is_critical_trace(item):
            critical_indices.append(idx)
        else:
            normal_indices.append(idx)

    remaining = max(DECISION_TRACE_MAX - len(pinned_indices), 0)
    if len(priority_indices) > remaining:
        dropped = len(priority_indices) - remaining
        keep_priority = priority_indices[-remaining:] if remaining else []
        logger.warning(
            "Decision trace priority retention exceeded limit",
            extra={
                "context": {
                    "priority_count": len(priority_indices),
                    "dropped_priority": dropped,
                    "pinned_count": len(pinned_indices),
                    "trace_max": DECISION_TRACE_MAX,
                }
            },
        )
        keep_indices = set(pinned_indices + keep_priority)
    else:
        remaining = max(remaining - len(priority_indices), 0)
        if len(critical_indices) > remaining:
            dropped = len(critical_indices) - remaining
            keep_critical = critical_indices[-remaining:] if remaining else []
            logger.warning(
                "Decision trace critical retention exceeded limit",
                extra={
                    "context": {
                        "priority_count": len(priority_indices),
                        "critical_count": len(critical_indices),
                        "pinned_count": len(pinned_indices),
                        "dropped_critical": dropped,
                        "trace_max": DECISION_TRACE_MAX,
                    }
                },
            )
        else:
            keep_critical = critical_indices
        remaining = max(remaining - len(keep_critical), 0)
        keep_normals = normal_indices[-remaining:] if remaining else []
        keep_indices = set(pinned_indices + priority_indices + keep_critical + keep_normals)

    return [item for idx, item in enumerate(trace_list) if idx in keep_indices]


def _update_message_decision_metadata(message: Message, updates: dict[str, Any]) -> None:
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    decision_meta.update(updates)
    metadata["decision_meta"] = decision_meta
    message.message_metadata = metadata


def _merge_message_timing(message: Message | None, timing_updates: dict[str, Any] | None) -> None:
    if not message or not isinstance(timing_updates, dict):
        return
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    existing = decision_meta.get("timing")
    merged: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    for key, value in timing_updates.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    decision_meta["timing"] = merged
    metadata["decision_meta"] = decision_meta
    message.message_metadata = metadata


def _record_message_decision_meta(
    message: Message | None,
    *,
    action: str | None,
    intent: str | None,
    source: str,
    fast_intent: bool,
) -> None:
    if not message:
        return
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    defaults = {
        "controller_attempted": False,
        "controller_fallback_reason": None,
        "controller_low_confidence": False,
    }
    updates = {
        "action": action,
        "intent": intent,
        "source": source,
        "fast_intent": fast_intent,
        "llm_primary_used": False,
        "llm_used": False,
        "llm_timeout": False,
        "llm_cache_hit": False,
        "llm_degradation_reason": None,
    }
    for key, value in defaults.items():
        if key not in decision_meta:
            updates[key] = value
    _update_message_decision_metadata(
        message,
        updates,
    )


def _record_decision_trace(conversation: Conversation, trace: dict[str, Any]) -> None:
    from . import _legacy as legacy

    context = legacy._get_conversation_context(conversation)
    payload = dict(trace)
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    try:
        TraceContract(**payload)
    except ValidationError as exc:
        payload["trace_contract_error"] = str(exc)
        logger.warning(
            "Decision trace contract validation failed",
            extra={
                "context": {
                    "error": str(exc),
                    "stage": payload.get("stage"),
                    "decision": payload.get("decision"),
                }
            },
        )
    existing = context.get(DECISION_TRACE_KEY)
    if isinstance(existing, list):
        trace_list = [item for item in existing if isinstance(item, dict)]
    elif isinstance(existing, dict):
        trace_list = [existing]
    else:
        trace_list = []
    trace_list.append(payload)
    trace_list = _retain_decision_trace(trace_list)
    context[DECISION_TRACE_KEY] = trace_list
    legacy._set_conversation_context(conversation, context)


def _attach_llm_cache_flag(trace: dict[str, Any], timing_context: dict | None) -> dict[str, Any]:
    if timing_context and "llm_cache_hit" in timing_context:
        trace["llm_cache_hit"] = timing_context["llm_cache_hit"]
    return trace


__all__ = [
    "DECISION_TRACE_CRITICAL_STAGES",
    "DECISION_TRACE_KEY",
    "DECISION_TRACE_MAX",
    "DECISION_TRACE_PINNED_STAGES",
    "DECISION_STAGE_ORDER_SNAPSHOT",
    "_attach_llm_cache_flag",
    "_record_decision_trace",
    "_record_message_decision_meta",
    "_merge_message_timing",
    "_update_message_decision_metadata",
]
