import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.logging_config import get_logger, setup_logging
from app.services.calendar_sync_service import schedule_inbound_syncs
from app.services.metrics_daily_service import (
    get_metrics_daily_status_allowlist,
    run_metrics_daily_snapshot,
)
from app.services.outbox_service import claim_pending_outbox_batches, release_stale_processing
from app.services.runtime_safety import assert_outbox_worker_startup_safe

setup_logging()
logger = get_logger("outbox_worker")
otel_logger = get_logger("otel")


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _setup_otel() -> None:
    if not _is_env_enabled(os.environ.get("OTEL_ENABLED"), default=False):
        return
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        otel_logger.warning("OTEL_ENABLED set but OTEL_EXPORTER_OTLP_ENDPOINT missing")
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        otel_logger.warning("OTel dependencies missing")
        return
    except Exception as exc:
        otel_logger.warning(
            "OTel setup failed",
            extra={"context": {"error": str(exc)}},
        )
        return

    service_name = (
        os.environ.get("OTEL_SERVICE_NAME_OUTBOX")
        or os.environ.get("OTEL_SERVICE_NAME")
        or "truffles-outbox"
    )
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()
    # We need the engine to instrument SQLAlchemy, but we are using SessionLocal.
    # We can import engine from app.database
    from app.database import engine
    SQLAlchemyInstrumentor().instrument(engine=engine)
    otel_logger.info("OTel enabled", extra={"context": {"endpoint": endpoint, "service": service_name}})

def _get_outbox_worker_settings() -> tuple[float, int, int, int, float, int, int]:
    interval_seconds = float(os.environ.get("OUTBOX_WORKER_INTERVAL_SECONDS", "2"))
    interval_seconds = max(interval_seconds, 0.1)
    limit = int(os.environ.get("OUTBOX_PROCESS_LIMIT", "10"))
    idle_seconds = int(float(os.environ.get("OUTBOX_COALESCE_SECONDS", "8")))
    max_wait_seconds = int(float(os.environ.get("OUTBOX_MAX_WAIT_SECONDS", "10")))
    max_attempts = int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5"))
    retry_backoff_seconds = float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2"))
    stale_seconds = int(float(os.environ.get("OUTBOX_STALE_PROCESSING_SECONDS", "120")))
    stale_seconds = max(stale_seconds, 0)
    max_wait_seconds = max(max_wait_seconds, 0)
    return (
        interval_seconds,
        limit,
        idle_seconds,
        max_wait_seconds,
        max_attempts,
        retry_backoff_seconds,
        stale_seconds,
    )


def _get_metrics_daily_settings() -> tuple[bool, int, int, int, int, int]:
    enabled = _is_env_enabled(os.environ.get("METRICS_DAILY_AUTO_ENABLED"), default=False)
    try:
        run_hour = int(os.environ.get("METRICS_DAILY_RUN_HOUR_UTC", "1"))
    except (TypeError, ValueError):
        run_hour = 1
    try:
        run_minute = int(os.environ.get("METRICS_DAILY_RUN_MINUTE_UTC", "5"))
    except (TypeError, ValueError):
        run_minute = 5
    try:
        offset_days = int(os.environ.get("METRICS_DAILY_TARGET_OFFSET_DAYS", "1"))
    except (TypeError, ValueError):
        offset_days = 1
    try:
        retry_seconds = int(os.environ.get("METRICS_DAILY_RETRY_SECONDS", "600"))
    except (TypeError, ValueError):
        retry_seconds = 600
    try:
        retry_max = int(os.environ.get("METRICS_DAILY_RETRY_MAX", "3"))
    except (TypeError, ValueError):
        retry_max = 3

    run_hour = min(max(run_hour, 0), 23)
    run_minute = min(max(run_minute, 0), 59)
    offset_days = max(offset_days, 0)
    retry_seconds = max(retry_seconds, 60)
    retry_max = max(retry_max, 0)
    return enabled, run_hour, run_minute, offset_days, retry_seconds, retry_max


def _get_metrics_daily_run_at(now: datetime, run_hour: int, run_minute: int) -> datetime:
    return datetime(
        now.year,
        now.month,
        now.day,
        run_hour,
        run_minute,
        tzinfo=timezone.utc,
    )

