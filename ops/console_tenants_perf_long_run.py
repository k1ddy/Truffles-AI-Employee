#!/usr/bin/env python3
"""Run authenticated tenants load profile and validate runtime latency snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

try:
    import console_tenants_perf_snapshot as perf_snapshot
except ImportError:  # pragma: no cover
    from ops import console_tenants_perf_snapshot as perf_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "https://api.truffles.kz"


def _first_env(keys: list[str]) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute reproducible authenticated load profile for tenants endpoints and enforce perf gates."
    )
    parser.add_argument("--base-url", default=os.getenv("TENANTS_PERF_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument(
        "--metrics-url",
        default=os.getenv("TENANTS_PERF_METRICS_URL", "https://api.truffles.kz/metrics"),
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--loops", type=int, default=40)
    parser.add_argument("--sleep-ms", type=int, default=0, help="Delay between request batches.")
    parser.add_argument("--portfolio-limit", type=int, default=20)
    parser.add_argument("--company-cockpit-limit", type=int, default=20)
    parser.add_argument("--branches-limit", type=int, default=20)
    parser.add_argument("--company-id", default=os.getenv("TENANTS_PERF_COMPANY_ID"))
    parser.add_argument("--client-id", default=os.getenv("TENANTS_PERF_CLIENT_ID"))
    parser.add_argument("--branch-id", default=os.getenv("TENANTS_PERF_BRANCH_ID"))
    parser.add_argument("--portfolio-p95-ms", type=float, default=1200.0)
    parser.add_argument("--company-cockpit-p95-ms", type=float, default=1000.0)
    parser.add_argument("--branches-p95-ms", type=float, default=800.0)
    parser.add_argument("--portfolio-min-samples", type=int, default=40)
    parser.add_argument("--company-cockpit-min-samples", type=int, default=40)
    parser.add_argument("--branches-min-samples", type=int, default=80)
    parser.add_argument("--output", help="Path for combined load+snapshot report JSON.")
    parser.add_argument("--snapshot-output", help="Optional path for raw snapshot JSON.")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--fail-on-breach", action="store_true")
    parser.add_argument("--allow-request-failures", action="store_true")
    parser.add_argument("--token-url", default=_first_env(["KEYCLOAK_TOKEN_URL", "CONSOLE_KEYCLOAK_TOKEN_URL"]))
    parser.add_argument("--token-client-id", default=_first_env(["KEYCLOAK_CLIENT_ID", "CONSOLE_KEYCLOAK_CLIENT_ID"]))
    parser.add_argument("--token-client-secret", default=_first_env(["KEYCLOAK_CLIENT_SECRET", "CONSOLE_KEYCLOAK_CLIENT_SECRET"]))
    parser.add_argument("--token-username", default=_first_env(["KEYCLOAK_USERNAME", "CONSOLE_KEYCLOAK_USERNAME", "CONSOLE_E2E_USERNAME"]))
    parser.add_argument("--token-password", default=_first_env(["KEYCLOAK_PASSWORD", "CONSOLE_KEYCLOAK_PASSWORD", "CONSOLE_E2E_PASSWORD"]))
    return parser.parse_args()


def _request_access_token(args: argparse.Namespace) -> str:
    if not args.token_url or not args.token_client_id or not args.token_username or not args.token_password:
        raise RuntimeError("Missing token config (token-url/client-id/username/password).")
    payload = {
        "grant_type": "password",
        "client_id": args.token_client_id,
        "username": args.token_username,
        "password": args.token_password,
    }
    if args.token_client_secret:
        payload["client_secret"] = args.token_client_secret
    body = parse.urlencode(payload).encode("utf-8")
    req = request.Request(
        url=args.token_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with request.urlopen(req, timeout=args.timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    token = data.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Token response missing access_token")
    return token


def _call_json(url: str, *, token: str, timeout: float) -> tuple[int | None, str | None]:
    req = request.Request(
        url=url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            response.read()
            return int(response.status), None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return exc.code, detail[:300]
    except Exception as exc:  # pragma: no cover - network/infra dependent
        return None, f"{type(exc).__name__}: {exc}"


def _build_url(base_url: str, path: str, params: dict[str, Any]) -> str:
    query = parse.urlencode({key: value for key, value in params.items() if value is not None and value != ""})
    return f"{base_url.rstrip('/')}{path}?{query}"


def _record_call(stats: dict[str, Any], endpoint: str, status: int | None, error_text: str | None) -> None:
    endpoint_stats = stats.setdefault(endpoint, {"ok": 0, "failed": 0, "statuses": {}, "errors": []})
    status_key = str(status) if status is not None else "network_error"
    endpoint_stats["statuses"][status_key] = endpoint_stats["statuses"].get(status_key, 0) + 1
    if status == 200:
        endpoint_stats["ok"] += 1
        return
    endpoint_stats["failed"] += 1
    if error_text:
        endpoint_stats["errors"].append(error_text)


def _write_json(path_value: str | None, payload: dict[str, Any], *, pretty: bool) -> None:
    if not path_value:
        return
    path = Path(path_value)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2 if pretty else None, sort_keys=pretty)
        + ("\n" if pretty else ""),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    token = _request_access_token(args)

    stats: dict[str, Any] = {}
    sleep_seconds = max(args.sleep_ms, 0) / 1000.0

    for _ in range(max(args.loops, 0)):
        portfolio_url = _build_url(
            args.base_url,
            "/console/v1/admin/tenants/portfolio",
            {"limit": args.portfolio_limit},
        )
        status, detail = _call_json(portfolio_url, token=token, timeout=args.timeout)
        _record_call(stats, "portfolio", status, detail)

        company_cockpit_url = _build_url(
            args.base_url,
            "/console/v1/admin/tenants/company-cockpit",
            {
                "company_id": args.company_id,
                "client_id": args.client_id,
                "include_branches": "false",
                "client_limit": args.company_cockpit_limit,
            },
        )
        status, detail = _call_json(company_cockpit_url, token=token, timeout=args.timeout)
        _record_call(stats, "company_cockpit", status, detail)

        branches_url = _build_url(
            args.base_url,
            "/console/v1/admin/branches",
            {
                "company_id": args.company_id,
                "client_id": args.client_id,
                "branch_id": args.branch_id,
                "limit": args.branches_limit,
            },
        )
        status, detail = _call_json(branches_url, token=token, timeout=args.timeout)
        _record_call(stats, "branches", status, detail)

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    snapshot_report = perf_snapshot.capture_tenants_perf_snapshot(
        metrics_url=args.metrics_url,
        timeout=args.timeout,
        portfolio_p95_ms=args.portfolio_p95_ms,
        company_cockpit_p95_ms=args.company_cockpit_p95_ms,
        branches_p95_ms=args.branches_p95_ms,
        portfolio_min_samples=args.portfolio_min_samples,
        company_cockpit_min_samples=args.company_cockpit_min_samples,
        branches_min_samples=args.branches_min_samples,
        branch_path=perf_snapshot.DEFAULT_BRANCH_PATH,
    )

    request_failures = sum(int(endpoint.get("failed", 0)) for endpoint in stats.values())
    request_failures_allowed = bool(args.allow_request_failures)
    request_failures_failed = (request_failures > 0) and (not request_failures_allowed)
    status = "pass"
    if snapshot_report.get("status") != "pass" or request_failures_failed:
        status = "fail"

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "started_at": started_at,
        "base_url": args.base_url,
        "metrics_url": args.metrics_url,
        "loops": args.loops,
        "sleep_ms": args.sleep_ms,
        "request_stats": stats,
        "request_failures": request_failures,
        "request_failures_allowed": request_failures_allowed,
        "request_failures_failed": request_failures_failed,
        "snapshot": snapshot_report,
        "status": status,
    }

    _write_json(args.snapshot_output, snapshot_report, pretty=args.pretty)
    _write_json(args.output, report, pretty=args.pretty)
    print(json.dumps(report, ensure_ascii=True, indent=2 if args.pretty else None, sort_keys=args.pretty))

    if args.fail_on_breach and status != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
