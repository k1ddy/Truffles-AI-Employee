# Platform Admin Control Loop

Goal
- Run a repeatable weekly control loop for Platform Admin that is fact-first, evidence-backed, and anti-drift.

Prerequisites
- Work from repo root (`/home/zhan/truffles-main` or active worktree).
- Network access to Console/API endpoints.
- Python 3.11+.

## 1) Capture KPI snapshot

Run:

```bash
python3 ops/console_platform_admin_kpi_snapshot.py \
  --pretty \
  --output /tmp/platform_admin_kpi_$(date +%Y%m%d_%H%M%S).json
```

Expected output
- `runtime.console_health` and `runtime.admin_version` payloads.
- Derived outbox hints (`outbox_pending_hint`, `outbox_failed_hint`).
- LOC heatmap for Platform Admin-critical files.
- `toast.error` surface counts.
- e2e concentration metrics (`smoke_lines`, `platform_admin_lines`, share).

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
npm --prefix console-web exec playwright test --list
python3 ops/console_platform_admin_kpi_snapshot.py --pretty
scripts/session_check.sh
```

Optional (when available):

```bash
npm --prefix console-web run build
```

## 5) Evidence package for PR/session

Include:
- `git status -sb`
- `git diff --stat`
- KPI snapshot path in `/tmp` or committed report artifact
- Validation command outputs (key lines)
- Updated docs paths

Stop-the-line
- If runtime health is `unhealthy` with growing outbox backlog, mark as P0 and do not present as stable.
- If lint/test/session gates fail, keep session open and fix before merge.
