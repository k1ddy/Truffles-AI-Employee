from __future__ import annotations

import os

from fastapi import FastAPI, Request

from app.logging_config import setup_logging
from app.routers import decision_core

setup_logging()

app = FastAPI(
    title="Truffles Decision Core",
    description="Decision core service",
    version="0.1.0",
)

app.include_router(decision_core.router)


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@app.get("/health")
async def health(request: Request):
    return {
        "status": "ok",
        "service": "decision_core",
        "decision_enabled": _is_env_enabled(
            os.environ.get("DECISION_CORE_ENABLED"),
            default=False,
        ),
    }
