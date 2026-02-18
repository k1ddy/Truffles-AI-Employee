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

EXPECTED_EXTERNAL_BLOCK_PATTERNS = [
    "chatflow_billing_blocked",
    "billing blocked",
    "plan renewal required",
    "payment required",
    "subscription expired",
    "insufficient balance",
    "unpaid",
]


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
    parser.add_argument("--postgres-container", default="truffles_postgres_1", help="Postgres container name")
    parser.add_argument("--postgres-db", default="chatbot", help="Postgres database name")
    parser.add_argument("--db-user", default=None, help="Postgres user override")
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

    reason_breakdown = collect_outbox_reason_breakdown(args)
    failed_class_totals = (
        reason_breakdown.get("classification_by_status", {})
        .get("FAILED", {})
        if isinstance(reason_breakdown, dict)
        else {}
    )
    failed_expected_external = int(failed_class_totals.get("expected_external_block", 0) or 0)
    failed_unexpected = int(failed_class_totals.get("unexpected_failure", 0) or 0)

    incident_class = "none"
    if coerce_int(failed_value) and int(failed_value) > 0:
        if failed_unexpected > 0:
            incident_class = "runtime_incident"
        elif failed_expected_external > 0:
            incident_class = "external_block_only"
        else:
            incident_class = "unknown_failure_mix"

    guidance: list[str] = []
    if overall_status in {"warning", "critical"}:
        if incident_class == "external_block_only":
            guidance = [
                "Отметить backlog как expected_external_block (billing/provider) и вести как бизнес-ограничение.",
                "Не открывать runtime incident без unexpected_failure; эскалировать billing/account remediation.",
                "Повторить snapshot после внешнего unblock и проверить нормализацию failed.",
            ]
        else:
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
        "incident_class": incident_class,
        "failed_reason_classes": {
            "expected_external_block": failed_expected_external,
            "unexpected_failure": failed_unexpected,
        },
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
        "reason_breakdown": reason_breakdown,
        "guidance": guidance,
    }


def classify_outbox_reason(reason: str) -> str:
    token = (reason or "").strip().casefold()
    if not token or token == "(empty)":
        return "unknown"
    if any(pattern in token for pattern in EXPECTED_EXTERNAL_BLOCK_PATTERNS):
        return "expected_external_block"
    return "unexpected_failure"


def resolve_db_user(args: argparse.Namespace) -> str:
    if args.db_user:
        return args.db_user
    env_user = os.getenv("DB_USER")
    if env_user:
        return env_user
    try:
        detected = run_command(
            [
                "docker",
                "exec",
                "-i",
                args.postgres_container,
                "/bin/sh",
                "-lc",
                "printf '%s' \"${POSTGRES_USER:-postgres}\"",
            ]
        )
        detected = detected.strip()
        if detected:
            return detected
    except RuntimeError:
        pass
    return "postgres"


def load_outbox_reason_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    db_user = resolve_db_user(args)
    sql = (
        "SELECT status, COALESCE(NULLIF(LEFT(last_error, 220), ''), '(empty)') AS reason, COUNT(*)::bigint "
        "FROM outbox_messages "
        "WHERE status IN ('FAILED', 'PENDING', 'PROCESSING') "
        "GROUP BY status, reason "
        "ORDER BY COUNT(*) DESC;"
    )
    completed = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            args.postgres_container,
            "psql",
            "-U",
            db_user,
            "-d",
            args.postgres_db,
            "-AtF",
            "\t",
            "-c",
            sql,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(stderr or "psql failed")

    rows: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        parts = line.strip().split("\t")
        if len(parts) != 3:
            continue
        status, reason, count_str = parts
        try:
            count_value = int(count_str)
        except ValueError:
            continue
        rows.append(
            {
                "status": status,
                "reason": reason,
                "count": count_value,
                "class": classify_outbox_reason(reason),
            }
        )
    return rows


def collect_outbox_reason_breakdown(args: argparse.Namespace) -> dict[str, Any]:
    try:
        rows = load_outbox_reason_rows(args)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "rows": [],
            "classification_totals": {},
            "status_totals": {},
            "classification_by_status": {},
        }

    classification_totals: dict[str, int] = {}
    status_totals: dict[str, int] = {}
    classification_by_status: dict[str, dict[str, int]] = {}

    for row in rows:
        status = str(row.get("status") or "UNKNOWN")
        reason_class = str(row.get("class") or "unknown")
        count_value = int(row.get("count") or 0)

        status_totals[status] = status_totals.get(status, 0) + count_value
        classification_totals[reason_class] = classification_totals.get(reason_class, 0) + count_value

        status_bucket = classification_by_status.setdefault(status, {})
        status_bucket[reason_class] = status_bucket.get(reason_class, 0) + count_value

    return {
        "status": "ok",
        "rows": rows[:20],
        "rows_total": sum(item.get("count", 0) for item in rows),
        "classification_totals": classification_totals,
        "status_totals": status_totals,
        "classification_by_status": classification_by_status,
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
