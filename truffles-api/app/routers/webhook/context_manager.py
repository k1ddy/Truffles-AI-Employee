"""Conversation context manager helpers (carryover, confirmations, summaries)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.models import Conversation, Message
from app.routers.webhook.booking import _get_booking_context
from app.routers.webhook.runtime_primitives import SERVICE_CARRYOVER_TTL_MESSAGES
from app.routers.webhook.session_memory import (
    _record_session_memory_update,
    _update_session_memory_on_question,
)
from app.routers.webhook.trace import (
    DECISION_TRACE_KEY,
    _record_decision_trace,
    _retain_decision_trace,
    _update_message_decision_metadata,
)

CANONICAL_DIALOG_STATE_KEY = "canonical_dialog_state"
CANONICAL_DIALOG_STATE_OWNER = "context_manager.dialog_state.v1"
CANONICAL_DIALOG_STATE_VERSION = "v1"
_CANONICAL_REFERENT_KEYS = {"service", "master", "branch", "booking_ref"}
_EXPECTED_REPLY_SLOT_BY_TYPE = {
    "service_choice": "service",
    "time": "datetime",
    "name": "name",
    "phone": "phone",
}


def _canonical_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def _canonical_int(value: Any, *, default: int = 0) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default
    return max(normalized, 0)


def _canonical_state_base() -> dict[str, Any]:
    return {
        "owner_id": CANONICAL_DIALOG_STATE_OWNER,
        "version": CANONICAL_DIALOG_STATE_VERSION,
        "current_referents": {},
    }


def _get_canonical_dialog_state(manager: dict) -> dict[str, Any]:
    payload = manager.get(CANONICAL_DIALOG_STATE_KEY) if isinstance(manager, dict) else None
    state = dict(payload) if isinstance(payload, dict) else _canonical_state_base()
    owner_id = _canonical_text(state.get("owner_id")) or CANONICAL_DIALOG_STATE_OWNER
    version = _canonical_text(state.get("version")) or CANONICAL_DIALOG_STATE_VERSION
    referents = state.get("current_referents")
    cleaned_referents: dict[str, dict[str, Any]] = {}
    if isinstance(referents, dict):
        for referent_key, raw_payload in referents.items():
            if referent_key not in _CANONICAL_REFERENT_KEYS or not isinstance(raw_payload, dict):
                continue
            value = _canonical_text(raw_payload.get("value"))
            if not value:
                continue
            item: dict[str, Any] = {"value": value, "message_count": _canonical_int(raw_payload.get("message_count"))}
            source = _canonical_text(raw_payload.get("source"))
            if source:
                item["source"] = source
            score = raw_payload.get("score")
            if isinstance(score, (int, float)):
                item["score"] = float(score)
            ttl = raw_payload.get("ttl")
            if isinstance(ttl, int) and ttl > 0:
                item["ttl"] = ttl
            cleaned_referents[referent_key] = item
    state["owner_id"] = owner_id
    state["version"] = version
    state["current_referents"] = cleaned_referents

    pending_question_contract = state.get("pending_question_contract")
    if isinstance(pending_question_contract, dict):
        cleaned_pending: dict[str, Any] = {}
        slot = _canonical_text(pending_question_contract.get("slot"))
        if slot in {"service", "datetime", "name", "phone"}:
            cleaned_pending["slot"] = slot
        expected_reply_type = _canonical_text(pending_question_contract.get("expected_reply_type"))
        if expected_reply_type:
            cleaned_pending["expected_reply_type"] = expected_reply_type
        reason = _canonical_text(pending_question_contract.get("reason"))
        if reason:
            cleaned_pending["reason"] = reason
        value = _canonical_text(pending_question_contract.get("value"))
        if value:
            cleaned_pending["value"] = value
        cleaned_pending["message_count"] = _canonical_int(pending_question_contract.get("message_count"))
        if cleaned_pending.get("slot") or cleaned_pending.get("expected_reply_type"):
            state["pending_question_contract"] = cleaned_pending
        else:
            state.pop("pending_question_contract", None)
    else:
        state.pop("pending_question_contract", None)

    consult_state = state.get("consult_state")
    if isinstance(consult_state, dict):
        cleaned_consult: dict[str, Any] = {"message_count": _canonical_int(consult_state.get("message_count"))}
        topic = _canonical_text(consult_state.get("topic"))
        if topic:
            cleaned_consult["topic"] = topic
        question = _canonical_text(consult_state.get("question"))
        if question:
            cleaned_consult["question"] = question
        raw_questions = consult_state.get("questions")
        if isinstance(raw_questions, list):
            questions = [_canonical_text(item) for item in raw_questions]
            questions = [item for item in questions if item]
            if questions:
                cleaned_consult["questions"] = questions
        ttl = consult_state.get("ttl")
        if isinstance(ttl, int) and ttl > 0:
            cleaned_consult["ttl"] = ttl
        if len(cleaned_consult) > 1:
            state["consult_state"] = cleaned_consult
        else:
            state.pop("consult_state", None)
    else:
        state.pop("consult_state", None)
    return state


def _set_canonical_dialog_state(manager: dict, state: dict[str, Any] | None) -> dict:
    manager = dict(manager)
    if state:
        manager[CANONICAL_DIALOG_STATE_KEY] = state
    else:
        manager.pop(CANONICAL_DIALOG_STATE_KEY, None)
    return manager


def _referent_ttl(referent_key: str) -> int | None:
    if referent_key in {"service", "master"}:
        return SERVICE_CARRYOVER_TTL_MESSAGES
    return None


def _set_canonical_referent(
    manager: dict,
    *,
    referent_key: str,
    value: str | None,
    message_count: int,
    source: str | None = None,
    score: float | None = None,
    ttl: int | None = None,
) -> dict:
    if referent_key not in _CANONICAL_REFERENT_KEYS:
        return dict(manager)
    manager = dict(manager)
    state = _get_canonical_dialog_state(manager)
    referents = dict(state.get("current_referents") or {})
    normalized_value = _canonical_text(value)
    if not normalized_value:
        referents.pop(referent_key, None)
    else:
        payload: dict[str, Any] = {
            "value": normalized_value,
            "message_count": _canonical_int(message_count),
        }
        normalized_source = _canonical_text(source)
        if normalized_source:
            payload["source"] = normalized_source
        if isinstance(score, (int, float)):
            payload["score"] = float(score)
        referent_ttl = ttl if isinstance(ttl, int) and ttl > 0 else _referent_ttl(referent_key)
        if isinstance(referent_ttl, int) and referent_ttl > 0:
            payload["ttl"] = referent_ttl
        referents[referent_key] = payload
    state["current_referents"] = referents
    return _set_canonical_dialog_state(manager, state)


def _project_canonical_referent(
    manager: dict,
    *,
    referent_key: str,
    message_count: int,
) -> dict[str, Any] | None:
    state = _get_canonical_dialog_state(manager)
    referents = state.get("current_referents")
    payload = referents.get(referent_key) if isinstance(referents, dict) else None
    if not isinstance(payload, dict):
        return None
    value = _canonical_text(payload.get("value"))
    if not value:
        return None
    ttl = payload.get("ttl")
    ttl_value = ttl if isinstance(ttl, int) and ttl > 0 else None
    age = max(_canonical_int(message_count) - _canonical_int(payload.get("message_count")), 0)
    if ttl_value is not None and age > ttl_value:
        return None
    return {
        "value": value,
        "source": _canonical_text(payload.get("source")),
        "score": payload.get("score") if isinstance(payload.get("score"), (int, float)) else None,
        "age": max(age, 1),
        "ttl": ttl_value,
        "remaining": max((ttl_value or 0) - age + 1, 0) if ttl_value is not None else None,
        "projection_source": CANONICAL_DIALOG_STATE_KEY,
        "canonical_state_owner": state.get("owner_id") or CANONICAL_DIALOG_STATE_OWNER,
    }


def _prune_canonical_referent(
    manager: dict,
    *,
    referent_key: str,
    message_count: int,
) -> tuple[dict, dict[str, Any] | None]:
    manager = dict(manager)
    state = _get_canonical_dialog_state(manager)
    referents = dict(state.get("current_referents") or {})
    payload = referents.get(referent_key)
    if not isinstance(payload, dict):
        return manager, None
    ttl = payload.get("ttl")
    if not isinstance(ttl, int) or ttl <= 0:
        return manager, None
    age = max(_canonical_int(message_count) - _canonical_int(payload.get("message_count")), 0)
    if age <= ttl:
        return manager, None
    value = _canonical_text(payload.get("value"))
    referents.pop(referent_key, None)
    state["current_referents"] = referents
    manager = _set_canonical_dialog_state(manager, state)
    return manager, {
        "reason": "expired",
        "age": age,
        "ttl": ttl,
        "value": value,
        "projection_source": CANONICAL_DIALOG_STATE_KEY,
        "canonical_state_owner": state.get("owner_id") or CANONICAL_DIALOG_STATE_OWNER,
    }


def _set_canonical_pending_question_contract(
    manager: dict,
    *,
    expected_reply_type: str | None,
    reason: str | None,
    message_count: int,
    value: str | None = None,
) -> dict:
    manager = dict(manager)
    state = _get_canonical_dialog_state(manager)
    normalized_expected_reply_type = _canonical_text(expected_reply_type)
    if not normalized_expected_reply_type:
        state.pop("pending_question_contract", None)
        return _set_canonical_dialog_state(manager, state)
    payload: dict[str, Any] = {
        "expected_reply_type": normalized_expected_reply_type,
        "message_count": _canonical_int(message_count),
    }
    slot = _EXPECTED_REPLY_SLOT_BY_TYPE.get(normalized_expected_reply_type)
    if slot:
        payload["slot"] = slot
    normalized_reason = _canonical_text(reason)
    if normalized_reason:
        payload["reason"] = normalized_reason
    normalized_value = _canonical_text(value)
    if normalized_value:
        payload["value"] = normalized_value
    state["pending_question_contract"] = payload
    return _set_canonical_dialog_state(manager, state)


def _set_canonical_consult_state(
    manager: dict,
    *,
    topic: str | None,
    question: str | None,
    questions: list[str] | None,
    message_count: int,
) -> dict:
    from . import _legacy as legacy

    manager = dict(manager)
    state = _get_canonical_dialog_state(manager)
    normalized_topic = _canonical_text(topic)
    normalized_question = _canonical_text(question)
    cleaned_questions = [
        item for item in (_canonical_text(entry) for entry in (questions or [])) if item
    ]
    if not normalized_topic and not normalized_question and not cleaned_questions:
        state.pop("consult_state", None)
        return _set_canonical_dialog_state(manager, state)
    state["consult_state"] = {
        "topic": normalized_topic,
        "question": normalized_question,
        "questions": cleaned_questions,
        "message_count": _canonical_int(message_count),
        "ttl": legacy.CONSULT_CONTEXT_TTL_MESSAGES,
    }
    return _set_canonical_dialog_state(manager, state)


def _project_canonical_consult_state(
    manager: dict,
    *,
    message_count: int,
) -> dict[str, Any] | None:
    state = _get_canonical_dialog_state(manager)
    consult_state = state.get("consult_state")
    if not isinstance(consult_state, dict):
        return None
    ttl = consult_state.get("ttl")
    ttl_value = ttl if isinstance(ttl, int) and ttl > 0 else None
    age = max(_canonical_int(message_count) - _canonical_int(consult_state.get("message_count")), 0)
    if ttl_value is not None and age > ttl_value:
        return None
    result: dict[str, Any] = {
        "age": max(age, 1),
        "ttl": ttl_value,
        "remaining": max((ttl_value or 0) - age + 1, 0) if ttl_value is not None else None,
        "projection_source": CANONICAL_DIALOG_STATE_KEY,
        "canonical_state_owner": state.get("owner_id") or CANONICAL_DIALOG_STATE_OWNER,
    }
    topic = _canonical_text(consult_state.get("topic"))
    if topic:
        result["topic"] = topic
    question = _canonical_text(consult_state.get("question"))
    if question:
        result["question"] = question
    questions = consult_state.get("questions")
    if isinstance(questions, list):
        cleaned_questions = [
            item for item in (_canonical_text(entry) for entry in questions) if item
        ]
        if cleaned_questions:
            result["questions"] = cleaned_questions
    if "topic" not in result and "question" not in result and "questions" not in result:
        return None
    return result


def _prune_canonical_consult_state(
    manager: dict,
    *,
    message_count: int,
) -> tuple[dict, dict[str, Any] | None]:
    manager = dict(manager)
    state = _get_canonical_dialog_state(manager)
    consult_state = state.get("consult_state")
    if not isinstance(consult_state, dict):
        return manager, None
    ttl = consult_state.get("ttl")
    if not isinstance(ttl, int) or ttl <= 0:
        return manager, None
    age = max(_canonical_int(message_count) - _canonical_int(consult_state.get("message_count")), 0)
    if age <= ttl:
        return manager, None
    state.pop("consult_state", None)
    manager = _set_canonical_dialog_state(manager, state)
    return manager, {
        "reason": "expired",
        "age": age,
        "ttl": ttl,
        "projection_source": CANONICAL_DIALOG_STATE_KEY,
        "canonical_state_owner": state.get("owner_id") or CANONICAL_DIALOG_STATE_OWNER,
    }


def _sync_canonical_dialog_state(
    manager: dict,
    *,
    booking_state: dict[str, Any] | None,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    message_count: int,
    branch_id: Any = None,
    consult_context: dict[str, Any] | None = None,
) -> dict:
    from . import _legacy as legacy

    manager = dict(manager)
    if isinstance(booking_state, dict):
        service_value = _canonical_text(booking_state.get("service"))
        if service_value:
            manager = _set_canonical_referent(
                manager,
                referent_key="service",
                value=service_value,
                source="booking_state",
                score=1.0,
                message_count=message_count,
            )
        specialist_value = _canonical_text(
            booking_state.get("specialist_name") or booking_state.get("specialist_id")
        )
        if specialist_value:
            manager = _set_canonical_referent(
                manager,
                referent_key="master",
                value=specialist_value,
                source="booking_state",
                score=1.0,
                message_count=message_count,
            )
        for ref_key in ("appointment_id", "booking_id", "external_booking_id"):
            reference_value = _canonical_text(booking_state.get(ref_key))
            if reference_value:
                manager = _set_canonical_referent(
                    manager,
                    referent_key="booking_ref",
                    value=reference_value,
                    source="booking_state",
                    score=1.0,
                    message_count=message_count,
                    ttl=None,
                )
                break
    if branch_id is not None:
        manager = _set_canonical_referent(
            manager,
            referent_key="branch",
            value=str(branch_id),
            source="conversation_branch",
            score=1.0,
            message_count=message_count,
            ttl=None,
        )
    state = _get_canonical_dialog_state(manager)
    referents = state.get("current_referents") if isinstance(state, dict) else {}
    service_payload = referents.get("service") if isinstance(referents, dict) else None
    if not isinstance(service_payload, dict):
        legacy_payload = manager.get(legacy.SERVICE_CARRYOVER_KEY) if isinstance(manager, dict) else None
        if isinstance(legacy_payload, dict):
            service_query = _canonical_text(legacy_payload.get("service_query"))
            if service_query:
                manager = _set_canonical_referent(
                    manager,
                    referent_key="service",
                    value=service_query,
                    source=_canonical_text(legacy_payload.get("service_query_source")) or "legacy_service_carryover",
                    score=legacy_payload.get("service_query_score") if isinstance(legacy_payload.get("service_query_score"), (int, float)) else None,
                    message_count=_canonical_int(legacy_payload.get("message_count"), default=message_count),
                    ttl=legacy_payload.get("ttl") if isinstance(legacy_payload.get("ttl"), int) else None,
                )
    if isinstance(consult_context, dict):
        manager = _set_canonical_consult_state(
            manager,
            topic=consult_context.get("topic"),
            question=consult_context.get("question"),
            questions=consult_context.get("questions") if isinstance(consult_context.get("questions"), list) else None,
            message_count=message_count,
        )
    elif isinstance(manager.get(legacy.CONSULT_CONTEXT_KEY), dict):
        legacy_consult = manager.get(legacy.CONSULT_CONTEXT_KEY)
        manager = _set_canonical_consult_state(
            manager,
            topic=legacy_consult.get("topic") if isinstance(legacy_consult, dict) else None,
            question=legacy_consult.get("question") if isinstance(legacy_consult, dict) else None,
            questions=legacy_consult.get("questions") if isinstance(legacy_consult, dict) else None,
            message_count=_canonical_int(
                legacy_consult.get("message_count") if isinstance(legacy_consult, dict) else None,
                default=message_count,
            ),
        )
    manager = _set_canonical_pending_question_contract(
        manager,
        expected_reply_type=expected_reply_type,
        reason=expected_reply_reason,
        message_count=message_count,
    )
    return manager


def _get_conversation_context(conversation: Conversation) -> dict:
    context = conversation.context or {}
    if isinstance(context, dict):
        return dict(context)
    return {}


def _trace_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _trace_key(item: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (item.get("stage"), item.get("decision"), item.get("recorded_at"))


def _merge_decision_trace(existing: Any, incoming: Any) -> list[dict[str, Any]] | None:
    existing_list = _trace_list(existing)
    incoming_list = _trace_list(incoming)
    if not existing_list and not incoming_list:
        return None
    if not existing_list:
        return _retain_decision_trace(incoming_list)
    if not incoming_list:
        return _retain_decision_trace(existing_list)

    merged = list(existing_list)
    seen = {_trace_key(item) for item in existing_list}
    for item in incoming_list:
        key = _trace_key(item)
        if key != (None, None, None) and key in seen:
            continue
        merged.append(item)
        seen.add(key)
    return _retain_decision_trace(merged)


def _set_conversation_context(conversation: Conversation, context: dict) -> None:
    if not isinstance(context, dict):
        conversation.context = context
        return
    existing_context = conversation.context if isinstance(conversation.context, dict) else {}
    if existing_context:
        for key in ("simulation", "simulation_mode", "simulation_id", "simulation_llm", "simulation_time"):
            if key not in context and key in existing_context:
                context = dict(context)
                context[key] = existing_context.get(key)
    merged_trace = _merge_decision_trace(
        existing_context.get(DECISION_TRACE_KEY),
        context.get(DECISION_TRACE_KEY),
    )
    if merged_trace is not None:
        context = dict(context)
        context[DECISION_TRACE_KEY] = merged_trace
    conversation.context = context


def _get_expected_reply_type(context: dict) -> str | None:
    if not isinstance(context, dict):
        return None
    from . import _legacy as legacy

    value = context.get(legacy.EXPECTED_REPLY_TYPE_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _get_expected_reply_reason(context: dict) -> str | None:
    if not isinstance(context, dict):
        return None
    from . import _legacy as legacy

    value = context.get(legacy.EXPECTED_REPLY_REASON_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _set_expected_reply_type(context: dict, expected_reply_type: str | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    context.pop(legacy.EXPECTED_REPLY_REASON_KEY, None)
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        context[legacy.EXPECTED_REPLY_TYPE_KEY] = expected_reply_type.strip()
    else:
        context.pop(legacy.EXPECTED_REPLY_TYPE_KEY, None)
    return context


def _get_re_entry_required(context: dict) -> dict | None:
    from . import _legacy as legacy

    payload = context.get(legacy.RE_ENTRY_REQUIRED_KEY) if isinstance(context, dict) else None
    if isinstance(payload, dict):
        return dict(payload)
    return None


def _is_re_entry_required(context: dict) -> bool:
    payload = _get_re_entry_required(context)
    if not isinstance(payload, dict):
        return False
    return payload.get("required") is True


def _set_re_entry_required(context: dict, *, reason: str, now: datetime) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    context[legacy.RE_ENTRY_REQUIRED_KEY] = {
        "required": True,
        "reason": reason,
        "set_at": now.isoformat(),
    }
    return context


def _clear_re_entry_required(context: dict, *, reason: str, now: datetime) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    context[legacy.RE_ENTRY_REQUIRED_KEY] = {
        "required": False,
        "reason": reason,
        "cleared_at": now.isoformat(),
    }
    return context


def _set_expected_reply_context(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    context: dict,
    expected_reply_type: str | None,
    reason: str,
    now: datetime,
) -> dict:
    context = _set_expected_reply_type(context, expected_reply_type)
    if isinstance(reason, str) and reason.strip():
        from . import _legacy as legacy

        context[legacy.EXPECTED_REPLY_REASON_KEY] = reason.strip()
    context_manager = _get_context_manager(context)
    context_manager = _set_canonical_pending_question_contract(
        context_manager,
        expected_reply_type=expected_reply_type,
        reason=reason,
        message_count=_canonical_int(context_manager.get("message_count")),
    )
    context = _set_context_manager(context, context_manager)
    re_entry_cleared = False
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        if _is_re_entry_required(context):
            context = _clear_re_entry_required(context, reason=reason, now=now)
            re_entry_cleared = True
    _set_conversation_context(conversation, context)
    if re_entry_cleared:
        _record_decision_trace(
            conversation,
            {
                "stage": "re_entry",
                "decision": "cleared",
                "reason": reason,
            },
        )
    _record_decision_trace(
        conversation,
        {
            "stage": "question_contract",
            "decision": "set",
            "expected_reply_type": expected_reply_type,
            "reason": reason,
        },
    )
    if saved_message:
        _update_message_decision_metadata(
            saved_message,
            {
                "expected_reply_type": expected_reply_type,
                "expected_reply_reason": reason,
            },
        )
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        context_manager = _get_context_manager(context)
        active_goal = None
        if isinstance(context_manager, dict):
            active_goal = context_manager.get("current_goal")
            if isinstance(active_goal, str):
                active_goal = active_goal.strip() or None
            else:
                active_goal = None
        context, memory = _update_session_memory_on_question(
            context,
            expected_reply_type=expected_reply_type.strip(),
            active_goal=active_goal,
            now=now,
        )
        _set_conversation_context(conversation, context)
        _record_session_memory_update(
            conversation,
            saved_message,
            memory=memory,
            reason="question_set",
        )
    return context


def _get_context_manager(context: dict) -> dict:
    from . import _legacy as legacy

    manager = context.get(legacy.CONTEXT_MANAGER_KEY) if isinstance(context, dict) else None
    if isinstance(manager, dict):
        return dict(manager)
    return {}


def _set_context_manager(context: dict, manager: dict) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    context[legacy.CONTEXT_MANAGER_KEY] = manager
    return context


def _increment_context_message_count(manager: dict) -> int:
    value = manager.get("message_count", 0)
    try:
        count = max(0, int(value))
    except (TypeError, ValueError):
        count = 0
    count += 1
    manager["message_count"] = count
    return count


def _prune_class_carryover(manager: dict, *, message_count: int) -> tuple[dict, dict | None]:
    from . import _legacy as legacy

    payload = manager.get(legacy.CLASS_CARRYOVER_KEY)
    if not isinstance(payload, dict):
        return manager, None
    class_name = payload.get("class")
    if not isinstance(class_name, str) or not class_name.strip():
        manager = dict(manager)
        manager.pop(legacy.CLASS_CARRYOVER_KEY, None)
        return manager, {"reason": "invalid"}
    try:
        last_count = int(payload.get("message_count"))
    except (TypeError, ValueError):
        manager = dict(manager)
        manager.pop(legacy.CLASS_CARRYOVER_KEY, None)
        return manager, {"reason": "invalid"}
    ttl = payload.get("ttl", legacy.CLASS_CARRYOVER_TTL_MESSAGES)
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        ttl = legacy.CLASS_CARRYOVER_TTL_MESSAGES
    if ttl <= 0:
        ttl = legacy.CLASS_CARRYOVER_TTL_MESSAGES
    age = message_count - last_count
    if age > ttl:
        manager = dict(manager)
        manager.pop(legacy.CLASS_CARRYOVER_KEY, None)
        return manager, {"reason": "expired", "age": age, "ttl": ttl, "class": class_name}
    return manager, None


def _get_class_carryover(manager: dict, *, message_count: int) -> dict | None:
    from . import _legacy as legacy

    payload = manager.get(legacy.CLASS_CARRYOVER_KEY)
    if not isinstance(payload, dict):
        return None
    class_name = payload.get("class")
    if not isinstance(class_name, str) or not class_name.strip():
        return None
    try:
        last_count = int(payload.get("message_count"))
    except (TypeError, ValueError):
        return None
    ttl = payload.get("ttl", legacy.CLASS_CARRYOVER_TTL_MESSAGES)
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        return None
    if ttl <= 0:
        return None
    age = message_count - last_count
    if age <= 0 or age > ttl:
        return None
    remaining = max(ttl - age + 1, 0)
    intents = payload.get("intents")
    if isinstance(intents, list):
        intents = [intent for intent in intents if isinstance(intent, str) and intent.strip()]
    else:
        intents = []
    info_sections = payload.get("info_sections")
    if not isinstance(info_sections, list):
        info_sections = []
    return {
        "class": class_name.strip(),
        "intents": intents,
        "info_sections": info_sections,
        "age": age,
        "ttl": ttl,
        "remaining": remaining,
    }


def _set_class_carryover(
    manager: dict,
    *,
    class_name: str,
    intents: list[str],
    info_sections: list[str] | None,
    message_count: int,
) -> dict:
    from . import _legacy as legacy

    manager = dict(manager)
    normalized_class = legacy._normalize_class_name(class_name)
    section_intent_map = {
        "address": "location",
        "location": "location",
        "hours": "hours",
        "parking": "parking",
        "guest_policy": "guest_policy",
        "pricing": "pricing",
        "price": "pricing",
        "duration": "duration",
        "service_duration": "duration",
        "promotions": "promotions",
        "promotion": "promotions",
        "promo": "promotions",
        "discounts": "promotions",
        "discount": "promotions",
        "master": "master",
        "specialist": "master",
        "contact": "contact",
    }
    cleaned_intents = []
    seen = set()
    for intent in intents:
        if not isinstance(intent, str):
            continue
        value = intent.strip().casefold()
        if not value or value in seen:
            continue
        cleaned_intents.append(value)
        seen.add(value)
    cleaned_sections = []
    if isinstance(info_sections, list):
        for section in info_sections:
            if not isinstance(section, str):
                continue
            value = section.strip()
            if not value:
                continue
            cleaned_sections.append(value)
            normalized_section = value.casefold()
            derived_intent = section_intent_map.get(normalized_section)
            if (
                derived_intent
                and derived_intent in legacy.INFO_INTENTS
                and derived_intent not in seen
            ):
                cleaned_intents.append(derived_intent)
                seen.add(derived_intent)
    manager[legacy.CLASS_CARRYOVER_KEY] = {
        "class": normalized_class,
        "intents": cleaned_intents,
        "info_sections": cleaned_sections,
        "message_count": message_count,
        "ttl": legacy.CLASS_CARRYOVER_TTL_MESSAGES,
    }
    return manager


def _maybe_store_class_carryover(
    *,
    conversation: Conversation,
    class_name: str,
    intents: list[str] | None,
    info_meta: dict | None,
    message_count: int,
    reason: str,
) -> None:
    from . import _legacy as legacy

    normalized_class = legacy._normalize_class_name(class_name)
    if normalized_class not in legacy.CLASS_CARRYOVER_CLASSES:
        return
    intent_list = intents or []
    info_sections = []
    if isinstance(info_meta, dict):
        info_sections = info_meta.get("info_sections") if isinstance(info_meta.get("info_sections"), list) else []
    context = _get_conversation_context(conversation)
    context_manager = _get_context_manager(context)
    context_manager = _set_class_carryover(
        context_manager,
        class_name=normalized_class,
        intents=intent_list,
        info_sections=info_sections,
        message_count=message_count,
    )
    stored_payload = (
        context_manager.get(legacy.CLASS_CARRYOVER_KEY)
        if isinstance(context_manager, dict)
        else None
    )
    context = _set_context_manager(context, context_manager)
    _set_conversation_context(conversation, context)
    _record_decision_trace(
        conversation,
        {
            "stage": "class_carryover",
            "decision": "set",
            "class": normalized_class,
            "intents": (
                stored_payload.get("intents")
                if isinstance(stored_payload, dict)
                else intent_list
            ),
            "info_sections": (
                stored_payload.get("info_sections")
                if isinstance(stored_payload, dict)
                else info_sections
            ),
            "ttl": legacy.CLASS_CARRYOVER_TTL_MESSAGES,
            "reason": reason,
        },
    )


def _prune_service_carryover(manager: dict, *, message_count: int) -> tuple[dict, dict | None]:
    from . import _legacy as legacy

    manager, canonical_event = _prune_canonical_referent(
        manager,
        referent_key="service",
        message_count=message_count,
    )
    payload = manager.get(legacy.SERVICE_CARRYOVER_KEY)
    if not isinstance(payload, dict):
        return manager, canonical_event
    service_query = payload.get("service_query")
    if not isinstance(service_query, str) or not service_query.strip():
        manager = dict(manager)
        manager.pop(legacy.SERVICE_CARRYOVER_KEY, None)
        return manager, canonical_event or {"reason": "invalid"}
    try:
        last_count = int(payload.get("message_count"))
    except (TypeError, ValueError):
        manager = dict(manager)
        manager.pop(legacy.SERVICE_CARRYOVER_KEY, None)
        return manager, canonical_event or {"reason": "invalid"}
    ttl = payload.get("ttl", legacy.SERVICE_CARRYOVER_TTL_MESSAGES)
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        ttl = legacy.SERVICE_CARRYOVER_TTL_MESSAGES
    if ttl <= 0:
        ttl = legacy.SERVICE_CARRYOVER_TTL_MESSAGES
    age = message_count - last_count
    if age > ttl:
        manager = dict(manager)
        manager.pop(legacy.SERVICE_CARRYOVER_KEY, None)
        return manager, canonical_event or {
            "reason": "expired",
            "age": age,
            "ttl": ttl,
            "service_query": service_query,
        }
    return manager, canonical_event


def _get_service_carryover(manager: dict, *, message_count: int) -> dict | None:
    from . import _legacy as legacy

    canonical_projection = _project_canonical_referent(
        manager,
        referent_key="service",
        message_count=message_count,
    )
    if isinstance(canonical_projection, dict):
        return {
            "service_query": canonical_projection.get("value"),
            "service_query_source": canonical_projection.get("source"),
            "service_query_score": canonical_projection.get("score"),
            "age": canonical_projection.get("age"),
            "ttl": canonical_projection.get("ttl"),
            "remaining": canonical_projection.get("remaining"),
            "projection_source": canonical_projection.get("projection_source"),
            "canonical_state_owner": canonical_projection.get("canonical_state_owner"),
        }

    payload = manager.get(legacy.SERVICE_CARRYOVER_KEY)
    if not isinstance(payload, dict):
        return None
    service_query = payload.get("service_query")
    if not isinstance(service_query, str) or not service_query.strip():
        return None
    try:
        last_count = int(payload.get("message_count"))
    except (TypeError, ValueError):
        return None
    ttl = payload.get("ttl", legacy.SERVICE_CARRYOVER_TTL_MESSAGES)
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        return None
    if ttl <= 0:
        return None
    age = message_count - last_count
    if age <= 0 or age > ttl:
        return None
    remaining = max(ttl - age + 1, 0)
    return {
        "service_query": service_query.strip(),
        "service_query_source": payload.get("service_query_source"),
        "service_query_score": payload.get("service_query_score"),
        "age": age,
        "ttl": ttl,
        "remaining": remaining,
        "projection_source": payload.get("projection_source"),
        "canonical_state_owner": payload.get("canonical_state_owner"),
    }


def _set_service_carryover(
    manager: dict,
    *,
    service_query: str,
    source: str | None,
    score: float | None,
    message_count: int,
) -> dict:
    from . import _legacy as legacy

    manager = dict(manager)
    score_value = 0.0
    if isinstance(score, (int, float)):
        score_value = float(score)
    manager = _set_canonical_referent(
        manager,
        referent_key="service",
        value=service_query,
        source=source or "unknown",
        score=score_value,
        message_count=message_count,
    )
    manager[legacy.SERVICE_CARRYOVER_KEY] = {
        "service_query": service_query,
        "service_query_source": source or "unknown",
        "service_query_score": score_value,
        "message_count": message_count,
        "ttl": legacy.SERVICE_CARRYOVER_TTL_MESSAGES,
        "projection_source": CANONICAL_DIALOG_STATE_KEY,
        "canonical_state_owner": CANONICAL_DIALOG_STATE_OWNER,
    }
    return manager


def _maybe_store_service_carryover(
    *,
    conversation: Conversation,
    service_meta: dict | None,
    intent: str | None,
    message_count: int,
    reason: str,
) -> None:
    from . import _legacy as legacy

    if not isinstance(service_meta, dict):
        return
    service_query = service_meta.get("service_query")
    if not isinstance(service_query, str) or not service_query.strip():
        return
    if intent and intent in legacy.SERVICE_CARRYOVER_SKIP_INTENTS:
        return
    source = service_meta.get("service_query_source")
    score = service_meta.get("service_query_score")
    context = _get_conversation_context(conversation)
    context_manager = _get_context_manager(context)
    context_manager = _set_service_carryover(
        context_manager,
        service_query=service_query.strip(),
        source=source if isinstance(source, str) else None,
        score=score if isinstance(score, (int, float)) else None,
        message_count=message_count,
    )
    context = _set_context_manager(context, context_manager)
    _set_conversation_context(conversation, context)
    _record_decision_trace(
        conversation,
        {
            "stage": "service_carryover",
            "decision": "set",
            "service_query": service_query.strip(),
            "service_query_source": source,
            "service_query_score": score,
            "ttl": legacy.SERVICE_CARRYOVER_TTL_MESSAGES,
            "projection_source": CANONICAL_DIALOG_STATE_KEY,
            "canonical_state_owner": CANONICAL_DIALOG_STATE_OWNER,
            "reason": reason,
        },
    )


def _prune_consult_context(manager: dict, *, message_count: int) -> tuple[dict, dict | None]:
    from . import _legacy as legacy

    manager, canonical_event = _prune_canonical_consult_state(
        manager,
        message_count=message_count,
    )
    payload = manager.get(legacy.CONSULT_CONTEXT_KEY)
    if not isinstance(payload, dict):
        return manager, canonical_event
    try:
        last_count = int(payload.get("message_count"))
    except (TypeError, ValueError):
        manager = dict(manager)
        manager.pop(legacy.CONSULT_CONTEXT_KEY, None)
        return manager, canonical_event or {"reason": "invalid"}
    ttl = payload.get("ttl", legacy.CONSULT_CONTEXT_TTL_MESSAGES)
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        ttl = legacy.CONSULT_CONTEXT_TTL_MESSAGES
    if ttl <= 0:
        ttl = legacy.CONSULT_CONTEXT_TTL_MESSAGES
    age = message_count - last_count
    if age > ttl:
        manager = dict(manager)
        manager.pop(legacy.CONSULT_CONTEXT_KEY, None)
        return manager, canonical_event or {"reason": "expired", "age": age, "ttl": ttl}
    return manager, canonical_event


def _get_consult_context(manager: dict, *, message_count: int) -> dict | None:
    from . import _legacy as legacy

    canonical_projection = _project_canonical_consult_state(
        manager,
        message_count=message_count,
    )
    if isinstance(canonical_projection, dict):
        return canonical_projection

    payload = manager.get(legacy.CONSULT_CONTEXT_KEY)
    if not isinstance(payload, dict):
        return None
    try:
        last_count = int(payload.get("message_count"))
    except (TypeError, ValueError):
        return None
    ttl = payload.get("ttl", legacy.CONSULT_CONTEXT_TTL_MESSAGES)
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        return None
    if ttl <= 0:
        return None
    age = message_count - last_count
    if age <= 0 or age > ttl:
        return None
    remaining = max(ttl - age + 1, 0)
    questions_raw = payload.get("questions")
    questions: list[str] = []
    if isinstance(questions_raw, list):
        for item in questions_raw:
            if not isinstance(item, str):
                continue
            value = item.strip()
            if value:
                questions.append(value)
    topic = payload.get("topic")
    topic_value = topic.strip() if isinstance(topic, str) and topic.strip() else None
    question = payload.get("question")
    question_value = question.strip() if isinstance(question, str) and question.strip() else None
    return {
        "questions": questions,
        "topic": topic_value,
        "question": question_value,
        "age": age,
        "ttl": ttl,
        "remaining": remaining,
        "projection_source": payload.get("projection_source"),
        "canonical_state_owner": payload.get("canonical_state_owner"),
    }


def _set_consult_context(
    manager: dict,
    *,
    consult_meta: dict,
    message_count: int,
) -> dict:
    from . import _legacy as legacy

    manager = dict(manager)
    questions_raw = consult_meta.get("consult_questions") if isinstance(consult_meta, dict) else None
    questions: list[str] = []
    if isinstance(questions_raw, list):
        for item in questions_raw:
            if not isinstance(item, str):
                continue
            value = item.strip()
            if value:
                questions.append(legacy._ensure_question_mark(value))
    topic = consult_meta.get("consult_topic") if isinstance(consult_meta, dict) else None
    topic_value = topic.strip() if isinstance(topic, str) and topic.strip() else None
    question = consult_meta.get("consult_question") if isinstance(consult_meta, dict) else None
    question_value = question.strip() if isinstance(question, str) and question.strip() else None
    manager = _set_canonical_consult_state(
        manager,
        topic=topic_value,
        question=question_value,
        questions=questions,
        message_count=message_count,
    )
    manager[legacy.CONSULT_CONTEXT_KEY] = {
        "questions": questions,
        "topic": topic_value,
        "question": question_value,
        "message_count": message_count,
        "ttl": legacy.CONSULT_CONTEXT_TTL_MESSAGES,
        "projection_source": CANONICAL_DIALOG_STATE_KEY,
        "canonical_state_owner": CANONICAL_DIALOG_STATE_OWNER,
    }
    return manager


def _build_consult_return_prompt(consult_context: dict | None) -> str | None:
    if not isinstance(consult_context, dict):
        return None
    questions = consult_context.get("questions")
    if isinstance(questions, list):
        cleaned = [item.strip() for item in questions if isinstance(item, str) and item.strip()]
        if cleaned:
            return f"Если вернуться к вашему вопросу: {' '.join(cleaned)}"
    question = consult_context.get("question")
    if isinstance(question, str) and question.strip():
        from . import _legacy as legacy

        return f"Если вернуться к вашему вопросу: {legacy._ensure_question_mark(question)}"
    return "Если хотите, продолжим консультацию."


def _apply_consult_return(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    bot_response: str | None,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    reason: str,
) -> str | None:
    if not bot_response or not consult_return_prompt:
        return bot_response
    trace_payload = {
        "stage": "consult_return",
        "decision": "attached",
        "current_goal": "consult",
        "reason": reason,
    }
    if isinstance(consult_context, dict):
        consult_topic = consult_context.get("topic")
        consult_question = consult_context.get("question")
        if consult_topic:
            trace_payload["consult_topic"] = consult_topic
        if consult_question:
            trace_payload["consult_question"] = consult_question
        projection_source = consult_context.get("projection_source")
        canonical_state_owner = consult_context.get("canonical_state_owner")
        if projection_source:
            trace_payload["projection_source"] = projection_source
        if canonical_state_owner:
            trace_payload["canonical_state_owner"] = canonical_state_owner
    _record_decision_trace(conversation, trace_payload)
    if saved_message:
        updates = {"consult_return": True, "current_goal": "consult"}
        if isinstance(consult_context, dict):
            consult_topic = consult_context.get("topic")
            if consult_topic:
                updates["consult_topic"] = consult_topic
            projection_source = consult_context.get("projection_source")
            canonical_state_owner = consult_context.get("canonical_state_owner")
            if projection_source:
                updates["projection_source"] = projection_source
            if canonical_state_owner:
                updates["canonical_state_owner"] = canonical_state_owner
        _update_message_decision_metadata(saved_message, updates)
    from . import _legacy as legacy

    return legacy._append_followup(bot_response, consult_return_prompt)


def _resolve_current_goal(
    intent_set: set[str],
    consult_intent: bool,
    expected_reply_type: str | None = None,
    expected_reply_reason: str | None = None,
) -> str | None:
    from . import _legacy as legacy

    if consult_intent:
        return "consult"
    if expected_reply_type in {
        legacy.EXPECTED_REPLY_SERVICE,
        legacy.EXPECTED_REPLY_TIME,
        legacy.EXPECTED_REPLY_NAME,
    }:
        if expected_reply_reason and expected_reply_reason != "booking_prompt":
            return None
        return "booking"
    if "booking" in intent_set:
        return "booking"
    if intent_set & legacy.INFO_INTENTS:
        return "info"
    return None


def _build_compact_summary_text(
    *,
    booking: dict,
    refusal_flags: dict,
    language: str | None,
) -> str:
    parts: list[str] = []
    service = booking.get("service")
    if isinstance(service, str) and service.strip():
        parts.append(f"Услуга: {service.strip()}")
    datetime_pref = booking.get("datetime")
    if isinstance(datetime_pref, str) and datetime_pref.strip():
        parts.append(f"Время: {datetime_pref.strip()}")
    name = booking.get("name")
    if isinstance(name, str) and name.strip():
        parts.append(f"Имя: {name.strip()}")
    from . import _legacy as legacy

    if not name and legacy._is_refusal_flag_active(refusal_flags, "name"):
        parts.append("Имя: отказ")
    if legacy._is_refusal_flag_active(refusal_flags, "phone"):
        parts.append("Телефон: отказ")
    if isinstance(language, str) and language and language != "unknown":
        parts.append(f"Язык: {language}")
    return "; ".join(parts).strip()


def _update_compact_summary(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    reason: str,
    now: datetime,
) -> None:
    context = _get_conversation_context(conversation)
    manager = _get_context_manager(context)
    refusal_flags = manager.get("refusal_flags")
    refusal_flags = dict(refusal_flags) if isinstance(refusal_flags, dict) else {}
    booking = _get_booking_context(context)
    from . import _legacy as legacy

    language = legacy._resolve_backlog_language(saved_message) if saved_message else "unknown"
    summary_text = _build_compact_summary_text(
        booking=booking,
        refusal_flags=refusal_flags,
        language=language,
    )
    manager["compact_summary"] = {
        "text": summary_text,
        "updated_at": now.isoformat(),
        "reason": reason,
    }
    context = _set_context_manager(context, manager)
    _set_conversation_context(conversation, context)
    if saved_message:
        _update_message_decision_metadata(saved_message, {"summary_updated": reason})
    _record_decision_trace(
        conversation,
        {
            "stage": "context_manager",
            "decision": "summary_updated",
            "reason": reason,
            "summary_text": summary_text,
        },
    )


def _record_context_manager_decision(
    conversation: Conversation,
    saved_message: Message | None,
    *,
    decision: str,
    updates: dict,
) -> None:
    if saved_message and updates:
        _update_message_decision_metadata(saved_message, updates)
    trace = {"stage": "context_manager", "decision": decision}
    trace.update(updates)
    _record_decision_trace(conversation, trace)


def _get_low_confidence_retry_count(context: dict) -> int:
    value = context.get("low_confidence_retry_count", 0) if isinstance(context, dict) else 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _set_low_confidence_retry_count(context: dict, count: int) -> dict:
    context = dict(context)
    context["low_confidence_retry_count"] = max(0, int(count))
    return context


def _reset_low_confidence_retry(conversation: Conversation) -> None:
    context = _get_conversation_context(conversation)
    if context.get("low_confidence_retry_count"):
        context = _set_low_confidence_retry_count(context, 0)
        _set_conversation_context(conversation, context)
    conversation.retry_offered_at = None


def _get_handover_confirmation(context: dict) -> dict | None:
    confirmation = context.get("handover_confirmation") if isinstance(context, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None


def _set_handover_confirmation(context: dict, confirmation: dict | None) -> dict:
    context = dict(context)
    if confirmation:
        context["handover_confirmation"] = confirmation
    else:
        context.pop("handover_confirmation", None)
    return context


def _is_handover_confirmation_active(confirmation: dict, now: datetime) -> bool:
    from . import _legacy as legacy

    asked_at_raw = confirmation.get("asked_at")
    if not asked_at_raw:
        return False
    try:
        asked_at = datetime.fromisoformat(asked_at_raw)
    except (TypeError, ValueError):
        return False
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=timezone.utc)
    return (now - asked_at) <= timedelta(minutes=legacy.HANDOVER_CONFIRM_WINDOW_MINUTES)


def _get_reengage_confirmation(context: dict) -> dict | None:
    from . import _legacy as legacy

    confirmation = context.get(legacy.REENGAGE_CONFIRM_KEY) if isinstance(context, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None


def _set_reengage_confirmation(context: dict, confirmation: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if confirmation:
        context[legacy.REENGAGE_CONFIRM_KEY] = confirmation
    else:
        context.pop(legacy.REENGAGE_CONFIRM_KEY, None)
    return context


def _is_reengage_confirmation_active(confirmation: dict, now: datetime) -> bool:
    from . import _legacy as legacy

    asked_at_raw = confirmation.get("asked_at")
    if not asked_at_raw:
        return False
    try:
        asked_at = datetime.fromisoformat(asked_at_raw)
    except (TypeError, ValueError):
        return False
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=timezone.utc)
    return (now - asked_at) <= timedelta(minutes=legacy.REENGAGE_CONFIRM_WINDOW_MINUTES)


def _get_asr_confirmation(context: dict) -> dict | None:
    from . import _legacy as legacy

    confirmation = context.get(legacy.ASR_CONFIRM_KEY) if isinstance(context, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None


def _set_asr_confirmation(context: dict, confirmation: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if confirmation:
        context[legacy.ASR_CONFIRM_KEY] = confirmation
    else:
        context.pop(legacy.ASR_CONFIRM_KEY, None)
    return context


def _is_asr_confirmation_active(confirmation: dict, now: datetime) -> bool:
    from . import _legacy as legacy

    asked_at_raw = confirmation.get("asked_at")
    if not asked_at_raw:
        return False
    try:
        asked_at = datetime.fromisoformat(asked_at_raw)
    except (TypeError, ValueError):
        return False
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=timezone.utc)
    return (now - asked_at) <= timedelta(minutes=legacy.ASR_CONFIRM_WINDOW_MINUTES)


def _parse_profile_time(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _get_asr_inflight(context: dict, *, now: datetime) -> tuple[dict | None, bool]:
    from . import _legacy as legacy

    payload = context.get(legacy.ASR_INFLIGHT_KEY) if isinstance(context, dict) else None
    if not isinstance(payload, dict):
        return None, False
    expires_at = _parse_profile_time(payload.get("expires_at"))
    if expires_at and expires_at <= now:
        return None, True
    return dict(payload), False


def _set_asr_inflight(context: dict, payload: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if payload:
        context[legacy.ASR_INFLIGHT_KEY] = payload
    else:
        context.pop(legacy.ASR_INFLIGHT_KEY, None)
    return context


def _get_style_reference_pending(context: dict, *, now: datetime) -> tuple[dict | None, bool]:
    from . import _legacy as legacy

    payload = context.get(legacy.STYLE_REFERENCE_PENDING_KEY) if isinstance(context, dict) else None
    if not isinstance(payload, dict):
        return None, False
    expires_at = _parse_profile_time(payload.get("expires_at"))
    if expires_at and expires_at <= now:
        return None, True
    return dict(payload), False


def _set_style_reference_pending(context: dict, payload: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if payload:
        context[legacy.STYLE_REFERENCE_PENDING_KEY] = payload
    else:
        context.pop(legacy.STYLE_REFERENCE_PENDING_KEY, None)
    return context


def _normalize_memory_profile(profile: dict | None, *, now: datetime) -> tuple[dict, bool]:
    from . import _legacy as legacy

    changed = False
    if not isinstance(profile, dict):
        profile = {}
        changed = True
    normalized = dict(profile)
    if normalized.get("version") != 1:
        normalized["version"] = 1
        changed = True
    ttl_days = normalized.get("ttl_days")
    if not isinstance(ttl_days, int) or ttl_days <= 0:
        normalized["ttl_days"] = legacy.MEMORY_PROFILE_TTL_DAYS
        changed = True
    consent = normalized.get("consent")
    if not isinstance(consent, dict):
        consent = {}
        changed = True
    status = consent.get("status")
    if status not in {"unknown", "asked", "granted", "declined"}:
        consent["status"] = "unknown"
        changed = True
    if "prompt_count" not in consent:
        consent["prompt_count"] = 0
        changed = True
    normalized["consent"] = consent
    items = normalized.get("items")
    if not isinstance(items, dict):
        items = {}
        changed = True
    pruned = {}
    for key, item in items.items():
        if not isinstance(key, str) or not isinstance(item, dict):
            changed = True
            continue
        expires_at = _parse_profile_time(item.get("expires_at"))
        if expires_at and expires_at <= now:
            changed = True
            continue
        pruned[key] = item
    if pruned != items:
        changed = True
    normalized["items"] = pruned
    last_updated_at = normalized.get("last_updated_at")
    if last_updated_at and not _parse_profile_time(last_updated_at):
        normalized.pop("last_updated_at", None)
        changed = True
    return normalized, changed


def _get_memory_profile(context: dict, *, now: datetime) -> tuple[dict, bool]:
    from . import _legacy as legacy

    payload = context.get(legacy.MEMORY_PROFILE_KEY) if isinstance(context, dict) else None
    normalized, changed = _normalize_memory_profile(payload, now=now)
    return normalized, changed


def _set_memory_profile(context: dict, profile: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if profile:
        context[legacy.MEMORY_PROFILE_KEY] = profile
    else:
        context.pop(legacy.MEMORY_PROFILE_KEY, None)
    return context


def _get_memory_pending(context: dict, *, now: datetime) -> tuple[dict | None, bool]:
    from . import _legacy as legacy

    pending = context.get(legacy.MEMORY_PENDING_KEY) if isinstance(context, dict) else None
    if not isinstance(pending, dict):
        return None, False
    expires_at = _parse_profile_time(pending.get("expires_at"))
    if expires_at and expires_at <= now:
        return None, True
    return dict(pending), False


def _set_memory_pending(context: dict, pending: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if pending:
        context[legacy.MEMORY_PENDING_KEY] = pending
    else:
        context.pop(legacy.MEMORY_PENDING_KEY, None)
    return context


__all__ = [
    "_apply_consult_return",
    "_build_compact_summary_text",
    "_build_consult_return_prompt",
    "_get_canonical_dialog_state",
    "_get_asr_confirmation",
    "_get_asr_inflight",
    "_get_class_carryover",
    "_get_consult_context",
    "_get_context_manager",
    "_get_conversation_context",
    "_get_expected_reply_reason",
    "_get_expected_reply_type",
    "_get_handover_confirmation",
    "_get_low_confidence_retry_count",
    "_get_re_entry_required",
    "_get_reengage_confirmation",
    "_get_service_carryover",
    "_increment_context_message_count",
    "_is_asr_confirmation_active",
    "_is_handover_confirmation_active",
    "_is_re_entry_required",
    "_is_reengage_confirmation_active",
    "_maybe_store_class_carryover",
    "_maybe_store_service_carryover",
    "_prune_class_carryover",
    "_prune_consult_context",
    "_prune_service_carryover",
    "_record_context_manager_decision",
    "_reset_low_confidence_retry",
    "_resolve_current_goal",
    "_set_asr_confirmation",
    "_set_asr_inflight",
    "_set_class_carryover",
    "_set_consult_context",
    "_set_context_manager",
    "_set_conversation_context",
    "_sync_canonical_dialog_state",
    "_set_re_entry_required",
    "_clear_re_entry_required",
    "_set_expected_reply_context",
    "_set_expected_reply_type",
    "_set_handover_confirmation",
    "_set_low_confidence_retry_count",
    "_set_reengage_confirmation",
    "_get_style_reference_pending",
    "_get_memory_profile",
    "_set_memory_profile",
    "_get_memory_pending",
    "_set_memory_pending",
    "_normalize_memory_profile",
    "_set_service_carryover",
    "_set_style_reference_pending",
    "_update_compact_summary",
]
