from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REQUIRED_METRICS = (
    "health_check_knowledge_activation_status",
    "knowledge_activation_jobs_total",
    "knowledge_activation_failed_24h_total",
    "knowledge_activation_stale_running_total",
    "knowledge_activation_oldest_queued_age_seconds",
    "knowledge_activation_oldest_running_heartbeat_age_seconds",
)
_STATUS_RANK = {
    "healthy": 0,
    "warning": 1,
    "critical": 2,
    "error": 3,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout: float = 5.0,
) -> tuple[int | None, dict[str, Any] | None, str | None]:
    request = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=max(timeout, 0.1)) as response:
            payload = response.read().decode("utf-8")
            return int(getattr(response, "status", 200)), json.loads(payload or "{}"), None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, None, body or str(exc)
    except urllib.error.URLError as exc:
        return None, None, str(exc.reason or exc)
    except Exception as exc:  # pragma: no cover - safety net
        return None, None, str(exc)


def _text_request(url: str, *, timeout: float = 5.0) -> tuple[int | None, str | None, str | None]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=max(timeout, 0.1)) as response:
            payload = response.read().decode("utf-8")
            return int(getattr(response, "status", 200)), payload, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, None, body or str(exc)
    except urllib.error.URLError as exc:
        return None, None, str(exc.reason or exc)
    except Exception as exc:  # pragma: no cover - safety net
        return None, None, str(exc)


def _collect_metrics_snapshot(metrics_text: str | None) -> dict[str, Any]:
    present: list[str] = []
    missing: list[str] = []
    text = metrics_text or ""
    for metric_name in _REQUIRED_METRICS:
        pattern = re.compile(rf"(?m)^{re.escape(metric_name)}(?:\{{|\s)")
        if pattern.search(text):
            present.append(metric_name)
        else:
            missing.append(metric_name)
    return {
        "required": list(_REQUIRED_METRICS),
        "present": present,
        "missing": missing,
    }


def build_release_guard_snapshot(
    *,
    service_health_url: str,
    process_url: str,
    admin_health_url: str,
    metrics_url: str,
    service_token: str | None,
    timeout_seconds: float,
    max_activation_status: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    health_status_code, service_health, service_error = _json_request(
        service_health_url,
        timeout=timeout_seconds,
    )
    if health_status_code != 200 or not isinstance(service_health, dict):
        reasons.append("service_health_unavailable")
    elif str(service_health.get("status") or "").strip().lower() != "ok":
        reasons.append("service_health_not_ok")
    elif service_health.get("knowledge_activation_enabled") is not True:
        reasons.append("service_not_enabled")

    headers: dict[str, str] = {}
    if service_token:
        headers["X-Knowledge-Activation-Service-Token"] = service_token
    process_status_code, process_payload, process_error = _json_request(
        process_url,
        method="POST",
        headers=headers,
        timeout=timeout_seconds,
    )
    if process_status_code != 200 or not isinstance(process_payload, dict):
        reasons.append("process_probe_failed")

    admin_status_code, admin_health, admin_error = _json_request(
        admin_health_url,
        timeout=timeout_seconds,
    )
    activation_health: dict[str, Any] | None = None
    if admin_status_code != 200 or not isinstance(admin_health, dict):
        reasons.append("admin_health_unavailable")
    else:
        checks = admin_health.get("checks") if isinstance(admin_health.get("checks"), dict) else {}
        activation_health = checks.get("knowledge_activation") if isinstance(checks.get("knowledge_activation"), dict) else None
        if activation_health is None:
            reasons.append("activation_health_missing")
        else:
            raw_status = str(activation_health.get("status") or "error").strip().lower()
            actual_rank = _STATUS_RANK.get(raw_status, _STATUS_RANK["error"])
            allowed_rank = _STATUS_RANK.get(max_activation_status, _STATUS_RANK["warning"])
            if actual_rank > allowed_rank:
                reasons.append(f"activation_health_{raw_status}")

    metrics_status_code, metrics_text, metrics_error = _text_request(metrics_url, timeout=timeout_seconds)
    metrics_snapshot = _collect_metrics_snapshot(metrics_text)
    if metrics_status_code != 200:
        reasons.append("metrics_unavailable")
    elif metrics_snapshot["missing"]:
        reasons.append("activation_metrics_missing")

    decision = "go" if not reasons else "no_go"
    return {
        "captured_at": _iso_now(),
        "decision": decision,
        "reasons": reasons,
        "service_health": {
            "url": service_health_url,
            "status_code": health_status_code,
            "payload": service_health,
            "error": service_error,
        },
        "process_probe": {
            "url": process_url,
            "status_code": process_status_code,
            "payload": process_payload,
            "error": process_error,
        },
        "admin_health": {
            "url": admin_health_url,
            "status_code": admin_status_code,
            "payload": admin_health,
            "knowledge_activation": activation_health,
            "error": admin_error,
            "max_allowed_status": max_activation_status,
        },
        "metrics": {
            "url": metrics_url,
            "status_code": metrics_status_code,
            "snapshot": metrics_snapshot,
            "error": metrics_error,
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge activation release guard")
    parser.add_argument(
        "--service-health-url",
        default=os.environ.get("KNOWLEDGE_ACTIVATION_SERVICE_HEALTH_URL", "http://127.0.0.1:8015/health"),
    )
    parser.add_argument(
        "--process-url",
        default=os.environ.get("KNOWLEDGE_ACTIVATION_PROCESS_URL", "http://127.0.0.1:8015/knowledge-activation/process"),
    )
    parser.add_argument(
        "--admin-health-url",
        default=os.environ.get("KNOWLEDGE_ACTIVATION_ADMIN_HEALTH_URL", "http://127.0.0.1:8000/admin/health/check"),
    )
    parser.add_argument(
        "--metrics-url",
        default=os.environ.get("KNOWLEDGE_ACTIVATION_METRICS_URL", "http://127.0.0.1:8000/metrics"),
    )
    parser.add_argument(
        "--service-token",
        default=os.environ.get("KNOWLEDGE_ACTIVATION_SERVICE_TOKEN"),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.environ.get("KNOWLEDGE_ACTIVATION_RELEASE_GUARD_TIMEOUT_SECONDS", "5")),
    )
    parser.add_argument(
        "--max-activation-status",
        choices=("healthy", "warning", "critical"),
        default=os.environ.get("KNOWLEDGE_ACTIVATION_RELEASE_MAX_STATUS", "warning"),
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    snapshot = build_release_guard_snapshot(
        service_health_url=args.service_health_url,
        process_url=args.process_url,
        admin_health_url=args.admin_health_url,
        metrics_url=args.metrics_url,
        service_token=args.service_token,
        timeout_seconds=max(float(args.timeout_seconds), 0.1),
        max_activation_status=args.max_activation_status,
    )
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + ("\n" if not payload.endswith("\n") else ""), encoding="utf-8")
    print(payload)
    return 0 if snapshot.get("decision") == "go" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
