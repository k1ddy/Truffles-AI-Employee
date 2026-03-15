from __future__ import annotations

import os

from fastapi import FastAPI, Request

from app.logging_config import setup_logging
from app.routers import knowledge_activation_service

setup_logging()

app = FastAPI(
    title="Truffles Knowledge Activation Service",
    description="Dedicated knowledge activation processing service",
    version="0.1.0",
)

app.include_router(knowledge_activation_service.router)


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@app.get("/health")
async def health(request: Request):
    return {
        "status": "ok",
        "service": "knowledge_activation_service",
        "knowledge_activation_enabled": _is_env_enabled(
            os.environ.get("KNOWLEDGE_ACTIVATION_SERVICE_ENABLED"),
            default=False,
        ),
    }
