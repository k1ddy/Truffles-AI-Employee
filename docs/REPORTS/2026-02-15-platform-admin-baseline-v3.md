# Platform Admin Baseline v3 (2026-02-15, wave 1+2 follow-up)

Status
- `FACT` (runtime + code evidence)
- Window: `2026-02-15T08:06:10Z`
- Branch/worktree: `feat/2026-02-15-platform-admin-wave12345-a1` / `/home/zhan/worktrees/2026-02-15-platform-admin-wave12345-a1`

## 1) Runtime fact snapshot

Commands

```bash
curl -sS https://console.truffles.kz/api/health/full
curl -sS https://api.truffles.kz/admin/version
python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_20260215_1250_wave12.json
python3 ops/console_platform_admin_kpi_snapshot.py --fail-on-breach --fail-level critical --pretty --output /tmp/platform_admin_kpi_20260215_1250_gate.json
```

Observed
- `health/full` at `2026-02-15T08:06:10Z`: `status=unhealthy`, `outbox.pending=1653`, `outbox.failed=679`.
- `admin/version`: `git_commit=9c7e3e5e36098fd2661b7846a90e7c3a1c61e06c`, `build_time=2026-02-15T08:00:00Z`.
- Outbox guard (`ops/console_platform_admin_kpi_snapshot.py`): `status=critical`.
- Gate command exit code: `2` (`--fail-on-breach --fail-level critical`).

Interpretation
- Platform Admin runtime remains P0 degraded.
- Guardrail is now machine-verifiable and can fail-fast in CI/manual checks.

## 2) Wave 1 result: outbox recovery guard

Implemented
- Threshold-aware outbox guard in `ops/console_platform_admin_kpi_snapshot.py`:
  - warning/critical thresholds for pending+failed
  - derived severity: `ok|unknown|warning|critical`
  - `--fail-on-breach` + `--fail-level warning|critical`

Runbook update
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md` now includes threshold commands and exit code semantics (`0`/`2`).

## 3) Wave 2 result: UX error-recovery clarity

Implemented
- Added shared validation reporter in Platform Admin pages:
  - `reportValidationError(...)` = `toast` + `inline error summary`
  - applied to validation/operator-input branches in:
    - `console-web/src/app/tenants/page.tsx`
    - `console-web/src/app/company-workspace/page.tsx`
- Added explicit recovery hints in inline error summary blocks for both pages.

Measured change
- `toast.error` occurrences (code-surface metric):
  - `tenants/page.tsx`: `37 -> 1` (helper only)
  - `company-workspace/page.tsx`: `17 -> 1` (helper only)

Note
- User-visible toasts remain, but they are no longer toast-only for validation paths; errors persist in inline context panel.

## 4) Residual open risks

1. Runtime outbox backlog still critical; guard added, backlog not yet reduced.
2. API/component complexity hotspots remain (`console.py`, `ProvisioningWizard.tsx`, `tenants/page.tsx`).
3. Next step should target actual backlog reduction/remediation evidence after guard firing.

## 5) Evidence artifacts

- `/tmp/platform_admin_kpi_20260215_1250_wave12.json`
- `/tmp/platform_admin_kpi_20260215_1250_gate.json`
- `/tmp/platform_admin_kpi_20260215_1250_gate_stdout.json`
