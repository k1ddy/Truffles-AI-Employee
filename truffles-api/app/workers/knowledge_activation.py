import asyncio
import os

from app.database import SessionLocal
from app.logging_config import get_logger, setup_logging
from app.services.knowledge_registry_service import (
    KNOWLEDGE_ACTIVATION_STUCK_AFTER_SECONDS,
    process_queued_knowledge_activation_jobs,
)

setup_logging()
logger = get_logger("knowledge_activation_worker")


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _get_worker_settings() -> tuple[float, int, int]:
    interval_seconds = float(os.environ.get("KNOWLEDGE_ACTIVATION_WORKER_INTERVAL_SECONDS", "2"))
    interval_seconds = max(interval_seconds, 0.1)
    limit = int(os.environ.get("KNOWLEDGE_ACTIVATION_PROCESS_LIMIT", "10"))
    stuck_after_seconds = int(
        float(
            os.environ.get(
                "KNOWLEDGE_ACTIVATION_STUCK_AFTER_SECONDS",
                str(KNOWLEDGE_ACTIVATION_STUCK_AFTER_SECONDS),
            )
        )
    )
    return interval_seconds, limit, max(stuck_after_seconds, 1)


async def run_worker():
    if not _is_env_enabled(os.environ.get("KNOWLEDGE_ACTIVATION_WORKER_ENABLED"), default=True):
        logger.info("Knowledge Activation Worker disabled via KNOWLEDGE_ACTIVATION_WORKER_ENABLED")
        while True:
            await asyncio.sleep(60)

    logger.info("Starting Knowledge Activation Worker...")
    while True:
        try:
            interval_seconds, limit, stuck_after_seconds = _get_worker_settings()
            db = SessionLocal()
            try:
                results = process_queued_knowledge_activation_jobs(
                    db,
                    limit=limit,
                    stuck_after_seconds=stuck_after_seconds,
                )
                if results["claimed"] or results["failed"] or results["stuck"]:
                    logger.info(
                        "Knowledge activation worker processed jobs",
                        extra={"context": results},
                    )
            finally:
                db.close()
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Knowledge Activation Worker cancelled")
            break
        except Exception as exc:
            logger.error(
                "Knowledge activation worker loop failed",
                extra={"context": {"error": str(exc)}},
            )
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
