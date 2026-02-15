#!/usr/bin/env python3
"""Collect a lightweight Platform Admin KPI snapshot for Console Plane."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_LOC_FILES = [
    "truffles-api/app/routers/console.py",
    "console-web/src/components/ProvisioningWizard.tsx",
    "console-web/src/app/tenants/page.tsx",
    "console-web/src/app/integrations/page.tsx",
    "console-web/src/app/company-workspace/page.tsx",
    "console-web/e2e/smoke.spec.ts",
    "console-web/e2e/platform-admin.spec.ts",
]

DEFAULT_TOAST_FILES = [
    "console-web/src/components/ProvisioningWizard.tsx",
    "console-web/src/app/tenants/page.tsx",
    "console-web/src/app/company-workspace/page.tsx",
]

SEVERITY_ORDER = {
    "ok": 0,
    "unknown": 1,
    "warning": 2,
    "critical": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Platform Admin KPI snapshot")
    parser.add_argument(
        "--console-health-url",
        default=os.getenv("CONSOLE_HEALTH_FULL_URL", "https://console.truffles.kz/api/health/full"),
        help="Console health URL",
    )
    parser.add_argument(
        "--admin-version-url",
        default=os.getenv("ADMIN_VERSION_URL", "https://api.truffles.kz/admin/version"),
        help="Admin version URL",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    parser.add_argument("--output", help="Output file path for JSON snapshot")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--outbox-pending-warning", type=int, default=500, help="Outbox pending warning threshold")
    parser.add_argument("--outbox-pending-critical", type=int, default=1000, help="Outbox pending critical threshold")
    parser.add_argument("--outbox-failed-warning", type=int, default=100, help="Outbox failed warning threshold")
    parser.add_argument("--outbox-failed-critical", type=int, default=300, help="Outbox failed critical threshold")
    parser.add_argument(
        "--fail-on-breach",
        action="store_true",
        help="Exit non-zero when outbox guard reaches fail level",
    )
    parser.add_argument(
        "--fail-level",
        choices=["warning", "critical"],
        default="critical",
        help="Minimum outbox guard level that triggers non-zero exit with --fail-on-breach",
    )
    return parser.parse_args()


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(f"command failed: {' '.join(command)} :: {stderr}")
    return completed.stdout.strip()


def http_json(url: str, timeout: float) -> dict[str, Any]:
    req = request.Request(url=url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        payload = None
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
        return {
            "url": url,
            "ok": False,
            "status_code": exc.code,
            "error": f"HTTPError: {exc.reason}",
            "payload": payload,
            "raw": body[:2000],
        }
    except Exception as exc:  # pragma: no cover - network errors are environment-specific
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        payload = json.loads(body)
        return {
            "url": url,
            "ok": 200 <= status_code < 300,
            "status_code": status_code,
            "payload": payload,
        }
    except json.JSONDecodeError:
        return {
            "url": url,
            "ok": False,
            "status_code": status_code,
            "error": "non_json_response",
            "raw": body[:2000],
        }


def deep_find_first(obj: Any, wanted_keys: set[str]) -> Any:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in wanted_keys:
                return value
            nested = deep_find_first(value, wanted_keys)
            if nested is not None:
                return nested
    elif isinstance(obj, list):
        for item in obj:
            nested = deep_find_first(item, wanted_keys)
            if nested is not None:
                return nested
    return None


def coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return int(float(normalized))
        except ValueError:
            return None
    return None


def classify_threshold(value: int | None, warning_threshold: int, critical_threshold: int) -> str:
    if value is None:
        return "unknown"
    if value >= critical_threshold:
        return "critical"
    if value >= warning_threshold:
        return "warning"
    return "ok"


def evaluate_outbox_guard(pending: Any, failed: Any, args: argparse.Namespace) -> dict[str, Any]:
    pending_value = coerce_int(pending)
    failed_value = coerce_int(failed)

    pending_status = classify_threshold(
        pending_value,
        args.outbox_pending_warning,
        args.outbox_pending_critical,
    )
    failed_status = classify_threshold(
        failed_value,
        args.outbox_failed_warning,
        args.outbox_failed_critical,
    )

    overall_status = max(
        [pending_status, failed_status],
        key=lambda item: SEVERITY_ORDER.get(item, 0),
    )

    guidance: list[str] = []
    if overall_status in {"warning", "critical"}:
        guidance = [
            "Проверить backlog outbox в Console Ops и зафиксировать trend за 24ч.",
            "Запустить remediation runbook outbox и повторить snapshot после действий.",
            "Если status=critical: stop-the-line для Platform Admin релизных решений.",
        ]
    elif overall_status == "unknown":
        guidance = [
            "Не удалось извлечь outbox metrics из health payload; проверить доступность endpoint и формат ответа.",
        ]

    return {
        "status": overall_status,
        "metrics": {
            "pending": {
                "value": pending_value,
                "status": pending_status,
                "warning_threshold": args.outbox_pending_warning,
                "critical_threshold": args.outbox_pending_critical,
            },
            "failed": {
                "value": failed_value,
                "status": failed_status,
                "warning_threshold": args.outbox_failed_warning,
                "critical_threshold": args.outbox_failed_critical,
            },
        },
        "guidance": guidance,
    }


def count_lines(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def count_regex(path: Path, pattern: str) -> int:
    if not path.exists() or not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(pattern, text))


def collect_loc_metrics(files: list[str]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for rel in files:
        abs_path = REPO_ROOT / rel
        line_count = count_lines(abs_path)
        records.append(
            {
                "path": rel,
                "lines": line_count,
                "exists": abs_path.exists(),
            }
        )

    records_sorted = sorted(records, key=lambda item: item["lines"], reverse=True)
    total = sum(item["lines"] for item in records_sorted)
    files_above_1000 = [item["path"] for item in records_sorted if item["lines"] >= 1000]

    return {
        "files": records_sorted,
        "total_lines": total,
        "max_loc_file": records_sorted[0]["path"] if records_sorted else None,
        "files_above_1000": files_above_1000,
    }


def collect_toast_metrics(files: list[str]) -> dict[str, int]:
    return {rel: count_regex(REPO_ROOT / rel, r"toast\.error") for rel in files}


def collect_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    collected_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    local_branch = "unknown"
    local_commit = "unknown"
    try:
        local_branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        local_commit = run_command(["git", "rev-parse", "HEAD"])
    except RuntimeError as exc:
        local_branch = f"error: {exc}"

    console_health = http_json(args.console_health_url, args.timeout)
    admin_version = http_json(args.admin_version_url, args.timeout)

    health_payload = console_health.get("payload", {}) if isinstance(console_health.get("payload"), dict) else {}
    outbox_pending = deep_find_first(health_payload, {"outbox_pending", "pending", "pending_count"})
    outbox_failed = deep_find_first(health_payload, {"outbox_failed", "failed", "failed_count"})
    outbox_guard = evaluate_outbox_guard(outbox_pending, outbox_failed, args)

    loc_metrics = collect_loc_metrics(DEFAULT_LOC_FILES)
    toast_metrics = collect_toast_metrics(DEFAULT_TOAST_FILES)

    smoke_lines = count_lines(REPO_ROOT / "console-web/e2e/smoke.spec.ts")
    platform_admin_lines = count_lines(REPO_ROOT / "console-web/e2e/platform-admin.spec.ts")
    e2e_total = smoke_lines + platform_admin_lines

    snapshot = {
        "collected_at": collected_at,
        "repo": {
            "root": str(REPO_ROOT),
            "branch": local_branch,
            "commit": local_commit,
        },
        "runtime": {
            "console_health": console_health,
            "admin_version": admin_version,
            "derived": {
                "outbox_pending_hint": outbox_pending,
                "outbox_failed_hint": outbox_failed,
            },
            "guards": {
                "outbox": outbox_guard,
            },
        },
        "code_metrics": loc_metrics,
        "ux_metrics": {
            "toast_error_occurrences": toast_metrics,
        },
        "e2e_metrics": {
            "smoke_lines": smoke_lines,
            "platform_admin_lines": platform_admin_lines,
            "combined_lines": e2e_total,
            "platform_admin_share": round(platform_admin_lines / e2e_total, 4) if e2e_total else 0,
        },
    }
    return snapshot


def main() -> int:
    args = parse_args()
    snapshot = collect_snapshot(args)
    indent = 2 if args.pretty else None
    payload = json.dumps(snapshot, ensure_ascii=False, indent=indent)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = REPO_ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")

    print(payload)
    if args.fail_on_breach:
        guard_status = (
            snapshot
            .get("runtime", {})
            .get("guards", {})
            .get("outbox", {})
            .get("status", "ok")
        )
        fail_rank = SEVERITY_ORDER.get(args.fail_level, SEVERITY_ORDER["critical"])
        guard_rank = SEVERITY_ORDER.get(str(guard_status), SEVERITY_ORDER["ok"])
        if guard_rank >= fail_rank:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
