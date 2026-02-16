import asyncio
import os
import time

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
from app.logging_config import (
    CONTENT_TYPE_LATEST,
    generate_latest_metrics,
    get_logger,
    http_in_progress_dec,
    http_in_progress_inc,
    record_http_request,
    set_database_health,
    set_outbox_backlog,
    set_qdrant_health,
    setup_logging,
)
from app.models import Conversation, Handover, Message, User
from app.routers import (
    admin,
    alerts,
    calendar,
    callback,
    console,
    knowledge_gateway,
    message,
    provider_gateway,
    reminders,
    telegram_webhook,
    webhook,
)
from app.services.console_errors import ConsoleAPIError, build_console_error_payload

setup_logging()

app = FastAPI(
    title="Truffles API",
    description="Backend service for Truffles chatbot",
    version="0.1.0",
)

otel_logger = get_logger("otel")
metrics_logger = get_logger("metrics")

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


# Metrics middleware for HTTP request tracking
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track HTTP request metrics (count, latency, in-progress)."""
    method = request.method
    path = request.url.path
    
    # Skip metrics endpoint to avoid recursion
    if path == "/metrics":
        return await call_next(request)
    
    start_time = time.time()
    http_in_progress_inc(method)
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        record_http_request(method, path, response.status_code, duration)
        return response
    except Exception:
        duration = time.time() - start_time
        record_http_request(method, path, 500, duration)
        raise
    finally:
        http_in_progress_dec(method)


@app.exception_handler(ConsoleAPIError)
async def console_api_exception_handler(request: Request, exc: ConsoleAPIError):
    print(f"DEBUG: ConsoleAPIError: {exc.code} - {exc.message} - {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content=build_console_error_payload(request, exc),
    )

app.include_router(message.router)
app.include_router(callback.router)
app.include_router(reminders.router)
app.include_router(webhook.router)
app.include_router(provider_gateway.router)
app.include_router(knowledge_gateway.router)
app.include_router(telegram_webhook.router)
app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(console.router)
app.include_router(calendar.router, prefix="/console/v1")

def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _float_env(name: str, default: float, minimum: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        parsed = float(raw)
    except ValueError:
        return default
    return max(minimum, parsed)


_ADMIN_HEALTH_CACHE_TTL_SECONDS = _float_env("ADMIN_HEALTH_CACHE_TTL_SECONDS", 10.0, 0.0)
_ADMIN_HEALTH_QDRANT_TIMEOUT_SECONDS = _float_env(
    "ADMIN_HEALTH_QDRANT_TIMEOUT_SECONDS",
    1.5,
    0.2,
)
_admin_health_cache: dict[str, object] = {"expires_at": 0.0, "payload": None}
_admin_health_lock = asyncio.Lock()




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
    db_healthy = True
    db_latency_ms = None
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = int((time.time() - start) * 1000)
    except Exception as exc:
        db_healthy = False
        metrics_logger.warning(
            "Database health check failed",
            extra={"context": {"error": str(exc)[:200]}},
        )
    set_database_health(db_healthy, db_latency_ms)

    try:
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
    except Exception as exc:
        metrics_logger.warning(
            "Outbox backlog query failed",
            extra={"context": {"error": str(exc)[:200]}},
        )
        set_outbox_backlog({})

    qdrant_healthy = True
    qdrant_latency_ms = None
    qdrant_url = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
    qdrant_key = os.environ.get("QDRANT_API_KEY")
    try:
        import httpx

        start = time.time()
        headers = {"api-key": qdrant_key} if qdrant_key else {}
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{qdrant_url}/collections", headers=headers)
        if resp.status_code == 200:
            qdrant_latency_ms = int((time.time() - start) * 1000)
        else:
            qdrant_healthy = False
    except Exception as exc:
        qdrant_healthy = False
        metrics_logger.warning(
            "Qdrant health check failed",
            extra={"context": {"error": str(exc)[:200]}},
        )
    set_qdrant_health(qdrant_healthy, qdrant_latency_ms)

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
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check for monitoring with short-lived caching."""
    now = time.time()
    cached_payload = _admin_health_cache.get("payload")
    expires_at = _admin_health_cache.get("expires_at")
    if isinstance(cached_payload, dict) and isinstance(expires_at, (int, float)) and now < float(expires_at):
        response = dict(cached_payload)
        response["cached"] = True
        response["cache_ttl_seconds"] = _ADMIN_HEALTH_CACHE_TTL_SECONDS
        return response

    async with _admin_health_lock:
        now = time.time()
        cached_payload = _admin_health_cache.get("payload")
        expires_at = _admin_health_cache.get("expires_at")
        if isinstance(cached_payload, dict) and isinstance(expires_at, (int, float)) and now < float(expires_at):
            response = dict(cached_payload)
            response["cached"] = True
            response["cache_ttl_seconds"] = _ADMIN_HEALTH_CACHE_TTL_SECONDS
            return response

        payload = await _compute_admin_health_payload(db)
        if _ADMIN_HEALTH_CACHE_TTL_SECONDS > 0:
            _admin_health_cache["payload"] = payload
            _admin_health_cache["expires_at"] = time.time() + _ADMIN_HEALTH_CACHE_TTL_SECONDS

        response = dict(payload)
        response["cached"] = False
        response["cache_ttl_seconds"] = _ADMIN_HEALTH_CACHE_TTL_SECONDS
        return response


