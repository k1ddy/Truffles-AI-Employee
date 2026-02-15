# Platform Admin Baseline v2 (2026-02-15)

Status
- `FACT` (with runtime + code evidence)
- Window: 2026-02-15 07:24Z to 07:34Z
- Branch/worktree: `feat/2026-02-15-platform-admin-wave12345-a1` / `/home/zhan/worktrees/2026-02-15-platform-admin-wave12345-a1`

## 1) Runtime fact snapshot

Commands

```bash
curl -sS https://console.truffles.kz/api/health/full
curl -sS https://api.truffles.kz/admin/version
```

Observed at `2026-02-15T07:33:08Z` to `2026-02-15T07:33:09Z`:
- `health/full`: `status=unhealthy`, api version `4373d6a6`, outbox `pending=1640`, `failed=676`.
- `admin/version`: `version=main`, `git_commit=4373d6a607ecc6480d2f3ab5c416bd4831e8e3dd`, `build_time=2026-02-15T07:08:44Z`.

Interpretation
- Platform Admin sees real degradation signal and queue pressure now.
- Priority remains P0 for outbox stabilization and operational recovery loop.

## 2) Complexity / UX friction baseline

### LOC heatmap

```text
12066 truffles-api/app/routers/console.py
 4945 console-web/src/components/ProvisioningWizard.tsx
 3706 console-web/src/app/tenants/page.tsx
 1791 console-web/src/app/integrations/page.tsx
 1404 console-web/src/app/company-workspace/page.tsx
 1146 console-web/e2e/smoke.spec.ts
  444 console-web/e2e/platform-admin.spec.ts
```

### Error-surface signal (`toast.error`)

```text
ProvisioningWizard.tsx: 1
tenants/page.tsx: 37
company-workspace/page.tsx: 17
```

Interpretation
- UI error handling is still concentrated in Platform Admin-heavy pages (`tenants`, `company-workspace`).
- Router/component hot spots stay large; decomposition remains a P1 maintainability objective.

## 3) This wave implementation result

### QA complexity reduction

Change
- Extracted Platform Admin critical smoke scenarios from `console-web/e2e/smoke.spec.ts` into dedicated `console-web/e2e/platform-admin.spec.ts`.

Measured effect
- `smoke.spec.ts`: `1451 -> 1146` lines (minus 305 lines, `-21.02%`).
- New dedicated suite: `platform-admin.spec.ts` (`444` lines).
- Platform Admin suite now isolated for faster triage and lane-level ownership.

## 4) KPI anti-drift tooling

Added
- `ops/console_platform_admin_kpi_snapshot.py`
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`

Snapshot artifact
- `/tmp/platform_admin_kpi_20260215_0734.json`

Verification command

```bash
python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_20260215_0734.json
```

## 5) 30-day prioritized waves (execution order)

1. P0: Outbox recovery loop (thresholds + remediation ownership + weekly evidence).
2. P0/P1: Keep Platform Admin regressions isolated and tracked separately from generic smoke.
3. P1: Reduce toast-only error handling in `tenants` and `company-workspace` with contextual recovery hints.
4. P1: Start decomposition of `console.py` and `ProvisioningWizard.tsx` behind contract tests.
