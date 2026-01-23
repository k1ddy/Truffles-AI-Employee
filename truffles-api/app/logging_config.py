"""JSON logging configuration for Truffles API."""

import json
from contextlib import contextmanager
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
DATABASE_HEALTH_STATUS = _get_or_create_metric(
    Gauge,
    "health_check_database_status",
    "Database health status (1=healthy, 0=unhealthy).",
    (),
)
DATABASE_HEALTH_LATENCY_MS = _get_or_create_metric(
    Gauge,
    "health_check_database_latency_ms",
    "Database health check latency in ms.",
    (),
)
QDRANT_HEALTH_STATUS = _get_or_create_metric(
    Gauge,
    "health_check_qdrant_status",
    "Qdrant health status (1=healthy, 0=unhealthy).",
    (),
)
QDRANT_HEALTH_LATENCY_MS = _get_or_create_metric(
    Gauge,
    "health_check_qdrant_latency_ms",
    "Qdrant health check latency in ms.",
    (),
)

# HTTP request metrics
HTTP_REQUEST_COUNT = _get_or_create_metric(
    Counter,
    "http_request_count",
    "HTTP requests count.",
    ("method", "path", "status"),
)
HTTP_REQUEST_LATENCY = _get_or_create_metric(
    Histogram,
    "http_request_latency",
    "HTTP request latency in seconds.",
    ("method", "path"),
    buckets=_HISTOGRAM_BUCKETS,
)
HTTP_REQUEST_IN_PROGRESS = _get_or_create_metric(
    Gauge,
    "http_request_in_progress",
    "HTTP requests currently in progress.",
    ("method",),
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


def set_database_health(status: bool, latency_ms: int | None) -> None:
    if DATABASE_HEALTH_STATUS is not None:
        DATABASE_HEALTH_STATUS.set(1 if status else 0)
    if DATABASE_HEALTH_LATENCY_MS is None:
        return
    if latency_ms is None or latency_ms < 0:
        DATABASE_HEALTH_LATENCY_MS.set(0)
        return
    DATABASE_HEALTH_LATENCY_MS.set(latency_ms)


def set_qdrant_health(status: bool, latency_ms: int | None) -> None:
    if QDRANT_HEALTH_STATUS is not None:
        QDRANT_HEALTH_STATUS.set(1 if status else 0)
    if QDRANT_HEALTH_LATENCY_MS is None:
        return
    if latency_ms is None or latency_ms < 0:
        QDRANT_HEALTH_LATENCY_MS.set(0)
        return
    QDRANT_HEALTH_LATENCY_MS.set(latency_ms)


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


_TRACE_ATTR_KEYS = (
    "message_id",
    "outbox_id",
    "trace_id",
    "client_slug",
    "conversation_id",
    "branch_id",
)


def build_trace_attributes(context: dict | None) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    attrs: dict[str, Any] = {}
    for key in _TRACE_ATTR_KEYS:
        value = context.get(key)
        if value is None:
            continue
        if isinstance(value, (list, dict)):
            continue
        attrs[key] = str(value)
    return attrs


@contextmanager
def start_span(
    name: str,
    *,
    context: dict | None = None,
    attributes: dict[str, Any] | None = None,
):
    if trace is None:
        yield None
        return
    tracer = trace.get_tracer("truffles")
    with tracer.start_as_current_span(name) as span:
        attrs = build_trace_attributes(context)
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    attrs[key] = value
        if attrs:
            span.set_attributes(attrs)
        yield span


# HTTP metrics helpers
_PATH_NORMALIZATIONS = [
    # Console API paths with UUIDs
    (r"/console/v1/cases/[a-f0-9-]{36}", "/console/v1/cases/{id}"),
    (r"/console/v1/conversations/[a-f0-9-]{36}", "/console/v1/conversations/{id}"),
    # Webhook paths
    (r"/webhook/inbound/[^/]+", "/webhook/inbound/{client}"),
    (r"/callback/[^/]+", "/callback/{client}"),
]


def _normalize_path(path: str) -> str:
    """Normalize path for grouping in metrics (remove IDs)."""
    import re
    for pattern, replacement in _PATH_NORMALIZATIONS:
        path = re.sub(pattern, replacement, path)
    return path


def record_http_request(method: str, path: str, status: int, duration_seconds: float) -> None:
    """Record HTTP request metrics."""
    normalized_path = _normalize_path(path)
    if HTTP_REQUEST_COUNT is not None:
        HTTP_REQUEST_COUNT.labels(method=method, path=normalized_path, status=str(status)).inc()
    if HTTP_REQUEST_LATENCY is not None:
        HTTP_REQUEST_LATENCY.labels(method=method, path=normalized_path).observe(duration_seconds)


def http_in_progress_inc(method: str) -> None:
    """Increment in-progress counter."""
    if HTTP_REQUEST_IN_PROGRESS is not None:
        HTTP_REQUEST_IN_PROGRESS.labels(method=method).inc()


def http_in_progress_dec(method: str) -> None:
    """Decrement in-progress counter."""
    if HTTP_REQUEST_IN_PROGRESS is not None:
        HTTP_REQUEST_IN_PROGRESS.labels(method=method).dec()
