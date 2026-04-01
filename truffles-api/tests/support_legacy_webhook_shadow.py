"""Shadow-only legacy root webhook helper for tests.

`app/webhook.py` is removed from runtime code. This file preserves the
former thin compatibility delegate only for deterministic test coverage.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.public_entrypoint_contract import (
    PublicEntrypointMaterializationMode,
    handle_public_webhook_payload,
)
from app.schemas.webhook import WebhookRequest, WebhookResponse

router = APIRouter()


@router.post("/webhook/debug")
async def debug_webhook(request: Request):
    from app.routers.webhook import http as webhook_http

    return await webhook_http.debug_webhook(request)


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(request: WebhookRequest, db: Session = Depends(get_db)):
    from app.routers.webhook.http import _should_enqueue_only

    return await handle_public_webhook_payload(
        request,
        db,
        entrypoint_name="Legacy webhook",
        materialization_mode=PublicEntrypointMaterializationMode.ALLOW_UNMATERIALIZED,
        provided_secret=None,
        enforce_secret=False,
        enqueue_only=_should_enqueue_only(),
    )


__all__ = ["router", "debug_webhook", "handle_webhook"]
