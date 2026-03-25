"""Legacy reasoning-core compatibility shim.

Active webhook runtime ownership lives in `app.core.consultant_runtime`.
This module only preserves the thin compatibility surface that tests and
legacy wrappers still import while shadow runtime code is removed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import BlockBoundaryRequest, DegradeBoundaryRequest, DialogStateService, TurnExecutor, TurnPlanner
from app.logging_config import get_trace_id, start_span
from app.models import Client, Conversation, Message, User
from app.routers.webhook import decision as decision_router
from app.routers.webhook.media import _extract_media_info
from app.routers.webhook.runtime_primitives import SERVICE_CARRYOVER_TTL_MESSAGES
from app.routers.webhook.trace import DECISION_STAGE_ORDER_SNAPSHOT, _record_decision_trace
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.booking_signal_service import extract_time_token


STAGE_ORDER_SNAPSHOT = DECISION_STAGE_ORDER_SNAPSHOT
REASONING_CORE_DEGRADE_REASON = "runtime_exception"
REASONING_CORE_DEGRADE_OWNER = "reasoning_core_exception_degrade"
REASONING_CORE_PREFLIGHT_REASON = "empty_message"
REASONING_CORE_PREFLIGHT_OWNER = "reasoning_core_empty_message"
REASONING_CORE_MISSING_REMOTE_JID_REASON = "missing_remote_jid"
REASONING_CORE_MISSING_REMOTE_JID_OWNER = "reasoning_core_missing_remote_jid"
REASONING_CORE_MISSING_TENANT_CONTEXT_REASON = "missing_tenant_context"
REASONING_CORE_MISSING_TENANT_CONTEXT_OWNER = "reasoning_core_missing_tenant_context"
REASONING_CORE_SENDER_BRANCH_IGNORE_REASON = "sender_is_branch"
REASONING_CORE_SENDER_BRANCH_IGNORE_OWNER = "reasoning_core_sender_branch_ignore"
REASONING_CORE_TENANT_CONTEXT_INVALID_REASON = "tenant_context_contract_invalid"
REASONING_CORE_TENANT_CONTEXT_INVALID_OWNER = "reasoning_core_tenant_context_invalid"
REASONING_CORE_REMOTE_BRANCH_PHONE_REASON = "remote_is_branch_phone"
REASONING_CORE_REMOTE_BRANCH_PHONE_OWNER = "reasoning_core_remote_branch_phone_ignore"
REASONING_CORE_DUPLICATE_REASON = "duplicate_message_id"
REASONING_CORE_DUPLICATE_OWNER = "reasoning_core_duplicate_message"

_EXPECTED_REPLY_TYPE_FIELD = "expected_reply_type"
_EXPECTED_REPLY_REASON_FIELD = "expected_reply_reason"


@dataclass(frozen=True)
class ReasoningCoreRequest:
    payload: WebhookRequest
    db: Session
    provided_secret: str | None
    enforce_secret: bool
    enqueue_only: bool = False
    skip_persist: bool = False
    conversation_id: UUID | None = None
    batch_messages: list[str] | None = None
    outbox_ids: list[str] | None = None
    outbox_created_at: datetime | None = None
    preflight_payload: dict[str, object] | None = None


@dataclass(frozen=True)
class ReasoningCoreDegradeArtifact:
    turn_result: Any
    turn_outcome: Any


@dataclass(frozen=True)
class ReasoningCorePreflightArtifact:
    turn_result: Any
    turn_outcome: Any


@dataclass(frozen=True)
class ReasoningCoreDuplicateProbe:
    duplicate: bool
    backend: str | None = None
    fallback_reason: str | None = None


@dataclass(frozen=True)
class ReasoningCoreTenantContextRejection:
    reason_code: str
    message: str
    interaction_owner: str
    trace_message: str
    meta: dict[str, object] | None = None


@dataclass(frozen=True)
class ReasoningCoreConversationSnapshot:
    conversation_id: UUID
    state: str
    bot_status: str | None
    branch_id: UUID | None
    reply_slot: str | None
    current_goal: str | None
    booking_active: bool
    allow_bot_reply: bool
    resume_reason: str | None = None
    booking_time_token: str | None = None
    booking_datetime_value: str | None = None
    service_referent: str | None = None


def stage_order_hash(stage_order: Sequence[str] | None = None) -> str:
    order = stage_order or STAGE_ORDER_SNAPSHOT
    return hashlib.sha256("\n".join(order).encode("utf-8")).hexdigest()


def _build_runtime_exception_artifact(
    *,
    bot_response: str,
    transport_status: str,
    transport_reason: str | None,
) -> ReasoningCoreDegradeArtifact:
    artifact = TurnExecutor().build_degrade_boundary_artifact_from_request(
        request=DegradeBoundaryRequest(
            reason_code=REASONING_CORE_DEGRADE_REASON,
            action="handoff",
            intent="runtime_error",
            interaction_owner=REASONING_CORE_DEGRADE_OWNER,
            interaction_relation="runtime_exception",
            public_message=bot_response,
            trace_message="reasoning_core exception degraded through new core",
            transport_status=transport_status,
            transport_reason=transport_reason,
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCoreDegradeArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_empty_message_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_PREFLIGHT_REASON,
            action="preflight_reject",
            intent="empty_message",
            interaction_owner=REASONING_CORE_PREFLIGHT_OWNER,
            interaction_relation="empty_message",
            trace_message="reasoning_core blocked empty non-media inbound",
            replan_hints=["require non-empty text or media"],
            tool_action="preflight.empty_message",
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(artifact.turn_result, artifact.turn_outcome)


def _build_missing_remote_jid_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_MISSING_REMOTE_JID_REASON,
            action="preflight_reject",
            intent="missing_remote_jid",
            interaction_owner=REASONING_CORE_MISSING_REMOTE_JID_OWNER,
            interaction_relation="missing_remote_jid",
            trace_message="reasoning_core blocked inbound without metadata.remoteJid",
            replan_hints=["require metadata.remoteJid"],
            tool_action="preflight.missing_remote_jid",
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(artifact.turn_result, artifact.turn_outcome)


def _build_missing_tenant_context_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_MISSING_TENANT_CONTEXT_REASON,
            action="preflight_reject",
            intent="missing_tenant_context",
            interaction_owner=REASONING_CORE_MISSING_TENANT_CONTEXT_OWNER,
            interaction_relation="missing_tenant_context",
            trace_message="reasoning_core blocked inbound without usable tenant_context",
            replan_hints=["require tenant_context client_id or client_slug"],
            tool_action="preflight.missing_tenant_context",
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(artifact.turn_result, artifact.turn_outcome)


def _build_sender_branch_ignore_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_SENDER_BRANCH_IGNORE_REASON,
            action="ignore",
            intent="sender_is_branch",
            interaction_owner=REASONING_CORE_SENDER_BRANCH_IGNORE_OWNER,
            interaction_relation="sender_is_branch",
            trace_message="reasoning_core ignored active branch sender",
            replan_hints=["skip branch-originated inbound"],
            tool_action="preflight.sender_is_branch",
            ignored=True,
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(artifact.turn_result, artifact.turn_outcome)


def _build_tenant_context_reject_artifact(
    *,
    rejection: ReasoningCoreTenantContextRejection,
) -> ReasoningCorePreflightArtifact:
    meta = rejection.meta or {}
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=rejection.reason_code,
            action="preflight_reject",
            intent=rejection.reason_code,
            interaction_owner=rejection.interaction_owner,
            interaction_relation=rejection.reason_code,
            trace_message=rejection.trace_message,
            replan_hints=["require valid tenant_context contract"],
            tool_action=f"preflight.{rejection.reason_code}",
            override_meta={"source": "reasoning_core", **meta},
            outcome_meta={"tenant_context_guard": True, **meta},
        )
    )
    return ReasoningCorePreflightArtifact(artifact.turn_result, artifact.turn_outcome)


def _build_remote_branch_phone_ignore_artifact(
    *,
    matched_phone: str | None,
) -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_REMOTE_BRANCH_PHONE_REASON,
            action="ignore",
            intent="remote_is_branch_phone",
            interaction_owner=REASONING_CORE_REMOTE_BRANCH_PHONE_OWNER,
            interaction_relation="remote_is_branch_phone",
            trace_message="reasoning_core ignored same-client branch phone sender",
            replan_hints=["skip same-client branch phone inbound"],
            tool_action="preflight.remote_is_branch_phone",
            ignored=True,
            override_meta={"source": "reasoning_core", "matched_phone": matched_phone},
            outcome_meta={"matched_phone": matched_phone},
        )
    )
    return ReasoningCorePreflightArtifact(artifact.turn_result, artifact.turn_outcome)


def _build_duplicate_message_artifact(
    *,
    dedup_backend: str | None,
    dedup_fallback_reason: str | None,
) -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_DUPLICATE_REASON,
            action="ignore",
            intent="duplicate_message_id",
            interaction_owner=REASONING_CORE_DUPLICATE_OWNER,
            interaction_relation="duplicate_message_id",
            trace_message="reasoning_core ignored preexisting duplicate message_id",
            replan_hints=["skip duplicate inbound message_id"],
            tool_action="preflight.duplicate_message_id",
            ignored=True,
            override_meta={
                "source": "reasoning_core",
                "dedup_backend": dedup_backend,
                "dedup_fallback_reason": dedup_fallback_reason,
            },
            outcome_meta={
                "dedup_backend": dedup_backend,
                "dedup_fallback_reason": dedup_fallback_reason,
                "preexisting_duplicate": True,
            },
        )
    )
    return ReasoningCorePreflightArtifact(artifact.turn_result, artifact.turn_outcome)


def _resolve_snapshot_booking_datetime_value(context: dict[str, object], *, booking_active: bool) -> str | None:
    booking_state = context.get("booking") if isinstance(context, dict) else None
    if not booking_active or not isinstance(booking_state, dict):
        return None
    value = booking_state.get("datetime")
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _resolve_snapshot_booking_time_token(*, booking_datetime_value: str | None) -> str | None:
    if not isinstance(booking_datetime_value, str) or not booking_datetime_value.strip():
        return None
    return extract_time_token(booking_datetime_value)


def _resolve_snapshot_service_referent(context: dict[str, object], *, booking_active: bool) -> str | None:
    booking_state = context.get("booking") if isinstance(context, dict) else None
    if booking_active and isinstance(booking_state, dict):
        booking_service = booking_state.get("service")
        if isinstance(booking_service, str) and booking_service.strip():
            return booking_service.strip()

    manager = context.get("context_manager") if isinstance(context, dict) else None
    if not isinstance(manager, dict):
        return None

    try:
        message_count = int(manager.get("message_count"))
    except (TypeError, ValueError):
        return None
    if message_count <= 0:
        return None

    canonical_projection = DialogStateService().normalize_context_manager_canonical_state(
        manager.get("canonical_dialog_state") if isinstance(manager.get("canonical_dialog_state"), dict) else None
    )
    referents = canonical_projection.get("current_referents")
    service_payload = referents.get("service") if isinstance(referents, dict) else None
    if isinstance(service_payload, dict):
        service_value = service_payload.get("value")
        if isinstance(service_value, str) and service_value.strip():
            ttl = service_payload.get("ttl")
            last_count = service_payload.get("message_count")
            try:
                last_count_value = int(last_count)
            except (TypeError, ValueError):
                last_count_value = message_count
            age = max(message_count - last_count_value, 0)
            if not isinstance(ttl, int) or ttl <= 0 or age <= ttl:
                return service_value.strip()

    legacy_payload = manager.get("service_carryover")
    if not isinstance(legacy_payload, dict):
        return None
    projected = DialogStateService().get_service_carryover(
        legacy_payload,
        message_count=message_count,
        default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
    )
    if not isinstance(projected, dict):
        return None
    service_query = projected.get("service_query")
    if isinstance(service_query, str) and service_query.strip():
        return service_query.strip()
    return None


def _build_conversation_snapshot(
    conversation: Conversation,
    *,
    message_text: str | None = None,
    client_slug: str | None = None,
) -> ReasoningCoreConversationSnapshot:
    context = conversation.context if isinstance(conversation.context, dict) else {}
    dialog_state_service = DialogStateService()
    now = datetime.now(timezone.utc)
    context_pending_question_contract = dialog_state_service.project_context_pending_question_contract(
        context,
        session_memory_key="__disabled_session_memory__",
    )
    expected_reply = dialog_state_service.project_expected_reply_projections(
        expected_reply_type=(
            context_pending_question_contract.get(_EXPECTED_REPLY_TYPE_FIELD)
            if isinstance(context_pending_question_contract, dict)
            else context.get(_EXPECTED_REPLY_TYPE_FIELD)
        ),
        expected_reply_reason=(
            context_pending_question_contract.get("reason")
            if isinstance(context_pending_question_contract, dict)
            else context.get(_EXPECTED_REPLY_REASON_FIELD)
        ),
    ).model_dump()
    booking_state = dict(context.get("booking") or {}) if isinstance(context.get("booking"), dict) else {}
    booking_active = bool(booking_state.get("active"))
    current_goal = context.get("current_goal")
    normalized_goal = current_goal.strip() if isinstance(current_goal, str) and current_goal.strip() else None

    if expected_reply.get(_EXPECTED_REPLY_TYPE_FIELD) is None and isinstance(message_text, str) and message_text.strip():
        session_memory = context.get("session_memory") if isinstance(context.get("session_memory"), dict) else None
        re_entry_required = context.get("re_entry_required")
        if (
            isinstance(session_memory, dict)
            and not dialog_state_service.is_re_entry_required(re_entry_required)
            and not dialog_state_service.is_session_memory_expired(session_memory, now=now, default_ttl_hours=24)
        ):
            memory_active_goal = session_memory.get("active_goal")
            normalized_memory_goal = (
                memory_active_goal.strip()
                if isinstance(memory_active_goal, str) and memory_active_goal.strip()
                else None
            )
            memory_pending_question_contract = (
                dialog_state_service.project_session_memory_pending_question_contract(session_memory)
            )
            memory_expected_reply = (
                memory_pending_question_contract.get(_EXPECTED_REPLY_TYPE_FIELD)
                if isinstance(memory_pending_question_contract, dict)
                else None
            )
            memory_expected_reply_reason = (
                memory_pending_question_contract.get("reason")
                if isinstance(memory_pending_question_contract, dict)
                else None
            )
            is_short_reply = decision_router._is_short_reply(message_text)
            if (
                not is_short_reply
                and memory_expected_reply == decision_router.EXPECTED_REPLY_TIME
                and decision_router._extract_datetime(message_text, client_slug=client_slug)
            ):
                is_short_reply = True
            if (
                memory_expected_reply in {
                    decision_router.EXPECTED_REPLY_SERVICE,
                    decision_router.EXPECTED_REPLY_TIME,
                    decision_router.EXPECTED_REPLY_NAME,
                }
                and is_short_reply
                and not decision_router._looks_like_info_query(message_text, client_slug=client_slug)
                and not decision_router._looks_like_policy_topic(message_text, policy_type=None, policy_pack=None)
                and (
                    not normalized_memory_goal or not normalized_goal or normalized_memory_goal == normalized_goal
                )
            ):
                expected_reply[_EXPECTED_REPLY_TYPE_FIELD] = memory_expected_reply
                if (
                    expected_reply.get(_EXPECTED_REPLY_REASON_FIELD) is None
                    and isinstance(memory_expected_reply_reason, str)
                    and memory_expected_reply_reason.strip()
                ):
                    expected_reply[_EXPECTED_REPLY_REASON_FIELD] = memory_expected_reply_reason.strip()

    pending_boundary = dialog_state_service.derive_pending_booking_resume_boundary_payload(context, now=now)
    boundary_booking_state = pending_boundary.get("booking_state") if isinstance(pending_boundary, dict) else None
    if expected_reply.get(_EXPECTED_REPLY_TYPE_FIELD) is None and isinstance(pending_boundary, dict):
        boundary_expected_reply = pending_boundary.get("expected_reply_type")
        if isinstance(boundary_expected_reply, str) and boundary_expected_reply.strip():
            expected_reply[_EXPECTED_REPLY_TYPE_FIELD] = boundary_expected_reply.strip()
            if expected_reply.get(_EXPECTED_REPLY_REASON_FIELD) is None:
                pending_resume_reason = dialog_state_service.derive_pending_resume_reason(context)
                if isinstance(pending_resume_reason, str) and pending_resume_reason.strip():
                    expected_reply[_EXPECTED_REPLY_REASON_FIELD] = pending_resume_reason.strip()
    if not booking_active and isinstance(boundary_booking_state, dict):
        booking_state = dict(boundary_booking_state)
        booking_active = bool(booking_state.get("active"))
    if normalized_goal is None and isinstance(pending_boundary, dict):
        normalized_goal = "booking"

    merged_context = {**context, "booking": booking_state}
    booking_datetime_value = _resolve_snapshot_booking_datetime_value(merged_context, booking_active=booking_active)
    booking_time_token = _resolve_snapshot_booking_time_token(booking_datetime_value=booking_datetime_value)
    service_referent = _resolve_snapshot_service_referent(merged_context, booking_active=booking_active)
    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    return ReasoningCoreConversationSnapshot(
        conversation_id=conversation.id,
        state=conversation.state,
        bot_status=conversation.bot_status,
        branch_id=conversation.branch_id,
        reply_slot=expected_reply.get(_EXPECTED_REPLY_TYPE_FIELD),
        resume_reason=expected_reply.get(_EXPECTED_REPLY_REASON_FIELD),
        current_goal=normalized_goal,
        booking_active=booking_active,
        allow_bot_reply=bool(routing.get("allow_bot_reply", False)),
        booking_time_token=booking_time_token,
        booking_datetime_value=booking_datetime_value,
        service_referent=service_referent,
    )


def _lookup_preexisting_duplicate_message(
    db: Session,
    *,
    client_id: UUID | None,
    message_id: str | None,
) -> ReasoningCoreDuplicateProbe:
    from app.routers.webhook import dedup as dedup_helpers

    owner_probe = dedup_helpers._lookup_preexisting_duplicate_message(
        db,
        client_id=client_id,
        message_id=message_id,
    )
    return ReasoningCoreDuplicateProbe(
        duplicate=owner_probe.duplicate,
        backend=owner_probe.backend,
        fallback_reason=owner_probe.fallback_reason,
    )


def _normalize_payload_for_delegation(payload: WebhookRequest) -> WebhookRequest:
    raw_message_type = payload.body.messageType if payload and payload.body else None
    inbound = TurnPlanner().coerce_inbound(
        {
            "message_text": payload.body.message if payload and payload.body else None,
            "message_type": raw_message_type,
            "has_media": (
                bool(payload.body.mediaData)
                or bool(isinstance(raw_message_type, str) and raw_message_type.strip().lower() != "text")
            ) if payload and payload.body else False,
        }
    )
    media_info = _extract_media_info(payload.body) if payload and payload.body else None
    normalized_text = inbound.normalized_message_text(media_caption=media_info.caption if media_info else None)
    if normalized_text == payload.body.message:
        return payload
    return payload.model_copy(
        update={
            "body": payload.body.model_copy(
                update={
                    "message": normalized_text,
                }
            )
        }
    )


def _resolve_secret_preflight_trace_conversation(
    db: Session,
    *,
    trace_client: Client | None,
    trace_conversation_id: UUID | None,
    trace_message_id: str | None,
    trace_remote_jid: str | None,
) -> Conversation | None:
    if trace_conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == trace_conversation_id).first()
        if conversation:
            return conversation
    if trace_client and trace_message_id:
        saved_message = decision_router._find_message_by_message_id(db, trace_client.id, trace_message_id)
        if saved_message:
            return db.query(Conversation).filter(Conversation.id == saved_message.conversation_id).first()
    if trace_client and trace_remote_jid:
        user = (
            db.query(User)
            .filter(User.client_id == trace_client.id, User.remote_jid == trace_remote_jid)
            .first()
        )
        if user:
            return (
                db.query(Conversation)
                .filter(
                    Conversation.client_id == trace_client.id,
                    Conversation.user_id == user.id,
                    Conversation.status == "active",
                )
                .first()
            )
    return None


def _record_secret_preflight_trace(
    trace_conversation: Conversation | None,
    *,
    stage: str,
    decision: str,
    reason: str,
    meta: dict[str, object] | None = None,
) -> bool:
    if not trace_conversation:
        return False
    payload = {"stage": stage, "decision": decision, "reason": reason}
    if meta:
        payload.update(meta)
    _record_decision_trace(trace_conversation, payload)
    return True


def _run_secret_enforced_preflight(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    conversation_id: UUID | None,
) -> tuple[WebhookResponse | None, dict[str, object]]:
    from app.routers.webhook import http as http_helpers

    context = {"client_slug": payload.client_slug}
    trace_id = get_trace_id()
    if trace_id:
        context["trace_id"] = trace_id
    with start_span("webhook.preflight", context=context):
        return http_helpers._run_preflight(
            payload,
            db,
            provided_secret=provided_secret,
            enforce_secret=True,
            conversation_id=conversation_id,
            resolve_trace_conversation=lambda **kwargs: _resolve_secret_preflight_trace_conversation(db, **kwargs),
            record_early_trace=_record_secret_preflight_trace,
        )


def _finalize_turn_planner_owner_cutover(**_kwargs):
    raise RuntimeError("reasoning_core shadow owner path removed; use consultant_runtime")


def _finalize_tool_reply_owner_execution(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    conversation: Conversation,
    saved_message: Message | None,
    owner_execution: Any,
    reply_text: str,
    reply_intent: str | None,
    reply_source: str,
    owner_cutover: str,
    tool_decision: str | None,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    maybe_apply_fact_guard: Callable[..., WebhookResponse | None],
    guard_decision_meta: dict[str, object] | None,
    allow_handover: bool,
    send_and_save: Callable[[str], tuple[str, bool]],
    transport_status_token: str | None,
    transport_reason_token: str | None,
    success_label: str = "LLM policy core tool response",
) -> WebhookResponse | None:
    guard_response = maybe_apply_fact_guard(
        decision_meta=guard_decision_meta,
        intent=reply_intent,
        source=reply_source,
        allow_handover=allow_handover,
    )
    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=None,
        conversation_id=conversation.id,
        decision=owner_execution.decision,
        reply_text=reply_text,
        reply_meta=None,
        trace_meta=None,
        owner_cutover=owner_cutover,
        stage="llm_policy_core_tool",
        success_label=success_label,
        tool_decision=tool_decision,
        outcome_action="reply",
        outcome_source=reply_source,
        artifact=owner_execution.payload.artifact,
        existing_conversation=conversation,
        existing_saved_message=saved_message,
        send_and_save=send_and_save,
        transport_status_token=transport_status_token,
        transport_reason_token=transport_reason_token,
        trace_payload_override=owner_execution.payload.trace_payload_override,
        guard_response=guard_response,
        extra_trace_payloads=owner_execution.payload.extra_trace_payloads,
        extra_meta_updates=owner_execution.payload.extra_meta_updates,
        followup_type=expected_reply_type,
        question_reason=expected_reply_reason,
    )


async def run_reasoning_core(request: ReasoningCoreRequest) -> WebhookResponse:
    return await handle_webhook_payload(
        request.payload,
        request.db,
        provided_secret=request.provided_secret,
        enforce_secret=request.enforce_secret,
        enqueue_only=request.enqueue_only,
        skip_persist=request.skip_persist,
        conversation_id=request.conversation_id,
        batch_messages=request.batch_messages,
        outbox_ids=request.outbox_ids,
        outbox_created_at=request.outbox_created_at,
        preflight_payload=request.preflight_payload,
    )


async def handle_webhook_payload(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    enforce_secret: bool,
    enqueue_only: bool = False,
    skip_persist: bool = False,
    conversation_id: UUID | None = None,
    batch_messages: list[str] | None = None,
    outbox_ids: list[str] | None = None,
    outbox_created_at: datetime | None = None,
    preflight_payload: dict[str, object] | None = None,
) -> WebhookResponse:
    from app.core import consultant_runtime

    return await consultant_runtime.handle_webhook_payload(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=enforce_secret,
        enqueue_only=enqueue_only,
        skip_persist=skip_persist,
        conversation_id=conversation_id,
        batch_messages=batch_messages,
        outbox_ids=outbox_ids,
        outbox_created_at=outbox_created_at,
        preflight_payload=preflight_payload,
    )


__all__ = [
    "ReasoningCoreDuplicateProbe",
    "ReasoningCorePreflightArtifact",
    "ReasoningCoreDegradeArtifact",
    "ReasoningCoreRequest",
    "ReasoningCoreTenantContextRejection",
    "ReasoningCoreConversationSnapshot",
    "REASONING_CORE_DEGRADE_REASON",
    "REASONING_CORE_DUPLICATE_REASON",
    "REASONING_CORE_MISSING_REMOTE_JID_REASON",
    "REASONING_CORE_MISSING_TENANT_CONTEXT_REASON",
    "REASONING_CORE_PREFLIGHT_REASON",
    "REASONING_CORE_REMOTE_BRANCH_PHONE_REASON",
    "REASONING_CORE_SENDER_BRANCH_IGNORE_REASON",
    "REASONING_CORE_TENANT_CONTEXT_INVALID_OWNER",
    "REASONING_CORE_TENANT_CONTEXT_INVALID_REASON",
    "STAGE_ORDER_SNAPSHOT",
    "_build_duplicate_message_artifact",
    "_build_empty_message_artifact",
    "_build_missing_remote_jid_artifact",
    "_build_missing_tenant_context_artifact",
    "_build_remote_branch_phone_ignore_artifact",
    "_build_sender_branch_ignore_artifact",
    "_build_tenant_context_reject_artifact",
    "_build_runtime_exception_artifact",
    "_build_conversation_snapshot",
    "_lookup_preexisting_duplicate_message",
    "_normalize_payload_for_delegation",
    "_run_secret_enforced_preflight",
    "_finalize_tool_reply_owner_execution",
    "_finalize_turn_planner_owner_cutover",
    "handle_webhook_payload",
    "run_reasoning_core",
    "stage_order_hash",
]
