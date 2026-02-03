"""Outbox processing helpers (batch merge + enqueue replay)."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.chatflow import ChatFlowAdapter
from app.adapters.provider_gateway import ProviderGatewayAdapter
from app.logging_config import (
    get_logger,
    record_delivery_failure,
    record_outbox_latency,
    start_span,
)
from app.models import Conversation, OutboxMessage, User
from app.ports.messaging import MessageOptions
from app.routers.webhook.media import (
    _build_media_caption,
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
from app.services.alert_service import alert_error
from app.services.calendar_sync_service import (
    OUTBOX_EVENT_CALENDAR_SYNC_INBOUND,
    OUTBOX_EVENT_CALENDAR_SYNC_OUTBOUND,
    process_inbound_sync_event,
    process_outbound_sync_event,
)
from app.services.escalation_service import get_telegram_credentials
from app.services.outbox_service import (
    build_inbound_message_id,
    enqueue_outbox_message,
    mark_outbox_status,
)
from app.services.state_machine import ConversationState
from app.services.state_service import is_simulation_context
from app.services.telegram_service import TelegramService

logger = get_logger("webhook")

if TYPE_CHECKING:
    from app.models import Client, Message


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
    from . import _legacy as legacy

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
        legacy._record_decision_trace(
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
        saved_message = legacy._find_message_by_message_id(db, client.id, message_id)
    if not saved_message and outbox_created_at:
        saved_message = legacy._find_message_by_conversation_created_at(
            db,
            conversation.id,
            outbox_created_at,
            message_text=message_text,
        )
    legacy._ensure_rag_meta_defaults(saved_message)
    media_decision = None
    if media_info and saved_message:
        saved_media = (
            saved_message.message_metadata.get("media")
            if isinstance(saved_message.message_metadata, dict)
            else None
        )
        media_decision = legacy._deserialize_media_decision(
            saved_media.get("decision") if isinstance(saved_media, dict) else None
        )
    if media_info and media_decision is None and media_policy:
        media_decision = await legacy._evaluate_media_decision(
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
    from . import _legacy as legacy

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
        branch_id = None
        if conversation_id:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if conversation:
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
        client_id = info.get("client_id")
        message = None
        if client_id and inbound_message_id:
            message = legacy._find_message_by_message_id(db, client_id, str(inbound_message_id))
        if not message and info.get("conversation_id") and info.get("created_at"):
            message = legacy._find_message_by_conversation_created_at(
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
                    "stage": stage,
                    "decision": "reject",
                    "reason": reason,
                    "state": conversation.state,
                },
            )
        message = _resolve_outbox_message(outbox_id)
        if message:
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
            if isinstance(decision_meta, dict) and decision_meta.get("action"):
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
                                outbox_id=outbox_id_str, reason=f"event:{error}"
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
                if event_type not in {"whatsapp.send_text", "whatsapp.send_media"}:
                    _record_outbox_payload_error(outbox_id=outbox_id_str, reason=f"event:{event_type}")
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
                from app.services import reasoning_core

                with start_span("outbox.process", context=span_context):
                    response = await reasoning_core.handle_webhook_payload(
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
            _record_outbox_action_error(outbox_id=outbox_id_str, error=str(exc))
            _log_outbox_done(outbox_id_str, error=str(exc), total_ms=outbox_total_ms)
            now = datetime.now(timezone.utc)
            attempts = int(row.get("attempts") or 0)
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
                from app.services import reasoning_core

                timing_start = time.monotonic()
                response = await reasoning_core.handle_webhook_payload(
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
    "_coerce_outbox_created_at",
    "_get_outbox_window_merge_seconds",
    "_handle_enqueue_only_accept",
    "_prepare_skip_persist",
    "_process_outbox_rows",
    "_split_outbox_batches",
]
