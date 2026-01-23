import asyncio
import os

import httpx
from sqlalchemy import text

from app.database import SessionLocal
from app.logging_config import get_logger, setup_logging, start_span
from app.models import Handover, OutboxMessage
from app.services.health_service import check_and_alert_health, check_and_heal_conversations

setup_logging()
logger = get_logger("sentinel_worker")
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
        os.environ.get("OTEL_SERVICE_NAME_SENTINEL")
        or os.environ.get("OTEL_SERVICE_NAME")
        or "truffles-sentinel"
    )
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()
    from app.database import engine
    SQLAlchemyInstrumentor().instrument(engine=engine)
    otel_logger.info("OTel enabled", extra={"context": {"endpoint": endpoint, "service": service_name}})

def _get_sentinel_settings() -> tuple[float, bool]:
    interval = float(os.environ.get("SENTINEL_INTERVAL_SECONDS", "300"))
    interval = max(interval, 60)
    heal_enabled = os.environ.get("SENTINEL_HEAL_ENABLED", "1").lower() not in ("0", "false", "no")
    return interval, heal_enabled

async def _run_sentinel_health_checks(db) -> dict:
    checks = {}
    
    # Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)[:100]}
    
    # Qdrant check
    qdrant_url = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
    qdrant_key = os.environ.get("QDRANT_API_KEY")
    try:
        headers = {"api-key": qdrant_key} if qdrant_key else {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{qdrant_url}/collections", headers=headers)
            if resp.status_code == 200:
                checks["qdrant"] = {"status": "healthy"}
            else:
                checks["qdrant"] = {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        checks["qdrant"] = {"status": "unhealthy", "error": str(e)[:100]}
    
    # Outbox check
    try:
        pending = db.query(OutboxMessage).filter(OutboxMessage.status == "PENDING").count()
        failed = db.query(OutboxMessage).filter(OutboxMessage.status == "FAILED").count()
        checks["outbox"] = {"pending": pending, "failed": failed}
    except Exception:
        pass
    
    # Handovers check
    try:
        active = db.query(Handover).filter(Handover.status.in_(["pending", "active"])).count()
        checks["handovers"] = {"active": active}
    except Exception:
        pass
    
    return checks

async def run_worker():
    # 0. Check enabled flag
    if not _is_env_enabled(os.environ.get("SENTINEL_ENABLED"), default=True):
        logger.info("Sentinel Worker disabled via SENTINEL_ENABLED")
        while True:
            await asyncio.sleep(60)

    # 1. Setup OTel
    _setup_otel()

    logger.info("Starting Sentinel Worker...")
    while True:
        try:
            interval, heal_enabled = _get_sentinel_settings()
            
            # Legacy behavior: sleep FIRST (avoid boot storm / wait for DB)
            await asyncio.sleep(interval)
            
            db = SessionLocal()
            try:
                # Run health checks
                with start_span("sentinel.health_check"):
                    checks = await _run_sentinel_health_checks(db)
                
                # Send alerts
                alerts = check_and_alert_health(checks)
                if alerts:
                    logger.warning(
                        "Sentinel alerts sent",
                        extra={"context": {"alerts": alerts, "checks": checks}},
                    )
                
                # Self-heal
                if heal_enabled:
                    with start_span("sentinel.heal"):
                        result = check_and_heal_conversations(db)
                    if result["healed_count"] > 0:
                        logger.info(
                            "Sentinel healed conversations",
                            extra={"context": result},
                        )
            finally:
                db.close()
            
        except asyncio.CancelledError:
            logger.info("Sentinel Worker cancelled")
            break
        except Exception as exc:
            logger.error(
                "Sentinel worker loop failed",
                extra={"context": {"error": str(exc)}},
            )
            await asyncio.sleep(60)  # Backoff

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
