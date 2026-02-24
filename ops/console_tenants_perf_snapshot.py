#!/usr/bin/env python3
"""Capture tenants latency histogram snapshot and evaluate SLO thresholds."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parent.parent

TENANTS_METRIC = "console_tenants_endpoint_latency"
HTTP_METRIC = "http_request_latency"
DEFAULT_BRANCH_PATH = "/console/v1/admin/branches"
DEFAULT_TIMEOUT_SECONDS = 10.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture tenants endpoint latency snapshot from Prometheus metrics (with optional branches HTTP metric)."
    )
    parser.add_argument(
        "--metrics-url",
        default=os.getenv("TENANTS_PERF_METRICS_URL", "http://localhost:8000/metrics"),
        help="Prometheus/OpenMetrics endpoint URL.",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="HTTP timeout in seconds.")
    parser.add_argument("--portfolio-p95-ms", type=float, default=1200.0, help="SLO threshold for portfolio p95.")
    parser.add_argument(
        "--company-cockpit-p95-ms",
        type=float,
        default=1000.0,
        help="SLO threshold for company cockpit p95.",
    )
    parser.add_argument("--branches-p95-ms", type=float, default=800.0, help="SLO threshold for branches list p95.")
    parser.add_argument(
        "--portfolio-min-samples",
        type=int,
        default=20,
        help="Minimum required sample count for portfolio histogram.",
    )
    parser.add_argument(
        "--company-cockpit-min-samples",
        type=int,
        default=20,
        help="Minimum required sample count for company_cockpit histogram.",
    )
    parser.add_argument(
        "--branches-min-samples",
        type=int,
        default=50,
        help="Minimum required sample count for branches GET histogram.",
    )
    parser.add_argument("--branch-path", default=DEFAULT_BRANCH_PATH, help="Normalized HTTP path for branches latency.")
    parser.add_argument(
        "--fail-on-breach",
        action="store_true",
        help="Exit non-zero when any required SLO is missing or breached.",
    )
    parser.add_argument("--output", help="Write JSON report to file.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def fetch_metrics_text(metrics_url: str, timeout: float) -> tuple[str | None, str | None]:
    req = request.Request(url=metrics_url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return body, None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, f"HTTPError {exc.code}: {exc.reason}; body={detail[:400]}"
    except Exception as exc:  # pragma: no cover - network failures are environment-specific
        return None, f"{type(exc).__name__}: {exc}"


_METRIC_LINE_RE = re.compile(
    r"""^
    (?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)
    (?:\{(?P<labels>[^}]*)\})?
    \s+
    (?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|[Ii]nf)
    $""",
    re.VERBOSE,
)
_LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:\\.|[^"\\])*)"')


def _parse_labels(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    labels: dict[str, str] = {}
    for match in _LABEL_RE.finditer(raw):
        key = match.group(1)
        value = match.group(2).replace(r"\\", "\\").replace(r"\"", '"')
        labels[key] = value
    return labels


def _parse_metric_lines(metrics_text: str, metric_name: str) -> list[tuple[dict[str, str], float]]:
    rows: list[tuple[dict[str, str], float]] = []
    for raw_line in metrics_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _METRIC_LINE_RE.match(line)
        if not match:
            continue
        if match.group("name") != metric_name:
            continue
        labels = _parse_labels(match.group("labels"))
        value_token = match.group("value")
        value = float("inf") if value_token.lower() == "inf" else float(value_token)
        rows.append((labels, value))
    return rows


def _extract_histogram_by_label(
    metrics_text: str,
    *,
    metric_prefix: str,
    key_label: str,
    filters: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    filters = filters or {}
    bucket_rows = _parse_metric_lines(metrics_text, f"{metric_prefix}_bucket")
    count_rows = _parse_metric_lines(metrics_text, f"{metric_prefix}_count")
    grouped: dict[str, dict[str, Any]] = {}

    for labels, value in bucket_rows:
        if any(labels.get(k) != v for k, v in filters.items()):
            continue
        key = labels.get(key_label)
        le_raw = labels.get("le")
        if key is None or le_raw is None:
            continue
        le_value = float("inf") if le_raw == "+Inf" else float(le_raw)
        payload = grouped.setdefault(key, {"buckets": [], "count": None})
        payload["buckets"].append((le_value, value))

    for labels, value in count_rows:
        if any(labels.get(k) != v for k, v in filters.items()):
            continue
        key = labels.get(key_label)
        if key is None:
            continue
        payload = grouped.setdefault(key, {"buckets": [], "count": None})
        payload["count"] = value

    for payload in grouped.values():
        payload["buckets"] = sorted(payload["buckets"], key=lambda item: item[0])
    return grouped


def _estimate_quantile_seconds(buckets: list[tuple[float, float]], quantile: float) -> float | None:
    if not buckets:
        return None
    total = buckets[-1][1]
    if total <= 0:
        return None
    target = total * quantile
    for le, cumulative_count in buckets:
        if cumulative_count >= target:
            return le
    return buckets[-1][0]


def _build_histogram_report(
    grouped: dict[str, dict[str, Any]],
    *,
    p95_slo_ms: float | None = None,
) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    for key, payload in grouped.items():
        buckets = payload.get("buckets") or []
        count_value = payload.get("count")
        p50 = _estimate_quantile_seconds(buckets, 0.5)
        p95 = _estimate_quantile_seconds(buckets, 0.95)
        p99 = _estimate_quantile_seconds(buckets, 0.99)
        p95_ms = round(p95 * 1000.0, 2) if p95 is not None and p95 != float("inf") else None
        slo_pass = None
        if p95_slo_ms is not None and p95_ms is not None:
            slo_pass = p95_ms <= p95_slo_ms
        report[key] = {
            "samples": int(count_value) if isinstance(count_value, (int, float)) else None,
            "p50_ms": round(p50 * 1000.0, 2) if p50 is not None and p50 != float("inf") else None,
            "p95_ms": p95_ms,
            "p99_ms": round(p99 * 1000.0, 2) if p99 is not None and p99 != float("inf") else None,
            "p95_slo_ms": p95_slo_ms,
            "p95_slo_pass": slo_pass,
        }
    return report


def _write_report(report: dict[str, Any], output_path: str | None, *, pretty: bool) -> None:
    if output_path is None:
        return
    path = Path(output_path)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=True, indent=2 if pretty else None, sort_keys=pretty)
    path.write_text(payload + ("\n" if pretty else ""), encoding="utf-8")


def _required_slo_failed(report: dict[str, Any]) -> bool:
    tenants = report.get("tenants_endpoint_latency") if isinstance(report, dict) else None
    if not isinstance(tenants, dict):
        return True

    required = ("portfolio", "company_cockpit")
    for endpoint in required:
        endpoint_metrics = tenants.get(endpoint)
        if not isinstance(endpoint_metrics, dict):
            return True
        if endpoint_metrics.get("p95_slo_pass") is not True:
            return True

    branches = report.get("branches_get_latency")
    if isinstance(branches, dict) and branches:
        branch_metrics = next(iter(branches.values()))
        if isinstance(branch_metrics, dict) and branch_metrics.get("p95_slo_pass") is False:
            return True
    return False


def _required_sample_size_failed(
    report: dict[str, Any],
    *,
    portfolio_min_samples: int,
    company_cockpit_min_samples: int,
    branches_min_samples: int,
) -> bool:
    tenants = report.get("tenants_endpoint_latency") if isinstance(report, dict) else None
    if not isinstance(tenants, dict):
        return True

    portfolio = tenants.get("portfolio")
    company_cockpit = tenants.get("company_cockpit")
    if not isinstance(portfolio, dict) or not isinstance(company_cockpit, dict):
        return True

    portfolio_samples = portfolio.get("samples")
    company_cockpit_samples = company_cockpit.get("samples")
    if not isinstance(portfolio_samples, int) or portfolio_samples < portfolio_min_samples:
        return True
    if not isinstance(company_cockpit_samples, int) or company_cockpit_samples < company_cockpit_min_samples:
        return True

    branches = report.get("branches_get_latency")
    if not isinstance(branches, dict) or not branches:
        return True
    branch_metrics = next(iter(branches.values()))
    if not isinstance(branch_metrics, dict):
        return True
    branch_samples = branch_metrics.get("samples")
    if not isinstance(branch_samples, int) or branch_samples < branches_min_samples:
        return True
    return False


def capture_tenants_perf_snapshot(
    *,
    metrics_url: str,
    timeout: float,
    portfolio_p95_ms: float,
    company_cockpit_p95_ms: float,
    branches_p95_ms: float,
    portfolio_min_samples: int,
    company_cockpit_min_samples: int,
    branches_min_samples: int,
    branch_path: str,
) -> dict[str, Any]:
    metrics_text, error_text = fetch_metrics_text(metrics_url, timeout=timeout)
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()

    report: dict[str, Any] = {
        "generated_at": generated_at,
        "metrics_url": metrics_url,
        "error": error_text,
        "tenants_endpoint_latency": {},
        "branches_get_latency": {},
        "slo_targets_ms": {
            "portfolio_p95": portfolio_p95_ms,
            "company_cockpit_p95": company_cockpit_p95_ms,
            "branches_get_p95": branches_p95_ms,
        },
        "sample_targets": {
            "portfolio_min_samples": portfolio_min_samples,
            "company_cockpit_min_samples": company_cockpit_min_samples,
            "branches_min_samples": branches_min_samples,
        },
    }

    if metrics_text is not None:
        tenants_hist = _extract_histogram_by_label(
            metrics_text,
            metric_prefix=TENANTS_METRIC,
            key_label="endpoint",
        )
        tenants_report = _build_histogram_report(tenants_hist)
        if "portfolio" in tenants_report:
            tenants_report["portfolio"]["p95_slo_ms"] = portfolio_p95_ms
            p95_ms = tenants_report["portfolio"].get("p95_ms")
            tenants_report["portfolio"]["p95_slo_pass"] = (
                p95_ms <= portfolio_p95_ms if isinstance(p95_ms, (int, float)) else None
            )
        if "company_cockpit" in tenants_report:
            tenants_report["company_cockpit"]["p95_slo_ms"] = company_cockpit_p95_ms
            p95_ms = tenants_report["company_cockpit"].get("p95_ms")
            tenants_report["company_cockpit"]["p95_slo_pass"] = (
                p95_ms <= company_cockpit_p95_ms if isinstance(p95_ms, (int, float)) else None
            )
        report["tenants_endpoint_latency"] = tenants_report

        branches_hist = _extract_histogram_by_label(
            metrics_text,
            metric_prefix=HTTP_METRIC,
            key_label="path",
            filters={"method": "GET", "path": branch_path},
        )
        report["branches_get_latency"] = _build_histogram_report(
            branches_hist,
            p95_slo_ms=branches_p95_ms,
        )

    report["required_slo_failed"] = _required_slo_failed(report)
    report["required_sample_size_failed"] = _required_sample_size_failed(
        report,
        portfolio_min_samples=portfolio_min_samples,
        company_cockpit_min_samples=company_cockpit_min_samples,
        branches_min_samples=branches_min_samples,
    )
    report["status"] = "fail" if (report["required_slo_failed"] or report["required_sample_size_failed"]) else "pass"
    return report


def main() -> int:
    args = parse_args()
    report = capture_tenants_perf_snapshot(
        metrics_url=args.metrics_url,
        timeout=args.timeout,
        portfolio_p95_ms=args.portfolio_p95_ms,
        company_cockpit_p95_ms=args.company_cockpit_p95_ms,
        branches_p95_ms=args.branches_p95_ms,
        portfolio_min_samples=args.portfolio_min_samples,
        company_cockpit_min_samples=args.company_cockpit_min_samples,
        branches_min_samples=args.branches_min_samples,
        branch_path=args.branch_path,
    )

    _write_report(report, args.output, pretty=args.pretty)
    print(json.dumps(report, ensure_ascii=True, indent=2 if args.pretty else None, sort_keys=args.pretty))

    if args.fail_on_breach and (report["required_slo_failed"] or report["required_sample_size_failed"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
