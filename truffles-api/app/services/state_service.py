import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Conversation, Handover, Message, User
from app.services.handover_context_service import (
    build_handover_context_summary,
    build_handover_messages,
    get_recent_conversation_messages,
)
from app.services.runtime_mode_service import is_local_eval_mode
from app.services.state_machine import ConversationState, is_transition_allowed

logger = get_logger("state_service")


def _dialog_state_service():
    from app.core.dialog_state_service import DialogStateService

    return DialogStateService()


@dataclass(frozen=True)
class PendingResumeBoundaryRestore:
    context: dict[str, Any]
    restored: bool
    pending_reason: str | None = None
    expected_reply_type: str | None = None
    boundary_payload: dict[str, Any] | None = None
    apply_boundary_booking_state: bool = False


@dataclass(frozen=True)
class PendingResumeBoundaryRuntimeHooks:
    set_booking_context: Callable[..., dict[str, Any]]
    set_expected_reply_context: Callable[..., dict[str, Any]]
    set_conversation_context: Callable[..., None]
    record_decision_trace: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]


@dataclass(frozen=True)
class PendingResumeBoundaryActivation:
    context: dict[str, Any]
    boundary_payload: dict[str, Any] | None
    boundary_active: bool
    boundary_restored: bool


@dataclass(frozen=True)
class ResolvedHandoffResumeBoundaryResult:
    context: dict[str, Any]
    restored: bool


@dataclass(frozen=True)
class PendingResumeSessionMemoryPolicy:
    preserve_session_memory: bool = False
    reset_reason: str | None = None
    trace_payload: dict[str, Any] | None = None
    decision_meta_updates: dict[str, Any] | None = None


@dataclass(frozen=True)
class ContinuityTransportDecision:
    handled: bool
    bot_response: str | None = None
    success_message: str | None = None
    failure_message: str | None = None


@dataclass(frozen=True)
class PendingContinuityRuntimeHooks:
    get_conversation_context: Callable[..., dict[str, Any]]
    set_conversation_context: Callable[..., None]
    transition_state: Callable[..., Any]
    manager_resolve: Callable[..., Any]
    record_decision_trace: Callable[..., None]
    update_message_decision_metadata: Callable[..., None]


@dataclass(frozen=True)
class HandoverConfirmationRuntimeHooks:
    get_conversation_context: Callable[..., dict[str, Any]]
    get_handover_confirmation: Callable[..., dict[str, Any] | None]
    is_handover_confirmation_active: Callable[..., bool]
    set_handover_confirmation: Callable[..., dict[str, Any]]
    set_conversation_context: Callable[..., None]
    reset_low_confidence_retry: Callable[..., None]
    classify_confirmation: Callable[..., str | None]
    reuse_active_handover: Callable[..., tuple[Any, bool, bool]]
    escalate_to_pending: Callable[..., Any]
    send_telegram_notification: Callable[..., bool]
    record_escalation_metric: Callable[..., None]
    record_decision_trace: Callable[..., None]
    msg_escalated: str
    msg_ai_error: str
    msg_handover_declined: str


@dataclass(frozen=True)
class SessionMemoryRuntimeHooks:
    set_context_manager: Callable[..., dict[str, Any]]
    set_expected_reply_type: Callable[..., dict[str, Any]]
    set_intent_queue: Callable[..., dict[str, Any]]
    set_booking_context: Callable[..., dict[str, Any]]
    clear_service_hint: Callable[..., dict[str, Any]]


PENDING_RESUME_KEY = "pending_resume"
DECISION_TRACE_KEY = "decision_trace"
SIMULATION_CONTEXT_KEY = "simulation"
PENDING_SLA_CONTEXT_KEY = "pending_sla"
HANDOVER_CONFIRMATION_KEY = "handover_confirmation"
RE_ENTRY_REQUIRED_KEY = "re_entry_required"
PENDING_RESUME_SNAPSHOT_KEYS = {
    "context_manager",
    "expected_reply_type",
    "expected_reply_reason",
    "intent_queue",
    "booking",
    "session_memory",
    "last_service_hint",
    "last_service_hint_at",
}
PENDING_RESUME_CLEAR_KEYS = {
    "context_manager",
    "expected_reply_type",
    "expected_reply_reason",
    "intent_queue",
    "booking",
    "session_memory",
    "last_service_hint",
    "last_service_hint_at",
}
HANDOVER_MEDIA_LOOKBACK_LIMIT = 12
HANDOVER_MEDIA_HISTORY_WINDOW = timedelta(minutes=30)


