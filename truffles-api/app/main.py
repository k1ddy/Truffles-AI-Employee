import asyncio
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.logging_config import get_logger, setup_logging
from app.models import Conversation, Handover, Message, User
from app.routers import admin, alerts, callback, message, reminders, telegram_webhook, webhook
from app.services.outbox_service import claim_pending_outbox_batches

setup_logging()

app = FastAPI(
    title="Truffles API",
    description="Backend service for Truffles chatbot",
    version="0.1.0",
)

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

app.include_router(message.router)
app.include_router(callback.router)
app.include_router(reminders.router)
app.include_router(webhook.router)
app.include_router(telegram_webhook.router)
app.include_router(alerts.router)
app.include_router(admin.router)

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


def _get_outbox_worker_settings() -> tuple[float, int, int, int, float]:
    interval_seconds = float(os.environ.get("OUTBOX_WORKER_INTERVAL_SECONDS", "2"))
    interval_seconds = max(interval_seconds, 0.1)
    limit = int(os.environ.get("OUTBOX_PROCESS_LIMIT", "10"))
    idle_seconds = int(float(os.environ.get("OUTBOX_COALESCE_SECONDS", "8")))
    max_attempts = int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5"))
    retry_backoff_seconds = float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2"))
    return interval_seconds, limit, idle_seconds, max_attempts, retry_backoff_seconds


async def _outbox_worker_loop() -> None:
    while True:
        try:
            interval_seconds, limit, idle_seconds, max_attempts, retry_backoff_seconds = (
                _get_outbox_worker_settings()
            )
            await asyncio.sleep(interval_seconds)
            db = SessionLocal()
            try:
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
