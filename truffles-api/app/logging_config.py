"""JSON logging configuration for Truffles API."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

try:  # Optional at runtime; required in requirements.txt
    from opentelemetry import trace
except Exception:  # pragma: no cover
    trace = None

try:  # Optional at runtime; required in requirements.txt
    from prometheus_client import (  # noqa: I001
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        REGISTRY,
        generate_latest,
    )
except Exception:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    Counter = None
    Gauge = None
    Histogram = None
    REGISTRY = None
    generate_latest = None


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


_HISTOGRAM_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60)


def _get_or_create_metric(metric_cls, name: str, documentation: str, labelnames: tuple[str, ...], **kwargs):
    if metric_cls is None or REGISTRY is None:
        return None
    try:
        return metric_cls(name, documentation, labelnames=labelnames, **kwargs)
    except ValueError:
        existing = REGISTRY._names_to_collectors.get(name)
        return existing


INBOUND_COUNT = _get_or_create_metric(
    Counter,
    "inbound_count",
    "Inbound webhook messages.",
    ("client_slug",),
)
OUTBOX_BACKLOG = _get_or_create_metric(
    Gauge,
    "outbox_backlog",
    "Pending outbox backlog.",
    ("client_slug",),
)
OUTBOX_LATENCY = _get_or_create_metric(
    Histogram,
    "outbox_latency",
    "Outbox wait time in seconds.",
    ("client_slug",),
    buckets=_HISTOGRAM_BUCKETS,
)
LLM_TIME = _get_or_create_metric(
    Histogram,
    "llm_time",
    "LLM call time in seconds.",
    ("client_slug", "stage"),
    buckets=_HISTOGRAM_BUCKETS,
)
RAG_TIME = _get_or_create_metric(
    Histogram,
    "rag_time",
    "RAG retrieval time in seconds.",
    ("client_slug",),
    buckets=_HISTOGRAM_BUCKETS,
)
BGE_TIME = _get_or_create_metric(
    Histogram,
    "bge_time",
    "BGE embedding time in seconds.",
    ("client_slug",),
    buckets=_HISTOGRAM_BUCKETS,
)
POLICY_COUNT = _get_or_create_metric(
    Counter,
    "policy_count",
    "Policy gate hits.",
    ("client_slug", "policy_gate"),
)
ESCALATION_COUNT = _get_or_create_metric(
    Counter,
    "escalation_count",
    "Escalations triggered.",
    ("client_slug", "trigger"),
)


def _normalize_client_slug(client_slug: str | None) -> str:
    if isinstance(client_slug, str) and client_slug.strip():
        return client_slug.strip()
    return "unknown"


def generate_latest_metrics() -> bytes:
    if generate_latest is None:
        return b""
    return generate_latest()


def record_inbound_count(client_slug: str | None) -> None:
    if INBOUND_COUNT is None:
        return
    INBOUND_COUNT.labels(client_slug=_normalize_client_slug(client_slug)).inc()


def record_outbox_latency(client_slug: str | None, wait_ms: float | None) -> None:
    if OUTBOX_LATENCY is None or wait_ms is None:
        return
    if wait_ms < 0:
        return
    OUTBOX_LATENCY.labels(client_slug=_normalize_client_slug(client_slug)).observe(wait_ms / 1000.0)


def record_llm_time(client_slug: str | None, stage: str, elapsed_ms: float) -> None:
    if LLM_TIME is None or elapsed_ms < 0:
        return
    LLM_TIME.labels(
        client_slug=_normalize_client_slug(client_slug),
        stage=stage,
    ).observe(elapsed_ms / 1000.0)


def record_rag_time(client_slug: str | None, elapsed_ms: float) -> None:
    if RAG_TIME is None or elapsed_ms < 0:
        return
    RAG_TIME.labels(client_slug=_normalize_client_slug(client_slug)).observe(elapsed_ms / 1000.0)


def record_bge_time(client_slug: str | None, elapsed_ms: float) -> None:
    if BGE_TIME is None or elapsed_ms < 0:
        return
    BGE_TIME.labels(client_slug=_normalize_client_slug(client_slug)).observe(elapsed_ms / 1000.0)


def record_policy_count(client_slug: str | None, policy_gate: str) -> None:
    if POLICY_COUNT is None:
        return
    if not policy_gate:
        policy_gate = "unknown"
    POLICY_COUNT.labels(
        client_slug=_normalize_client_slug(client_slug),
        policy_gate=policy_gate,
    ).inc()


def record_escalation_count(client_slug: str | None, trigger: str) -> None:
    if ESCALATION_COUNT is None:
        return
    if not trigger:
        trigger = "unknown"
    ESCALATION_COUNT.labels(
        client_slug=_normalize_client_slug(client_slug),
        trigger=trigger,
    ).inc()


def set_outbox_backlog(counts: dict[str, int]) -> None:
    if OUTBOX_BACKLOG is None:
        return
    if hasattr(OUTBOX_BACKLOG, "clear"):
        OUTBOX_BACKLOG.clear()
    for client_slug, backlog in counts.items():
        OUTBOX_BACKLOG.labels(client_slug=_normalize_client_slug(client_slug)).set(max(int(backlog), 0))


def get_trace_id() -> str | None:
    if trace is None:
        return None
    span = trace.get_current_span()
    if span is None:
        return None
    context = span.get_span_context()
    if not context or not context.is_valid:
        return None
    return f"{context.trace_id:032x}"
