from __future__ import annotations

import os

from fastapi import FastAPI, Request

from app.logging_config import setup_logging
from app.routers import inbox_service

setup_logging()

app = FastAPI(
    title="Truffles Inbox Service",
    description="Durable inbox ingest service",
    version="0.1.0",
)

app.include_router(inbox_service.router)


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@app.get("/health")
async def health(request: Request):
    return {
        "status": "ok",
        "service": "inbox_service",
        "inbox_enabled": _is_env_enabled(
            os.environ.get("INBOX_SERVICE_ENABLED"),
            default=False,
        ),
    }