async def _compute_admin_health_payload(db: Session) -> dict:
    import time
    import httpx

    checks = {}
    start_total = time.time()
    overall_healthy = True

    # Database check
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "latency_ms": int((time.time() - start) * 1000)}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)[:100]}
        overall_healthy = False
    
    # Qdrant check (bounded timeout to avoid 5s tail on each poll)
    qdrant_url = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
    qdrant_key = os.environ.get("QDRANT_API_KEY")
    try:
        start = time.time()
        headers = {"api-key": qdrant_key} if qdrant_key else {}
        async with httpx.AsyncClient(timeout=_ADMIN_HEALTH_QDRANT_TIMEOUT_SECONDS) as client:
            resp = await client.get(f"{qdrant_url}/collections", headers=headers)
            if resp.status_code == 200:
                checks["qdrant"] = {"status": "healthy", "latency_ms": int((time.time() - start) * 1000)}
            else:
                checks["qdrant"] = {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
                overall_healthy = False
    except Exception as e:
        checks["qdrant"] = {"status": "unhealthy", "error": str(e)[:100]}
        overall_healthy = False
    
    # Outbox check via a single grouped query.
    try:
        from app.models import OutboxMessage

        counts_rows = (
            db.query(
                OutboxMessage.status,
                func.count(OutboxMessage.id).label("count"),
            )
            .filter(OutboxMessage.status.in_(["PENDING", "FAILED"]))
            .group_by(OutboxMessage.status)
            .all()
        )
        pending = 0
        failed = 0
        for status_value, count in counts_rows:
            normalized = str(status_value or "").upper()
            if normalized == "PENDING":
                pending = int(count or 0)
            elif normalized == "FAILED":
                failed = int(count or 0)
        checks["outbox"] = {"status": "healthy" if failed < 100 else "warning", "pending": pending, "failed": failed}
        if failed >= 100:
            overall_healthy = False
    except Exception as e:
        checks["outbox"] = {"status": "error", "error": str(e)[:100]}
    
    # Active handovers
    try:
        active = db.query(Handover).filter(Handover.status.in_(["pending", "active"])).count()
        checks["handovers"] = {"active": active}
    except Exception:
        pass
    
    total_latency = int((time.time() - start_total) * 1000)
    
    # Send alerts for critical issues
    from app.services.health_service import check_and_alert_health
    alerts_sent = check_and_alert_health(checks)
    
    response = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latency_ms": total_latency,
        "checks": checks,
    }
    
    if alerts_sent:
        response["alerts_sent"] = alerts_sent

    return response
