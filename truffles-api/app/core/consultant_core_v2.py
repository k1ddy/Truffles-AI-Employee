from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.consultant_runtime import ConsultantRuntime
from app.schemas.webhook import WebhookRequest, WebhookResponse

_SEMANTIC_RUNTIME_PATH = "consultant_core_v2"


class ConsultantCoreV2Runtime(ConsultantRuntime):
    def __init__(self) -> None:
        super().__init__(semantic_runtime_path=_SEMANTIC_RUNTIME_PATH)


_RUNTIME = ConsultantCoreV2Runtime()


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
    return await _RUNTIME.handle_webhook_payload(
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
    "ConsultantCoreV2Runtime",
    "handle_webhook_payload",
]
