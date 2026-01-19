"""Outbox processing helpers (batch merge + enqueue replay)."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger, record_outbox_latency
from app.models import Conversation, User
from app.routers.webhook.media import (
    _build_media_caption,
    _send_telegram_media,
    _store_media_locally,
    _update_message_media_metadata,
)
from app.routers.webhook.trace import _record_decision_trace
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.escalation_service import get_telegram_credentials
from app.services.outbox_service import (
    build_inbound_message_id,
    enqueue_outbox_message,
    mark_outbox_status,
)
from app.services.state_machine import ConversationState
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
                    storage_path = None
                    if media_policy and media_policy.get("store_media"):
                        if saved_message and isinstance(saved_message.message_metadata, dict):
                            storage_path = (saved_message.message_metadata.get("media") or {}).get(
                                "storage_path"
                            )
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
    enqueued = enqueue_outbox_message(
        db,
        client_id=client.id,
        conversation_id=conversation.id,
        inbound_message_id=inbound_message_id,
        payload_json=payload_json,
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
    for row in rows:
        outbox_id = row.get("id")
        if not outbox_id:
            continue
        payload_json = row.get("payload_json") or {}
        created_at = row.get("created_at")
        conversation_id = row.get("conversation_id")
        outbox_id_str = str(outbox_id)
        pick_info[outbox_id_str] = {
            "picked_at": picked_at,
            "created_at": created_at,
            "conversation_id": conversation_id,
            "client_slug": payload_json.get("client_slug"),
        }
        logger.info(
            "Outbox picked",
            extra={
                "context": {
                    "outbox_id": outbox_id_str,
                    "conversation_id": str(conversation_id) if conversation_id else None,
                    "client_slug": payload_json.get("client_slug"),
                    "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
                    "outbox_picked_at": picked_at.isoformat(),
                }
            },
        )

    def _log_outbox_done(outbox_id: str, *, error: str | None = None) -> None:
        info = pick_info.get(outbox_id, {})
        done_at = datetime.now(timezone.utc)
        created_at = info.get("created_at")
        picked_at_info = info.get("picked_at")
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
            "conversation_id": str(info.get("conversation_id")) if info.get("conversation_id") else None,
            "client_slug": info.get("client_slug"),
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

    def _row_has_media(row: dict) -> bool:
        payload_json = row.get("payload_json") or {}
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
        try:
            payload = WebhookRequest.model_validate(payload_json)
        except Exception as exc:
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="FAILED",
                last_error=f"invalid_payload:{exc}"[:500],
                next_attempt_at=None,
            )
            results["failed"] += 1
            return

        try:
            outbox_ids = [str(outbox_id)]
            timing_start = time.monotonic()
            response = await legacy._handle_webhook_payload(
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
            logger.info(
                "Outbox timing",
                extra={
                    "context": {
                        "outbox_id": str(outbox_id),
                        "outbox_ids": outbox_ids,
                        "conversation_id": conversation_id,
                        "client_slug": payload.client_slug,
                        "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                    }
                },
            )
            _log_outbox_done(str(outbox_id))
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
            logger.info(
                "Outbox timing",
                extra={
                    "context": {
                        "outbox_id": str(outbox_id),
                        "outbox_ids": [str(outbox_id)],
                        "conversation_id": conversation_id,
                        "client_slug": payload.client_slug,
                        "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                        "error": str(exc),
                    }
                },
            )
            _log_outbox_done(str(outbox_id), error=str(exc))
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
            outbox_ids = [row.get("id") for row in group]
            message_texts = []
            forwarded_in_batch = False
            group_created_at = None
            for row in group:
                payload_json = row.get("payload_json") or {}
                try:
                    payload = WebhookRequest.model_validate(payload_json)
                except Exception:
                    continue
                created_at = _coerce_outbox_created_at(row.get("created_at"))
                if created_at and (group_created_at is None or created_at > group_created_at):
                    group_created_at = created_at
                if payload.body.metadata and payload.body.metadata.forwarded_to_telegram:
                    forwarded_in_batch = True
                text = payload.body.message or ""
                if text.strip():
                    message_texts.append(text.strip())

            base_payload = WebhookRequest.model_validate(group[-1].get("payload_json") or {})
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
                        "conversation_id": conversation_id,
                        "attempts": group[-1].get("attempts"),
                        "coalesced_count": len(group),
                        "window_merge_seconds": window_seconds,
                    }
                },
            )

            try:
                timing_start = time.monotonic()
                response = await legacy._handle_webhook_payload(
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
                logger.info(
                    "Outbox timing",
                    extra={
                        "context": {
                            "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                            "conversation_id": conversation_id,
                            "client_slug": base_payload.client_slug,
                            "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                        }
                    },
                )
                for outbox_id in outbox_ids:
                    if outbox_id:
                        _log_outbox_done(str(outbox_id))
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
                    extra={"context": {"conversation_id": conversation_id, "coalesced_count": len(group)}},
                )
            except Exception as exc:
                try:
                    db.rollback()
                except Exception as rollback_exc:
                    logger.warning(
                        "Outbox rollback failed",
                        extra={"context": {"error": str(rollback_exc)}},
                    )
                logger.info(
                    "Outbox timing",
                    extra={
                        "context": {
                            "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                            "conversation_id": conversation_id,
                            "client_slug": base_payload.client_slug,
                            "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                            "error": str(exc),
                        }
                    },
                )
                for outbox_id in outbox_ids:
                    if outbox_id:
                        _log_outbox_done(str(outbox_id), error=str(exc))
                now = datetime.now(timezone.utc)
                for row in group:
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
