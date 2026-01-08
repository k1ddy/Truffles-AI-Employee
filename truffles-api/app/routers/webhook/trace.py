"""Decision trace/meta helpers for webhook processing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models import Conversation, Message

DECISION_TRACE_KEY = "decision_trace"


def _update_message_decision_metadata(message: Message, updates: dict[str, Any]) -> None:
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    decision_meta.update(updates)
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
    _update_message_decision_metadata(
        message,
        {
            "action": action,
            "intent": intent,
            "source": source,
            "fast_intent": fast_intent,
            "llm_primary_used": False,
            "llm_used": False,
            "llm_timeout": False,
            "llm_cache_hit": False,
        },
    )


def _record_decision_trace(conversation: Conversation, trace: dict[str, Any]) -> None:
    from . import _legacy as legacy

    context = legacy._get_conversation_context(conversation)
    payload = dict(trace)
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    existing = context.get(DECISION_TRACE_KEY)
    if isinstance(existing, list):
        trace_list = [item for item in existing if isinstance(item, dict)]
    elif isinstance(existing, dict):
        trace_list = [existing]
    else:
        trace_list = []
    trace_list.append(payload)
    if len(trace_list) > 12:
        trace_list = trace_list[-12:]
    context[DECISION_TRACE_KEY] = trace_list
    legacy._set_conversation_context(conversation, context)


def _attach_llm_cache_flag(trace: dict[str, Any], timing_context: dict | None) -> dict[str, Any]:
    if timing_context and "llm_cache_hit" in timing_context:
        trace["llm_cache_hit"] = timing_context["llm_cache_hit"]
    return trace


__all__ = [
    "DECISION_TRACE_KEY",
    "_attach_llm_cache_flag",
    "_record_decision_trace",
    "_record_message_decision_meta",
    "_update_message_decision_metadata",
]
