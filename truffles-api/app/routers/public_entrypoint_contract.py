from __future__ import annotations

from enum import Enum

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.webhook import WebhookRequest, WebhookResponse


class PublicEntrypointMaterializationMode(str, Enum):
    ALLOW_UNMATERIALIZED = "allow_unmaterialized"
    REQUIRE_CONVERSATION = "require_conversation"


def _require_materialized_response(response: WebhookResponse, *, entrypoint_name: str) -> WebhookResponse:
    if response.conversation_id:
        return response

    detail = (response.message or "").strip() or f"{entrypoint_name} pipeline returned no conversation_id"
    if not response.success:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"{entrypoint_name} pipeline returned no conversation_id: {detail}",
    )


async def handle_public_webhook_payload(
    payload: WebhookRequest,
    db: Session,
    *,
    entrypoint_name: str,
    materialization_mode: PublicEntrypointMaterializationMode,
    provided_secret: str | None,
    enforce_secret: bool,
    enqueue_only: bool = False,
    preflight_payload: dict[str, object] | None = None,
) -> WebhookResponse:
    from app.core.consultant_runtime import handle_webhook_payload

    response = await handle_webhook_payload(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=enforce_secret,
        enqueue_only=enqueue_only,
        preflight_payload=preflight_payload,
    )
    if materialization_mode is PublicEntrypointMaterializationMode.ALLOW_UNMATERIALIZED:
        return response
    return _require_materialized_response(response, entrypoint_name=entrypoint_name)


__all__ = [
    "PublicEntrypointMaterializationMode",
    "handle_public_webhook_payload",
]
