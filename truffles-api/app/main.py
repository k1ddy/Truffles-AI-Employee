import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
from app.logging_config import (
    CONTENT_TYPE_LATEST,
    generate_latest_metrics,
    get_logger,
    set_outbox_backlog,
    setup_logging,
)
from app.models import Conversation, Handover, Message, User
from app.routers import admin, alerts, calendar, callback, console, message, reminders, telegram_webhook, webhook
from app.services.console_errors import ConsoleAPIError, build_console_error_payload
from app.services.outbox_service import claim_pending_outbox_batches, release_stale_processing

setup_logging()

app = FastAPI(
    title="Truffles API",
    description="Backend service for Truffles chatbot",
    version="0.1.0",
)

otel_logger = get_logger("otel")

cors_env = os.environ.get("CORS_ALLOW_ORIGINS", "*")
cors_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
if not cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(ConsoleAPIError)
async def console_api_exception_handler(request: Request, exc: ConsoleAPIError):
    return JSONResponse(
        status_code=exc.status_code,
        content=build_console_error_payload(request, exc),
    )

app.include_router(message.router)
app.include_router(callback.router)
app.include_router(reminders.router)
app.include_router(webhook.router)
app.include_router(telegram_webhook.router)
app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(console.router)
app.include_router(calendar.router)

outbox_logger = get_logger("outbox_worker")
_outbox_worker_task: asyncio.Task | None = None


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_outbox_worker_enabled() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=True)


def _get_outbox_worker_settings() -> tuple[float, int, int, int, float, int]:
    interval_seconds = float(os.environ.get("OUTBOX_WORKER_INTERVAL_SECONDS", "2"))
    interval_seconds = max(interval_seconds, 0.1)
    limit = int(os.environ.get("OUTBOX_PROCESS_LIMIT", "10"))
    idle_seconds = int(float(os.environ.get("OUTBOX_COALESCE_SECONDS", "8")))
    max_attempts = int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5"))
    retry_backoff_seconds = float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2"))
    stale_seconds = int(float(os.environ.get("OUTBOX_STALE_PROCESSING_SECONDS", "120")))
    stale_seconds = max(stale_seconds, 0)
    return interval_seconds, limit, idle_seconds, max_attempts, retry_backoff_seconds, stale_seconds


async def _outbox_worker_loop() -> None:
    while True:
        try:
            (
                interval_seconds,
                limit,
                idle_seconds,
                max_attempts,
                retry_backoff_seconds,
                stale_seconds,
            ) = (
                _get_outbox_worker_settings()
            )
            await asyncio.sleep(interval_seconds)
            db = SessionLocal()
            try:
                released = release_stale_processing(
                    db,
                    stale_seconds=stale_seconds,
                    max_attempts=max_attempts,
                    retry_backoff_seconds=retry_backoff_seconds,
                )
                if released["released"] or released["failed"]:
                    outbox_logger.warning(
                        "Outbox stale processing released",
                        extra={"context": {**released, "stale_seconds": stale_seconds}},
                    )
                rows = claim_pending_outbox_batches(db, limit=limit, idle_seconds=idle_seconds)
                if rows:
                    results = await webhook._process_outbox_rows(
                        db,
                        rows,
                        max_attempts=max_attempts,
                        retry_backoff_seconds=retry_backoff_seconds,
                    )
                    outbox_logger.info(
                        "Outbox worker processed",
                        extra={"context": results},
                    )
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            outbox_logger.error(
                "Outbox worker loop failed",
                extra={"context": {"error": str(exc)}},
            )


@app.on_event("startup")
async def start_outbox_worker() -> None:
    global _outbox_worker_task
    if not _is_outbox_worker_enabled():
        return
    if _outbox_worker_task is None or _outbox_worker_task.done():
        _outbox_worker_task = asyncio.create_task(_outbox_worker_loop())
        outbox_logger.info("Outbox worker started")


@app.on_event("shutdown")
async def stop_outbox_worker() -> None:
    global _outbox_worker_task
    if _outbox_worker_task is None:
        return
    _outbox_worker_task.cancel()
    try:
        await _outbox_worker_task
    except asyncio.CancelledError:
        pass
    _outbox_worker_task = None


