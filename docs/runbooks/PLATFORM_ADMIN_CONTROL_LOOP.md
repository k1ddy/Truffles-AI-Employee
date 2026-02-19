# Platform Admin Control Loop

Goal
- Run a repeatable weekly control loop for Platform Admin that is fact-first, evidence-backed, and anti-drift.

Prerequisites
- Work from repo root (`/home/zhan/truffles-main` or active worktree).
- Network access to Console/API endpoints.
- Python 3.11+.

## 0) Integrity preflight (Wave 0.1 gate)

Run:

```bash
python3 ops/diagnose.py integrity-gate \
  --client-slug demo_salon \
  --pretty \
  --output /tmp/integrity_gate_$(date +%Y%m%d_%H%M%S).json
```

Hard gate mode:

```bash
python3 ops/diagnose.py integrity-gate \
  --client-slug demo_salon \
  --fail-on-critical \
  --output /tmp/integrity_gate_gate.json
```

Interpretation
- `summary.status=PASS|WARN|FAIL`, `summary.critical_failures[]`.
- При `FAIL` для critical checks rollout/remediation wave блокируется до отдельного remediation TP или явного waiver.

## 1) Capture KPI snapshot

Run:

```bash
python3 ops/console_platform_admin_kpi_snapshot.py \
  --pretty \
  --outbox-pending-warning 500 \
  --outbox-pending-critical 1000 \
  --outbox-failed-warning 100 \
  --outbox-failed-critical 300 \
  --output /tmp/platform_admin_kpi_$(date +%Y%m%d_%H%M%S).json
```

Expected output
- `runtime.console_health` and `runtime.admin_version` payloads.
- Derived outbox hints (`outbox_pending_hint`, `outbox_failed_24h_hint`, `outbox_failed_total_hint`).
- Outbox guard severity (`runtime.guards.outbox.status`: `ok|warning|critical|unknown`).
- Outbox reason classes in guard:
  - `runtime.guards.outbox.incident_class` (`runtime_incident|external_block_only|unknown_failure_mix|none`)
  - `runtime.guards.outbox.failed_reason_classes.expected_external_block`
  - `runtime.guards.outbox.failed_reason_classes.unexpected_failure`
  - `runtime.guards.outbox.reason_breakdown` (top `last_error` rows + class totals).
- LOC heatmap for Platform Admin-critical files.
- `toast.error` surface counts.
- e2e concentration metrics (`smoke_lines`, `platform_admin_lines`, share).

Fail-fast mode (for CI/manual gate):

```bash
python3 ops/console_platform_admin_kpi_snapshot.py \
  --fail-on-breach \
  --fail-level critical \
  --pretty \
  --output /tmp/platform_admin_kpi_gate.json
```

Exit codes
- `0`: snapshot generated, guard below fail level.
- `2`: guard reached configured fail level (`warning` or `critical`).

## 2) Update audit artifacts

1. Refresh `docs/REPORTS/<date>-platform-admin-baseline-vN.md`.
2. Update `docs/CONSOLE_AUDIT/UX_BACKLOG.md` with P0/P1/P2 and concrete evidence.
3. If canon alignment changed, update `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`.

## 3) Apply one improvement wave

1. Choose one high-impact bottleneck (reliability, UX friction, or maintainability).
2. Deliver one contained change set with tests and evidence.
3. Keep API contract and RBAC invariants unchanged unless explicitly scoped.

## 4) Validation gates

Run minimally:

```bash
npm --prefix console-web run lint
npm --prefix console-web exec -- playwright test --list
python3 ops/console_platform_admin_kpi_snapshot.py --pretty
scripts/session_check.sh
```

Optional (when available):

```bash
npm --prefix console-web run build
```

## Outbox remediation params (Wave 0.2)

`/console/v1/ops/jobs/run` with `job_type=outbox_process` supports:

- `include_without_conversation` (`true` by default): allows processing `PENDING` rows where `conversation_id` is null.
- `archive_pending_older_than_hours` (`0` by default): optional archival cut-off for legacy pending tail.
- `archive_pending_limit` (`limit` by default): max rows archived in one execute call.
- `archive_pending_without_conversation_only` (`true` by default): keep archival scoped to rows without conversation context unless explicitly changed.

Operational guard
- Run outbox in one mode only: either `truffles-outbox` worker or legacy cron `/admin/outbox/process`, never both at once.
- If worker is enabled, disable cron-triggered `/admin/outbox/process` to prevent duplicate processing and API starvation.

Recommended sequence:

1. `dry_run` with archive preview and pending split.
2. Small `execute` batch with archive enabled.
3. Re-run KPI snapshot and SQL reason breakdown before next batch.

## 5) Evidence package for PR/session

Include:
- `git status -sb`
- `git diff --stat`
- KPI snapshot path in `/tmp` or committed report artifact
- Validation command outputs (key lines)
- Updated docs paths

Stop-the-line
- If runtime health is `unhealthy` with growing outbox backlog, mark as P0 and do not present as stable.
- If outbox guard is `critical` and `incident_class=runtime_incident`, platform rollout remains blocked.
- If outbox guard is `critical` but `incident_class=external_block_only`, classify as external billing/provider block (operational limit), not runtime defect.
- If lint/test/session gates fail, keep session open and fix before merge.
