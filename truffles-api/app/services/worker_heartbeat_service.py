from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import redis  # type: ignore


_DEFAULT_RUNTIME_REDIS_URL = "redis://truffles_redis_1:6379/0"
_WORKER_HEARTBEAT_PREFIX = "truffles:worker_heartbeat"
_WORKER_NAMES = ("truffles-outbox", "truffles-sentinel")
_WORKER_STALE_ENV = {
    "truffles-outbox": "OUTBOX_WORKER_HEARTBEAT_STALE_SECONDS",
    "truffles-sentinel": "SENTINEL_WORKER_HEARTBEAT_STALE_SECONDS",
}
_WORKER_DEFAULT_STALE_SECONDS = {
    "truffles-outbox": 30,
    "truffles-sentinel": 180,
}

_redis_client = None
_redis_url = None


def _get_redis_url() -> str:
    return ((os.environ.get("REDIS_URL") or "").strip() or _DEFAULT_RUNTIME_REDIS_URL)


def _get_redis_client():
    global _redis_client, _redis_url
    redis_url = _get_redis_url()
    if _redis_client is None or _redis_url != redis_url:
        _redis_url = redis_url
        _redis_client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _redis_client


def _stale_after_seconds(worker_name: str) -> int:
    env_name = _WORKER_STALE_ENV.get(worker_name)
    default = _WORKER_DEFAULT_STALE_SECONDS.get(worker_name, 180)
    raw = os.environ.get(env_name) if env_name else None
    try:
        value = int(float(raw)) if raw is not None else default
    except (TypeError, ValueError):
        value = default
    return max(value, 5)


def _heartbeat_ttl_seconds(worker_name: str) -> int:
    return max(_stale_after_seconds(worker_name) * 3, 300)


def _heartbeat_key(worker_name: str) -> str:
    return f"{_WORKER_HEARTBEAT_PREFIX}:{worker_name}"


def touch_worker_heartbeat(worker_name: str, *, now: datetime | None = None) -> None:
    reference_now = now or datetime.now(timezone.utc)
    timestamp = str(int(reference_now.timestamp()))
    client = _get_redis_client()
    client.setex(_heartbeat_key(worker_name), _heartbeat_ttl_seconds(worker_name), timestamp)


def build_worker_heartbeat_snapshot(
    *,
    worker_names: tuple[str, ...] = _WORKER_NAMES,
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    reference_now = now or datetime.now(timezone.utc)
    client = _get_redis_client()
    snapshot: dict[str, dict[str, Any]] = {}
    for worker_name in worker_names:
        stale_after = _stale_after_seconds(worker_name)
        try:
            raw_value = client.get(_heartbeat_key(worker_name))
        except Exception as exc:
            snapshot[worker_name] = {
                "status": "error",
                "stale_after_seconds": stale_after,
                "error": str(exc),
                "heartbeat_at": None,
                "age_seconds": None,
            }
            continue

        if not raw_value:
            snapshot[worker_name] = {
                "status": "missing",
                "stale_after_seconds": stale_after,
                "heartbeat_at": None,
                "age_seconds": None,
            }
            continue

        try:
            heartbeat_timestamp = int(float(raw_value))
            heartbeat_at = datetime.fromtimestamp(heartbeat_timestamp, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            snapshot[worker_name] = {
                "status": "error",
                "stale_after_seconds": stale_after,
                "error": "invalid_heartbeat",
                "heartbeat_at": None,
                "age_seconds": None,
            }
            continue

        age_seconds = max(int((reference_now - heartbeat_at).total_seconds()), 0)
        snapshot[worker_name] = {
            "status": "healthy" if age_seconds <= stale_after else "stale",
            "stale_after_seconds": stale_after,
            "heartbeat_at": heartbeat_at.isoformat(),
            "age_seconds": age_seconds,
        }

    return snapshot
