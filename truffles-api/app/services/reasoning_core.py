"""Unified Reasoning Core API (signals -> gates -> actions -> compose -> trace)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.routers.webhook import decision as decision_router
from app.routers.webhook.trace import DECISION_STAGE_ORDER_SNAPSHOT
from app.schemas.webhook import WebhookRequest, WebhookResponse

STAGE_ORDER_SNAPSHOT = DECISION_STAGE_ORDER_SNAPSHOT


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


__all__ = [
    "ReasoningCoreRequest",
    "STAGE_ORDER_SNAPSHOT",
    "handle_webhook_payload",
    "run_reasoning_core",
    "stage_order_hash",
]
