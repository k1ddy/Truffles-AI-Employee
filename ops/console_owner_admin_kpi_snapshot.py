#!/usr/bin/env python3
"""Capture owner/admin business KPI snapshot with baseline comparison."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

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

DEFAULT_LOC_FILES = [
    "truffles-api/app/routers/console.py",
    "truffles-api/app/services/console_owner_admin.py",
    "console-web/src/app/business/team-performance/page.tsx",
    "console-web/e2e/owner-admin-business.spec.ts",
    "docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture owner/admin KPI snapshot")
    parser.add_argument("--client-slug", default="demo_salon", help="Client slug to evaluate")
    parser.add_argument("--output", help="Write snapshot JSON to file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--baseline", help="Path to previous snapshot JSON for delta analysis")
    parser.add_argument("--timeout", type=float, default=20.0, help="Shell command timeout in seconds")
    parser.add_argument("--postgres-container", default="truffles_postgres_1", help="Postgres container name")
    parser.add_argument("--postgres-db", default="chatbot", help="Postgres database name")
    parser.add_argument("--db-user", default=None, help="Postgres user override")

    parser.add_argument("--outbox-warning", type=int, default=500, help="outbox_backlog warning threshold")
    parser.add_argument("--outbox-critical", type=int, default=1000, help="outbox_backlog critical threshold")
    parser.add_argument("--unresolved-warning", type=int, default=15, help="unresolved_cases warning threshold")
    parser.add_argument("--unresolved-critical", type=int, default=40, help="unresolved_cases critical threshold")
    parser.add_argument("--stale-warning", type=int, default=5, help="unresolved_older_than_60m warning threshold")
    parser.add_argument("--stale-critical", type=int, default=20, help="unresolved_older_than_60m critical threshold")
    parser.add_argument(
        "--p90-warning",
        type=float,
        default=600.0,
        help="first_response_p90_seconds warning threshold",
    )
    parser.add_argument(
        "--p90-critical",
        type=float,
        default=900.0,
        help="first_response_p90_seconds critical threshold",
    )

    parser.add_argument(
        "--fail-on-breach",
        action="store_true",
        help="Exit non-zero when guard status reaches fail-level",
    )
    parser.add_argument(
        "--fail-level",
        choices=["warning", "critical"],
        default="critical",
        help="Minimum guard level that triggers non-zero exit with --fail-on-breach",
    )
    return parser.parse_args()


def run_shell(command: str, *, timeout: float) -> str:
    completed = subprocess.run(
        ["/bin/bash", "-lc", command],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"exit={completed.returncode}"
        raise RuntimeError(detail)
    return completed.stdout.strip()


def parse_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
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


def parse_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def classify(value: float | None, warning_threshold: float, critical_threshold: float) -> str:
    if value is None:
        return "unknown"
    if value >= critical_threshold:
        return "critical"
    if value >= warning_threshold:
        return "warning"
    return "ok"


def resolve_db_user(args: argparse.Namespace, *, timeout: float) -> str:
    if args.db_user:
        return args.db_user
    shell = (
        "DB_USER=$(docker exec -i "
        f"{shlex.quote(args.postgres_container)} /bin/sh -lc 'printf %s \"${{POSTGRES_USER:-postgres}}\"')\n"
        "printf '%s' \"$DB_USER\""
    )
    try:
        resolved = run_shell(shell, timeout=timeout).strip()
        if resolved:
            return resolved
    except Exception:
        pass
    return "postgres"


def classify_outbox_reason(reason: str) -> str:
    token = (reason or "").strip().casefold()
    if not token or token == "(empty)":
        return "unknown"
    if any(pattern in token for pattern in EXPECTED_EXTERNAL_BLOCK_PATTERNS):
        return "expected_external_block"
    return "unexpected_failure"


def load_business_kpis(
    client_slug: str,
    timeout: float,
    *,
    postgres_container: str,
    postgres_db: str,
    db_user: str,
) -> dict[str, Any]:
    client_slug_sql = client_slug.replace("'", "''")
    sql = f"""