@app.get("/health")
async def health():
    return {"status": "ok"}


def _setup_otel(app_instance: FastAPI) -> None:
    if not _is_env_enabled(os.environ.get("OTEL_ENABLED"), default=False):
        return
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        otel_logger.warning("OTEL_ENABLED set but OTEL_EXPORTER_OTLP_ENDPOINT missing")
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception as exc:  # pragma: no cover
        otel_logger.warning(
            "OTel setup failed",
            extra={"context": {"error": str(exc)}},
        )
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "truffles-api")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app_instance)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine)
    otel_logger.info("OTel enabled", extra={"context": {"endpoint": endpoint, "service": service_name}})


_setup_otel(app)


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    rows = (
        db.execute(
            text(
                """
                SELECT c.name AS client_slug, COUNT(*) AS backlog
                FROM outbox_messages o
                JOIN clients c ON c.id = o.client_id
                WHERE o.status = 'PENDING'
                GROUP BY c.name
                """
            )
        )
        .mappings()
        .all()
    )
    backlog_counts = {row["client_slug"]: int(row.get("backlog") or 0) for row in rows}
    set_outbox_backlog(backlog_counts)
    payload = generate_latest_metrics()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    conversations_count = db.query(Conversation).count()
    users_count = db.query(User).count()
    messages_count = db.query(Message).count()
    handovers_count = db.query(Handover).count()
    return {
        "status": "ok",
        "conversations": conversations_count,
        "users": users_count,
        "messages": messages_count,
        "handovers": handovers_count,
    }


@app.get("/admin/health/check")
def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check for all platform components.
    Returns overall status and individual component statuses.
    """
    import httpx
    import time
    
    checks = {}
    overall_healthy = True
    start_time = time.time()
    
    # 1. Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False
    
    # 2. Qdrant check
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY")
    try:
        headers = {}
        if qdrant_api_key:
            headers["api-key"] = qdrant_api_key
        with httpx.Client(timeout=5.0) as client:
            qdrant_start = time.time()
            resp = client.get(f"{qdrant_url}/collections", headers=headers)
            qdrant_latency = int((time.time() - qdrant_start) * 1000)
            if resp.status_code == 200:
                checks["qdrant"] = {"status": "healthy", "latency_ms": qdrant_latency}
            else:
                checks["qdrant"] = {"status": "degraded", "status_code": resp.status_code}
                overall_healthy = False
    except Exception as e:
        checks["qdrant"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False
    
    # 3. Outbox queue check
    try:
        outbox_stats = db.execute(
            text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    MIN(created_at) as oldest
                FROM outbox_messages 
                WHERE status IN ('PENDING', 'PROCESSING', 'FAILED')
                GROUP BY status
            """)
        ).mappings().all()
        
        outbox_pending = 0
        outbox_processing = 0
        outbox_failed = 0
        for row in outbox_stats:
            if row["status"] == "PENDING":
                outbox_pending = row["count"]
            elif row["status"] == "PROCESSING":
                outbox_processing = row["count"]
            elif row["status"] == "FAILED":
                outbox_failed = row["count"]
        
        outbox_status = "healthy"
        if outbox_pending > 100:
            outbox_status = "degraded"
            overall_healthy = False
        if outbox_failed > 50:
            outbox_status = "unhealthy"
            overall_healthy = False
            
        checks["outbox"] = {
            "status": outbox_status,
            "pending": outbox_pending,
            "processing": outbox_processing,
            "failed": outbox_failed,
        }
    except Exception as e:
        checks["outbox"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False
    
    # 4. Active handovers (pending escalations)
    try:
        pending_handovers = db.execute(
            text("SELECT COUNT(*) as count FROM handovers WHERE status IN ('pending', 'active')")
        ).scalar()
        checks["handovers"] = {
            "status": "healthy",
            "active_count": pending_handovers,
        }
    except Exception as e:
        checks["handovers"] = {"status": "unknown", "error": str(e)}
    
    total_latency = int((time.time() - start_time) * 1000)
    
    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latency_ms": total_latency,
        "checks": checks,
    }