async def run_worker():
    # 0. Check enabled flag
    if not _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=True):
        logger.info("Outbox Worker disabled via OUTBOX_WORKER_ENABLED")
        while True:
            await asyncio.sleep(60)

    safety_snapshot = assert_outbox_worker_startup_safe()
    logger.info(
        "Outbox startup safety",
        extra={"context": safety_snapshot.to_dict()},
    )

    # 1. Setup OTel
    _setup_otel()

    from app.routers.webhook import _process_outbox_rows

    logger.info("Starting Outbox Worker...")
    next_inbound_schedule_at: datetime | None = None
    next_metrics_run_at: datetime | None = None
    last_metrics_metric_date = None
    metrics_retry_count = 0
    while True:
        try:
            (
                interval_seconds,
                limit,
                idle_seconds,
                max_wait_seconds,
                max_attempts,
                retry_backoff_seconds,
                stale_seconds,
            ) = _get_outbox_worker_settings()
            
            loop_start = time.monotonic()
            db = SessionLocal()
            try:
                # 1. Release stale locks
                released = release_stale_processing(
                    db,
                    stale_seconds=stale_seconds,
                    max_attempts=max_attempts,
                    retry_backoff_seconds=retry_backoff_seconds,
                )
                if released["released"] or released["failed"]:
                    logger.warning(
                        "Outbox stale processing released",
                        extra={"context": {**released, "stale_seconds": stale_seconds}},
                    )

                now = datetime.now(timezone.utc)
                if next_inbound_schedule_at is None or now >= next_inbound_schedule_at:
                    try:
                        inbound_results = schedule_inbound_syncs(db, now=now)
                    except Exception as exc:
                        inbound_results = {"interval_seconds": 60, "scheduled": 0, "errors": 1}
                        logger.warning(
                            "Inbound calendar sync scheduling failed",
                            extra={"context": {"error": str(exc)[:200]}},
                        )
                    schedule_interval = inbound_results.get("interval_seconds") or 60
                    next_inbound_schedule_at = now + timedelta(seconds=max(schedule_interval, 60))
                    if inbound_results.get("scheduled") or inbound_results.get("errors"):
                        logger.info(
                            "Inbound calendar sync scheduled",
                            extra={"context": inbound_results},
                        )

                (
                    metrics_enabled,
                    run_hour,
                    run_minute,
                    offset_days,
                    retry_seconds,
                    retry_max,
                ) = _get_metrics_daily_settings()
                if metrics_enabled:
                    if next_metrics_run_at is None:
                        next_metrics_run_at = _get_metrics_daily_run_at(now, run_hour, run_minute)
                    if now >= next_metrics_run_at:
                        target_date = (now - timedelta(days=offset_days)).date()
                        if last_metrics_metric_date == target_date:
                            next_metrics_run_at = _get_metrics_daily_run_at(
                                now + timedelta(days=1),
                                run_hour,
                                run_minute,
                            )
                        else:
                            status_allowlist = get_metrics_daily_status_allowlist()
                            metrics_db = SessionLocal()
                            try:
                                results = run_metrics_daily_snapshot(
                                    metrics_db,
                                    metric_date=target_date,
                                    status_allowlist=status_allowlist,
                                )
                            finally:
                                metrics_db.close()
                            if results["errors"]:
                                metrics_retry_count += 1
                                logger.warning(
                                    "Metrics daily snapshot errors",
                                    extra={"context": results},
                                )
                                if retry_max and metrics_retry_count <= retry_max:
                                    next_metrics_run_at = now + timedelta(seconds=retry_seconds)
                                else:
                                    last_metrics_metric_date = target_date
                                    metrics_retry_count = 0
                                    next_metrics_run_at = _get_metrics_daily_run_at(
                                        now + timedelta(days=1),
                                        run_hour,
                                        run_minute,
                                    )
                            else:
                                logger.info(
                                    "Metrics daily snapshot complete",
                                    extra={"context": results},
                                )
                                last_metrics_metric_date = target_date
                                metrics_retry_count = 0
                                next_metrics_run_at = _get_metrics_daily_run_at(
                                    now + timedelta(days=1),
                                    run_hour,
                                    run_minute,
                                )

                # 2. Process pending messages
                while True:
                    rows = claim_pending_outbox_batches(
                        db,
                        limit=limit,
                        idle_seconds=idle_seconds,
                        max_wait_seconds=max_wait_seconds,
                        include_without_conversation=True,
                    )
                    if not rows:
                        break
                    
                    results = await _process_outbox_rows(
                        db,
                        rows,
                        max_attempts=max_attempts,
                        retry_backoff_seconds=retry_backoff_seconds,
                    )
                    
                    logger.info(
                        "Outbox worker processed",
                        extra={"context": results},
                    )
                    
                    # Don't hog CPU if we processed a batch, check time
                    if time.monotonic() - loop_start >= interval_seconds:
                        break
            finally:
                db.close()
            
            elapsed = time.monotonic() - loop_start
            sleep_for = max(interval_seconds - elapsed, 0.1)
            await asyncio.sleep(sleep_for)
            
        except asyncio.CancelledError:
            logger.info("Outbox Worker cancelled")
            break
        except Exception as exc:
            logger.error(
                "Outbox worker loop failed",
                extra={"context": {"error": str(exc)}},
            )
            await asyncio.sleep(5)  # Backoff on crash

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
