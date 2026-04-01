"""Durable outbox action-plane helpers (batch merge + enqueue replay)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.adapters.chatflow import ChatFlowAdapter
from app.adapters.provider_gateway import ProviderGatewayAdapter
from app.logging_config import (
    get_logger,
    record_delivery_failure,
    record_outbox_latency,
    start_span,
)
from app.models import Conversation, Message, OutboxMessage, User
from app.ports.messaging import MessageOptions
from app.routers.webhook.media import (
    _build_media_caption,
    _deserialize_media_decision,
    _evaluate_media_decision,
    _send_telegram_media,
    _store_media_locally,
    _update_message_media_metadata,
)
from app.routers.webhook.trace import (
    _merge_message_timing,
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)
from app.schemas.outbox_payload import validate_outbox_payload
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.ai_service import normalize_for_matching
from app.services.alert_service import alert_error
from app.services.appointment_reminder_service import process_reminder_jobs
from app.services.calendar_sync_service import (
    OUTBOX_EVENT_CALENDAR_SYNC_INBOUND,
    OUTBOX_EVENT_CALENDAR_SYNC_OUTBOUND,
    process_inbound_sync_event,
    process_outbound_sync_event,
    schedule_inbound_syncs,
)
from app.services.escalation_service import get_telegram_credentials
from app.services.knowledge_registry_service import (
    OUTBOX_EVENT_KNOWLEDGE_SYNC,
    process_knowledge_sync_event,
)
from app.services.outbox_service import (
    archive_pending_outbox,
    build_inbound_message_id,
    claim_pending_outbox_batches,
    enqueue_outbox_message,
    mark_outbox_status,
    release_stale_processing,
)
from app.services.provider_error_policy import classify_provider_error, is_permanent_provider_error
from app.services.state_machine import ConversationState
from app.services.state_service import is_simulation_context
from app.services.telegram_service import TelegramService
from app.services.tenant_context_contract import validate_tenant_context_contract

logger = get_logger("webhook")

if TYPE_CHECKING:
    from app.models import Client


@dataclass(frozen=True)
class OutboxProcessSettings:
    limit: int
    idle_seconds: int
    max_wait_seconds: int
    max_attempts: int
    retry_backoff_seconds: float
    stale_seconds: int


@dataclass(frozen=True)
class OutboxWorkerCycleResult:
    next_inbound_schedule_at: datetime | None
    released_stale: dict[str, int]
    inbound_results: dict[str, int] | None
    processed_batches: int


def load_outbox_process_settings() -> OutboxProcessSettings:
    max_wait_seconds = max(int(float(os.environ.get("OUTBOX_MAX_WAIT_SECONDS", "10"))), 0)
    return OutboxProcessSettings(
        limit=int(os.environ.get("OUTBOX_PROCESS_LIMIT", "10")),
        idle_seconds=int(float(os.environ.get("OUTBOX_COALESCE_SECONDS", "8"))),
        max_wait_seconds=max_wait_seconds,
        max_attempts=int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5")),
        retry_backoff_seconds=float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2")),
        stale_seconds=max(int(float(os.environ.get("OUTBOX_STALE_PROCESSING_SECONDS", "120"))), 0),
    )


async def process_claimed_outbox_rows(
    db: Session,
    rows: list[dict],
    *,
    settings: OutboxProcessSettings,
) -> dict[str, int]:
    return await _process_outbox_rows(
        db,
        rows,
        max_attempts=settings.max_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    )


async def run_canonical_outbox_process(
    db: Session,
    *,
    settings: OutboxProcessSettings,
    claim_rows: Callable[[], list[dict[str, object]]],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    rows = claim_rows()
    if not rows:
        return rows, {"claimed": 0, "sent": 0, "failed": 0, "retry_scheduled": 0}
    results = await process_claimed_outbox_rows(db, rows, settings=settings)
    return rows, results


async def run_outbox_worker_cycle(
    db: Session,
    *,
    settings: OutboxProcessSettings,
    interval_seconds: float,
    next_inbound_schedule_at: datetime | None,
    now: datetime | None = None,
    loop_started_at: float | None = None,
) -> OutboxWorkerCycleResult:
    released = release_stale_processing(
        db,
        stale_seconds=settings.stale_seconds,
        max_attempts=settings.max_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    )
    if released["released"] or released["failed"]:
        logger.warning(
            "Outbox stale processing released",
            extra={"context": {**released, "stale_seconds": settings.stale_seconds}},
        )

    effective_now = now or datetime.now(timezone.utc)
    inbound_results: dict[str, int] | None = None
    if next_inbound_schedule_at is None or effective_now >= next_inbound_schedule_at:
        try:
            inbound_results = schedule_inbound_syncs(db, now=effective_now)
        except Exception as exc:
            inbound_results = {"interval_seconds": 60, "scheduled": 0, "errors": 1}
            logger.warning(
                "Inbound calendar sync scheduling failed",
                extra={"context": {"error": str(exc)[:200]}},
            )
        schedule_interval = inbound_results.get("interval_seconds") or 60
        next_inbound_schedule_at = effective_now + timedelta(seconds=max(schedule_interval, 60))
        if inbound_results.get("scheduled") or inbound_results.get("errors"):
            logger.info(
                "Inbound calendar sync scheduled",
                extra={"context": inbound_results},
            )

    started_at = loop_started_at if loop_started_at is not None else time.monotonic()
    processed_batches = 0
    while True:
        rows, results = await run_canonical_outbox_process(
            db,
            settings=settings,
            claim_rows=lambda: claim_pending_outbox_batches(
                db,
                limit=settings.limit,
                idle_seconds=settings.idle_seconds,
                max_wait_seconds=settings.max_wait_seconds,
                include_without_conversation=True,
            ),
        )
        if not rows:
            break

        processed_batches += 1
        logger.info(
            "Outbox worker processed",
            extra={"context": results},
        )

        if time.monotonic() - started_at >= interval_seconds:
            break

    return OutboxWorkerCycleResult(
        next_inbound_schedule_at=next_inbound_schedule_at,
        released_stale={
            "released": int(released.get("released", 0)),
            "failed": int(released.get("failed", 0)),
        },
        inbound_results=inbound_results,
        processed_batches=processed_batches,
    )


async def run_default_outbox_process(
    db: Session,
    *,
    include_reminders: bool,
) -> dict[str, int | dict[str, int]]:
    settings = load_outbox_process_settings()
    released = release_stale_processing(
        db,
        stale_seconds=settings.stale_seconds,
        max_attempts=settings.max_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    )
    inbound_results = schedule_inbound_syncs(db)
    _rows, results = await run_canonical_outbox_process(
        db,
        settings=settings,
        claim_rows=lambda: claim_pending_outbox_batches(
            db,
            limit=settings.limit,
            idle_seconds=settings.idle_seconds,
            max_wait_seconds=settings.max_wait_seconds,
            include_without_conversation=True,
        ),
    )
    if inbound_results.get("scheduled") or inbound_results.get("errors"):
        results["calendar_inbound"] = inbound_results
    if include_reminders:
        reminder_results = process_reminder_jobs(db)
        if reminder_results.get("total"):
            results["reminder_jobs"] = reminder_results
    if released["released"] or released["failed"]:
        results["released_stale"] = released["released"]
        results["failed_stale"] = released["failed"]
    return results


async def run_scoped_outbox_process(
    db: Session,
    *,
    client_id: UUID,
    allowed_branch_ids: list[UUID] | None,
    limit: int | None = None,
    idle_seconds: int | None = None,
    max_wait_seconds: int | None = None,
    include_without_conversation: bool = True,
    archive_pending_older_than_hours: int = 0,
    archive_pending_limit: int | None = None,
    archive_pending_without_conversation_only: bool = True,
) -> dict[str, int | dict[str, int] | dict[str, object]]:
    settings = load_outbox_process_settings()
    effective_limit = settings.limit if limit is None else limit
    effective_idle_seconds = settings.idle_seconds if idle_seconds is None else idle_seconds
    effective_max_wait_seconds = settings.max_wait_seconds if max_wait_seconds is None else max_wait_seconds
    effective_archive_limit = archive_pending_limit if archive_pending_limit is not None else effective_limit

    archive_result = None
    if archive_pending_older_than_hours > 0:
        archive_reason = f"archived_pending:older_than_{archive_pending_older_than_hours}h"
        archive_result = archive_pending_outbox(
            db,
            client_id=client_id,
            older_than_seconds=archive_pending_older_than_hours * 3600,
            limit=effective_archive_limit,
            reason=archive_reason,
            branch_ids=allowed_branch_ids,
            only_without_conversation=archive_pending_without_conversation_only,
        )

    claimed_rows, results = await run_canonical_outbox_process(
        db,
        settings=settings,
        claim_rows=lambda: claim_scoped_outbox_rows(
            db,
            client_id=client_id,
            allowed_branch_ids=allowed_branch_ids,
            limit=effective_limit,
            idle_seconds=effective_idle_seconds,
            max_wait_seconds=effective_max_wait_seconds,
            include_without_conversation=include_without_conversation,
        ),
    )
    if not claimed_rows:
        response: dict[str, int | dict[str, int] | dict[str, object]] = {
            "processed": 0,
            "results": {"processed": 0, "failed": 0},
        }
        if archive_result is not None:
            response["archive"] = archive_result
        return response

    response: dict[str, int | dict[str, int] | dict[str, object]] = {
        "processed": len(claimed_rows),
        "results": results,
    }
    if archive_result is not None:
        response["archive"] = archive_result
    return response


def claim_scoped_outbox_rows(
    db: Session,
    *,
    client_id: UUID,
    allowed_branch_ids: list[UUID] | None,
    limit: int,
    idle_seconds: int,
    max_wait_seconds: int,
    include_without_conversation: bool,
) -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    idle_cutoff = now - timedelta(seconds=idle_seconds)
    max_wait_cutoff = now - timedelta(seconds=max_wait_seconds)

    query = (
        db.query(
            OutboxMessage.conversation_id.label("conversation_id"),
            func.max(OutboxMessage.created_at).label("last_created_at"),
            func.min(OutboxMessage.created_at).label("first_created_at"),
        )
        .filter(
            OutboxMessage.client_id == client_id,
            OutboxMessage.status == "PENDING",
            OutboxMessage.conversation_id.isnot(None),
            or_(OutboxMessage.next_attempt_at.is_(None), OutboxMessage.next_attempt_at <= now),
        )
        .group_by(OutboxMessage.conversation_id)
        .order_by(func.max(OutboxMessage.created_at).asc())
        .limit(limit)
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return []
        query = query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))

    batches = query.all()
    conversation_ids: list[UUID] = []
    for batch in batches:
        if not batch.conversation_id:
            continue
        is_idle = bool(batch.last_created_at and batch.last_created_at <= idle_cutoff)
        is_max_wait = bool(max_wait_seconds > 0 and batch.first_created_at and batch.first_created_at <= max_wait_cutoff)
        if is_idle or is_max_wait:
            conversation_ids.append(batch.conversation_id)

    single_message_ids: list[UUID] = []
    remaining_slots = max(0, limit - len(conversation_ids))
    if include_without_conversation and remaining_slots > 0:
        age_filters = [OutboxMessage.created_at <= idle_cutoff]
        if max_wait_seconds > 0:
            age_filters.append(OutboxMessage.created_at <= max_wait_cutoff)
        singles_query = (
            db.query(OutboxMessage.id)
            .filter(
                OutboxMessage.client_id == client_id,
                OutboxMessage.status == "PENDING",
                OutboxMessage.conversation_id.is_(None),
                or_(OutboxMessage.next_attempt_at.is_(None), OutboxMessage.next_attempt_at <= now),
                or_(*age_filters),
            )
            .order_by(OutboxMessage.created_at.asc(), OutboxMessage.id.asc())
            .limit(remaining_slots)
        )
        if allowed_branch_ids is not None:
            singles_query = singles_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
        single_message_ids = [row.id for row in singles_query.all()]

    if not conversation_ids and not single_message_ids:
        return []

    filters = []
    if conversation_ids:
        filters.append(OutboxMessage.conversation_id.in_(conversation_ids))
    if single_message_ids:
        filters.append(OutboxMessage.id.in_(single_message_ids))

    rows_query = (
        db.query(OutboxMessage)
        .filter(
            OutboxMessage.client_id == client_id,
            OutboxMessage.status == "PENDING",
            or_(*filters),
        )
        .order_by(OutboxMessage.created_at.asc(), OutboxMessage.id.asc())
    )
    if allowed_branch_ids is not None:
        rows_query = rows_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
    rows = rows_query.all()

    for row in rows:
        row.status = "PROCESSING"
        row.attempts = int(row.attempts or 0) + 1
        row.updated_at = now
    db.commit()

    return [
        {
            "id": row.id,
            "client_id": row.client_id,
            "branch_id": row.branch_id,
            "conversation_id": row.conversation_id,
            "inbound_message_id": row.inbound_message_id,
            "payload_json": row.payload_json,
            "attempts": row.attempts,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def _find_message_by_message_id(db: Session, client_id: UUID, message_id: str):
    if not message_id:
        return None
    return (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            or_(
                Message.message_metadata["message_id"].astext == message_id,
                Message.message_metadata["messageId"].astext == message_id,
            ),
        )
        .order_by(Message.created_at.desc())
        .first()
    )


def _find_message_by_conversation_created_at(
    db: Session,
    conversation_id: UUID,
    created_at: datetime | None,
    *,
    message_text: str | None = None,
):
    if not conversation_id or not created_at:
        return None
    window_start = created_at - timedelta(seconds=120)
    window_end = created_at + timedelta(seconds=120)
    rows = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == "user",
            Message.created_at >= window_start,
            Message.created_at <= window_end,
        )
        .order_by(Message.created_at.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return None
    normalized_target = normalize_for_matching(message_text) if message_text else ""
    if normalized_target:
        for msg in rows:
            if normalize_for_matching(msg.content or "") == normalized_target:
                return msg
    return min(
        rows,
        key=lambda msg: abs((msg.created_at - created_at).total_seconds()) if msg.created_at else float("inf"),
    )


def _ensure_rag_meta_defaults(message) -> None:
    if not message:
        return
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    rag_scores = decision_meta.get("rag_scores")
    if not isinstance(rag_scores, dict):
        rag_scores = {}
    for key, default_value in {
        "bm25_max": 0.0,
        "vector_max": 0.0,
        "hybrid_max": 0.0,
    }.items():
        if not isinstance(rag_scores.get(key), (int, float)):
            rag_scores[key] = default_value
    updates = {"rag_scores": rag_scores}
    if "rag_confident" not in decision_meta:
        updates["rag_confident"] = False
    if "rag_reason" not in decision_meta:
        updates["rag_reason"] = "overridden_by_gate"
    if "router_eligible" not in decision_meta:
        updates["router_eligible"] = False
    if "router_skipped_reason" not in decision_meta:
        updates["router_skipped_reason"] = "not_run"
    _update_message_decision_metadata(message, updates)


def _get_outbox_window_merge_seconds() -> float:
    raw = os.environ.get("OUTBOX_WINDOW_MERGE_SECONDS", "2.5")
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, seconds)


def _coerce_outbox_created_at(value: datetime | None) -> datetime:
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _use_provider_gateway_outbound() -> bool:
    return _is_env_enabled(os.environ.get("PROVIDER_GATEWAY_OUTBOUND_ENABLED"), default=False)


def _is_outbox_event(payload_json: dict | None) -> bool:
    return isinstance(payload_json, dict) and payload_json.get("schema_version") == "outbox.v1"


def _is_send_text_event(payload_json: dict | None) -> bool:
    return _is_outbox_event(payload_json) and payload_json.get("event_type") == "whatsapp.send_text"


def _is_send_media_event(payload_json: dict | None) -> bool:
    return _is_outbox_event(payload_json) and payload_json.get("event_type") == "whatsapp.send_media"


def _split_outbox_batches(batch_sorted: list[dict], window_seconds: float) -> list[list[dict]]:
    if not batch_sorted:
        return []
    if window_seconds <= 0:
        return [batch_sorted]
    groups: list[list[dict]] = []
    current: list[dict] = []
    last_created: datetime | None = None
    for row in batch_sorted:
        created_at = _coerce_outbox_created_at(row.get("created_at"))
        if not current:
            current.append(row)
            last_created = created_at
            continue
        if last_created and (created_at - last_created).total_seconds() <= window_seconds:
            current.append(row)
        else:
            groups.append(current)
            current = [row]
        last_created = created_at
    if current:
        groups.append(current)
    return groups


def _merge_nested_dict(base: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


def _is_permanent_delivery_error(error_text: str) -> bool:
    return is_permanent_provider_error(error_text)


def _classify_transport_degradation(error_text: str | None) -> dict[str, str] | None:
    classified = classify_provider_error(error_text)
    if classified.kind != "billing_blocked":
        return None
    return {
        "delivery_state": "transport_degraded",
        "delivery_error_code": classified.error_code or "CHATFLOW_BILLING_BLOCKED",
        "delivery_error_class": classified.incident_reason_code,
        "delivery_error_kind": classified.kind,
    }


async def _prepare_skip_persist(
    *,
    db: Session,
    client: Client,
    conversation_id: UUID | None,
    message_id: str | None,
    remote_jid: str,
    message_text: str,
    media_info,
    media_policy: dict | None,
    media_redis_client,
    count_rate_limit: bool,
    outbox_created_at: datetime | None,
    timing_context: dict,
    resolve_trace_conversation,
    record_early_trace,
) -> tuple[WebhookResponse | None, Conversation | None, User | None, Message | None, object | None]:
    if not conversation_id:
        trace_conversation = resolve_trace_conversation(
            trace_client=client,
            trace_conversation_id=None,
            trace_message_id=message_id,
            trace_remote_jid=remote_jid,
        )
        if record_early_trace(
            trace_conversation,
            stage="skip_persist",
            decision="reject",
            reason="missing_conversation_id",
        ):
            db.commit()
        return WebhookResponse(success=False, message="Missing conversation_id"), None, None, None, None
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        trace_conversation = resolve_trace_conversation(
            trace_client=client,
            trace_conversation_id=None,
            trace_message_id=message_id,
            trace_remote_jid=remote_jid,
        )
        if record_early_trace(
            trace_conversation,
            stage="skip_persist",
            decision="reject",
            reason="conversation_not_found",
        ):
            db.commit()
        return WebhookResponse(success=False, message="Conversation not found"), None, None, None, None
    user = db.query(User).filter(User.id == conversation.user_id).first()
    if not user:
        _record_decision_trace(
            conversation,
            {
                "stage": "skip_persist",
                "decision": "reject",
                "reason": "user_not_found",
                "state": conversation.state,
            },
        )
        db.commit()
        return WebhookResponse(success=False, message="User not found"), None, None, None, None
    timing_context["conversation_id"] = str(conversation.id)
    saved_message = None
    if message_id:
        saved_message = _find_message_by_message_id(db, client.id, message_id)
    if not saved_message and outbox_created_at:
        saved_message = _find_message_by_conversation_created_at(
            db,
            conversation.id,
            outbox_created_at,
            message_text=message_text,
        )
    _ensure_rag_meta_defaults(saved_message)
    media_decision = None
    if media_info and saved_message:
        saved_media = (
            saved_message.message_metadata.get("media")
            if isinstance(saved_message.message_metadata, dict)
            else None
        )
        media_decision = _deserialize_media_decision(
            saved_media.get("decision") if isinstance(saved_media, dict) else None
        )
    if media_info and media_decision is None and media_policy:
        media_decision = await _evaluate_media_decision(
            media=media_info,
            client_id=client.id,
            remote_jid=remote_jid,
            policy=media_policy,
            redis_client=media_redis_client,
            count_rate_limit=count_rate_limit,
        )
    return None, conversation, user, saved_message, media_decision


async def _handle_enqueue_only_accept(
    *,
    db: Session,
    client: Client,
    conversation: Conversation,
    payload: WebhookRequest,
    remote_jid: str,
    message_id: str | None,
    message_text: str,
    metadata,
    saved_message: Message | None,
    media_info,
    media_policy: dict | None,
    media_decision,
) -> WebhookResponse:
    storage_path = None
    store_media_enabled = bool(media_policy and media_policy.get("store_media"))
    if media_info and store_media_enabled and (media_decision is None or media_decision.allowed):
        if saved_message and isinstance(saved_message.message_metadata, dict):
            storage_path = (saved_message.message_metadata.get("media") or {}).get("storage_path")
        if not storage_path:
            storage_result = await _store_media_locally(
                media=media_info,
                policy=media_policy,
                client_slug=client.name,
                conversation_id=conversation.id,
                message_id=message_id,
            )
            if storage_result.get("stored"):
                storage_path = storage_result.get("path")
            if saved_message:
                update_payload = {
                    "storage_path": storage_result.get("path"),
                    "stored": bool(storage_result.get("stored")),
                    "storage_error": storage_result.get("error"),
                    "size_bytes": storage_result.get("size_bytes") or media_info.size_bytes,
                    "sha256": storage_result.get("sha256"),
                }
                _update_message_media_metadata(saved_message, update_payload)
        elif saved_message:
            media_meta = saved_message.message_metadata.get("media") or {}
            if not media_meta.get("public_url"):
                _update_message_media_metadata(saved_message, {})

    if (
        conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]
        and conversation.telegram_topic_id
    ):
        bot_token, chat_id = get_telegram_credentials(db, client.id)
        if bot_token and chat_id:
            already_forwarded = bool(metadata and metadata.forwarded_to_telegram)
            if not already_forwarded:
                telegram = TelegramService(bot_token)
                forward_result = None
                if (
                    media_info
                    and media_decision
                    and media_decision.allowed
                    and (media_policy or {}).get("forward_to_telegram")
                ):
                    caption = _build_media_caption(message_text, media_info)
                    forward_result = _send_telegram_media(
                        telegram=telegram,
                        chat_id=chat_id,
                        topic_id=conversation.telegram_topic_id,
                        media=media_info,
                        caption=caption,
                        stored_path=storage_path,
                    )
                else:
                    forward_result = telegram.send_message(
                        chat_id=chat_id,
                        text=f"👤 <b>Клиент:</b> {message_text}",
                        message_thread_id=conversation.telegram_topic_id,
                    )
                if forward_result and forward_result.get("ok"):
                    if metadata:
                        metadata.forwarded_to_telegram = True
                    logger.info(
                        "Fast-forwarded inbound message to Telegram",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                            }
                        },
                    )
                else:
                    logger.warning(
                        "Fast-forward to Telegram failed",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                                "error": forward_result.get("description") if forward_result else None,
                            }
                        },
                    )
    inbound_message_id = build_inbound_message_id(
        message_id, remote_jid, metadata.timestamp if metadata else None, message_text
    )
    payload_json = payload.model_dump(exclude_none=True)
    tenant_context = {
        "client_id": str(client.id),
        "branch_id": str(conversation.branch_id) if conversation and conversation.branch_id else None,
        "client_slug": client.name,
        "source": "webhook",
    }
    _merge_nested_dict(
        payload_json,
        {"tenant_context": {key: value for key, value in tenant_context.items() if value is not None}},
    )
    validated_payload, payload_error = validate_outbox_payload(
        payload_json,
        expected_client_slug=client.name,
    )
    if payload_error:
        _record_decision_trace(
            conversation,
            {
                "stage": "outbox_payload_guard",
                "decision": "reject",
                "reason": payload_error,
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="error",
            intent=None,
            source="outbox_payload_guard",
            fast_intent=False,
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "action_error": "outbox_payload_invalid",
                    "outbox_payload_error": payload_error,
                },
            )
        db.commit()
        return WebhookResponse(success=False, message="Invalid outbox payload")
    payload_json = validated_payload.model_dump(exclude_none=True)
    enqueued = enqueue_outbox_message(
        db,
        client_id=client.id,
        conversation_id=conversation.id,
        inbound_message_id=inbound_message_id,
        payload_json=payload_json,
        branch_id=conversation.branch_id,
    )
    if enqueued:
        logger.info(
            "Outbox enqueued",
            extra={
                "context": {
                    "client_slug": payload.client_slug,
                    "conversation_id": str(conversation.id),
                    "inbound_message_id": inbound_message_id,
                }
            },
        )
    else:
        logger.info(
            "Outbox duplicate skipped",
            extra={
                "context": {
                    "client_slug": payload.client_slug,
                    "conversation_id": str(conversation.id),
                    "inbound_message_id": inbound_message_id,
                }
            },
        )
    _record_decision_trace(
        conversation,
        {
            "stage": "outbox",
            "decision": "enqueue_only",
            "reason": "enqueued" if enqueued else "duplicate",
            "state": conversation.state,
        },
    )
    db.commit()
    return WebhookResponse(
        success=True,
        message="Accepted",
        conversation_id=conversation.id,
        bot_response=None,
    )


async def _process_outbox_rows(
    db: Session,
    rows: list[dict],
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, int]:
    results = {"claimed": len(rows), "sent": 0, "failed": 0, "retry_scheduled": 0}
    if not rows:
        return results

    picked_at = datetime.now(timezone.utc)
    pick_info: dict[str, dict[str, object]] = {}

    def _resolve_simulation_context(conversation_id: UUID | None) -> tuple[bool, str | None]:
        if not conversation_id:
            return False, None
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not conversation:
            return False, None
        sim_id = None
        if isinstance(conversation.context, dict):
            sim_ctx = conversation.context.get("simulation")
            if isinstance(sim_ctx, dict):
                sim_id = sim_ctx.get("id")
        return is_simulation_context(conversation), sim_id

    for row in rows:
        outbox_id = row.get("id")
        if not outbox_id:
            continue
        payload_json = row.get("payload_json") or {}
        created_at = row.get("created_at")
        conversation_id = row.get("conversation_id")
        branch_id = row.get("branch_id")
        if conversation_id:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if conversation and conversation.branch_id:
                branch_id = conversation.branch_id
        inbound_message_id = row.get("inbound_message_id")
        client_id = row.get("client_id")
        message_text = None
        if isinstance(payload_json, dict):
            body = payload_json.get("body")
            if isinstance(body, dict):
                message_text = body.get("message")
        outbox_id_str = str(outbox_id)
        simulation_mode, simulation_id = _resolve_simulation_context(conversation_id)
        pick_info[outbox_id_str] = {
            "picked_at": picked_at,
            "created_at": created_at,
            "conversation_id": conversation_id,
            "branch_id": branch_id,
            "client_slug": payload_json.get("client_slug"),
            "client_id": client_id,
            "inbound_message_id": inbound_message_id,
            "message_text": message_text,
            "simulation_mode": simulation_mode,
            "simulation_id": simulation_id,
        }
        logger.info(
            "Outbox picked",
            extra={
                    "context": {
                        "outbox_id": outbox_id_str,
                        "conversation_id": str(conversation_id) if conversation_id else None,
                        "branch_id": str(branch_id) if branch_id else None,
                        "client_slug": payload_json.get("client_slug"),
                        "inbound_message_id": inbound_message_id,
                        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
                        "outbox_picked_at": picked_at.isoformat(),
                    }
            },
        )

    def _resolve_outbox_message(outbox_id: str):
        info = pick_info.get(outbox_id, {})
        inbound_message_id = info.get("inbound_message_id")
        inbound_message_id_token = (
            str(inbound_message_id).strip() if inbound_message_id is not None else ""
        )
        client_id = info.get("client_id")
        message = None
        if client_id and inbound_message_id_token:
            message = _find_message_by_message_id(
                db,
                client_id,
                inbound_message_id_token,
            )
        if message:
            return message
        if inbound_message_id_token:
            # Avoid conversation+timestamp fallback when an explicit idempotency key
            # was provided but not found: synthetic ids (e.g. calendar sync keys)
            # can otherwise attach timing/error metadata to an unrelated user turn.
            return None
        if info.get("conversation_id") and info.get("created_at"):
            message = _find_message_by_conversation_created_at(
                db,
                info.get("conversation_id"),
                info.get("created_at"),
                message_text=info.get("message_text"),
            )
        return message

    def _merge_outbox_meta(outbox_id: str, meta_update: dict[str, object]) -> None:
        try:
            outbox_uuid = UUID(outbox_id)
        except (TypeError, ValueError):
            return
        outbox_row = db.query(OutboxMessage).filter(OutboxMessage.id == outbox_uuid).first()
        if not outbox_row:
            return
        existing = dict(outbox_row.meta or {})
        outbox_row.meta = _merge_nested_dict(existing, meta_update)

    def _record_outbox_payload_error(
        *,
        outbox_id: str,
        reason: str,
        stage: str = "outbox_payload_guard",
        record_trace: bool = True,
        record_message: bool = True,
    ) -> None:
        info = pick_info.get(outbox_id, {})
        conversation = None
        if record_trace and info.get("conversation_id"):
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == info.get("conversation_id"))
                .first()
            )
        if record_trace and conversation:
            _record_decision_trace(
                conversation,
                {
                    "stage": stage,
                    "decision": "reject",
                    "reason": reason,
                    "state": conversation.state,
                },
            )
        message = _resolve_outbox_message(outbox_id) if record_message else None
        if record_message and message:
            _record_message_decision_meta(
                message,
                action="error",
                intent=None,
                source=stage,
                fast_intent=False,
            )
            _update_message_decision_metadata(
                message,
                {
                    "action_error": "outbox_payload_invalid",
                    "outbox_payload_error": reason,
                },
            )
        _merge_outbox_meta(
            outbox_id,
            {"contract_error": reason},
        )

    def _validate_outbox_row_tenant_context(*, row: dict, payload_json: dict, outbox_id: str) -> str | None:
        if not isinstance(payload_json, dict):
            return None

        row_client_id = None
        row_client_raw = row.get("client_id")
        if row_client_raw:
            try:
                row_client_id = UUID(str(row_client_raw))
            except (TypeError, ValueError):
                row_client_id = None

        row_branch_id = None
        row_branch_raw = pick_info.get(outbox_id, {}).get("branch_id")
        if row_branch_raw:
            try:
                row_branch_id = UUID(str(row_branch_raw))
            except (TypeError, ValueError):
                row_branch_id = None

        payload_client_id_raw = payload_json.get("client_id")
        if payload_client_id_raw:
            try:
                payload_client_id = UUID(str(payload_client_id_raw))
            except (TypeError, ValueError):
                return "event:invalid_client_id"
            if row_client_id and payload_client_id != row_client_id:
                return "event:client_id_mismatch"

        payload_branch_id_raw = payload_json.get("branch_id")
        if payload_branch_id_raw:
            try:
                payload_branch_id = UUID(str(payload_branch_id_raw))
            except (TypeError, ValueError):
                return "event:invalid_branch_id"
            if row_branch_id and payload_branch_id != row_branch_id:
                return "event:branch_id_mismatch"

        tenant_context = payload_json.get("tenant_context")
        if tenant_context is None:
            return "event:missing_tenant_context"
        tenant_context, tenant_contract_error = validate_tenant_context_contract(tenant_context)
        if tenant_contract_error:
            return "event:invalid_tenant_context_contract"

        tenant_client_id_raw = tenant_context.get("client_id")
        if tenant_client_id_raw:
            try:
                tenant_client_id = UUID(str(tenant_client_id_raw))
            except (TypeError, ValueError):
                return "event:invalid_tenant_context_client_id"
            if row_client_id and tenant_client_id != row_client_id:
                return "event:tenant_context_client_mismatch"

        tenant_branch_id_raw = tenant_context.get("branch_id")
        if tenant_branch_id_raw:
            try:
                tenant_branch_id = UUID(str(tenant_branch_id_raw))
            except (TypeError, ValueError):
                return "event:invalid_tenant_context_branch_id"
            if row_branch_id and tenant_branch_id != row_branch_id:
                return "event:tenant_context_branch_mismatch"

        return None

    def _record_outbox_action_error(*, outbox_id: str, error: str) -> None:
        info = pick_info.get(outbox_id, {})
        conversation = None
        if info.get("conversation_id"):
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == info.get("conversation_id"))
                .first()
            )
        message = _resolve_outbox_message(outbox_id)
        if message and isinstance(message.message_metadata, dict):
            decision_meta = message.message_metadata.get("decision_meta")
            # Do not overwrite an already-recorded inbound decision with transport-side errors.
            if isinstance(decision_meta, dict) and decision_meta:
                return
        if conversation:
            _record_decision_trace(
                conversation,
                {
                    "stage": "action_gate",
                    "decision": "error",
                    "reason": "pipeline_exception",
                    "error": error,
                    "state": conversation.state,
                },
            )
        if message:
            _record_message_decision_meta(
                message,
                action="error",
                intent=None,
                source="action_gate",
                fast_intent=False,
            )
            _update_message_decision_metadata(
                message,
                {
                    "action_error": "pipeline_exception",
                    "action_error_detail": error,
                },
            )

    def _record_outbox_transport_degraded(
        *,
        outbox_id: str,
        error: str,
        degradation_meta: dict[str, str],
    ) -> None:
        info = pick_info.get(outbox_id, {})
        conversation = None
        if info.get("conversation_id"):
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == info.get("conversation_id"))
                .first()
            )
        if conversation:
            _record_decision_trace(
                conversation,
                {
                    "stage": "transport",
                    "decision": "degraded",
                    "reason": degradation_meta.get("delivery_error_class"),
                    "error_code": degradation_meta.get("delivery_error_code"),
                    "error": error,
                    "state": conversation.state,
                },
            )
        message = _resolve_outbox_message(outbox_id)
        if message:
            _update_message_decision_metadata(
                message,
                {
                    "delivery_state": degradation_meta.get("delivery_state"),
                    "delivery_error_code": degradation_meta.get("delivery_error_code"),
                    "delivery_error_class": degradation_meta.get("delivery_error_class"),
                    "delivery_error_kind": degradation_meta.get("delivery_error_kind"),
                    "transport_degraded": True,
                },
            )
        _merge_outbox_meta(
            outbox_id,
            {
                "transport": {
                    "state": degradation_meta.get("delivery_state"),
                    "error_code": degradation_meta.get("delivery_error_code"),
                    "error_class": degradation_meta.get("delivery_error_class"),
                    "error_kind": degradation_meta.get("delivery_error_kind"),
                    "error": error,
                }
            },
        )

    def _notify_outbox_failure(
        *,
        outbox_id: str,
        reason: str,
        error: str | None = None,
        provider: str | None = None,
        attempts: int | None = None,
    ) -> None:
        info = pick_info.get(outbox_id, {})
        if info.get("simulation_mode"):
            return
        client_slug = info.get("client_slug")
        record_delivery_failure(
            client_slug,
            source="outbox",
            provider=provider or "internal",
            reason=reason,
        )
        alert_error(
            "Outbox delivery failed",
            {
                "outbox_id": outbox_id,
                "client_slug": client_slug,
                "conversation_id": str(info.get("conversation_id"))
                if info.get("conversation_id")
                else None,
                "inbound_message_id": info.get("inbound_message_id"),
                "provider": provider or "internal",
                "reason": reason,
                "error": error,
                "attempts": attempts,
            },
        )

    def _persist_outbox_timing(
        *,
        outbox_id: str,
        done_at: datetime,
        wait_ms: float | None,
        process_ms: float | None,
        total_ms: float | None,
        error: str | None,
    ) -> None:
        info = pick_info.get(outbox_id, {})
        inbound_message_id = info.get("inbound_message_id")
        message = _resolve_outbox_message(outbox_id)
        if not message:
            logger.warning(
                "Outbox timing message not found",
                extra={
                    "context": {
                        "outbox_id": outbox_id,
                        "inbound_message_id": str(inbound_message_id) if inbound_message_id else None,
                    }
                },
            )
            return
        payload = {
            "outbox": {
                "outbox_id": outbox_id,
                "inbound_message_id": str(inbound_message_id) if inbound_message_id else None,
                "created_at": info.get("created_at").isoformat()
                if isinstance(info.get("created_at"), datetime)
                else info.get("created_at"),
                "picked_at": info.get("picked_at").isoformat()
                if isinstance(info.get("picked_at"), datetime)
                else info.get("picked_at"),
                "done_at": done_at.isoformat(),
                "wait_ms": round(wait_ms, 2) if wait_ms is not None else None,
                "process_ms": round(process_ms, 2) if process_ms is not None else None,
                "total_ms": round(total_ms, 2) if total_ms is not None else None,
            }
        }
        if error:
            payload["outbox"]["error"] = error
        if process_ms is not None:
            payload["stages"] = {"outbox_process_ms": round(process_ms, 2)}
        _merge_message_timing(message, payload)

        decision_meta = {}
        if isinstance(message.message_metadata, dict):
            decision_meta = message.message_metadata.get("decision_meta") or {}
        trace_id = None
        if isinstance(decision_meta, dict):
            trace_id = decision_meta.get("trace_id")
        outbox_meta_update = {
            "timing": payload["outbox"],
            "correlation": {
                "inbound_message_id": str(inbound_message_id) if inbound_message_id else None,
                "trace_id": trace_id,
            },
        }
        _merge_outbox_meta(outbox_id, outbox_meta_update)

    def _log_outbox_done(
        outbox_id: str,
        *,
        error: str | None = None,
        total_ms: float | None = None,
    ) -> None:
        info = pick_info.get(outbox_id, {})
        done_at = datetime.now(timezone.utc)
        created_at = info.get("created_at")
        picked_at_info = info.get("picked_at")
        trace_id = None
        message = _resolve_outbox_message(outbox_id)
        if message and isinstance(message.message_metadata, dict):
            decision_meta = message.message_metadata.get("decision_meta")
            if isinstance(decision_meta, dict):
                trace_id = decision_meta.get("trace_id")
        wait_ms = None
        process_ms = None
        if isinstance(created_at, datetime) and isinstance(picked_at_info, datetime):
            wait_ms = (picked_at_info - created_at).total_seconds() * 1000
        if isinstance(picked_at_info, datetime):
            process_ms = (done_at - picked_at_info).total_seconds() * 1000
        if wait_ms is not None:
            record_outbox_latency(info.get("client_slug"), wait_ms)
        context = {
            "outbox_id": outbox_id,
            "inbound_message_id": info.get("inbound_message_id"),
            "conversation_id": str(info.get("conversation_id")) if info.get("conversation_id") else None,
            "client_slug": info.get("client_slug"),
            "trace_id": trace_id,
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
            "outbox_picked_at": picked_at_info.isoformat()
            if isinstance(picked_at_info, datetime)
            else picked_at_info,
            "outbox_done_at": done_at.isoformat(),
            "wait_ms": round(wait_ms, 2) if wait_ms is not None else None,
            "process_ms": round(process_ms, 2) if process_ms is not None else None,
        }
        if error:
            context["error"] = error
        logger.info("Outbox done", extra={"context": context})
        if process_ms is not None:
            logger.info(
                "Timing",
                extra={
                    "context": {
                        "message_id": str(info.get("inbound_message_id"))
                        if info.get("inbound_message_id")
                        else None,
                        "outbox_id": outbox_id,
                        "trace_id": trace_id,
                        "stage": "outbox_process_ms",
                        "elapsed_ms": round(process_ms, 2),
                        "client_slug": info.get("client_slug"),
                        "conversation_id": str(info.get("conversation_id"))
                        if info.get("conversation_id")
                        else None,
                    }
                },
            )
        _persist_outbox_timing(
            outbox_id=outbox_id,
            done_at=done_at,
            wait_ms=wait_ms,
            process_ms=process_ms,
            total_ms=total_ms,
            error=error,
        )

    def _row_has_media(row: dict) -> bool:
        payload_json = row.get("payload_json") or {}
        if _is_outbox_event(payload_json):
            return False
        try:
            payload = WebhookRequest.model_validate(payload_json)
        except Exception:
            return False
        message_type = (payload.body.messageType or "").strip().lower()
        return bool(payload.body.mediaData) or (message_type and message_type != "text")

    async def _process_single_row(row: dict, *, conversation_id: str) -> None:
        outbox_id = row.get("id")
        if not outbox_id:
            return
        payload_json = row.get("payload_json") or {}
        outbox_id_str = str(outbox_id)
        client_slug = payload_json.get("client_slug")
        outbox_ids = [outbox_id_str]
        timing_start = time.monotonic()

        tenant_guard_error = _validate_outbox_row_tenant_context(
            row=row,
            payload_json=payload_json,
            outbox_id=outbox_id_str,
        )
        if tenant_guard_error:
            _record_outbox_payload_error(outbox_id=outbox_id_str, reason=tenant_guard_error)
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="FAILED",
                last_error=f"invalid_payload:{tenant_guard_error}"[:500],
                next_attempt_at=None,
            )
            _notify_outbox_failure(
                outbox_id=outbox_id_str,
                reason="invalid_payload",
                error=tenant_guard_error,
                provider=payload_json.get("provider") or "internal",
                attempts=int(row.get("attempts") or 0),
            )
            results["failed"] += 1
            return

        sim_info = pick_info.get(outbox_id_str, {})
        message = _resolve_outbox_message(outbox_id_str)
        if sim_info.get("simulation_mode"):
            _merge_outbox_meta(
                outbox_id_str,
                {"simulation": {"mode": True, "id": sim_info.get("simulation_id")}},
            )
            if message:
                _update_message_decision_metadata(message, {"outbox_simulated": True})
            outbox_total_ms = round((time.monotonic() - timing_start) * 1000, 2)
            _log_outbox_done(outbox_id_str, total_ms=outbox_total_ms)
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="SENT",
                last_error=None,
                next_attempt_at=None,
            )
            results["sent"] += 1
            return
        span_context = {
            "message_id": row.get("inbound_message_id"),
            "outbox_id": outbox_id_str,
            "client_slug": client_slug,
            "conversation_id": conversation_id,
        }
        branch_id = sim_info.get("branch_id")
        if branch_id:
            span_context["branch_id"] = str(branch_id)
        if message and isinstance(message.message_metadata, dict):
            decision_meta = message.message_metadata.get("decision_meta")
            if isinstance(decision_meta, dict) and decision_meta.get("trace_id"):
                span_context["trace_id"] = decision_meta.get("trace_id")

        try:
            if _is_outbox_event(payload_json):
                event_type = payload_json.get("event_type")
                if event_type in {
                    OUTBOX_EVENT_CALENDAR_SYNC_OUTBOUND,
                    OUTBOX_EVENT_CALENDAR_SYNC_INBOUND,
                }:
                    if event_type == OUTBOX_EVENT_CALENDAR_SYNC_OUTBOUND:
                        ok, error = process_outbound_sync_event(
                            db=db,
                            payload_json=payload_json,
                        )
                    else:
                        ok, error = process_inbound_sync_event(
                            db=db,
                            payload_json=payload_json,
                        )
                    if not ok:
                        if error in {
                            "missing_fields",
                            "invalid_appointment_id",
                            "appointment_not_found",
                            "missing_branch_id",
                            "invalid_branch_id",
                            "branch_not_found",
                            "connection_missing",
                            "unsupported_action",
                        }:
                            _record_outbox_payload_error(
                                outbox_id=outbox_id_str,
                                reason=f"event:{error}",
                                record_trace=False,
                                record_message=False,
                            )
                            mark_outbox_status(
                                db,
                                outbox_id=outbox_id,
                                status="FAILED",
                                last_error=f"invalid_payload:{error}"[:500],
                                next_attempt_at=None,
                            )
                            _notify_outbox_failure(
                                outbox_id=outbox_id_str,
                                reason="invalid_payload",
                                error=f"event:{error}",
                                provider="calendar",
                                attempts=int(row.get("attempts") or 0),
                            )
                            results["failed"] += 1
                            return
                        raise RuntimeError(f"calendar_sync_failed:{error or 'unknown'}")
                    results["sent"] += 1
                    return
                if event_type == OUTBOX_EVENT_KNOWLEDGE_SYNC:
                    ok, error = process_knowledge_sync_event(
                        db=db,
                        payload_json=payload_json,
                    )
                    if not ok:
                        _record_outbox_action_error(
                            outbox_id=outbox_id_str,
                            error=f"knowledge_sync:{error or 'unknown'}",
                        )
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="FAILED",
                            last_error=f"knowledge_sync:{error or 'unknown'}"[:500],
                            next_attempt_at=None,
                        )
                        _notify_outbox_failure(
                            outbox_id=outbox_id_str,
                            reason="knowledge_sync_failed",
                            error=error or "unknown",
                            provider="knowledge",
                            attempts=int(row.get("attempts") or 0),
                        )
                        results["failed"] += 1
                        return
                    results["sent"] += 1
                    return
                if event_type not in {"whatsapp.send_text", "whatsapp.send_media"}:
                    _record_outbox_payload_error(
                        outbox_id=outbox_id_str,
                        reason=f"event:{event_type}",
                        record_trace=False,
                        record_message=False,
                    )
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="FAILED",
                        last_error=f"invalid_payload:unsupported_event:{event_type}"[:500],
                        next_attempt_at=None,
                    )
                    _notify_outbox_failure(
                        outbox_id=outbox_id_str,
                        reason="invalid_payload",
                        error=f"event:{event_type}",
                        provider="internal",
                        attempts=int(row.get("attempts") or 0),
                    )
                    results["failed"] += 1
                    return
                payload = payload_json.get("payload") or {}
                remote_jid = payload.get("remote_jid")
                instance_id = payload.get("instance_id")
                idempotency_key = payload.get("idempotency_key") or payload_json.get("idempotency_key")
                if not remote_jid or not instance_id:
                    _record_outbox_payload_error(outbox_id=outbox_id_str, reason="event:missing_fields")
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="FAILED",
                        last_error="invalid_payload:missing_fields",
                        next_attempt_at=None,
                    )
                    _notify_outbox_failure(
                        outbox_id=outbox_id_str,
                        reason="invalid_payload",
                        error="event:missing_fields",
                        provider="internal",
                        attempts=int(row.get("attempts") or 0),
                    )
                    results["failed"] += 1
                    return
                use_gateway = _use_provider_gateway_outbound()
                provider_name = payload_json.get("provider") or "chatflow"
                channel_name = payload_json.get("channel") or "whatsapp"
                if use_gateway:
                    adapter = ProviderGatewayAdapter()
                    options = MessageOptions(
                        idempotency_key=idempotency_key,
                        extra={
                            "outbox_id": outbox_id_str,
                            "tenant_context": payload_json.get("tenant_context"),
                            "provider": provider_name,
                            "channel": channel_name,
                            "callback_url": os.environ.get("PROVIDER_GATEWAY_STATUS_CALLBACK_URL"),
                            "metadata": {
                                "event_type": payload_json.get("event_type"),
                                "conversation_id": payload_json.get("conversation_id"),
                                "client_id": payload_json.get("client_id"),
                                "branch_id": payload_json.get("branch_id"),
                                "instance_id": instance_id,
                            },
                        },
                    )
                else:
                    adapter = ChatFlowAdapter()
                    options = MessageOptions(
                        instance_id=instance_id,
                        idempotency_key=idempotency_key,
                    )

                if event_type == "whatsapp.send_text":
                    text = payload.get("text")
                    if not text:
                        _record_outbox_payload_error(outbox_id=outbox_id_str, reason="event:missing_text")
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="FAILED",
                            last_error="invalid_payload:missing_text",
                            next_attempt_at=None,
                        )
                        _notify_outbox_failure(
                            outbox_id=outbox_id_str,
                            reason="invalid_payload",
                            error="event:missing_text",
                            provider=provider_name,
                            attempts=int(row.get("attempts") or 0),
                        )
                        results["failed"] += 1
                        return
                    with start_span("outbox.send", context=span_context) as span:
                        result = adapter.send_text(remote_jid, text, options)
                else:
                    media_url = payload.get("media_url") or payload.get("signed_url")
                    media_type = payload.get("media_type")
                    caption = payload.get("caption")
                    media_meta = payload.get("media_meta")
                    if not media_url or not media_type:
                        _record_outbox_payload_error(outbox_id=outbox_id_str, reason="event:missing_media")
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="FAILED",
                            last_error="invalid_payload:missing_media",
                            next_attempt_at=None,
                        )
                        _notify_outbox_failure(
                            outbox_id=outbox_id_str,
                            reason="invalid_payload",
                            error="event:missing_media",
                            provider=provider_name,
                            attempts=int(row.get("attempts") or 0),
                        )
                        results["failed"] += 1
                        return
                    if caption:
                        options.caption = caption
                    if use_gateway and isinstance(options.extra, dict) and isinstance(media_meta, dict):
                        options.extra["media_meta"] = media_meta
                    with start_span("outbox.send", context=span_context) as span:
                        result = adapter.send_media(remote_jid, media_url, media_type, options)
                if span is not None:
                    span.set_attribute("send.ok", result.is_ok())
                if not result.is_ok():
                    raise RuntimeError(f"Outbound delivery failed: {result.error}")
                if use_gateway and outbox_id_str:
                    sent = result.unwrap()
                    _merge_outbox_meta(
                        outbox_id_str,
                        {
                            "provider_gateway": {
                                "provider": provider_name,
                                "channel": channel_name,
                                "message_id": sent.message_id,
                                "response": sent.provider_response,
                            }
                        },
                    )
            else:
                validated_payload, payload_error = validate_outbox_payload(payload_json)
                if payload_error:
                    _record_outbox_payload_error(outbox_id=outbox_id_str, reason=payload_error)
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="FAILED",
                        last_error=f"invalid_payload:{payload_error}"[:500],
                        next_attempt_at=None,
                    )
                    _notify_outbox_failure(
                        outbox_id=outbox_id_str,
                        reason="invalid_payload",
                        error=payload_error,
                        provider="internal",
                        attempts=int(row.get("attempts") or 0),
                    )
                    results["failed"] += 1
                    return
                payload_json = validated_payload.model_dump(exclude_none=True)
                payload = WebhookRequest.model_validate(payload_json)
                client_slug = payload.client_slug
                from app.core.consultant_core_v2 import handle_webhook_payload as handle_consultant_core_v2

                with start_span("outbox.process", context=span_context):
                    response = await handle_consultant_core_v2(
                        payload,
                        db,
                        provided_secret=None,
                        enforce_secret=False,
                        skip_persist=True,
                        conversation_id=UUID(conversation_id),
                        outbox_ids=outbox_ids,
                        outbox_created_at=row.get("created_at"),
                    )
                if not response.success:
                    raise RuntimeError(response.message)

            outbox_total_ms = round((time.monotonic() - timing_start) * 1000, 2)
            logger.info(
                "Outbox timing",
                extra={
                    "context": {
                        "outbox_id": outbox_id_str,
                        "outbox_ids": outbox_ids,
                        "conversation_id": conversation_id,
                        "client_slug": client_slug,
                        "inbound_message_id": row.get("inbound_message_id"),
                        "outbox_total_ms": outbox_total_ms,
                    }
                },
            )
            _log_outbox_done(outbox_id_str, total_ms=outbox_total_ms)
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="SENT",
                last_error=None,
                next_attempt_at=None,
            )
            results["sent"] += 1
        except Exception as exc:
            commit_on_failure = (
                isinstance(exc, RuntimeError)
                and str(exc).strip() == "ChatFlow delivery failed"
            )
            if commit_on_failure:
                try:
                    db.commit()
                except Exception as commit_exc:
                    logger.warning(
                        "Outbox commit failed after delivery error",
                        extra={"context": {"error": str(commit_exc)}},
                    )
                    try:
                        db.rollback()
                    except Exception as rollback_exc:
                        logger.warning(
                            "Outbox rollback failed",
                            extra={"context": {"error": str(rollback_exc)}},
                        )
            else:
                try:
                    db.rollback()
                except Exception as rollback_exc:
                    logger.warning(
                        "Outbox rollback failed",
                        extra={"context": {"error": str(rollback_exc)}},
                    )
            outbox_total_ms = round((time.monotonic() - timing_start) * 1000, 2)
            logger.info(
                "Outbox timing",
                extra={
                    "context": {
                        "outbox_id": outbox_id_str,
                        "outbox_ids": [outbox_id_str],
                        "conversation_id": conversation_id,
                        "client_slug": client_slug,
                        "inbound_message_id": row.get("inbound_message_id"),
                        "outbox_total_ms": outbox_total_ms,
                        "error": str(exc),
                    }
                },
            )
            degradation_meta = _classify_transport_degradation(str(exc))
            if degradation_meta:
                _record_outbox_transport_degraded(
                    outbox_id=outbox_id_str,
                    error=str(exc),
                    degradation_meta=degradation_meta,
                )
            else:
                _record_outbox_action_error(outbox_id=outbox_id_str, error=str(exc))
            _log_outbox_done(outbox_id_str, error=str(exc), total_ms=outbox_total_ms)
            now = datetime.now(timezone.utc)
            attempts = int(row.get("attempts") or 0)
            if _is_permanent_delivery_error(str(exc)):
                mark_outbox_status(
                    db,
                    outbox_id=outbox_id,
                    status="FAILED",
                    last_error=str(exc)[:500],
                    next_attempt_at=None,
                )
                provider_name = payload_json.get("provider") or "chatflow"
                _notify_outbox_failure(
                    outbox_id=outbox_id_str,
                    reason=(
                        degradation_meta.get("delivery_error_class")
                        if isinstance(degradation_meta, dict)
                        else "permanent_provider_error"
                    ),
                    error=str(exc),
                    provider=provider_name,
                    attempts=attempts,
                )
                results["failed"] += 1
                return
            if attempts >= max_attempts:
                mark_outbox_status(
                    db,
                    outbox_id=outbox_id,
                    status="FAILED",
                    last_error=str(exc)[:500],
                    next_attempt_at=None,
                )
                provider_name = payload_json.get("provider") or "chatflow"
                _notify_outbox_failure(
                    outbox_id=outbox_id_str,
                    reason="max_attempts",
                    error=str(exc),
                    provider=provider_name,
                    attempts=attempts,
                )
                results["failed"] += 1
                return
            backoff = retry_backoff_seconds * (2 ** max(attempts - 1, 0))
            next_attempt_at = now + timedelta(seconds=backoff)
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="PENDING",
                last_error=str(exc)[:500],
                next_attempt_at=next_attempt_at,
            )
            results["retry_scheduled"] += 1

    event_rows: list[dict] = []
    webhook_rows: list[dict] = []
    for row in rows:
        payload_json = row.get("payload_json") or {}
        if _is_outbox_event(payload_json):
            event_rows.append(row)
        else:
            webhook_rows.append(row)

    for row in event_rows:
        conversation_id = row.get("conversation_id")
        await _process_single_row(
            row,
            conversation_id=str(conversation_id) if conversation_id else "",
        )

    rows = webhook_rows
    if not rows:
        return results

    batches: dict[str, list[dict]] = {}
    for row in rows:
        conversation_id = row.get("conversation_id")
        if not conversation_id:
            continue
        batches.setdefault(str(conversation_id), []).append(row)

    for conversation_id, batch in batches.items():
        batch_sorted = sorted(
            batch,
            key=lambda r: r.get("created_at")
            if isinstance(r.get("created_at"), datetime)
            else datetime.min.replace(tzinfo=timezone.utc),
        )
        if any(_row_has_media(row) for row in batch_sorted):
            for row in batch_sorted:
                await _process_single_row(row, conversation_id=str(conversation_id))
            logger.info(
                "Outbox processed (media rows)",
                extra={"context": {"conversation_id": conversation_id, "count": len(batch_sorted)}},
            )
            continue

        window_seconds = _get_outbox_window_merge_seconds()
        grouped_batches = _split_outbox_batches(batch_sorted, window_seconds)
        for group in grouped_batches:
            outbox_ids = []
            message_texts = []
            forwarded_in_batch = False
            group_created_at = None
            valid_rows: list[tuple[dict, WebhookRequest]] = []
            invalid_count = 0
            for row in group:
                payload_json = row.get("payload_json") or {}
                outbox_id = row.get("id")
                outbox_id_str = str(outbox_id) if outbox_id else None
                validated_payload, payload_error = validate_outbox_payload(payload_json)
                if payload_error:
                    if outbox_id_str:
                        _record_outbox_payload_error(outbox_id=outbox_id_str, reason=payload_error)
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="FAILED",
                            last_error=f"invalid_payload:{payload_error}"[:500],
                            next_attempt_at=None,
                        )
                        _notify_outbox_failure(
                            outbox_id=outbox_id_str,
                            reason="invalid_payload",
                            error=payload_error,
                            provider="internal",
                            attempts=int(row.get("attempts") or 0),
                        )
                        results["failed"] += 1
                    invalid_count += 1
                    continue
                payload_json = validated_payload.model_dump(exclude_none=True)
                payload = WebhookRequest.model_validate(payload_json)
                valid_rows.append((row, payload))
                created_at = _coerce_outbox_created_at(row.get("created_at"))
                if created_at and (group_created_at is None or created_at > group_created_at):
                    group_created_at = created_at
                if payload.body.metadata and payload.body.metadata.forwarded_to_telegram:
                    forwarded_in_batch = True
                text = payload.body.message or ""
                if text.strip():
                    message_texts.append(text.strip())

            if not valid_rows:
                logger.warning(
                    "Outbox batch skipped (invalid payloads)",
                    extra={
                        "context": {
                            "conversation_id": conversation_id,
                            "invalid_count": invalid_count,
                        }
                    },
                )
                continue

            outbox_ids = [row.get("id") for row, _ in valid_rows]
            inbound_message_ids = [row.get("inbound_message_id") for row, _ in valid_rows]
            base_payload = valid_rows[-1][1]
            combined_text = " ".join(message_texts).strip()
            if combined_text:
                base_payload.body.message = combined_text
            if forwarded_in_batch and base_payload.body.metadata:
                base_payload.body.metadata.forwarded_to_telegram = True

            logger.info(
                "Outbox processing start",
                extra={
                    "context": {
                        "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                        "inbound_message_ids": inbound_message_ids,
                        "conversation_id": conversation_id,
                        "attempts": valid_rows[-1][0].get("attempts"),
                        "coalesced_count": len(valid_rows),
                        "invalid_count": invalid_count,
                        "window_merge_seconds": window_seconds,
                    }
                },
            )

            try:
                from app.core.consultant_core_v2 import handle_webhook_payload as handle_consultant_core_v2

                timing_start = time.monotonic()
                response = await handle_consultant_core_v2(
                    base_payload,
                    db,
                    provided_secret=None,
                    enforce_secret=False,
                    skip_persist=True,
                    conversation_id=UUID(conversation_id),
                    batch_messages=message_texts,
                    outbox_ids=[str(oid) for oid in outbox_ids if oid],
                    outbox_created_at=group_created_at,
                )
                if not response.success:
                    raise RuntimeError(response.message)
                outbox_total_ms = round((time.monotonic() - timing_start) * 1000, 2)
                logger.info(
                    "Outbox timing",
                    extra={
                    "context": {
                        "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                        "inbound_message_ids": inbound_message_ids,
                        "conversation_id": conversation_id,
                        "client_slug": base_payload.client_slug,
                        "outbox_total_ms": outbox_total_ms,
                    }
                },
                )
                for outbox_id in outbox_ids:
                    if outbox_id:
                        _log_outbox_done(str(outbox_id), total_ms=outbox_total_ms)
                for outbox_id in outbox_ids:
                    if outbox_id:
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="SENT",
                            last_error=None,
                            next_attempt_at=None,
                        )
                results["sent"] += len(outbox_ids)
                logger.info(
                    "Outbox processed",
                    extra={
                        "context": {
                            "conversation_id": conversation_id,
                            "coalesced_count": len(valid_rows),
                        }
                    },
                )
            except Exception as exc:
                try:
                    db.rollback()
                except Exception as rollback_exc:
                    logger.warning(
                        "Outbox rollback failed",
                        extra={"context": {"error": str(rollback_exc)}},
                    )
                outbox_total_ms = round((time.monotonic() - timing_start) * 1000, 2)
                logger.info(
                    "Outbox timing",
                    extra={
                    "context": {
                        "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                        "inbound_message_ids": inbound_message_ids,
                        "conversation_id": conversation_id,
                        "client_slug": base_payload.client_slug,
                        "outbox_total_ms": outbox_total_ms,
                        "error": str(exc),
                    }
                    },
                )
                for outbox_id in outbox_ids:
                    if outbox_id:
                        _record_outbox_action_error(outbox_id=str(outbox_id), error=str(exc))
                for outbox_id in outbox_ids:
                    if outbox_id:
                        _log_outbox_done(
                            str(outbox_id),
                            error=str(exc),
                            total_ms=outbox_total_ms,
                        )
                now = datetime.now(timezone.utc)
                for row, _ in valid_rows:
                    outbox_id = row.get("id")
                    if not outbox_id:
                        continue
                    attempts = int(row.get("attempts") or 0)
                    if attempts >= max_attempts:
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="FAILED",
                            last_error=str(exc)[:500],
                            next_attempt_at=None,
                        )
                        _notify_outbox_failure(
                            outbox_id=str(outbox_id),
                            reason="max_attempts",
                            error=str(exc),
                            provider="internal",
                            attempts=attempts,
                        )
                        results["failed"] += 1
                        continue
                    backoff = retry_backoff_seconds * (2 ** max(attempts - 1, 0))
                    next_attempt_at = now + timedelta(seconds=backoff)
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="PENDING",
                        last_error=str(exc)[:500],
                        next_attempt_at=next_attempt_at,
                    )
                    results["retry_scheduled"] += 1
                logger.error(
                    "Outbox processing failed",
                    extra={
                        "context": {
                            "conversation_id": conversation_id,
                            "error": str(exc),
                            "coalesced_count": len(group),
                        }
                    },
                )

    return results


__all__ = [
    "_classify_transport_degradation",
    "_coerce_outbox_created_at",
    "_get_outbox_window_merge_seconds",
    "_handle_enqueue_only_accept",
    "_prepare_skip_persist",
    "_process_outbox_rows",
    "_split_outbox_batches",
    "claim_scoped_outbox_rows",
    "load_outbox_process_settings",
    "process_claimed_outbox_rows",
    "run_canonical_outbox_process",
    "run_default_outbox_process",
    "run_outbox_worker_cycle",
    "run_scoped_outbox_process",
]
