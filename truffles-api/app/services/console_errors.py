from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from fastapi import Request

from app.logging_config import get_trace_id


@dataclass
class ConsoleAPIError(Exception):
    status_code: int
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


def build_console_error_payload(request: Request, exc: ConsoleAPIError) -> dict:
    trace_id = get_trace_id() or request.headers.get("x-request-id") or uuid4().hex
    return {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "trace_id": trace_id,
        }
    }