WITH target AS (
  SELECT id FROM clients WHERE name = '{client_slug_sql}' LIMIT 1
)
SELECT json_build_object(
  'client_id', (SELECT id::text FROM target),
  'outbox_backlog', (
    SELECT COUNT(*)
    FROM outbox_messages o
    JOIN target t ON o.client_id = t.id
    WHERE o.status IN ('PENDING', 'PROCESSING')
  ),
  'unresolved_cases', (
    SELECT COUNT(*)
    FROM handovers h
    JOIN target t ON h.client_id = t.id
    WHERE h.status IN ('pending', 'active')
  ),
  'unresolved_older_than_60m', (
    SELECT COUNT(*)
    FROM handovers h
    JOIN target t ON h.client_id = t.id
    WHERE h.status IN ('pending', 'active')
      AND h.created_at < NOW() - INTERVAL '60 minutes'
  ),
  'first_response_p90_seconds', (
    SELECT m.first_response_p90_seconds
    FROM metrics_analytics_daily m
    JOIN target t ON m.client_id = t.id
    ORDER BY m.metric_date DESC
    LIMIT 1
  ),
  'metric_date', (
    SELECT m.metric_date::text
    FROM metrics_analytics_daily m
    JOIN target t ON m.client_id = t.id
    ORDER BY m.metric_date DESC
    LIMIT 1
  ),
  'reminder_1_minutes', (
    SELECT s.reminder_timeout_1
    FROM client_settings s
    JOIN target t ON s.client_id = t.id
    LIMIT 1
  ),
  'reminder_2_minutes', (
    SELECT s.reminder_timeout_2
    FROM client_settings s
    JOIN target t ON s.client_id = t.id
    LIMIT 1
  ),
  'escalation_timeout_minutes', (
    SELECT s.auto_close_timeout
    FROM client_settings s
    JOIN target t ON s.client_id = t.id
    LIMIT 1
  )
)::text;
"""

    shell = (
        f"docker exec -i {shlex.quote(postgres_container)} "
        f"psql -U {shlex.quote(db_user)} -d {shlex.quote(postgres_db)} -Atc {shlex.quote(sql)}"
    )
    raw = run_shell(shell, timeout=timeout)
    line = ""
    for candidate in reversed(raw.splitlines()):
        if candidate.strip():
            line = candidate.strip()
            break
    if not line:
        raise RuntimeError("empty SQL output")
    payload = json.loads(line)
    if not payload.get("client_id"):
        raise RuntimeError(f"client not found: {client_slug}")
    return payload


def collect_outbox_reason_breakdown(
    *,
    client_id: str,
    timeout: float,
    postgres_container: str,
    postgres_db: str,
    db_user: str,
) -> dict[str, Any]:
    client_id_sql = str(client_id or "").replace("'", "''")
    sql = (
        "SELECT status, COALESCE(NULLIF(LEFT(last_error, 220), ''), '(empty)') AS reason, COUNT(*)::bigint "
        "FROM outbox_messages "
        f"WHERE client_id = '{client_id_sql}'::uuid "
        "AND status IN ('FAILED', 'PENDING', 'PROCESSING') "
        "GROUP BY status, reason "
        "ORDER BY COUNT(*) DESC;"
    )
    shell = (
        f"docker exec -i {shlex.quote(postgres_container)} "
        f"psql -U {shlex.quote(db_user)} -d {shlex.quote(postgres_db)} -AtF $'\\t' -c {shlex.quote(sql)}"
    )

    try:
        raw = run_shell(shell, timeout=timeout)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "rows": [],
            "classification_totals": {},
            "status_totals": {},
            "classification_by_status": {},
        }

    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
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

    classification_totals: dict[str, int] = {}
    status_totals: dict[str, int] = {}
    classification_by_status: dict[str, dict[str, int]] = {}
    for row in rows:
        status = str(row.get("status") or "UNKNOWN")
        reason_class = str(row.get("class") or "unknown")
        count_value = int(row.get("count") or 0)
        classification_totals[reason_class] = classification_totals.get(reason_class, 0) + count_value
        status_totals[status] = status_totals.get(status, 0) + count_value
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


def collect_loc_metrics() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for rel in DEFAULT_LOC_FILES:
        abs_path = REPO_ROOT / rel
        records.append(
            {
                "path": rel,
                "exists": abs_path.exists(),
                "lines": count_lines(abs_path),
            }
        )
    return {
        "files": records,
        "total_lines": sum(item["lines"] for item in records),
    }


def evaluate_guard(
    kpi_values: dict[str, float | int | None],
    args: argparse.Namespace,
    *,
    outbox_reason_breakdown: dict[str, Any] | None = None,
) -> dict[str, Any]:
    statuses = {
        "outbox_backlog": classify(parse_float(kpi_values.get("outbox_backlog")), args.outbox_warning, args.outbox_critical),
        "unresolved_cases": classify(parse_float(kpi_values.get("unresolved_cases")), args.unresolved_warning, args.unresolved_critical),
        "unresolved_older_than_60m": classify(parse_float(kpi_values.get("unresolved_older_than_60m")), args.stale_warning, args.stale_critical),
        "first_response_p90_seconds": classify(parse_float(kpi_values.get("first_response_p90_seconds")), args.p90_warning, args.p90_critical),
    }
    overall = max(statuses.values(), key=lambda value: SEVERITY_ORDER.get(value, 0))

    failed_class_totals = (
        (outbox_reason_breakdown or {}).get("classification_by_status", {}).get("FAILED", {})
        if isinstance(outbox_reason_breakdown, dict)
        else {}
    )
    failed_expected_external = int(failed_class_totals.get("expected_external_block", 0) or 0)
    failed_unexpected = int(failed_class_totals.get("unexpected_failure", 0) or 0)

    incident_class = "none"
    failed_total = int(
        ((outbox_reason_breakdown or {}).get("status_totals", {}).get("FAILED", 0) or 0)
        if isinstance(outbox_reason_breakdown, dict)
        else 0
    )
    if failed_total > 0:
        if failed_unexpected > 0:
            incident_class = "runtime_incident"
        elif failed_expected_external > 0:
            incident_class = "external_block_only"
        else:
            incident_class = "unknown_failure_mix"

    guidance: list[str] = []
    if overall in {"warning", "critical"}:
        if incident_class == "external_block_only":
            guidance.append("Зафиксировать failed как expected_external_block (например ChatFlow unpaid/billing).")
            guidance.append("Не открывать runtime incident без unexpected_failure; эскалировать billing unblock.")
            guidance.append("Сравнить T+24 snapshot после внешнего unblock и проверить динамику failed.")
        else:
            guidance.append("Открыть Team Performance и зафиксировать remediation шаг (quick profile/распределение нагрузки).")
            guidance.append("Сравнить T+24 snapshot с baseline и проверить снижение backlog/stale-cases.")
            guidance.append("Если status=critical: stop-the-line для owner/admin rollout решений до стабилизации.")
    elif overall == "unknown":
        guidance.append("Не удалось собрать часть KPI; проверить доступ к postgres контейнеру и client slug.")

    return {
        "status": overall,
        "incident_class": incident_class,
        "failed_reason_classes": {
            "expected_external_block": failed_expected_external,
            "unexpected_failure": failed_unexpected,
        },
        "reason_breakdown": outbox_reason_breakdown or {},
        "metrics": statuses,
        "guidance": guidance,
    }


def load_baseline(path: str) -> dict[str, Any]:
    baseline_path = Path(path)
    raw = baseline_path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("baseline must be a JSON object")
    return payload


def compare_metric(current_value: float | None, baseline_value: float | None) -> dict[str, Any]:
    if current_value is None or baseline_value is None:
        return {"trend": "unknown", "delta": None}
    delta = round(current_value - baseline_value, 3)
    if abs(delta) < 1e-9:
        trend = "stable"
    elif delta < 0:
        trend = "improved"
    else:
        trend = "regressed"
    return {"trend": trend, "delta": delta}


def build_impact(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    current_kpi = current.get("kpi", {}) if isinstance(current.get("kpi"), dict) else {}
    baseline_kpi = baseline.get("kpi", {}) if isinstance(baseline.get("kpi"), dict) else {}

    metrics: dict[str, dict[str, Any]] = {}
    for name in [
        "outbox_backlog",
        "unresolved_cases",
        "unresolved_older_than_60m",
        "first_response_p90_seconds",
    ]:
        current_value = parse_float(current_kpi.get(name, {}).get("value") if isinstance(current_kpi.get(name), dict) else None)
        baseline_value = parse_float(baseline_kpi.get(name, {}).get("value") if isinstance(baseline_kpi.get(name), dict) else None)
        metrics[name] = {
            "current": current_value,
            "baseline": baseline_value,
            **compare_metric(current_value, baseline_value),
        }

    score_map = {"regressed": 1, "stable": 0, "improved": -1, "unknown": 0}
    score = sum(score_map[item.get("trend", "unknown")] for item in metrics.values())
    if score > 0:
        summary = "regressed"
    elif score < 0:
        summary = "improved"
    else:
        summary = "mixed_or_stable"

    return {
        "summary": summary,
        "metrics": metrics,
    }


def main() -> int:
    args = parse_args()
    captured_at = dt.datetime.now(dt.timezone.utc).isoformat()

    snapshot: dict[str, Any] = {
        "captured_at": captured_at,
        "client_slug": args.client_slug,
        "status": "ok",
    }

    db_user = resolve_db_user(args, timeout=args.timeout)

    try:
        raw_kpis = load_business_kpis(
            client_slug=args.client_slug,
            timeout=args.timeout,
            postgres_container=args.postgres_container,
            postgres_db=args.postgres_db,
            db_user=db_user,
        )
    except Exception as exc:
        snapshot["status"] = "error"
        snapshot["error"] = f"{type(exc).__name__}: {exc}"
        output = json.dumps(snapshot, ensure_ascii=False, indent=2 if args.pretty else None)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(output)
        return 1

    kpi = {
        "outbox_backlog": {
            "value": parse_int(raw_kpis.get("outbox_backlog")),
            "warning_threshold": args.outbox_warning,
            "critical_threshold": args.outbox_critical,
        },
        "unresolved_cases": {
            "value": parse_int(raw_kpis.get("unresolved_cases")),
            "warning_threshold": args.unresolved_warning,
            "critical_threshold": args.unresolved_critical,
        },
        "unresolved_older_than_60m": {
            "value": parse_int(raw_kpis.get("unresolved_older_than_60m")),
            "warning_threshold": args.stale_warning,
            "critical_threshold": args.stale_critical,
        },
        "first_response_p90_seconds": {
            "value": parse_float(raw_kpis.get("first_response_p90_seconds")),
            "warning_threshold": args.p90_warning,
            "critical_threshold": args.p90_critical,
        },
    }

    outbox_reason_breakdown = collect_outbox_reason_breakdown(
        client_id=str(raw_kpis.get("client_id") or ""),
        timeout=args.timeout,
        postgres_container=args.postgres_container,
        postgres_db=args.postgres_db,
        db_user=db_user,
    )

    guard = evaluate_guard(
        {
            "outbox_backlog": kpi["outbox_backlog"]["value"],
            "unresolved_cases": kpi["unresolved_cases"]["value"],
            "unresolved_older_than_60m": kpi["unresolved_older_than_60m"]["value"],
            "first_response_p90_seconds": kpi["first_response_p90_seconds"]["value"],
        },
        args,
        outbox_reason_breakdown=outbox_reason_breakdown,
    )

    snapshot.update(
        {
            "status": "ok",
            "client_id": raw_kpis.get("client_id"),
            "metric_date": raw_kpis.get("metric_date"),
            "kpi": {
                **kpi,
                "guard": guard,
            },
            "settings_profile": {
                "reminder_1_minutes": parse_int(raw_kpis.get("reminder_1_minutes")),
                "reminder_2_minutes": parse_int(raw_kpis.get("reminder_2_minutes")),
                "escalation_timeout_minutes": parse_int(raw_kpis.get("escalation_timeout_minutes")),
            },
            "loc": collect_loc_metrics(),
        }
    )

    if args.baseline:
        try:
            baseline_payload = load_baseline(args.baseline)
            snapshot["impact"] = {
                "baseline_path": args.baseline,
                **build_impact(snapshot, baseline_payload),
            }
        except Exception as exc:
            snapshot["impact"] = {
                "baseline_path": args.baseline,
                "error": f"{type(exc).__name__}: {exc}",
            }

    output = json.dumps(snapshot, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)

    if args.fail_on_breach:
        guard_status = guard.get("status", "ok")
        fail_rank = SEVERITY_ORDER[args.fail_level]
        guard_rank = SEVERITY_ORDER.get(guard_status, 0)
        if guard_rank >= fail_rank:
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
