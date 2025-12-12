"""JSON logging configuration for Truffles API."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Configure JSON logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(f"truffles.{name}")


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to log records."""

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        context = kwargs.pop("context", None)
        if context or self.extra:
            combined_context = {**self.extra, **(context or {})}
            kwargs["extra"] = {"context": combined_context}
        return msg, kwargs
