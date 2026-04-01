"""In-memory SLA tracking for router fallback/timeout rates."""

from __future__ import annotations

import threading

_router_sla_lock = threading.Lock()
_router_sla_counts = {"attempts": 0, "fallbacks": 0, "timeouts": 0}
_router_fallback_flag_threshold = 0.1


def _update_router_sla(*, attempted: bool, fallback: bool, timeout: bool) -> dict:
    if not attempted:
        return {
            "attempts": 0,
            "fallbacks": 0,
            "timeouts": 0,
            "fallback_rate": 0.0,
            "timeout_rate": 0.0,
            "fallback_rate_flag": False,
        }
    with _router_sla_lock:
        _router_sla_counts["attempts"] += 1
        if fallback:
            _router_sla_counts["fallbacks"] += 1
        if timeout:
            _router_sla_counts["timeouts"] += 1
        attempts = _router_sla_counts["attempts"]
        fallbacks = _router_sla_counts["fallbacks"]
        timeouts = _router_sla_counts["timeouts"]
    fallback_rate = fallbacks / max(attempts, 1)
    timeout_rate = timeouts / max(attempts, 1)
    return {
        "attempts": attempts,
        "fallbacks": fallbacks,
        "timeouts": timeouts,
        "fallback_rate": round(fallback_rate, 4),
        "timeout_rate": round(timeout_rate, 4),
        "fallback_rate_flag": fallback_rate > _router_fallback_flag_threshold,
    }


__all__ = ["_update_router_sla"]
