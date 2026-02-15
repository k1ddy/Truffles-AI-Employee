#!/usr/bin/env python3
"""Run owner/admin control-loop snapshots (T+0/T+24) with brief output."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_SCRIPT = REPO_ROOT / "ops" / "console_owner_admin_kpi_snapshot.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Owner/Admin control-loop orchestrator")
    parser.add_argument("--mode", choices=["t0", "t24"], required=True, help="Control-loop phase")
    parser.add_argument("--client-slug", default="demo_salon", help="Client slug")
    parser.add_argument(
        "--output-root",
        default="/tmp/owner_admin_control_loop",
        help="Directory where run artifacts are stored",
    )
    parser.add_argument("--run-id", help="Run id (defaults to UTC timestamp)")
    parser.add_argument(
        "--baseline",
        help="Path to T+0 baseline snapshot (required for --mode t24 unless auto-resolved)",
    )
    parser.add_argument(
        "--fail-level",
        choices=["warning", "critical"],
        default="critical",
        help="Fail threshold for gate snapshot",
    )
    parser.add_argument(
        "--skip-gate",
        action="store_true",
        help="Skip fail-on-breach gate run",
    )
    parser.add_argument("--print-json", action="store_true", help="Print summary as JSON")
    return parser.parse_args()


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return payload


def latest_t0_snapshot(output_root: Path, client_slug: str) -> Path | None:
    candidates = sorted(output_root.glob(f"*/{client_slug}_t0.json"))
    if not candidates:
        return None
    return candidates[-1]


def run_snapshot(
    *,
    client_slug: str,
    output_path: Path,
    baseline: Path | None = None,
    fail_on_breach: bool = False,
    fail_level: str = "critical",
) -> tuple[int, str]:
    command = [
        sys.executable,
        str(SNAPSHOT_SCRIPT),
        "--client-slug",
        client_slug,
        "--output",
        str(output_path),
    ]
    if baseline is not None:
        command.extend(["--baseline", str(baseline)])
    if fail_on_breach:
        command.extend(["--fail-on-breach", "--fail-level", fail_level])

    completed = run_command(command)
    output_text = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return completed.returncode, output_text.strip()


def build_brief(snapshot: dict[str, Any], mode: str) -> str:
    guard = snapshot.get("kpi", {}).get("guard", {}) if isinstance(snapshot.get("kpi"), dict) else {}
    guard_status = guard.get("status", "unknown")
    kpi = snapshot.get("kpi", {}) if isinstance(snapshot.get("kpi"), dict) else {}

    lines = [
        f"# Owner/Admin Control Loop Brief ({mode.upper()})",
        "",
        f"- captured_at: {snapshot.get('captured_at', 'unknown')}",
        f"- client_slug: {snapshot.get('client_slug', 'unknown')}",
        f"- guard_status: {guard_status}",
        f"- outbox_backlog: {kpi.get('outbox_backlog', {}).get('value') if isinstance(kpi.get('outbox_backlog'), dict) else 'n/a'}",
        f"- unresolved_cases: {kpi.get('unresolved_cases', {}).get('value') if isinstance(kpi.get('unresolved_cases'), dict) else 'n/a'}",
        f"- unresolved_older_than_60m: {kpi.get('unresolved_older_than_60m', {}).get('value') if isinstance(kpi.get('unresolved_older_than_60m'), dict) else 'n/a'}",
        f"- first_response_p90_seconds: {kpi.get('first_response_p90_seconds', {}).get('value') if isinstance(kpi.get('first_response_p90_seconds'), dict) else 'n/a'}",
    ]

    impact = snapshot.get("impact") if isinstance(snapshot.get("impact"), dict) else None
    if impact:
        lines.extend([
            "",
            "## Impact",
            f"- summary: {impact.get('summary', 'unknown')}",
        ])
        metrics = impact.get("metrics") if isinstance(impact.get("metrics"), dict) else {}
        for key in ["outbox_backlog", "unresolved_cases", "unresolved_older_than_60m", "first_response_p90_seconds"]:
            metric = metrics.get(key) if isinstance(metrics.get(key), dict) else {}
            lines.append(
                f"- {key}: trend={metric.get('trend', 'unknown')} delta={metric.get('delta', 'n/a')}"
            )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    if not SNAPSHOT_SCRIPT.exists():
        print(f"ERROR: snapshot script not found: {SNAPSHOT_SCRIPT}", file=sys.stderr)
        return 1

    now = dt.datetime.now(dt.timezone.utc)
    run_id = args.run_id or now.strftime("%Y%m%d-%H%M%S")
    output_root = Path(args.output_root)
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = run_dir / f"{args.client_slug}_{args.mode}.json"
    gate_path = run_dir / f"{args.client_slug}_{args.mode}_gate.json"
    brief_path = run_dir / f"{args.client_slug}_{args.mode}_brief.md"
    log_path = run_dir / f"{args.client_slug}_{args.mode}.log"

    baseline_path: Path | None = None
    if args.mode == "t24":
        if args.baseline:
            baseline_path = Path(args.baseline)
        else:
            baseline_path = latest_t0_snapshot(output_root, args.client_slug)
        if baseline_path is None or not baseline_path.exists():
            print("ERROR: baseline is required for t24 (use --baseline or ensure previous t0 exists)", file=sys.stderr)
            return 1

    snapshot_code, snapshot_output = run_snapshot(
        client_slug=args.client_slug,
        output_path=snapshot_path,
        baseline=baseline_path,
        fail_on_breach=False,
    )
    log_lines = [
        f"snapshot_exit={snapshot_code}",
        snapshot_output,
    ]
    if snapshot_code != 0:
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        print(f"ERROR: snapshot failed, see {log_path}", file=sys.stderr)
        return snapshot_code

    gate_code = None
    gate_output = ""
    if not args.skip_gate:
        gate_code, gate_output = run_snapshot(
            client_slug=args.client_slug,
            output_path=gate_path,
            baseline=baseline_path,
            fail_on_breach=True,
            fail_level=args.fail_level,
        )
        log_lines.extend([f"gate_exit={gate_code}", gate_output])

    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    snapshot = load_json(snapshot_path)
    brief = build_brief(snapshot, args.mode)
    brief_path.write_text(brief, encoding="utf-8")

    summary: dict[str, Any] = {
        "mode": args.mode,
        "run_id": run_id,
        "client_slug": args.client_slug,
        "run_dir": str(run_dir),
        "snapshot": str(snapshot_path),
        "brief": str(brief_path),
        "log": str(log_path),
        "guard_status": (
            snapshot.get("kpi", {}).get("guard", {}).get("status")
            if isinstance(snapshot.get("kpi"), dict)
            else None
        ),
        "baseline": str(baseline_path) if baseline_path else None,
        "gate": {
            "path": str(gate_path) if not args.skip_gate else None,
            "exit_code": gate_code,
            "skipped": args.skip_gate,
        },
    }

    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"mode={summary['mode']} run_id={summary['run_id']} guard={summary['guard_status']}")
        print(f"snapshot={summary['snapshot']}")
        print(f"brief={summary['brief']}")
        print(f"log={summary['log']}")
        if summary["baseline"]:
            print(f"baseline={summary['baseline']}")
        if not args.skip_gate:
            print(f"gate_exit={gate_code} gate_path={gate_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