def _normalize_slot_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _build_session_memory_observability_snapshot(
    memory: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_memory, _ = _dialog_state_service().normalize_session_memory_payload(memory)
    explicit_pending_question_contract = _dialog_state_service().project_pending_question_contract(
        memory.get("pending_question_contract")
        if isinstance(memory, dict)
        else None
    )
    pending_slots = normalized_memory.get("pending_slots")
    if isinstance(pending_slots, dict):
        pending_keys = sorted(
            key for key in pending_slots.keys() if isinstance(key, str) and key.strip()
        )
    else:
        pending_keys = []
    goal_stack = normalized_memory.get("goal_stack")
    if isinstance(goal_stack, list):
        cleaned_goals = [item for item in goal_stack if isinstance(item, str) and item.strip()]
    else:
        cleaned_goals = []
    unanswered = normalized_memory.get("unanswered_questions")
    if isinstance(unanswered, list):
        unanswered_count = len([item for item in unanswered if isinstance(item, str) and item.strip()])
    else:
        unanswered_count = 0
    interaction_state = normalized_memory.get("interaction_state")
    interaction_resume_slot = None
    interaction_owner = None
    if isinstance(interaction_state, dict):
        raw_resume_slot = interaction_state.get("resume_slot")
        if isinstance(raw_resume_slot, str) and raw_resume_slot.strip():
            interaction_resume_slot = raw_resume_slot.strip()
        raw_interaction_owner = interaction_state.get("interaction_owner")
        if isinstance(raw_interaction_owner, str) and raw_interaction_owner.strip():
            interaction_owner = raw_interaction_owner.strip()
    snapshot = {
        "active_goal": normalized_memory.get("active_goal"),
        "goal_stack_depth": len(cleaned_goals),
        "goal_stack_top": cleaned_goals[-1] if cleaned_goals else None,
        "pending_slots": pending_keys,
        "unanswered_questions_count": unanswered_count,
        "interaction_resume_slot": interaction_resume_slot,
        "interaction_owner": interaction_owner,
    }
    if explicit_pending_question_contract is not None:
        snapshot["pending_question_contract"] = explicit_pending_question_contract
    else:
        last_question_type = _dialog_state_service().project_expected_reply_projections(
            expected_reply_type=(
                memory.get("last_question_type")
                if isinstance(memory, dict)
                else None
            ),
            expected_reply_reason=None,
        ).expected_reply_type
        if last_question_type is not None:
            snapshot["last_question_type"] = last_question_type
    return snapshot


def _get_pending_sla(context: dict | None) -> dict[str, Any]:
    payload = context.get(PENDING_SLA_CONTEXT_KEY) if isinstance(context, dict) else None
    return dict(payload) if isinstance(payload, dict) else {}


def _set_pending_sla(context: dict | None, payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(context) if isinstance(context, dict) else {}
    updated[PENDING_SLA_CONTEXT_KEY] = dict(payload) if isinstance(payload, dict) else {}
    return updated


def _get_pending_resume(context: dict | None) -> dict[str, Any] | None:
    payload = context.get(PENDING_RESUME_KEY) if isinstance(context, dict) else None
    return dict(payload) if isinstance(payload, dict) else None


def _set_pending_resume(
    context: dict | None,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(context) if isinstance(context, dict) else {}
    if payload:
        updated[PENDING_RESUME_KEY] = dict(payload)
    else:
        updated.pop(PENDING_RESUME_KEY, None)
    return updated


def _normalize_media_ref(
    raw_media: dict | None,
    *,
    source: str,
    inbound_message_id: str | None = None,
) -> dict | None:
    if not isinstance(raw_media, dict):
        return None

    ref: dict[str, object] = {"source": source}
    for key in (
        "media_type",
        "raw_type",
        "mime",
        "url",
        "file_name",
        "caption",
        "storage_path",
        "public_url",
        "expires_at",
        "sha256",
    ):
        value = _normalize_slot_value(raw_media.get(key))
        if value:
            ref[key] = value

    if "media_type" not in ref:
        media_type = _normalize_slot_value(raw_media.get("type"))
        if media_type:
            ref["media_type"] = media_type

    size_bytes = raw_media.get("size_bytes")
    if isinstance(size_bytes, int) and size_bytes >= 0:
        ref["size_bytes"] = size_bytes
    duration_seconds = raw_media.get("duration_seconds")
    if isinstance(duration_seconds, int) and duration_seconds >= 0:
        ref["duration_seconds"] = duration_seconds
    if isinstance(raw_media.get("ptt"), bool):
        ref["ptt"] = raw_media["ptt"]
    if isinstance(raw_media.get("forwarded_to_telegram"), bool):
        ref["forwarded_to_telegram"] = raw_media["forwarded_to_telegram"]
    if inbound_message_id:
        ref["inbound_message_id"] = inbound_message_id

    # Require at least one concrete media locator to avoid empty contracts.
    if not any(ref.get(locator_key) for locator_key in ("storage_path", "public_url", "url")):
        return None
    return ref


def _media_ref_fingerprint(ref: dict) -> tuple[str | None, ...]:
    return (
        ref.get("sha256"),
        ref.get("storage_path"),
        ref.get("public_url"),
        ref.get("url"),
        ref.get("media_type"),
        ref.get("inbound_message_id"),
    )


def _extract_handover_media_refs(
    conversation: Conversation,
    message: Message | None,
    *,
    recent_messages: list[Message] | None = None,
) -> tuple[list[dict], bool]:
    refs: list[dict] = []
    required = False
    reference_time = datetime.now(timezone.utc)
    trigger_created_at = getattr(message, "created_at", None) if message is not None else None
    if isinstance(trigger_created_at, datetime):
        if trigger_created_at.tzinfo is None:
            trigger_created_at = trigger_created_at.replace(tzinfo=timezone.utc)
        reference_time = trigger_created_at

    message_meta = message.message_metadata if message and isinstance(message.message_metadata, dict) else {}
    message_media = message_meta.get("media") if isinstance(message_meta, dict) else None
    if isinstance(message_media, dict):
        required = True
        inbound_message_id = _normalize_slot_value(getattr(message, "message_id", None))
        media_ref = _normalize_media_ref(
            message_media,
            source="message_metadata",
            inbound_message_id=inbound_message_id,
        )
        if media_ref:
            refs.append(media_ref)

    context = conversation.context if isinstance(conversation.context, dict) else {}
    pending_style = context.get("style_reference_pending") if isinstance(context, dict) else None
    if isinstance(pending_style, dict):
        pending_media = pending_style.get("media")
        if isinstance(pending_media, dict):
            required = True
            pending_payload = dict(pending_media)
            for key in ("storage_path", "public_url", "sha256"):
                if key in pending_style and key not in pending_payload:
                    pending_payload[key] = pending_style.get(key)
            if "expires_at" not in pending_payload:
                media_expires_at = (
                    pending_style.get("public_url_expires_at")
                    or pending_style.get("media_expires_at")
                    or pending_style.get("expires_at")
                )
                if media_expires_at:
                    pending_payload["expires_at"] = media_expires_at
            media_ref = _normalize_media_ref(
                pending_payload,
                source="style_reference_pending",
            )
            if media_ref:
                refs.append(media_ref)

    for recent_message in recent_messages or []:
        if recent_message is None:
            continue
        created_at = getattr(recent_message, "created_at", None)
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if reference_time - created_at > HANDOVER_MEDIA_HISTORY_WINDOW:
                continue
        if message is not None and getattr(recent_message, "id", None) == getattr(message, "id", None):
            continue
        recent_meta = (
            recent_message.message_metadata
            if isinstance(recent_message.message_metadata, dict)
            else {}
        )
        recent_media = recent_meta.get("media") if isinstance(recent_meta, dict) else None
        if not isinstance(recent_media, dict):
            continue
        required = True
        recent_inbound_id = _normalize_slot_value(getattr(recent_message, "message_id", None))
        media_ref = _normalize_media_ref(
            recent_media,
            source="recent_message_history",
            inbound_message_id=recent_inbound_id,
        )
        if media_ref:
            refs.append(media_ref)
    deduped: list[dict] = []
    seen: set[tuple[str | None, ...]] = set()
    for ref in refs:
        fingerprint = _media_ref_fingerprint(ref)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduped.append(ref)

    return deduped, required


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _simulation_allowlist() -> set[str]:
    raw = os.environ.get("SIMULATION_ALLOWLIST_JIDS") or os.environ.get("OUTBOUND_ALLOWLIST_JIDS") or ""
    return {item.strip() for item in raw.split(",") if item.strip()}


def _is_simulation_allowed(metadata, *, allow_internal_source: bool = False) -> bool:
    if is_local_eval_mode(os.environ):
        return True
    if allow_internal_source:
        return True
    if metadata is None:
        return False
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return False
    return remote_jid.strip() in _simulation_allowlist()


def _clear_simulation_context(context: dict) -> dict:
    updated = dict(context)
    updated.pop(SIMULATION_CONTEXT_KEY, None)
    for key in ("simulation_mode", "simulation_id", "simulation_llm", "simulation_time"):
        updated.pop(key, None)
    return updated


def _extract_decision_meta(message: Message | None) -> dict:
    if not message or not isinstance(message.message_metadata, dict):
        return {}
    decision_meta = message.message_metadata.get("decision_meta")
    return decision_meta if isinstance(decision_meta, dict) else {}


def _reset_context_preserving_trace(conversation: Conversation) -> None:
    existing = conversation.context if isinstance(conversation.context, dict) else {}
    preserved: dict = {}
    if DECISION_TRACE_KEY in existing:
        preserved[DECISION_TRACE_KEY] = existing.get(DECISION_TRACE_KEY)
    if SIMULATION_CONTEXT_KEY in existing:
        preserved[SIMULATION_CONTEXT_KEY] = existing.get(SIMULATION_CONTEXT_KEY)
    if "memory_profile" in existing:
        preserved["memory_profile"] = existing.get("memory_profile")
    if "memory_pending" in existing:
        preserved["memory_pending"] = existing.get("memory_pending")
    conversation.context = preserved or {}


def _extract_simulation_meta(metadata) -> dict | None:
    if not metadata:
        return None
    sim_mode = getattr(metadata, "simulation_mode", None)
    sim_id = getattr(metadata, "simulation_id", None)
    sim_llm = getattr(metadata, "simulation_llm", None)
    sim_time = getattr(metadata, "simulation_time", None)
    if sim_mode is None and sim_id is None and sim_llm is None and sim_time is None:
        return None
    if sim_mode is None:
        sim_mode = True
    payload = {"mode": bool(sim_mode), "id": sim_id}
    if sim_llm is not None:
        payload["llm_allowed"] = bool(sim_llm)
    if sim_time is not None:
        payload["time"] = sim_time
    return payload


def build_simulation_context(metadata) -> dict | None:
    return _extract_simulation_meta(metadata)


def _get_simulation_context(value) -> dict | None:
    if hasattr(value, "context"):
        context = value.context
    else:
        context = value
    if not isinstance(context, dict):
        return None
    sim_context = context.get(SIMULATION_CONTEXT_KEY)
    if isinstance(sim_context, dict):
        if sim_context.get("mode") is None:
            sim_context = dict(sim_context)
            sim_context["mode"] = True
        if sim_context.get("time") is None and sim_context.get("simulation_time") is not None:
            sim_context = dict(sim_context)
            sim_context["time"] = sim_context.get("simulation_time")
        return sim_context
    sim_mode = context.get("simulation_mode")
    sim_id = context.get("simulation_id")
    sim_llm = context.get("simulation_llm")
    sim_time = context.get("simulation_time")
    if sim_mode is None and sim_id is None and sim_llm is None and sim_time is None:
        return None
    if sim_mode is None:
        sim_mode = True
    payload = {"mode": bool(sim_mode), "id": sim_id}
    if sim_llm is not None:
        payload["llm_allowed"] = bool(sim_llm)
    if sim_time is not None:
        payload["time"] = sim_time
    return payload


def apply_simulation_context(
    conversation: Conversation,
    metadata,
    *,
    allow_internal_source: bool = False,
) -> dict | None:
    context = conversation.context if isinstance(conversation.context, dict) else {}
    sim_meta = _extract_simulation_meta(metadata)
    if not sim_meta:
        if context.get(SIMULATION_CONTEXT_KEY) and not _is_simulation_allowed(
            metadata,
            allow_internal_source=allow_internal_source,
        ):
            conversation.context = _clear_simulation_context(context)
        return None
    if not _is_simulation_allowed(metadata, allow_internal_source=allow_internal_source):
        if context.get(SIMULATION_CONTEXT_KEY):
            conversation.context = _clear_simulation_context(context)
        logger.warning(
            "Simulation metadata ignored for non-test traffic",
            extra={
                "context": {
                    "conversation_id": str(conversation.id),
                    "remote_jid": getattr(metadata, "remoteJid", None),
                }
            },
        )
        return None
    updated = dict(context)
    sim_context = dict(updated.get(SIMULATION_CONTEXT_KEY) or {})
    if sim_meta.get("id") and not sim_context.get("id"):
        sim_context["id"] = sim_meta["id"]
    if "mode" in sim_meta:
        sim_context["mode"] = sim_meta["mode"]
    if "llm_allowed" in sim_meta:
        sim_context["llm_allowed"] = sim_meta["llm_allowed"]
    if "time" in sim_meta:
        sim_context["time"] = sim_meta["time"]
    sim_context.setdefault("source", "webhook_metadata")
    sim_context["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated[SIMULATION_CONTEXT_KEY] = sim_context
    conversation.context = updated
    return sim_context


def is_simulation_context(value) -> bool:
    sim_context = _get_simulation_context(value)
    if not sim_context:
        return False
    if sim_context.get("mode") is not None:
        return bool(sim_context.get("mode"))
    return True


def _parse_simulation_time(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def get_simulation_time(value) -> datetime | None:
    sim_context = _get_simulation_context(value)
    if not sim_context:
        return None
    return _parse_simulation_time(sim_context.get("time") or sim_context.get("simulation_time"))


def _capture_pending_resume_context(context: dict | None) -> dict:
    if not isinstance(context, dict):
        return {}
    if PENDING_RESUME_KEY in context:
        return context
    resume_payload = _dialog_state_service().capture_pending_resume_payload(
        context,
        snapshot_keys=PENDING_RESUME_SNAPSHOT_KEYS,
    )
    if not resume_payload:
        return context
    updated = dict(context)
    updated[PENDING_RESUME_KEY] = resume_payload
    for key in PENDING_RESUME_CLEAR_KEYS:
        updated.pop(key, None)
    return updated


def _restore_pending_resume_context(context: dict | None, *, now: datetime) -> tuple[dict, bool]:
    if not isinstance(context, dict):
        return {}, False
    pending_resume = context.get(PENDING_RESUME_KEY)
    if not isinstance(pending_resume, dict):
        return context, False

    restored = dict(context)
    restored.pop(PENDING_RESUME_KEY, None)
    restored.pop(PENDING_SLA_CONTEXT_KEY, None)
    restored.pop(HANDOVER_CONFIRMATION_KEY, None)
    for key in PENDING_RESUME_CLEAR_KEYS:
        restored.pop(key, None)
    restored.update(_dialog_state_service().restore_pending_resume_payload(pending_resume, now=now))
    return restored, True


def capture_pending_resume_on_conversation(conversation: Conversation) -> bool:
    original_context = (
        dict(conversation.context)
        if isinstance(conversation.context, dict)
        else conversation.context
    )
    captured_context = _capture_pending_resume_context(conversation.context)
    if not isinstance(captured_context, dict):
        captured_context = {}
    if captured_context == original_context:
        return False
    conversation.context = captured_context
    return True


def sync_pending_resume_on_handover_reuse(conversation: Conversation) -> bool:
    original_context = (
        dict(conversation.context)
        if isinstance(conversation.context, dict)
        else conversation.context
    )
    captured_context = _capture_pending_resume_context(conversation.context)
    if not isinstance(captured_context, dict):
        captured_context = {}
    if PENDING_RESUME_KEY in captured_context:
        normalized_context = dict(captured_context)
        for key in PENDING_RESUME_CLEAR_KEYS:
            normalized_context.pop(key, None)
    else:
        normalized_context = captured_context
    if normalized_context == original_context:
        return False
    conversation.context = normalized_context
    return True


def restore_pending_resume_on_conversation(
    conversation: Conversation,
    *,
    now: datetime,
) -> bool:
    restored_context, restored = _restore_pending_resume_context(conversation.context, now=now)
    if restored:
        conversation.context = restored_context
    return restored


def _build_pending_resume_snapshot_payload(
    *,
    context: dict | None,
    context_manager: dict,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    intent_queue: list[str] | None,
    booking_context: dict | None,
    session_memory: dict,
) -> dict[str, Any]:
    snapshot_context = dict(context) if isinstance(context, dict) else {}
    snapshot_context["context_manager"] = (
        dict(context_manager) if isinstance(context_manager, dict) else {}
    )
    snapshot_context["expected_reply_type"] = expected_reply_type
    snapshot_context["expected_reply_reason"] = expected_reply_reason
    snapshot_context["intent_queue"] = list(intent_queue) if isinstance(intent_queue, list) else []
    snapshot_context["booking"] = (
        dict(booking_context) if isinstance(booking_context, dict) else {"active": False}
    )
    snapshot_context["session_memory"] = dict(session_memory) if isinstance(session_memory, dict) else {}
    return _dialog_state_service().capture_pending_resume_payload(
        snapshot_context,
        snapshot_keys=PENDING_RESUME_SNAPSHOT_KEYS,
    )


def _restore_pending_resume_payload(
    *,
    context: dict | None,
    pending_resume: dict | None,
    now: datetime,
) -> dict[str, Any]:
    working_context = dict(context) if isinstance(context, dict) else {}
    if not isinstance(pending_resume, dict):
        return working_context
    working_context[PENDING_RESUME_KEY] = dict(pending_resume)
    restored_context, restored = _restore_pending_resume_context(working_context, now=now)
    if restored:
        return restored_context
    return working_context


def _derive_pending_resume_reason(context: dict | None) -> str | None:
    return _dialog_state_service().derive_pending_resume_reason(
        context,
        pending_resume_key=PENDING_RESUME_KEY,
    )


def _derive_pending_booking_resume_boundary_payload(
    context: dict | None,
    *,
    now: datetime | None = None,
    prompt_builder: Callable[[str | None], str | None] | None = None,
) -> dict[str, Any] | None:
    return _dialog_state_service().derive_pending_booking_resume_boundary_payload(
        context,
        now=now,
        prompt_builder=prompt_builder,
        pending_resume_key=PENDING_RESUME_KEY,
    )


def _prepare_pending_handoff_resume_boundary_restore(
    context: dict | None,
    *,
    now: datetime,
    prompt_builder: Callable[[str | None], str | None] | None = None,
) -> PendingResumeBoundaryRestore:
    if not isinstance(context, dict):
        return PendingResumeBoundaryRestore(context={}, restored=False)

    restored_context, restored = _restore_pending_resume_context(context, now=now)
    if not restored:
        return PendingResumeBoundaryRestore(context=context, restored=False)

    pending_question_contract = _dialog_state_service().project_context_pending_question_contract(
        restored_context
    )
    boundary_payload = _derive_pending_booking_resume_boundary_payload(
        restored_context,
        now=now,
        prompt_builder=prompt_builder,
    )
    expected_reply_type = (
        pending_question_contract.get("expected_reply_type")
        if isinstance(pending_question_contract, dict)
        else None
    )
    apply_boundary_booking_state = False
    if not expected_reply_type and boundary_payload is not None:
        expected_reply_type = boundary_payload.get("expected_reply_type")
        apply_boundary_booking_state = True

    return PendingResumeBoundaryRestore(
        context=restored_context,
        restored=True,
        pending_reason=_derive_pending_resume_reason(restored_context),
        expected_reply_type=expected_reply_type,
        boundary_payload=boundary_payload,
        apply_boundary_booking_state=apply_boundary_booking_state,
    )


def _prepare_resolved_handoff_resume_boundary_restore(
    context: dict | None,
    *,
    now: datetime,
    prompt_builder: Callable[[str | None], str | None] | None = None,
) -> PendingResumeBoundaryRestore:
    if not isinstance(context, dict):
        return PendingResumeBoundaryRestore(context={}, restored=False)
    if not _dialog_state_service().is_re_entry_required(context.get(RE_ENTRY_REQUIRED_KEY)):
        return PendingResumeBoundaryRestore(context=context, restored=False)

    pending_question_contract = _dialog_state_service().project_context_pending_question_contract(
        context
    )
    canonical_expected_reply_type = (
        pending_question_contract.get("expected_reply_type")
        if isinstance(pending_question_contract, dict)
        else None
    )
    canonical_reason = (
        pending_question_contract.get("reason")
        if isinstance(pending_question_contract, dict)
        else None
    )

    boundary_payload = _derive_pending_booking_resume_boundary_payload(
        context,
        now=now,
        prompt_builder=prompt_builder,
    )
    expected_reply_type = canonical_expected_reply_type or (
        boundary_payload.get("expected_reply_type")
        if isinstance(boundary_payload, dict)
        else None
    )
    pending_reason = canonical_reason or _derive_pending_resume_reason(context)
    if not (
        isinstance(expected_reply_type, str)
        and expected_reply_type.strip()
        and isinstance(pending_reason, str)
        and pending_reason.strip()
    ):
        return PendingResumeBoundaryRestore(context=context, restored=False)

    return PendingResumeBoundaryRestore(
        context=context,
        restored=True,
        pending_reason=pending_reason.strip(),
        expected_reply_type=expected_reply_type.strip(),
        boundary_payload=boundary_payload,
        apply_boundary_booking_state=boundary_payload is not None,
    )


def _resolve_resolved_handoff_resume_boundary_restore(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    context: dict | None,
    conversation_state: str | None,
    now: datetime,
    prompt_builder: Callable[[str | None], str | None] | None = None,
    hooks: PendingResumeBoundaryRuntimeHooks,
) -> ResolvedHandoffResumeBoundaryResult:
    working_context = context if isinstance(context, dict) else {}
    if conversation_state != ConversationState.BOT_ACTIVE.value:
        return ResolvedHandoffResumeBoundaryResult(context=working_context, restored=False)

    restore = _prepare_resolved_handoff_resume_boundary_restore(
        working_context,
        now=now,
        prompt_builder=prompt_builder,
    )
    if not restore.restored:
        return ResolvedHandoffResumeBoundaryResult(context=working_context, restored=False)

    restored_context = restore.context
    if restore.apply_boundary_booking_state and restore.boundary_payload is not None:
        restored_context = hooks.set_booking_context(
            restored_context,
            restore.boundary_payload.get("booking_state"),
        )
    restored_context = hooks.set_expected_reply_context(
        conversation=conversation,
        saved_message=saved_message,
        context=restored_context,
        expected_reply_type=restore.expected_reply_type.strip(),
        reason=restore.pending_reason.strip(),
        now=now,
    )
    hooks.record_decision_trace(
        conversation,
        {
            "stage": "pending_resume",
            "decision": "restore_resolved_handoff_boundary",
            "reason": "resolved_handoff_resume_boundary",
        },
    )
    if saved_message:
        hooks.update_message_decision_metadata(
            saved_message,
            {
                "pending_resume_restored": True,
                "pending_resume_restore_reason": "resolved_handoff_resume_boundary",
                "resolved_handoff_resume_boundary": True,
            },
        )
    return ResolvedHandoffResumeBoundaryResult(
        context=restored_context,
        restored=True,
    )


def _resolve_pending_resume_boundary_activation(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    context: dict | None,
    conversation_state: str | None,
    message_text: str | None,
    now: datetime,
    prompt_builder: Callable[[str | None], str | None] | None = None,
    is_handover_status_question: Callable[[str], bool] | None = None,
    is_opt_out_message: Callable[[str], bool] | None = None,
    hooks: PendingResumeBoundaryRuntimeHooks,
) -> PendingResumeBoundaryActivation:
    working_context = dict(context) if isinstance(context, dict) else {}
    pending_resume_control_message = bool(
        message_text
        and (
            callable(is_handover_status_question)
            and is_handover_status_question(message_text)
            or callable(is_opt_out_message)
            and is_opt_out_message(message_text)
        )
    )
    boundary_payload = _derive_pending_booking_resume_boundary_payload(
        working_context,
        now=now,
        prompt_builder=prompt_builder,
    )
    boundary_active = bool(
        conversation_state == ConversationState.PENDING.value
        and not pending_resume_control_message
        and boundary_payload is not None
    )
    boundary_restored = False
    if boundary_active and isinstance(working_context.get(PENDING_RESUME_KEY), dict):
        restore = _prepare_pending_handoff_resume_boundary_restore(
            working_context,
            now=now,
            prompt_builder=prompt_builder,
        )
        working_context = restore.context
        if restore.restored:
            boundary_restored = True
            if restore.apply_boundary_booking_state and restore.boundary_payload is not None:
                working_context = hooks.set_booking_context(
                    working_context,
                    restore.boundary_payload.get("booking_state"),
                )
            pending_reason = restore.pending_reason
            pending_expected_reply_type = restore.expected_reply_type
            if (
                pending_expected_reply_type
                and isinstance(pending_reason, str)
                and pending_reason.strip()
            ):
                working_context = hooks.set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=working_context,
                    expected_reply_type=pending_expected_reply_type,
                    reason=pending_reason.strip(),
                    now=now,
                )
            else:
                hooks.set_conversation_context(conversation, working_context)
            hooks.record_decision_trace(
                conversation,
                {
                    "stage": "pending_resume",
                    "decision": "restore_soft_pass",
                    "reason": "handover_soft_pass",
                },
            )
            if saved_message:
                hooks.update_message_decision_metadata(
                    saved_message,
                    {
                        "pending_resume_restored": True,
                        "pending_resume_restore_reason": "handover_soft_pass",
                    },
                )
        boundary_payload = _derive_pending_booking_resume_boundary_payload(
            working_context,
            now=now,
            prompt_builder=prompt_builder,
        )
        boundary_active = boundary_payload is not None
    return PendingResumeBoundaryActivation(
        context=working_context,
        boundary_payload=boundary_payload,
        boundary_active=boundary_active,
        boundary_restored=boundary_restored,
    )


def _resolve_pending_resume_session_memory_policy(
    *,
    conversation_state: str | None,
    resume_boundary_active: bool,
    boundary_restored: bool,
) -> PendingResumeSessionMemoryPolicy:
    if conversation_state not in {
        ConversationState.PENDING.value,
        ConversationState.MANAGER_ACTIVE.value,
    }:
        return PendingResumeSessionMemoryPolicy()
    if resume_boundary_active:
        return PendingResumeSessionMemoryPolicy(
            preserve_session_memory=True,
            trace_payload={
                "stage": "session_memory",
                "decision": "preserve",
                "reason": "pending_handoff_resume_boundary",
                "state": conversation_state,
                "restored_from_pending_resume": boundary_restored,
            },
            decision_meta_updates={
                "session_memory_reset_skipped": "pending_handoff_resume_boundary",
                "pending_handoff_resume_boundary": True,
            },
        )
    return PendingResumeSessionMemoryPolicy(reset_reason="handover")


def _resolve_pending_timeout_resume_boundary_payload(
    context: dict | None,
    *,
    conversation_state: str | None,
    policy_core_timeout_degrade: bool,
    resume_boundary_active: bool,
    now: datetime,
    prompt_builder: Callable[[str | None], str | None] | None = None,
    required_expected_reply_type: str | None = None,
) -> dict[str, Any] | None:
    if (
        conversation_state != ConversationState.PENDING.value
        or not policy_core_timeout_degrade
        or not resume_boundary_active
    ):
        return None
    boundary_payload = _derive_pending_booking_resume_boundary_payload(
        context,
        now=now,
        prompt_builder=prompt_builder,
    )
    if not isinstance(boundary_payload, dict):
        return None
    if (
        isinstance(required_expected_reply_type, str)
        and required_expected_reply_type.strip()
        and boundary_payload.get("expected_reply_type") != required_expected_reply_type
    ):
        return None
    return boundary_payload


def _should_reset_session_memory_trigger(
    message_text: str | None,
    *,
    normalize_text: Callable[[str], str | None],
    reset_phrases: list[str] | set[str] | tuple[str, ...],
) -> bool:
    if not message_text:
        return False
    normalized = normalize_text(message_text)
    if not normalized:
        return False
    return any(phrase in normalized for phrase in reset_phrases)


def _reset_session_memory_context(
    *,
    context: dict,
    context_manager: dict,
    reason: str,
    now: datetime,
    session_memory_ttl_hours: int,
    class_manager_key: str,
    service_manager_key: str,
    consult_manager_key: str,
    canonical_state_key: str,
    referent_key: str,
    hooks: SessionMemoryRuntimeHooks,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manager = _dialog_state_service().clear_context_manager_carryover_family(
        context_manager,
        class_manager_key=class_manager_key,
        service_manager_key=service_manager_key,
        consult_manager_key=consult_manager_key,
        canonical_state_key=canonical_state_key,
        referent_key=referent_key,
    )
    updated_context = hooks.set_context_manager(context, manager)
    updated_context = hooks.set_expected_reply_type(updated_context, None)
    updated_context = hooks.set_intent_queue(updated_context, [])
    updated_context = hooks.set_booking_context(updated_context, {"active": False})
    updated_context = hooks.clear_service_hint(updated_context)
    updated_context = _dialog_state_service().set_context_session_memory(
        updated_context,
        None,
        key="session_memory",
    )
    memory_payload = _dialog_state_service().touch_session_memory_payload(
        {},
        now=now,
        default_ttl_hours=session_memory_ttl_hours,
    )
    snapshot = _build_session_memory_observability_snapshot(memory_payload)
    snapshot["reason"] = reason
    return (
        updated_context,
        manager,
        snapshot,
    )


def _clear_session_memory_expected_reply_context(
    *,
    context: dict,
    expected_reply_type: str | None,
    now: datetime,
    session_memory_ttl_hours: int,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    memory = context.get("session_memory") if isinstance(context.get("session_memory"), dict) else {}
    if not memory:
        return context, {}, False
    memory, changed = _dialog_state_service().clear_session_memory_expected_reply(
        memory,
        expected_reply_type=expected_reply_type,
    )
    if not changed:
        return context, memory, False

    memory = _dialog_state_service().touch_session_memory_payload(
        memory,
        now=now,
        default_ttl_hours=session_memory_ttl_hours,
    )
    updated_context = _dialog_state_service().set_context_session_memory(
        context,
        memory,
        key="session_memory",
    )
    return updated_context, memory, True


def _resolve_pending_no_handover_reset(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    router_pending_meta: dict[str, Any] | None,
    hooks: PendingContinuityRuntimeHooks,
) -> None:
    context = hooks.get_conversation_context(conversation)
    context = _set_pending_resume(context, None)
    context = _set_pending_sla(context, {})
    context.pop(HANDOVER_CONFIRMATION_KEY, None)
    hooks.set_conversation_context(conversation, context)
    hooks.transition_state(
        conversation,
        ConversationState.BOT_ACTIVE,
        allow_same=False,
        enforce=True,
    )
    trace_payload = {
        "stage": "pending_guard",
        "decision": "reset_no_handover",
        "state": conversation.state,
    }
    if isinstance(router_pending_meta, dict):
        trace_payload.update(router_pending_meta)
    hooks.record_decision_trace(conversation, trace_payload)
    if saved_message:
        hooks.update_message_decision_metadata(
            saved_message,
            {
                "pending_action": "pending_guard_reset",
                "pending_guard": "no_handover",
            },
        )


def _resolve_pending_close(
    *,
    conversation: Conversation,
    handover: Handover | None,
    saved_message: Message | None,
    router_pending_meta: dict[str, Any] | None,
    hooks: PendingContinuityRuntimeHooks,
) -> ContinuityTransportDecision:
    if handover:
        hooks.manager_resolve(
            conversation,
            handover,
            manager_id="system",
            manager_name="system",
        )
    conversation.bot_status = "muted"
    conversation.bot_muted_until = None
    trace_payload = {
        "stage": "pending_sla",
        "decision": "pending_close",
        "state": conversation.state,
    }
    if isinstance(router_pending_meta, dict):
        trace_payload.update(router_pending_meta)
    hooks.record_decision_trace(conversation, trace_payload)
    if saved_message:
        hooks.update_message_decision_metadata(
            saved_message,
            {"pending_action": "pending_close"},
        )
    return ContinuityTransportDecision(
        handled=True,
        success_message="Pending closed by user",
    )


def _resolve_pending_ack(
    *,
    conversation: Conversation,
    handover: Handover | None,
    saved_message: Message | None,
    now: datetime,
    router_pending_meta: dict[str, Any] | None,
    msg_pending_ack: str,
    hooks: PendingContinuityRuntimeHooks,
) -> ContinuityTransportDecision:
    if handover:
        hooks.manager_resolve(
            conversation,
            handover,
            manager_id="system",
            manager_name="system",
            preserve_context=True,
        )
    else:
        hooks.transition_state(
            conversation,
            ConversationState.BOT_ACTIVE,
            allow_same=False,
            enforce=True,
        )
        if not isinstance(conversation.context, dict):
            conversation.context = {}
    conversation.bot_status = "active"

    context = hooks.get_conversation_context(conversation)
    pending_resume = _get_pending_resume(context)
    if pending_resume:
        restored_context = _restore_pending_resume_payload(
            context=context,
            pending_resume=pending_resume,
            now=now,
        )
        hooks.set_conversation_context(conversation, restored_context)
        hooks.record_decision_trace(
            conversation,
            {
                "stage": "pending_resume",
                "decision": "restore",
                "reason": "pending_ack",
            },
        )
        hooks.record_decision_trace(
            conversation,
            {
                "stage": "re_entry",
                "decision": "required",
                "reason": "pending_resume",
            },
        )
    elif not handover:
        hooks.record_decision_trace(
            conversation,
            {
                "stage": "pending_resume",
                "decision": "resume",
                "reason": "pending_ack_no_handover",
            },
        )

    trace_payload = {
        "stage": "pending_sla",
        "decision": "pending_ack",
        "state": conversation.state,
    }
    if isinstance(router_pending_meta, dict):
        trace_payload.update(router_pending_meta)
    hooks.record_decision_trace(conversation, trace_payload)
    if saved_message:
        hooks.update_message_decision_metadata(
            saved_message,
            {
                "pending_action": "pending_ack",
                "pending_resume_restored": bool(pending_resume),
            },
        )
    return ContinuityTransportDecision(
        handled=True,
        bot_response=msg_pending_ack,
        success_message="Pending ack response sent",
        failure_message="Pending ack send failed",
    )


def _record_pending_sla_violation_metadata(
    *,
    saved_message: Message | None,
    sla_violation,
    hooks: PendingContinuityRuntimeHooks,
) -> None:
    if not sla_violation or not saved_message:
        return
    hooks.update_message_decision_metadata(
        saved_message,
        {
            "sla_violation_severity": sla_violation.severity,
            "sla_violation_action": sla_violation.action,
            "sla_violation_reason": sla_violation.reason_code,
            "sla_elapsed_minutes": sla_violation.elapsed_minutes,
            "sla_threshold_minutes": sla_violation.threshold_minutes,
            "sla_profile_id": str(sla_violation.profile_id) if sla_violation.profile_id else None,
            "sla_profile_version": sla_violation.profile_version,
            "sla_profile_scope": sla_violation.profile_scope,
            "sla_domain_key": sla_violation.domain_key,
        },
    )


def _handle_pending_sla_runtime(
    *,
    db: Session,
    conversation: Conversation,
    saved_message: Message | None,
    now: datetime,
    guard_only_skip: bool,
    router_pending_meta: dict[str, Any] | None,
    pending_sla_ping_minutes: int,
    pending_sla_ping_sent_key: str,
    msg_pending_wait: str,
    msg_pending_sla_ping: str,
    resolve_pending_sla_violation_fn: Callable[..., Any],
    hooks: PendingContinuityRuntimeHooks,
) -> ContinuityTransportDecision | None:
    from app.services.sla_runtime_service import (
        SLA_RUNTIME_CONTEXT_KEY,
        build_collect_only_runtime_context,
    )

    context = hooks.get_conversation_context(conversation)
    pending_sla = _get_pending_sla(context)
    ping_sent_at = pending_sla.get(pending_sla_ping_sent_key)
    sla_violation = resolve_pending_sla_violation_fn(
        db,
        conversation=conversation,
        now=now,
    )
    _record_pending_sla_violation_metadata(
        saved_message=saved_message,
        sla_violation=sla_violation,
        hooks=hooks,
    )

    if sla_violation and sla_violation.severity != "none" and sla_violation.action == "collect_only":
        if guard_only_skip:
            trace_payload = {
                "stage": "pending_sla",
                "decision": "guard_only",
                "state": conversation.state,
                "sla_severity": sla_violation.severity,
                "sla_action": sla_violation.action,
                "sla_reason": sla_violation.reason_code,
            }
            if isinstance(router_pending_meta, dict):
                trace_payload.update(router_pending_meta)
            hooks.record_decision_trace(conversation, trace_payload)
            if saved_message:
                hooks.update_message_decision_metadata(
                    saved_message,
                    {
                        "pending_action": "pending_sla_collect_only_guard_only",
                        "pending_guard_only": True,
                    },
                )
            return None

        pending_sla[pending_sla_ping_sent_key] = now.isoformat()
        pending_sla["collect_only_at"] = now.isoformat()
        updated_context = _set_pending_sla(context, pending_sla)
        updated_context[SLA_RUNTIME_CONTEXT_KEY] = build_collect_only_runtime_context(
            decision=sla_violation,
            now=now,
        )
        hooks.set_conversation_context(conversation, updated_context)
        trace_payload = {
            "stage": "pending_sla",
            "decision": "collect_only",
            "state": conversation.state,
            "sla_severity": sla_violation.severity,
            "sla_action": sla_violation.action,
            "sla_reason": sla_violation.reason_code,
            "sla_elapsed_minutes": sla_violation.elapsed_minutes,
            "sla_threshold_minutes": sla_violation.threshold_minutes,
        }
        if isinstance(router_pending_meta, dict):
            trace_payload.update(router_pending_meta)
        hooks.record_decision_trace(conversation, trace_payload)
        if saved_message:
            hooks.update_message_decision_metadata(
                saved_message,
                {
                    "pending_action": "pending_sla_collect_only",
                    "sla_collect_only": True,
                },
            )
        return ContinuityTransportDecision(
            handled=True,
            bot_response=msg_pending_wait,
            success_message="Pending SLA collect_only response sent",
            failure_message="Pending SLA collect_only send failed",
        )

    escalated_at = conversation.escalated_at
    if escalated_at and escalated_at.tzinfo is None:
        escalated_at = escalated_at.replace(tzinfo=timezone.utc)
    if sla_violation:
        ping_due = bool(
            sla_violation.severity in {"breach", "severe_breach"}
            and sla_violation.action in {"notify_manager", "escalate"}
            and not ping_sent_at
        )
    else:
        ping_due = bool(
            escalated_at
            and not ping_sent_at
            and now - escalated_at >= timedelta(minutes=pending_sla_ping_minutes)
        )

    if not ping_due:
        return None

    if guard_only_skip:
        trace_payload = {
            "stage": "pending_sla",
            "decision": "guard_only",
            "state": conversation.state,
        }
        if sla_violation:
            trace_payload["sla_severity"] = sla_violation.severity
            trace_payload["sla_action"] = sla_violation.action
            trace_payload["sla_reason"] = sla_violation.reason_code
        if isinstance(router_pending_meta, dict):
            trace_payload.update(router_pending_meta)
        hooks.record_decision_trace(conversation, trace_payload)
        if saved_message:
            hooks.update_message_decision_metadata(
                saved_message,
                {
                    "pending_action": (
                        "pending_sla_escalate_guard_only"
                        if sla_violation and sla_violation.action == "escalate"
                        else "pending_sla_notify_manager_guard_only"
                        if sla_violation and sla_violation.action == "notify_manager"
                        else "pending_sla_guard_only"
                    ),
                    "pending_guard_only": True,
                },
            )
        return None

    pending_sla[pending_sla_ping_sent_key] = now.isoformat()
    updated_context = _set_pending_sla(context, pending_sla)
    hooks.set_conversation_context(conversation, updated_context)
    trace_payload = {
        "stage": "pending_sla",
        "decision": (
            "escalate"
            if sla_violation and sla_violation.action == "escalate"
            else "notify_manager"
            if sla_violation and sla_violation.action == "notify_manager"
            else "ping"
        ),
        "state": conversation.state,
    }
    if sla_violation:
        trace_payload["sla_severity"] = sla_violation.severity
        trace_payload["sla_action"] = sla_violation.action
        trace_payload["sla_reason"] = sla_violation.reason_code
        trace_payload["sla_elapsed_minutes"] = sla_violation.elapsed_minutes
        trace_payload["sla_threshold_minutes"] = sla_violation.threshold_minutes
    if isinstance(router_pending_meta, dict):
        trace_payload.update(router_pending_meta)
    hooks.record_decision_trace(conversation, trace_payload)
    if saved_message:
        hooks.update_message_decision_metadata(
            saved_message,
            {
                "pending_sla_ping": True,
                "pending_action": (
                    "pending_sla_escalate"
                    if sla_violation and sla_violation.action == "escalate"
                    else "pending_sla_notify_manager"
                    if sla_violation and sla_violation.action == "notify_manager"
                    else "pending_sla_ping"
                ),
            },
        )
    return ContinuityTransportDecision(
        handled=True,
        bot_response=msg_pending_sla_ping,
        success_message=(
            "Pending SLA escalation sent"
            if sla_violation and sla_violation.action == "escalate"
            else "Pending SLA notify sent"
            if sla_violation and sla_violation.action == "notify_manager"
            else "Pending SLA ping sent"
        ),
        failure_message="Pending SLA ping send failed",
    )


def _handle_handover_confirmation_runtime(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str,
    now: datetime,
    hooks: HandoverConfirmationRuntimeHooks,
) -> ContinuityTransportDecision:
    if conversation.state != ConversationState.BOT_ACTIVE.value:
        return ContinuityTransportDecision(handled=False)

    context = hooks.get_conversation_context(conversation)
    confirmation = hooks.get_handover_confirmation(context)
    if not confirmation:
        return ContinuityTransportDecision(handled=False)

    if not hooks.is_handover_confirmation_active(confirmation, now):
        cleared_context = hooks.set_handover_confirmation(context, None)
        hooks.set_conversation_context(conversation, cleared_context)
        return ContinuityTransportDecision(handled=False)

    decision = hooks.classify_confirmation(message_text)
    if decision == "yes":
        cleared_context = hooks.set_handover_confirmation(context, None)
        hooks.set_conversation_context(conversation, cleared_context)
        hooks.reset_low_confidence_retry(conversation)

        escalation_message = confirmation.get("user_message") or message_text
        _, reused, telegram_sent = hooks.reuse_active_handover(
            db=db,
            conversation=conversation,
            user=user,
            message=escalation_message,
            source="handover_confirmation",
            intent="low_confidence",
        )
        if reused:
            bot_response = hooks.msg_escalated
            success_message = (
                "Handover confirmed (reused), telegram=sent"
                if telegram_sent
                else "Handover confirmed (reused), telegram=failed"
            )
            failure_message = f"{success_message}; response_send=failed"
        else:
            hooks.record_escalation_metric("intent")
            escalation_result = hooks.escalate_to_pending(
                db=db,
                conversation=conversation,
                trigger_type="intent",
                trigger_value="low_confidence",
                user_message=escalation_message,
            )
            if escalation_result.ok:
                handover = escalation_result.value
                telegram_sent = hooks.send_telegram_notification(
                    db=db,
                    handover=handover,
                    conversation=conversation,
                    user=user,
                    message=escalation_message,
                )
                bot_response = hooks.msg_escalated
                success_message = (
                    "Handover confirmed, telegram=sent"
                    if telegram_sent
                    else "Handover confirmed, telegram=failed"
                )
                failure_message = f"{success_message}; response_send=failed"
            else:
                bot_response = hooks.msg_ai_error
                success_message = (
                    f"Handover confirm escalation failed: {escalation_result.error}"
                )
                failure_message = f"{success_message}; response_send=failed"

        hooks.record_decision_trace(
            conversation,
            {
                "stage": "handover_confirmation",
                "decision": "confirmed",
                "reason": "user_confirmed",
                "state": conversation.state,
                "reused": reused,
            },
        )
        return ContinuityTransportDecision(
            handled=True,
            bot_response=bot_response,
            success_message=success_message,
            failure_message=failure_message,
        )

    if decision == "no":
        cleared_context = hooks.set_handover_confirmation(context, None)
        hooks.set_conversation_context(conversation, cleared_context)
        hooks.reset_low_confidence_retry(conversation)
        hooks.record_decision_trace(
            conversation,
            {
                "stage": "handover_confirmation",
                "decision": "declined",
                "reason": "user_declined",
                "state": conversation.state,
            },
        )
        return ContinuityTransportDecision(
            handled=True,
            bot_response=hooks.msg_handover_declined,
            success_message="Handover declined, asked for salon details",
            failure_message="Handover decline send failed",
        )

    cleared_context = hooks.set_handover_confirmation(context, None)
    hooks.set_conversation_context(conversation, cleared_context)
    return ContinuityTransportDecision(handled=False)


def check_invariants(conversation: Conversation, handover: Handover = None) -> list[str]:
    """Проверить инварианты состояния. Возвращает список нарушений."""
    violations = []

    if conversation.state == ConversationState.MANAGER_ACTIVE.value:
        if not conversation.telegram_topic_id:
            violations.append("manager_active_no_topic")

    if conversation.state == ConversationState.PENDING.value:
        if not conversation.telegram_topic_id:
            violations.append("pending_no_topic")

    if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        if handover is None or handover.status not in ["pending", "active"]:
            violations.append("no_active_handover")

    return violations


def _coerce_state(value: str | ConversationState | None) -> ConversationState | None:
    if isinstance(value, ConversationState):
        return value
    if value is None:
        return None
    try:
        return ConversationState(value)
    except ValueError:
        return None


def transition_state(
    conversation: Conversation,
    to_state: ConversationState,
    *,
    allow_same: bool = False,
    enforce: bool = True,
    handover: Handover = None,
) -> dict:
    """Централизованный переход состояния с проверкой инвариантов."""
    from_state_value = conversation.state
    to_state_value = to_state.value
    from_state = _coerce_state(from_state_value)

    invalid_transition = False
    if from_state is None:
        invalid_transition = True
    else:
        invalid_transition = not is_transition_allowed(from_state, to_state, allow_same=allow_same)

    if not invalid_transition or not enforce:
        conversation.state = to_state_value

    violations = check_invariants(conversation, handover)

    return {
        "from_state": from_state_value,
        "to_state": to_state_value,
        "invalid_transition": invalid_transition,
        "violations": violations,
    }


def force_state(
    conversation: Conversation,
    to_state: ConversationState,
    *,
    reason: str | None = None,
    handover: Handover = None,
) -> dict:
    """Принудительный переход состояния (heal/cron)."""
    from_state_value = conversation.state
    to_state_value = to_state.value
    conversation.state = to_state_value

    violations = check_invariants(conversation, handover)
    logger.warning(
        "Forced state transition",
        extra={
            "from_state": from_state_value,
            "to_state": to_state_value,
            "reason": reason,
            "violations": violations,
        },
    )

    return {
        "from_state": from_state_value,
        "to_state": to_state_value,
        "invalid_transition": False,
        "violations": violations,
        "forced": True,
    }
