"""Session memory helpers for tracking question/answer context."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from app.models import Conversation, Message
from app.routers.webhook.trace import _record_decision_trace, _update_message_decision_metadata
from app.schemas.webhook import MemoryContract
from app.services.ai_service import normalize_for_matching


def _get_session_memory(context: dict) -> dict:
    from . import _legacy as legacy

    payload = context.get(legacy.SESSION_MEMORY_KEY) if isinstance(context, dict) else None
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _normalize_session_memory(memory: dict | None) -> tuple[dict, str | None]:
    if not isinstance(memory, dict):
        return {}, "invalid_type"
    normalized = dict(memory)
    errors: list[str] = []

    def mark_error(reason: str) -> None:
        if reason not in errors:
            errors.append(reason)

    def normalize_string(key: str) -> None:
        value = normalized.get(key)
        if value is None:
            return
        if not isinstance(value, str):
            normalized.pop(key, None)
            mark_error(f"{key}_type")
            return
        value = value.strip()
        if value:
            normalized[key] = value
        else:
            normalized.pop(key, None)

    def normalize_int(key: str) -> None:
        value = normalized.get(key)
        if value is None:
            return
        try:
            normalized[key] = int(value)
        except (TypeError, ValueError):
            normalized.pop(key, None)
            mark_error(f"{key}_type")

    def normalize_list(key: str, *, limit: int | None = None) -> None:
        value = normalized.get(key)
        if value is None:
            return
        if not isinstance(value, list):
            normalized.pop(key, None)
            mark_error(f"{key}_type")
            return
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            cleaned_item = item.strip()
            if cleaned_item:
                cleaned.append(cleaned_item)
        if limit:
            cleaned = cleaned[-limit:]
        normalized[key] = cleaned

    def normalize_dict(key: str, *, values_as_str: bool) -> None:
        value = normalized.get(key)
        if value is None:
            return
        if not isinstance(value, dict):
            normalized.pop(key, None)
            mark_error(f"{key}_type")
            return
        cleaned: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                continue
            cleaned_key = raw_key.strip()
            if not cleaned_key:
                continue
            if values_as_str:
                if not isinstance(raw_value, str):
                    continue
                cleaned_value = raw_value.strip()
                if not cleaned_value:
                    continue
                cleaned[cleaned_key] = cleaned_value
            else:
                cleaned[cleaned_key] = raw_value
        normalized[key] = cleaned

    normalize_string("mode")
    normalize_string("summary")
    normalize_string("last_updated")
    normalize_string("last_updated_at")
    normalize_string("active_goal")
    normalize_string("last_question_type")
    normalize_int("ttl")
    normalize_int("ttl_hours")
    normalize_list("goal_stack", limit=3)
    normalize_list("unanswered_questions")
    normalize_dict("slots", values_as_str=False)
    normalize_dict("pending_slots", values_as_str=True)

    try:
        MemoryContract(**normalized)
    except ValidationError as exc:
        return normalized, str(exc)
    if errors:
        return normalized, ",".join(errors)
    return normalized, None


def _set_session_memory(context: dict, memory: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if memory:
        context[legacy.SESSION_MEMORY_KEY] = memory
    else:
        context.pop(legacy.SESSION_MEMORY_KEY, None)
    return context


def _parse_session_memory_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_session_memory_expired(memory: dict, now: datetime) -> bool:
    from . import _legacy as legacy

    ttl_hours = memory.get("ttl_hours", legacy.SESSION_MEMORY_TTL_HOURS)
    try:
        ttl_hours = int(ttl_hours)
    except (TypeError, ValueError):
        ttl_hours = legacy.SESSION_MEMORY_TTL_HOURS
    last_updated_at = _parse_session_memory_time(memory.get("last_updated_at"))
    if not last_updated_at:
        return True
    return (now - last_updated_at) > timedelta(hours=max(1, ttl_hours))


def _should_reset_session_memory(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    from . import _legacy as legacy

    return any(phrase in normalized for phrase in legacy.SESSION_MEMORY_RESET_PHRASES)


def _is_session_reset_only_message(message_text: str | None) -> bool:
    if not message_text:
        return False
    cleaned = re.sub(r"\[[^\]]+\]", " ", message_text)
    normalized = normalize_for_matching(cleaned)
    if not normalized:
        return False
    from . import _legacy as legacy

    return normalized in legacy.SESSION_MEMORY_RESET_PHRASES


def _session_memory_snapshot(memory: dict) -> dict:
    pending_slots = memory.get("pending_slots")
    if isinstance(pending_slots, dict):
        pending_keys = sorted(
            key for key in pending_slots.keys() if isinstance(key, str) and key.strip()
        )
    else:
        pending_keys = []
    goal_stack = memory.get("goal_stack")
    if isinstance(goal_stack, list):
        cleaned_goals = [item for item in goal_stack if isinstance(item, str) and item.strip()]
    else:
        cleaned_goals = []
    unanswered = memory.get("unanswered_questions")
    if isinstance(unanswered, list):
        unanswered_count = len([item for item in unanswered if isinstance(item, str) and item.strip()])
    else:
        unanswered_count = 0
    return {
        "last_question_type": memory.get("last_question_type"),
        "active_goal": memory.get("active_goal"),
        "goal_stack_depth": len(cleaned_goals),
        "goal_stack_top": cleaned_goals[-1] if cleaned_goals else None,
        "pending_slots": pending_keys,
        "unanswered_questions_count": unanswered_count,
    }


def _record_session_memory_update(
    conversation: Conversation,
    saved_message: Message | None,
    *,
    memory: dict,
    reason: str,
) -> None:
    snapshot = _session_memory_snapshot(memory)
    trace = {"stage": "session_memory", "decision": "update", "reason": reason}
    trace.update(snapshot)
    _record_decision_trace(conversation, trace)
    if saved_message:
        _update_message_decision_metadata(saved_message, {"session_memory_update": snapshot})


def _reset_session_memory(
    *,
    context: dict,
    context_manager: dict,
    reason: str,
    now: datetime,
) -> tuple[dict, dict, dict]:
    from . import _legacy as legacy

    manager = dict(context_manager)
    manager.pop(legacy.CLASS_CARRYOVER_KEY, None)
    manager.pop(legacy.SERVICE_CARRYOVER_KEY, None)
    manager.pop(legacy.CONSULT_CONTEXT_KEY, None)
    context = legacy._set_context_manager(context, manager)
    context = legacy._set_expected_reply_type(context, None)
    context = legacy._set_intent_queue(context, [])
    context = legacy._set_booking_context(context, {"active": False})
    context = legacy._clear_service_hint(context)
    context = _set_session_memory(context, None)
    memory_payload = {"last_updated_at": now.isoformat(), "ttl_hours": legacy.SESSION_MEMORY_TTL_HOURS}
    return context, manager, {"reason": reason, **_session_memory_snapshot(memory_payload)}


def _update_session_memory_on_question(
    context: dict,
    *,
    expected_reply_type: str,
    active_goal: str | None,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    memory = _get_session_memory(context)
    unanswered = memory.get("unanswered_questions")
    unanswered_list = (
        [item for item in unanswered if isinstance(item, str) and item.strip()]
        if isinstance(unanswered, list)
        else []
    )
    if expected_reply_type not in unanswered_list:
        unanswered_list.append(expected_reply_type)
    memory["last_question_type"] = expected_reply_type
    if active_goal:
        memory["active_goal"] = active_goal
        goal_stack = memory.get("goal_stack")
        if not isinstance(goal_stack, list):
            goal_stack = []
        if not goal_stack or goal_stack[-1] != active_goal:
            goal_stack.append(active_goal)
        memory["goal_stack"] = goal_stack[-3:]
    memory["unanswered_questions"] = unanswered_list
    memory["last_updated_at"] = now.isoformat()
    memory["ttl_hours"] = legacy.SESSION_MEMORY_TTL_HOURS
    context = _set_session_memory(context, memory)
    return context, memory


def _update_session_memory_on_answer(
    context: dict,
    *,
    expected_reply_type: str,
    value: str,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    memory = _get_session_memory(context)
    pending_slots = memory.get("pending_slots")
    pending_map = dict(pending_slots) if isinstance(pending_slots, dict) else {}
    unanswered = memory.get("unanswered_questions")
    unanswered_list = (
        [item for item in unanswered if isinstance(item, str) and item.strip()]
        if isinstance(unanswered, list)
        else []
    )
    if expected_reply_type in unanswered_list:
        unanswered_list = [item for item in unanswered_list if item != expected_reply_type]
    slot_map = {
        legacy.EXPECTED_REPLY_SERVICE: "service",
        legacy.EXPECTED_REPLY_TIME: "datetime",
        legacy.EXPECTED_REPLY_NAME: "name",
    }
    slot_key = slot_map.get(expected_reply_type)
    if slot_key and isinstance(value, str) and value.strip():
        pending_map[slot_key] = value.strip()
    memory["pending_slots"] = pending_map
    memory["unanswered_questions"] = unanswered_list
    memory["last_updated_at"] = now.isoformat()
    memory["ttl_hours"] = legacy.SESSION_MEMORY_TTL_HOURS
    context = _set_session_memory(context, memory)
    return context, memory


def _clear_session_memory_expected_reply(
    context: dict,
    *,
    expected_reply_type: str | None,
    now: datetime,
) -> tuple[dict, dict, bool]:
    from . import _legacy as legacy

    memory = _get_session_memory(context)
    if not memory:
        return context, {}, False

    memory = dict(memory)
    expected_reply_tokens = {
        legacy.EXPECTED_REPLY_SERVICE,
        legacy.EXPECTED_REPLY_TIME,
        legacy.EXPECTED_REPLY_NAME,
    }
    expected_clean = (
        expected_reply_type.strip()
        if isinstance(expected_reply_type, str) and expected_reply_type.strip()
        else None
    )
    target_types: set[str] = set()
    if expected_clean in expected_reply_tokens:
        target_types.add(expected_clean)

    last_question_type = memory.get("last_question_type")
    if (
        isinstance(last_question_type, str)
        and last_question_type.strip()
        and last_question_type.strip() in expected_reply_tokens
    ):
        target_types.add(last_question_type.strip())

    if not target_types:
        return context, memory, False

    changed = False

    if (
        isinstance(memory.get("last_question_type"), str)
        and memory.get("last_question_type").strip() in target_types
    ):
        memory.pop("last_question_type", None)
        changed = True

    unanswered = memory.get("unanswered_questions")
    if isinstance(unanswered, list):
        filtered_unanswered = [
            item
            for item in unanswered
            if isinstance(item, str) and item.strip() and item.strip() not in target_types
        ]
        if filtered_unanswered != unanswered:
            memory["unanswered_questions"] = filtered_unanswered
            changed = True

    slot_map = {
        legacy.EXPECTED_REPLY_SERVICE: "service",
        legacy.EXPECTED_REPLY_TIME: "datetime",
        legacy.EXPECTED_REPLY_NAME: "name",
    }
    pending_slots = memory.get("pending_slots")
    if isinstance(pending_slots, dict):
        pending_map = dict(pending_slots)
        for expected_type in target_types:
            slot_key = slot_map.get(expected_type)
            if slot_key and slot_key in pending_map:
                pending_map.pop(slot_key, None)
                changed = True
        memory["pending_slots"] = pending_map

    if not changed:
        return context, memory, False

    memory["last_updated_at"] = now.isoformat()
    memory["ttl_hours"] = legacy.SESSION_MEMORY_TTL_HOURS
    context = _set_session_memory(context, memory)
    return context, memory, True


def _update_session_memory_goal(
    context: dict,
    *,
    active_goal: str,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    memory = _get_session_memory(context)
    memory["active_goal"] = active_goal
    goal_stack = memory.get("goal_stack")
    if not isinstance(goal_stack, list):
        goal_stack = []
    if not goal_stack or goal_stack[-1] != active_goal:
        goal_stack.append(active_goal)
    memory["goal_stack"] = goal_stack[-3:]
    memory["last_updated_at"] = now.isoformat()
    memory["ttl_hours"] = legacy.SESSION_MEMORY_TTL_HOURS
    context = _set_session_memory(context, memory)
    return context, memory
