"""Legacy context helper surface kept unreachable from the live runtime boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core import DialogStateService
from app.models import Conversation, Message
from app.routers.webhook.booking import _get_booking_context
from app.routers.webhook.class_router_runtime import _normalize_class_name
from app.routers.webhook.context_runtime import (
    ASR_CONFIRM_KEY,
    ASR_CONFIRM_WINDOW_MINUTES,
    ASR_INFLIGHT_KEY,
    CLASS_CARRYOVER_CLASSES,
    CLASS_CARRYOVER_KEY,
    CLASS_CARRYOVER_TTL_MESSAGES,
    CONSULT_CONTEXT_KEY,
    CONTEXT_MANAGER_KEY,
    EXPECTED_REPLY_REASON_KEY,
    EXPECTED_REPLY_TYPE_KEY,
    HANDOVER_CONFIRM_WINDOW_MINUTES,
    MEMORY_PENDING_KEY,
    MEMORY_PROFILE_KEY,
    MEMORY_PROFILE_TTL_DAYS,
    RE_ENTRY_REQUIRED_KEY,
    REENGAGE_CONFIRM_KEY,
    REENGAGE_CONFIRM_WINDOW_MINUTES,
    SERVICE_CARRYOVER_KEY,
    SERVICE_CARRYOVER_SKIP_INTENTS,
    SERVICE_HINT_KEY,
    SERVICE_HINT_WINDOW_MINUTES,
    STYLE_REFERENCE_PENDING_KEY,
    _ensure_question_mark,
    _is_refusal_flag_active,
)
from app.routers.webhook.knowledge_runtime import _resolve_backlog_language
from app.routers.webhook.runtime_primitives import (
    CONSULT_CONTEXT_TTL_MESSAGES,
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
    INFO_INTENTS,
    SERVICE_CARRYOVER_TTL_MESSAGES,
    _append_followup,
)
from app.routers.webhook.session_memory import (
    SESSION_MEMORY_KEY,
    SESSION_MEMORY_TTL_HOURS,
    _record_session_memory_update,
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
_DIALOG_STATE_SERVICE = DialogStateService()



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
    state = _DIALOG_STATE_SERVICE.normalize_context_manager_canonical_state(payload)
    if not state:
        return _canonical_state_base()
    return state


def _set_canonical_dialog_state(manager: dict, state: dict[str, Any] | None) -> dict:
    return _DIALOG_STATE_SERVICE.set_context_manager_canonical_state(
        manager,
        key=CANONICAL_DIALOG_STATE_KEY,
        state=state,
    )


def _project_canonical_referent(
    manager: dict,
    *,
    referent_key: str,
    message_count: int,
) -> dict[str, Any] | None:
    return _DIALOG_STATE_SERVICE.project_canonical_referent(
        _get_canonical_dialog_state(manager),
        referent_key=referent_key,
        message_count=message_count,
        projection_source=CANONICAL_DIALOG_STATE_KEY,
    )


def _prune_canonical_referent(
    manager: dict,
    *,
    referent_key: str,
    message_count: int,
) -> tuple[dict, dict[str, Any] | None]:
    manager = dict(manager)
    state, event = _DIALOG_STATE_SERVICE.prune_canonical_referent(
        _get_canonical_dialog_state(manager),
        referent_key=referent_key,
        message_count=message_count,
        projection_source=CANONICAL_DIALOG_STATE_KEY,
    )
    manager = _set_canonical_dialog_state(manager, state)
    return manager, event


def _project_canonical_consult_state(
    manager: dict,
    *,
    message_count: int,
) -> dict[str, Any] | None:
    state = _get_canonical_dialog_state(manager)
    return _DIALOG_STATE_SERVICE.get_canonical_consult_state(
        state,
        message_count=message_count,
    )


def _prune_canonical_consult_state(
    manager: dict,
    *,
    message_count: int,
) -> tuple[dict, dict[str, Any] | None]:
    manager = dict(manager)
    state = _get_canonical_dialog_state(manager)
    state, event = _DIALOG_STATE_SERVICE.prune_canonical_consult_state(
        state,
        message_count=message_count,
    )
    manager = _set_canonical_dialog_state(manager, state)
    return manager, event


def _sync_canonical_dialog_state(
    manager: dict,
    *,
    booking_state: dict[str, Any] | None,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    message_count: int,
    branch_id: Any = None,
    consult_context: dict[str, Any] | None = None,
    interaction_target: str | None = None,
    interaction_relation: str | None = None,
    interaction_owner: str | None = None,
    degrade_reason: str | None = None,
) -> dict:

    return _DIALOG_STATE_SERVICE.sync_context_manager_expected_reply_state(
        manager,
        booking_state=booking_state,
        expected_reply_type=expected_reply_type,
        expected_reply_reason=expected_reply_reason,
        message_count=message_count,
        service_carryover=(
            manager.get(SERVICE_CARRYOVER_KEY)
            if isinstance(manager, dict) and isinstance(manager.get(SERVICE_CARRYOVER_KEY), dict)
            else None
        ),
        consult_context=consult_context,
        legacy_consult_context=(
            manager.get(CONSULT_CONTEXT_KEY)
            if isinstance(manager, dict) and isinstance(manager.get(CONSULT_CONTEXT_KEY), dict)
            else None
        ),
        branch_id=branch_id,
        interaction_target=interaction_target,
        interaction_relation=interaction_relation,
        interaction_owner=interaction_owner,
        degrade_reason=degrade_reason,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        service_default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
        consult_default_ttl=CONSULT_CONTEXT_TTL_MESSAGES,
    )


def _get_conversation_context(conversation: Conversation) -> dict:
    context = conversation.context or {}
    if isinstance(context, dict):
        return dict(context)
    return {}


def _set_conversation_context(conversation: Conversation, context: dict) -> None:
    existing_context = conversation.context if isinstance(conversation.context, dict) else {}
    conversation.context = _DIALOG_STATE_SERVICE.prepare_conversation_context_write(
        existing_context,
        context,
        decision_trace_key=DECISION_TRACE_KEY,
        preserve_keys=(
            "simulation",
            "simulation_mode",
            "simulation_id",
            "simulation_llm",
            "simulation_time",
        ),
        retain_trace=_retain_decision_trace,
    )


def _get_expected_reply_type(context: dict) -> str | None:
    if not isinstance(context, dict):
        return None
    pending_question_contract = _get_pending_question_contract(context)
    if isinstance(pending_question_contract, dict):
        expected_reply_type = pending_question_contract.get("expected_reply_type")
        if isinstance(expected_reply_type, str) and expected_reply_type.strip():
            return expected_reply_type.strip()
    return None


def _get_expected_reply_reason(context: dict) -> str | None:
    if not isinstance(context, dict):
        return None
    pending_question_contract = _get_pending_question_contract(context)
    if isinstance(pending_question_contract, dict):
        reason = pending_question_contract.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return None


def _get_pending_question_contract(context: dict) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None
    return _DIALOG_STATE_SERVICE.project_context_pending_question_contract(
        context,
        context_manager_key=CONTEXT_MANAGER_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        session_memory_key=SESSION_MEMORY_KEY,
        expected_reply_type_key=EXPECTED_REPLY_TYPE_KEY,
        expected_reply_reason_key=EXPECTED_REPLY_REASON_KEY,
    )


def _set_expected_reply_type(context: dict, expected_reply_type: str | None) -> dict:
    updated = _DIALOG_STATE_SERVICE.set_expected_reply_context_fields(
        context,
        expected_reply_type=expected_reply_type,
        expected_reply_reason=None,
    )
    projections = _DIALOG_STATE_SERVICE.project_expected_reply_projections(
        expected_reply_type=expected_reply_type,
    )
    manager = _get_context_manager(updated)
    canonical_state = _get_canonical_dialog_state(manager)
    canonical_state = _DIALOG_STATE_SERVICE.set_canonical_pending_question_contract(
        canonical_state,
        expected_reply_type=projections.expected_reply_type,
        reason=None,
        message_count=0,
    )
    manager = _set_canonical_dialog_state(manager, canonical_state)
    return _set_context_manager(updated, manager)


def _get_re_entry_required(context: dict) -> dict | None:

    payload = context.get(RE_ENTRY_REQUIRED_KEY) if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.normalize_re_entry_required(payload)


def _is_re_entry_required(context: dict) -> bool:
    return _DIALOG_STATE_SERVICE.is_re_entry_required(_get_re_entry_required(context))


def _set_re_entry_required(context: dict, *, reason: str, now: datetime) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_re_entry_required(
        context,
        reason=reason,
        now=now,
        key=RE_ENTRY_REQUIRED_KEY,
    )


def _clear_re_entry_required(context: dict, *, reason: str, now: datetime) -> dict:

    return _DIALOG_STATE_SERVICE.clear_context_re_entry_required(
        context,
        reason=reason,
        now=now,
        key=RE_ENTRY_REQUIRED_KEY,
    )


def _set_expected_reply_context(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    context: dict,
    expected_reply_type: str | None,
    reason: str,
    now: datetime,
) -> dict:

    result = _DIALOG_STATE_SERVICE.build_expected_reply_context_sync_result(
        context,
        expected_reply_type=expected_reply_type,
        reason=reason,
        now=now,
        context_manager_key=CONTEXT_MANAGER_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        booking_key="booking",
        session_memory_key=SESSION_MEMORY_KEY,
        re_entry_required_key=RE_ENTRY_REQUIRED_KEY,
        service_carryover_key=SERVICE_CARRYOVER_KEY,
        consult_context_key=CONSULT_CONTEXT_KEY,
        session_memory_ttl_hours=SESSION_MEMORY_TTL_HOURS,
        service_default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
        consult_default_ttl=CONSULT_CONTEXT_TTL_MESSAGES,
    )
    context = result.context
    normalized_expected_reply_type = result.expected_reply_type
    normalized_reason = result.expected_reply_reason
    pending_question_contract = result.pending_question_contract
    _set_conversation_context(conversation, context)
    if result.re_entry_cleared:
        _record_decision_trace(
            conversation,
            {
                "stage": "re_entry",
                "decision": "cleared",
                "reason": normalized_reason,
            },
        )
    question_trace = {
        "stage": "question_contract",
        "decision": "set",
        "expected_reply_type": normalized_expected_reply_type,
        "reason": normalized_reason,
    }
    if pending_question_contract:
        question_trace["pending_question_contract"] = pending_question_contract
    _record_decision_trace(conversation, question_trace)
    if saved_message:
        meta_updates = {
            "expected_reply_type": normalized_expected_reply_type,
            "expected_reply_reason": normalized_reason,
        }
        if pending_question_contract:
            meta_updates["pending_question_contract"] = pending_question_contract
        _update_message_decision_metadata(saved_message, meta_updates)
    if normalized_expected_reply_type:
        _record_session_memory_update(
            conversation,
            saved_message,
            memory=result.question_memory or {},
            reason="question_set",
        )
    return context


def _get_context_manager(context: dict) -> dict:

    manager = context.get(CONTEXT_MANAGER_KEY) if isinstance(context, dict) else None
    if isinstance(manager, dict):
        return dict(manager)
    return {}


def _set_context_manager(context: dict, manager: dict) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_manager_payload(
        context,
        manager,
        key=CONTEXT_MANAGER_KEY,
    )


def _increment_context_message_count(manager: dict) -> int:
    updated, count = _DIALOG_STATE_SERVICE.increment_context_manager_message_count(manager)
    manager.clear()
    manager.update(updated)
    return count


def _prune_class_carryover(manager: dict, *, message_count: int) -> tuple[dict, dict | None]:

    return _DIALOG_STATE_SERVICE.prune_context_manager_class_carryover(
        manager,
        manager_key=CLASS_CARRYOVER_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        message_count=message_count,
        default_ttl=CLASS_CARRYOVER_TTL_MESSAGES,
    )


def _get_class_carryover(manager: dict, *, message_count: int) -> dict | None:

    canonical_state = manager.get(CANONICAL_DIALOG_STATE_KEY) if isinstance(manager, dict) else None
    if isinstance(canonical_state, dict):
        canonical_projection = _DIALOG_STATE_SERVICE.get_canonical_class_carryover(
            canonical_state,
            message_count=message_count,
        )
        if isinstance(canonical_projection, dict):
            return canonical_projection

    payload = manager.get(CLASS_CARRYOVER_KEY) if isinstance(manager, dict) else None
    return _DIALOG_STATE_SERVICE.get_class_carryover(payload, message_count=message_count)


def _set_class_carryover(
    manager: dict,
    *,
    class_name: str,
    intents: list[str],
    info_sections: list[str] | None,
    message_count: int,
) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_manager_class_carryover(
        manager,
        manager_key=CLASS_CARRYOVER_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        class_name=class_name,
        intents=intents,
        info_sections=info_sections,
        message_count=message_count,
        default_ttl=CLASS_CARRYOVER_TTL_MESSAGES,
        allowed_intents=INFO_INTENTS,
        normalize_class_name=_normalize_class_name,
    )


def _maybe_store_class_carryover(
    *,
    conversation: Conversation,
    class_name: str,
    intents: list[str] | None,
    info_meta: dict | None,
    message_count: int,
    reason: str,
) -> None:

    normalized_class = _normalize_class_name(class_name)
    if normalized_class not in CLASS_CARRYOVER_CLASSES:
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
        context_manager.get(CLASS_CARRYOVER_KEY)
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
            "ttl": CLASS_CARRYOVER_TTL_MESSAGES,
            "reason": reason,
        },
    )


def _prune_service_carryover(manager: dict, *, message_count: int) -> tuple[dict, dict | None]:

    return _DIALOG_STATE_SERVICE.prune_context_manager_service_carryover(
        manager,
        manager_key=SERVICE_CARRYOVER_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        referent_key="service",
        message_count=message_count,
        default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
        projection_source=CANONICAL_DIALOG_STATE_KEY,
    )


def _get_service_carryover(manager: dict, *, message_count: int) -> dict | None:

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

    payload = manager.get(SERVICE_CARRYOVER_KEY)
    return _DIALOG_STATE_SERVICE.get_service_carryover(
        payload,
        message_count=message_count,
        default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
    )


def _set_service_carryover(
    manager: dict,
    *,
    service_query: str,
    source: str | None,
    score: float | None,
    message_count: int,
) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_manager_service_carryover(
        manager,
        manager_key=SERVICE_CARRYOVER_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        referent_key="service",
        service_query=service_query,
        source=source,
        score=score,
        message_count=message_count,
        default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
        projection_source=CANONICAL_DIALOG_STATE_KEY,
        canonical_state_owner=CANONICAL_DIALOG_STATE_OWNER,
    )


def _maybe_store_service_carryover(
    *,
    conversation: Conversation,
    service_meta: dict | None,
    intent: str | None,
    message_count: int,
    reason: str,
) -> None:

    if not isinstance(service_meta, dict):
        return
    service_query = service_meta.get("service_query")
    if not isinstance(service_query, str) or not service_query.strip():
        return
    if intent and intent in SERVICE_CARRYOVER_SKIP_INTENTS:
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
            "ttl": SERVICE_CARRYOVER_TTL_MESSAGES,
            "projection_source": CANONICAL_DIALOG_STATE_KEY,
            "canonical_state_owner": CANONICAL_DIALOG_STATE_OWNER,
            "reason": reason,
        },
    )


def _prune_consult_context(manager: dict, *, message_count: int) -> tuple[dict, dict | None]:

    return _DIALOG_STATE_SERVICE.prune_context_manager_consult_context(
        manager,
        manager_key=CONSULT_CONTEXT_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        message_count=message_count,
        default_ttl=CONSULT_CONTEXT_TTL_MESSAGES,
    )


def _get_consult_context(manager: dict, *, message_count: int) -> dict | None:

    canonical_projection = _project_canonical_consult_state(
        manager,
        message_count=message_count,
    )
    if isinstance(canonical_projection, dict):
        return canonical_projection

    payload = manager.get(CONSULT_CONTEXT_KEY)
    return _DIALOG_STATE_SERVICE.get_consult_context(
        payload,
        message_count=message_count,
        default_ttl=CONSULT_CONTEXT_TTL_MESSAGES,
    )


def _set_consult_context(
    manager: dict,
    *,
    consult_meta: dict,
    message_count: int,
) -> dict:

    questions_raw = consult_meta.get("consult_questions") if isinstance(consult_meta, dict) else None
    questions = _DIALOG_STATE_SERVICE.normalize_consult_questions(
        questions_raw,
        transform=_ensure_question_mark,
    )
    topic = consult_meta.get("consult_topic") if isinstance(consult_meta, dict) else None
    topic_value = topic.strip() if isinstance(topic, str) and topic.strip() else None
    question = consult_meta.get("consult_question") if isinstance(consult_meta, dict) else None
    question_value = question.strip() if isinstance(question, str) and question.strip() else None
    return _DIALOG_STATE_SERVICE.set_context_manager_consult_context(
        manager,
        manager_key=CONSULT_CONTEXT_KEY,
        canonical_state_key=CANONICAL_DIALOG_STATE_KEY,
        topic=topic_value,
        question=question_value,
        questions=questions,
        message_count=message_count,
        default_ttl=CONSULT_CONTEXT_TTL_MESSAGES,
        projection_source=CANONICAL_DIALOG_STATE_KEY,
        canonical_state_owner=CANONICAL_DIALOG_STATE_OWNER,
    )


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
        return f"Если вернуться к вашему вопросу: {_ensure_question_mark(question)}"
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
    return _append_followup(bot_response, consult_return_prompt)


def _resolve_current_goal(
    intent_set: set[str],
    consult_intent: bool,
    expected_reply_type: str | None = None,
    expected_reply_reason: str | None = None,
) -> str | None:

    if consult_intent:
        return "consult"
    if expected_reply_type in {
        EXPECTED_REPLY_SERVICE,
        EXPECTED_REPLY_TIME,
        EXPECTED_REPLY_NAME,
    }:
        if expected_reply_reason and expected_reply_reason != "booking_prompt":
            return None
        return "booking"
    if "booking" in intent_set:
        return "booking"
    if intent_set & INFO_INTENTS:
        return "info"
    return None


def _build_compact_summary_text(
    *,
    booking: dict,
    refusal_flags: dict,
    language: str | None,
) -> str:

    return _DIALOG_STATE_SERVICE.build_compact_summary_text(
        booking=booking,
        refusal_flags=refusal_flags,
        language=language,
        is_refusal_flag_active=_is_refusal_flag_active,
    )


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

    language = _resolve_backlog_language(saved_message) if saved_message else "unknown"
    summary_text = _build_compact_summary_text(
        booking=booking,
        refusal_flags=refusal_flags,
        language=language,
    )
    manager = _DIALOG_STATE_SERVICE.set_compact_summary(
        manager,
        summary_text=summary_text,
        reason=reason,
        now=now,
    )
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
    return _DIALOG_STATE_SERVICE.get_low_confidence_retry_count(context)


def _set_low_confidence_retry_count(context: dict, count: int) -> dict:
    return _DIALOG_STATE_SERVICE.set_low_confidence_retry_count(context, count=count)


def _reset_low_confidence_retry(conversation: Conversation) -> None:
    context = _get_conversation_context(conversation)
    context, changed = _DIALOG_STATE_SERVICE.reset_low_confidence_retry_count(context)
    if changed:
        _set_conversation_context(conversation, context)
    conversation.retry_offered_at = None


def _get_handover_confirmation(context: dict) -> dict | None:
    confirmation = context.get("handover_confirmation") if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.normalize_handover_confirmation(confirmation)


def _set_handover_confirmation(context: dict, confirmation: dict | None) -> dict:
    return _DIALOG_STATE_SERVICE.set_context_handover_confirmation(context, confirmation)


def _is_handover_confirmation_active(confirmation: dict, now: datetime) -> bool:

    return _DIALOG_STATE_SERVICE.is_confirmation_active(
        confirmation,
        now=now,
        ttl_minutes=HANDOVER_CONFIRM_WINDOW_MINUTES,
    )


def _get_reengage_confirmation(context: dict) -> dict | None:

    confirmation = context.get(REENGAGE_CONFIRM_KEY) if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.normalize_reengage_confirmation(confirmation)


def _set_reengage_confirmation(context: dict, confirmation: dict | None) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_reengage_confirmation(
        context,
        confirmation,
        key=REENGAGE_CONFIRM_KEY,
    )


def _is_reengage_confirmation_active(confirmation: dict, now: datetime) -> bool:

    return _DIALOG_STATE_SERVICE.is_confirmation_active(
        confirmation,
        now=now,
        ttl_minutes=REENGAGE_CONFIRM_WINDOW_MINUTES,
    )


def _get_asr_confirmation(context: dict) -> dict | None:

    confirmation = context.get(ASR_CONFIRM_KEY) if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.normalize_asr_confirmation(confirmation)


def _set_asr_confirmation(context: dict, confirmation: dict | None) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_asr_confirmation(
        context,
        confirmation,
        key=ASR_CONFIRM_KEY,
    )


def _is_asr_confirmation_active(confirmation: dict, now: datetime) -> bool:

    return _DIALOG_STATE_SERVICE.is_confirmation_active(
        confirmation,
        now=now,
        ttl_minutes=ASR_CONFIRM_WINDOW_MINUTES,
    )


def _get_asr_inflight(context: dict, *, now: datetime) -> tuple[dict | None, bool]:

    payload = context.get(ASR_INFLIGHT_KEY) if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.get_asr_inflight(payload, now=now)


def _set_asr_inflight(context: dict, payload: dict | None) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_asr_inflight(
        context,
        payload,
        key=ASR_INFLIGHT_KEY,
    )


def _get_style_reference_pending(context: dict, *, now: datetime) -> tuple[dict | None, bool]:

    payload = context.get(STYLE_REFERENCE_PENDING_KEY) if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.get_style_reference_pending(payload, now=now)


def _set_style_reference_pending(context: dict, payload: dict | None) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_style_reference_pending(
        context,
        payload,
        key=STYLE_REFERENCE_PENDING_KEY,
    )


def _normalize_memory_profile(profile: dict | None, *, now: datetime) -> tuple[dict, bool]:

    return _DIALOG_STATE_SERVICE.normalize_memory_profile(
        profile,
        now=now,
        default_ttl_days=MEMORY_PROFILE_TTL_DAYS,
    )


def _get_memory_profile(context: dict, *, now: datetime) -> tuple[dict, bool]:

    payload = context.get(MEMORY_PROFILE_KEY) if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.get_memory_profile(
        payload,
        now=now,
        default_ttl_days=MEMORY_PROFILE_TTL_DAYS,
    )


def _set_memory_profile(context: dict, profile: dict | None) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_memory_profile(
        context,
        profile,
        key=MEMORY_PROFILE_KEY,
    )


def _get_memory_pending(context: dict, *, now: datetime) -> tuple[dict | None, bool]:

    pending = context.get(MEMORY_PENDING_KEY) if isinstance(context, dict) else None
    return _DIALOG_STATE_SERVICE.get_memory_pending(pending, now=now)


def _set_memory_pending(context: dict, pending: dict | None) -> dict:

    return _DIALOG_STATE_SERVICE.set_context_memory_pending(
        context,
        pending,
        key=MEMORY_PENDING_KEY,
    )


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
