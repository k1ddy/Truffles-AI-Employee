import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.logging_config import get_logger, setup_logging
from app.services.calendar_sync_service import schedule_inbound_syncs
from app.services.outbox_service import claim_pending_outbox_batches, release_stale_processing

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

async def run_worker():
    # 0. Check enabled flag
    if not _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=True):
        logger.info("Outbox Worker disabled via OUTBOX_WORKER_ENABLED")
        while True:
            await asyncio.sleep(60)

    # 1. Setup OTel
    _setup_otel()

    from app.routers.webhook import _process_outbox_rows

    logger.info("Starting Outbox Worker...")
    next_inbound_schedule_at: datetime | None = None
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

                # 2. Process pending messages
                while True:
                    rows = claim_pending_outbox_batches(
                        db,
                        limit=limit,
                        idle_seconds=idle_seconds,
                        max_wait_seconds=max_wait_seconds,
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
