from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.services.appointment_reminder_service import process_reminder_jobs
from app.services.calendar_sync_service import schedule_inbound_syncs
from app.services.outbox_service import (
    claim_pending_outbox_batches,
    release_stale_processing,
)

logger = get_logger("outbox_service")
router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_outbox_enabled() -> bool:
    return _is_env_enabled(os.environ.get("OUTBOX_SERVICE_ENABLED"), default=False)


def _enforce_outbox_token(request: Request) -> None:
    expected_token = os.environ.get("OUTBOX_SERVICE_TOKEN")
    if not expected_token:
        return
    provided_token = request.headers.get("X-Outbox-Service-Token") or request.headers.get("X-Outbox-Token")
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid outbox service token")


@router.post("/outbox/process")
async def process_outbox(request: Request, db: Session = Depends(get_db)):
    if not _is_outbox_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_outbox_token(request)

    limit = int(os.environ.get("OUTBOX_PROCESS_LIMIT", "10"))
    idle_seconds = int(float(os.environ.get("OUTBOX_COALESCE_SECONDS", "8")))
    max_wait_seconds = int(float(os.environ.get("OUTBOX_MAX_WAIT_SECONDS", "10")))
    max_attempts = int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5"))
    retry_backoff_seconds = float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2"))
    stale_seconds = int(float(os.environ.get("OUTBOX_STALE_PROCESSING_SECONDS", "120")))
    stale_seconds = max(stale_seconds, 0)
    max_wait_seconds = max(max_wait_seconds, 0)

    released = release_stale_processing(
        db,
        stale_seconds=stale_seconds,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    inbound_results = schedule_inbound_syncs(db)
    rows = claim_pending_outbox_batches(
        db,
        limit=limit,
        idle_seconds=idle_seconds,
        max_wait_seconds=max_wait_seconds,
    )

    from app.routers.webhook import _process_outbox_rows

    results = await _process_outbox_rows(
        db,
        rows,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    reminder_results = process_reminder_jobs(db)
    if inbound_results.get("scheduled") or inbound_results.get("errors"):
        results["calendar_inbound"] = inbound_results
    if reminder_results.get("total"):
        results["reminder_jobs"] = reminder_results
    if released["released"] or released["failed"]:
        results["released_stale"] = released["released"]
        results["failed_stale"] = released["failed"]
    return results


__all__ = ["process_outbox", "router"]
