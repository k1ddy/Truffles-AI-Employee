#!/usr/bin/env python3
"""Generate deterministic Platform Admin remediation assist artifacts from KPI snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Platform Admin remediation assist")
    parser.add_argument("--kpi-snapshot", required=True, help="Path to control-loop KPI snapshot JSON")
    parser.add_argument(
        "--output-dir",
        help="Output directory for remediation artifacts (default: KPI snapshot parent)",
    )
    parser.add_argument("--run-id", help="Optional deterministic run id")
    parser.add_argument("--strict", action="store_true", help="Exit 2 when decision.rollout=blocked")
    parser.add_argument("--print-json", action="store_true", help="Print remediation plan JSON to stdout")
    return parser.parse_args()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _ops_job_payload(mode: str, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_type": "outbox_process",
        "mode": mode,
        "params": params,
    }


def _curl_template(payload: dict[str, Any]) -> str:
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        "curl -sS -X POST \"${CONSOLE_API_BASE_URL}/console/v1/ops/jobs/run\" "
        "-H \"Authorization: Bearer ${CONSOLE_BEARER_TOKEN}\" "
        "-H \"Content-Type: application/json\" "
        f"--data '{compact}'"
    )


def build_remediation_plan(snapshot: dict[str, Any], *, run_id: str, source_snapshot: str) -> dict[str, Any]:
    runtime = _as_dict(snapshot.get("runtime"))
    guards = _as_dict(runtime.get("guards"))
    outbox_guard = _as_dict(guards.get("outbox"))

    guard_status = str(outbox_guard.get("status") or "unknown")
    incident_class = str(outbox_guard.get("incident_class") or "none")
    guard_guidance = [str(item) for item in _as_list(outbox_guard.get("guidance")) if str(item).strip()]

    reason_breakdown = _as_dict(outbox_guard.get("reason_breakdown"))
    reason_rows = _as_list(reason_breakdown.get("rows"))
    top_reasons = []
    for item in reason_rows[:5]:
        row = _as_dict(item)
        top_reasons.append(
            {
                "status": row.get("status"),
                "class": row.get("class"),
                "reason": row.get("reason"),
                "count": row.get("count"),
            }
        )

    dry_run_params = {
        "include_without_conversation": True,
        "archive_pending_older_than_hours": 24,
        "archive_pending_limit": 200,
        "archive_pending_without_conversation_only": True,
    }
    execute_params = {
        "include_without_conversation": True,
        "archive_pending_older_than_hours": 24,
        "archive_pending_limit": 200,
        "archive_pending_without_conversation_only": True,
    }

    actions: list[dict[str, Any]] = [
        {
            "id": "capture_integrity_gate",
            "priority": "p0",
            "title": "Проверить целостность среды перед remediation",
            "kind": "gate",
            "command": (
                "python3 ops/diagnose.py integrity-gate --client-slug demo_salon "
                "--fail-on-critical --output /tmp/platform_admin_integrity_gate.json"
            ),
            "why": "Fail-closed preflight before any operational action.",
        }
    ]

    ops_jobs: list[dict[str, Any]] = []
    rollout = "proceed"
    summary = "Control-loop green; no remediation required beyond routine observation."

    if guard_status in {"critical", "warning"} and incident_class == "external_block_only":
        rollout = "caution"
        summary = "External provider/billing block detected; runtime remediation is not primary action."
        actions.extend(
            [
                {
                    "id": "escalate_billing_provider",
                    "priority": "p0",
                    "title": "Эскалировать billing/provider ограничение",
                    "kind": "business_escalation",
                    "command": "Открыть provider billing ticket и зафиксировать incident owner + ETA.",
                    "why": "Reason class indicates external block rather than runtime defect.",
                },
                {
                    "id": "rerun_snapshot_after_unblock",
                    "priority": "p1",
                    "title": "Повторить KPI snapshot после внешнего unblock",
                    "kind": "verification",
                    "command": (
                        "python3 ops/console_platform_admin_kpi_snapshot.py --pretty "
                        "--output /tmp/platform_admin_kpi_post_unblock.json"
                    ),
                    "why": "Verify that failed/pending trends normalize after provider fix.",
                },
            ]
        )
    elif guard_status in {"critical", "warning"}:
        rollout = "blocked" if guard_status == "critical" else "caution"
        summary = "Runtime remediation required for outbox incident before rollout decisions."
        dry_run_payload = _ops_job_payload("dry_run", dry_run_params)
        execute_payload = _ops_job_payload("execute", execute_params)
        ops_jobs.extend(
            [
                {
                    "id": "outbox_process_dry_run",
                    "title": "Outbox remediation dry-run",
                    "payload": dry_run_payload,
                    "curl_template": _curl_template(dry_run_payload),
                },
                {
                    "id": "outbox_process_execute",
                    "title": "Outbox remediation execute (small batch)",
                    "payload": execute_payload,
                    "curl_template": _curl_template(execute_payload),
                },
            ]
        )
        actions.extend(
            [
                {
                    "id": "run_outbox_dry_run_first",
                    "priority": "p0",
                    "title": "Сначала dry-run outbox_process",
                    "kind": "ops_job",
                    "command": _curl_template(dry_run_payload),
                    "why": "Dry-run confirms candidate impact before execute.",
                },
                {
                    "id": "run_outbox_execute_small_batch",
                    "priority": "p0",
                    "title": "Execute outbox_process ограниченным батчем",
                    "kind": "ops_job",
                    "command": _curl_template(execute_payload),
                    "why": "Controlled execution limits blast radius.",
                },
                {
                    "id": "post_remediation_kpi_recheck",
                    "priority": "p0",
                    "title": "Перепроверить KPI и guard после remediation",
                    "kind": "verification",
                    "command": (
                        "python3 ops/console_platform_admin_kpi_snapshot.py --fail-on-breach --fail-level critical "
                        "--pretty --output /tmp/platform_admin_kpi_post_remediation.json"
                    ),
                    "why": "Remediation is accepted only after guard returns below fail level.",
                },
            ]
        )
    elif guard_status == "unknown":
        rollout = "caution"
        summary = "Guard status unknown; validate telemetry/health payload before operational decisions."
        actions.append(
            {
                "id": "repair_kpi_visibility",
                "priority": "p1",
                "title": "Восстановить наблюдаемость KPI",
                "kind": "diagnostics",
                "command": (
                    "python3 ops/console_platform_admin_kpi_snapshot.py --pretty "
                    "--output /tmp/platform_admin_kpi_visibility_check.json"
                ),
                "why": "Unknown guard means decision quality is insufficient for safe rollout.",
            }
        )

    decision = {
        "rollout": rollout,
        "requires_incident_tp": rollout in {"blocked", "caution"},
        "summary": summary,
    }

    return {
        "run_id": run_id,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source_snapshot": source_snapshot,
        "guard": {
            "status": guard_status,
            "incident_class": incident_class,
            "guidance": guard_guidance,
            "top_reasons": top_reasons,
        },
        "decision": decision,
        "actions": actions,
        "ops_jobs": ops_jobs,
        "notes": [
            "No new UI tabs/routes are introduced; remediation uses existing Ops Jobs contract.",
            "All execute actions remain operator-confirmed; no autonomous destructive path.",
        ],
    }


def build_brief(plan: dict[str, Any]) -> str:
    guard = _as_dict(plan.get("guard"))
    decision = _as_dict(plan.get("decision"))
    lines = [
        "# Platform Admin Remediation Brief",
        "",
        f"- run_id: {plan.get('run_id')}",
        f"- generated_at: {plan.get('generated_at')}",
        f"- guard_status: {guard.get('status')}",
        f"- incident_class: {guard.get('incident_class')}",
        f"- rollout_decision: {decision.get('rollout')}",
        f"- summary: {decision.get('summary')}",
        "",
        "## Что делать сейчас",
    ]

    for action in _as_list(plan.get("actions")):
        item = _as_dict(action)
        lines.append(f"- [{item.get('priority', 'p?')}] {item.get('title')}: {item.get('why')}")
        lines.append(f"  command: `{item.get('command')}`")

    top_reasons = _as_list(guard.get("top_reasons"))
    if top_reasons:
        lines.extend(["", "## Top причины outbox"]) 
        for row in top_reasons:
            item = _as_dict(row)
            lines.append(
                f"- status={item.get('status')} class={item.get('class')} count={item.get('count')}: {item.get('reason')}"
            )

    return "\n".join(lines) + "\n"


def write_commands(plan: dict[str, Any], destination: Path) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Fill env vars before running:",
        "#   export CONSOLE_API_BASE_URL=https://api.truffles.kz",
        "#   export CONSOLE_BEARER_TOKEN=<token>",
        "",
    ]

    for job in _as_list(plan.get("ops_jobs")):
        item = _as_dict(job)
        lines.append(f"# {item.get('title')}")
        lines.append(str(item.get("curl_template") or "echo 'missing curl template'") + "\n")

    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    destination.chmod(0o755)


def _load_snapshot(snapshot_path: Path) -> dict[str, Any]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("kpi snapshot must be a JSON object")
    return payload


def main() -> int:
    args = parse_args()
    snapshot_path = Path(args.kpi_snapshot)
    if not snapshot_path.exists():
        raise FileNotFoundError(f"snapshot not found: {snapshot_path}")

    snapshot = _load_snapshot(snapshot_path)
    run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    output_dir = Path(args.output_dir) if args.output_dir else snapshot_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    plan = build_remediation_plan(
        snapshot,
        run_id=run_id,
        source_snapshot=str(snapshot_path),
    )

    plan_path = output_dir / "remediation_plan.json"
    brief_path = output_dir / "remediation_brief.md"
    commands_path = output_dir / "remediation_commands.sh"

    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief_path.write_text(build_brief(plan), encoding="utf-8")
    write_commands(plan, commands_path)

    summary = {
        "run_id": run_id,
        "plan": str(plan_path),
        "brief": str(brief_path),
        "commands": str(commands_path),
        "rollout": _as_dict(plan.get("decision")).get("rollout"),
    }

    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"run_id={summary['run_id']} rollout={summary['rollout']}")
        print(f"plan={summary['plan']}")
        print(f"brief={summary['brief']}")
        print(f"commands={summary['commands']}")

    if args.strict and summary["rollout"] == "blocked":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
