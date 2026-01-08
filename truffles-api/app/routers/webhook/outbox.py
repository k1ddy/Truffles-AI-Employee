"""Outbox processing helpers (batch merge + enqueue replay)."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.schemas.webhook import WebhookRequest
from app.services.outbox_service import mark_outbox_status

logger = get_logger("webhook")


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
    "_process_outbox_rows",
    "_split_outbox_batches",
]
