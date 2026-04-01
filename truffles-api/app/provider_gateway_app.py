from __future__ import annotations

import os

from fastapi import FastAPI, Request

from app.logging_config import setup_logging
from app.routers import provider_gateway

setup_logging()

app = FastAPI(
    title="Truffles Provider Gateway",
    description="Provider gateway service",
    version="0.1.0",
)

app.include_router(provider_gateway.router)


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@app.get("/health")
async def health(request: Request):
    return {
        "status": "ok",
        "service": "provider_gateway",
        "inbound_enabled": _is_env_enabled(
            os.environ.get("PROVIDER_GATEWAY_INBOUND_ENABLED"),
            default=False,
        ),
        "status_enabled": _is_env_enabled(
            os.environ.get("PROVIDER_GATEWAY_STATUS_ENABLED"),
            default=False,
        ),
        "inbox_enabled": _is_env_enabled(
            os.environ.get("PROVIDER_GATEWAY_INBOX_ENABLED"),
            default=False,
        ),
        "outbound_enabled": _is_env_enabled(
            os.environ.get("PROVIDER_GATEWAY_OUTBOUND_ENABLED"),
            default=False,
        ),
    }
