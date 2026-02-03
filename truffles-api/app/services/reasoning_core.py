"""Unified Reasoning Core API (signals -> gates -> actions -> compose -> trace)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.logging_config import get_logger, record_delivery_failure, start_span
from app.routers.webhook import decision as decision_router
from app.routers.webhook.trace import DECISION_STAGE_ORDER_SNAPSHOT
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.alert_service import alert_error
from app.services.chatflow_service import send_message_safe

STAGE_ORDER_SNAPSHOT = DECISION_STAGE_ORDER_SNAPSHOT

logger = get_logger("reasoning_core")


def stage_order_hash(stage_order: Sequence[str] | None = None) -> str:
    order = stage_order or STAGE_ORDER_SNAPSHOT
    joined = "\n".join(order)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


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
) -> WebhookResponse:
    try:
        return await decision_router._handle_webhook_payload(
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
        )
    except HTTPException:
        raise
    except Exception as exc:
        try:
            db.rollback()
        except Exception as rollback_exc:
            logger.warning(
                "Webhook rollback failed",
                extra={"context": {"error": str(rollback_exc)}},
            )

        metadata = payload.body.metadata if payload and payload.body else None
        context = {
            "client_slug": payload.client_slug,
            "remote_jid": getattr(metadata, "remoteJid", None),
            "instance_id": getattr(metadata, "instanceId", None),
            "message_id": getattr(metadata, "messageId", None),
            "error": str(exc)[:200],
            "error_type": type(exc).__name__,
        }
        logger.error("Webhook processing failed", extra={"context": context})
        record_delivery_failure(
            payload.client_slug,
            source="webhook",
            provider="internal",
            reason="exception",
        )
        alert_error("Webhook processing failed", context)

        with start_span(
            "webhook.failure",
            context=context,
            attributes={
                "error_type": type(exc).__name__,
                "error": str(exc)[:200],
            },
        ):
            pass

        fallback_sent = False
        should_fallback = not skip_persist and not outbox_ids
        if should_fallback and metadata:
            instance_id = getattr(metadata, "instanceId", None)
            remote_jid = getattr(metadata, "remoteJid", None)
            message_id = getattr(metadata, "messageId", None)
            if instance_id and remote_jid:
                result = send_message_safe(
                    instance_id=instance_id,
                    remote_jid=remote_jid,
                    message=decision_router.MSG_DELIVERY_FAILED,
                    idempotency_key=message_id,
                    notify_on_failure=True,
                    record_metrics=True,
                )
                fallback_sent = result.is_ok()
                if not fallback_sent:
                    record_delivery_failure(
                        payload.client_slug,
                        source="webhook",
                        provider="chatflow",
                        reason="fallback_send_failed",
                    )

        result_message = "Fallback response sent" if fallback_sent else "Fallback response skipped"
        return WebhookResponse(
            success=True,
            message=result_message,
            bot_response=decision_router.MSG_DELIVERY_FAILED if fallback_sent else None,
        )


__all__ = [
    "ReasoningCoreRequest",
    "STAGE_ORDER_SNAPSHOT",
    "handle_webhook_payload",
    "run_reasoning_core",
    "stage_order_hash",
]
