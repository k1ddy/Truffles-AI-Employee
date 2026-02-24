# REPORT-2026-02-20-tenants-v3-redesign-plan

## Scope
- Deep-gap анализ `platform_admin` для `Tenants`.
- Цель: подтвердить системные причины неудобства управления компаниями (onboarding -> operate -> change -> decommission) и подготовить полный план редизайна.

## Wave 0 baseline run (2026-02-20, UTC)
1. Worktree/session initialized for redesign lane.
- Worktree: `/home/zhan/worktrees/2026-02-20-tenants-v3-redesign-a250`
- Branch: `feat/2026-02-20-tenants-v3-redesign-a250`

2. Baseline dependencies in worktree prepared.
- Команда: `npm --prefix console-web ci`
- Результат: install completed (`added 511 packages`).

3. Live Tenants smoke (platform_admin lane) validated.
- Команда: `npx playwright test e2e/platform-admin.spec.ts --grep "Platform Admin Tenants"`
- Результат: `8 passed (1.1m)` after retry.
- Наблюдение: первый прогон дал network/auth flake (`chrome-error://chromewebdata`, затем timeout в global-setup), повторный запуск зелёный.

4. Tenants a11y lane currently unstable/insufficient.
- Команда: `npx playwright test e2e/tenants-a11y.spec.ts`
- Результат: tests skipped (`2 skipped`, setup may pass) из-за условия availability/gate в тесте.
- Вывод: для baseline не хватает жёсткого fail-closed a11y lane (сейчас skip допускает ложный green).

5. Runtime health snapshot unstable/unhealthy.
- Команда: `curl -sS https://console.truffles.kz/api/health/full` (3 последовательных прогона).
- Результат: `status=unhealthy`, API `HTTP 502`, build hash `2934de8a`.

6. Platform KPI snapshot captured twice and показал дрейф runtime.
- Команда:
  - `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_tenants_v3_wave0_20260220.json`
  - `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_tenants_v3_wave0_20260220_r2.json`
- Результат:
  - Run-1 получил `console_health=healthy` (`version=098ee34b`) и outbox hints.
  - Run-2 получил `console_health=502` + `admin/version=2934de8a`.
- Вывод: live runtime нестабилен во времени, baseline должен хранить оба слепка.

## Verified facts
1. Текущая страница `Tenants` остаётся высокосвязанным монолитом.
- `console-web/src/app/tenants/page.tsx` содержит ~3961 LOC.
- Внутри страницы смешаны несколько независимых доменов (quick-create, KPI/reporting, fleet-risk, lifecycle modal, branch-change pipeline, wizard).

2. Контекст выступает скрытым фильтром списков.
- `clients` query зависит от `selectedCompanyId`.
- `branches` query зависит от `selectedClientId`.
- Это приводит к восприятию "данные пропали" при неочевидном контексте.

3. Weekly snapshots не имеют строгого typed-контракта и реализованы через audit events + local fallback.
- OpenAPI хранит `snapshot` как `object`.
- Backend фильтрует week_key постфактум на ограниченном батче.
- UI при серверной ошибке пишет успешный локальный save.

4. A11y/UX debt системный, не только точечный.
- В quick-create филиала есть placeholder-only inputs без явных label.
- Исторический live-отчёт фиксирует `critical/serious` axe-проблемы.

5. E2E-покрытие Tenants содержит мягкие early-return ветки.
- Часть тестов успешно завершается при отсутствии ключевых элементов/данных.
- Это снижает ценность регрессионного контроля.

## Root cause summary
1. Нет чёткой границы ответственности между `Tenants`, `Integrations`, `Company Workspace`.
2. Global context и page-level filters не разведены в UX-модели.
3. Память операционного цикла (`weekly snapshots`) построена как "audit + cache", а не как отдельный контракт данных.
4. Большой монолит UI/API делает целевую эволюцию медленной и рискованной.

## Wave 1-2 initial implementation (worktree only)
1. Workspace contract shifted to portfolio-first.
- `workspaceMode` default changed from `all` to `portfolio`.
- Removed `Все зоны` mode/button.
- Section rendering now follows single active workspace mode.

2. Added explicit Context Lens in Tenants header.
- New panel `tenants-context-lens` shows active company/client/branch filters.
- Added controls:
  - `tenants-context-clear-branch`
  - `tenants-context-clear-client`
  - `tenants-context-clear-all`
- Goal: make context-driven filtering explicit and reversible on-page.

3. Error summary now strictly mode-scoped.
- Removed legacy `all` scope branch; active scope follows current workspace mode.

4. Updated Tenants smoke contract for new IA.
- `console-web/e2e/platform-admin.spec.ts` no longer expects `tenants-mode-all`.
- Added assertion for `tenants-context-lens` visibility in workspace mode flow.

## Validation after implementation
1. Local static checks: pass.
- `npm --prefix console-web run lint -- --file src/app/tenants/page.tsx --file e2e/platform-admin.spec.ts`
- `npx tsc --noEmit`
- `npm --prefix console-web run build`

2. Live smoke against deployed `console.truffles.kz`: expected mismatch.
- Command: `... playwright test e2e/platform-admin.spec.ts --grep "Platform Admin Tenants" --retries=1`
- Result: fail on `tenants-context-lens` not found (deployed build does not include local worktree changes yet).

## Output artifact
- Полный план редизайна и реализации оформлен в:
  - `docs/TASK_PACKAGES/TP-2026-02-20-tenants-v3-platform-admin-redesign.md`

## Wave 3 completion: backfill verification (2026-02-22, UTC)
1. Snapshot storage backfill quality check executed against runtime DB `chatbot`.
- DB/container: `truffles_postgres_1` (`psql -U n8n -d chatbot`)
- Raw evidence: `/tmp/tenants_weekly_snapshots_backfill_verify_20260222.txt`

2. Verification thresholds (fail-closed contract).
- `missing_from_table = 0`
- `invalid_regex = 0`
- `snapshot_non_object = 0`
- `table_distinct_client_week = table_rows` (no duplicates per `(client_id, week_key)`)
- `schema_versions` explicitly observable from table/API contract

3. Captured result (current runtime slice).
- `audit_candidates = 0`
- `audit_valid_week_key_rows = 0`
- `audit_distinct_client_week = 0`
- `table_rows = 0`
- `table_distinct_client_week = 0`
- `missing_from_table = 0`
- `extra_in_table = 0`
- `invalid_regex = 0`
- `snapshot_non_object = 0`
- `snapshot_schema_version distribution = empty` (no rows yet)

4. Interpretation.
- Backfill is idempotent and contract-safe for current runtime state (no historical weekly snapshot rows to migrate).
- Runtime quality gates for snapshot storage are satisfied with explicit evidence.

## Wave 4 progress: UI decomposition
1. `Quick Create` block extracted from monolith `tenants/page.tsx` into dedicated component.
- New component: `console-web/src/components/TenantsQuickCreatePanel.tsx`
- Parent integration kept behavior-compatible via handler props and existing API flow.

2. Decomposition impact.
- `tenants/page.tsx` reduced by removal of inline quick-create rendering block.
- UI logic is now split into reusable, testable component boundary.

## Wave 5 progress: copy + a11y hardening
1. Business copy cleanup in top controls and tenants workspace.
- Reduced RU/EN + tech mix in key labels and helper text (`Context/Filters/KPI/Decommission/Snapshots` blocks).
- Context/apply semantics clarified in user language.

2. Quick-create accessibility hardening.
- Added explicit labels for all branch inputs (previously placeholder-only).
- Added stable input IDs and `data-testid` hooks for deterministic UI/e2e assertions.

## Wave 4 continuation + Wave 5 gate status (2026-02-22, UTC)
1. `Operational KPI` section extracted from `tenants/page.tsx` into dedicated component.
- New component: `console-web/src/components/TenantsOperationalKpiPanel.tsx`
- Parent `page.tsx` now wires handlers/derived data via explicit props.
- Monolith size reduced further: `4003 -> 3768` LOC.

2. Additional copy/a11y hardening in top controls.
- Increased foreground contrast for low-contrast labels/help text in:
  - `tenants-page-filters`
  - `tenants-context-lens`
- Keep behavior unchanged; this is presentation-only hardening.

3. A11y fail-closed lane is now enforced and reports current live blocker.
- Command:
  - `A11Y_FAIL_ON_THRESHOLDS=1 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz E2E_USERNAME=admin E2E_PASSWORD=admin E2E_USE_STORAGE_STATE=1 corepack pnpm -C console-web exec playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1 --reporter=line`
- Result:
  - `desktop serious axe violations = 1`
  - `mobile serious axe violations = 1`
  - violation id: `color-contrast`
- Interpretation:
  - This gate currently validates deployed runtime (`console.truffles.kz`), so red status reflects live build until branch deploy.

## Wave 4 continuation: fleet read-model cache + perf snapshot (2026-02-23, UTC)
1. Fleet read-model cache added for heavy tenants aggregations.
- New storage model/table:
  - `truffles-api/app/models/tenants_fleet_cache.py`
  - `truffles-api/migrations/038_add_tenants_fleet_cache.sql`
- Router integration:
  - `list_clients(include_summary)` now uses cache key by scope hash before running `_build_fleet_summary_for_scope`.
  - `list_fleet_attention` now uses cache key by active clients + stale window + include_low before heavy recalculation.
- Fail-open behavior:
  - Missing table / cache errors do not break API path (fallback to existing on-demand computation).

2. Contract tests added for cache-hit/cache-miss behavior.
- `truffles-api/tests/test_console_tenants_list.py`:
  - `test_list_clients_uses_cached_summary_when_available`
  - `test_list_clients_stores_summary_in_cache_after_miss`
  - `test_list_fleet_attention_returns_cached_response`

3. Perf evidence tool added.
- Script: `ops/console_tenants_perf_snapshot.py`
- Captures histogram quantiles for:
  - `console_tenants_endpoint_latency{endpoint=portfolio|company_cockpit}`
  - optional `http_request_latency{method=GET,path=/console/v1/admin/branches}`
- Computes p50/p95/p99 + SLO verdicts and can fail-closed (`--fail-on-breach`).

4. Runtime probe evidence (current environment).
- Command:
  - `python3 ops/console_tenants_perf_snapshot.py --metrics-url https://api.truffles.kz/metrics --pretty --output /tmp/tenants_perf_snapshot_20260223_after_probe.json`
- Result:
  - `portfolio p95 = 10ms` (5 samples, probe traffic)
  - `company_cockpit p95 = 10ms` (5 samples, probe traffic)
  - `status = pass`
- Note:
  - This is probe-level evidence (authless endpoint probes), not full-load baseline for large fleet.

## Wave 5/6 continuation: deep copy cleanup + rollout guardrails (2026-02-23, UTC)
1. Deep lifecycle/editor copy cleaned in operator flow.
- Updated files:
  - `console-web/src/components/TenantsClientLifecycleModal.tsx`
  - `console-web/src/components/TenantsClientsPanel.tsx`
  - `console-web/src/app/tenants/page.tsx`
- Removed technical wording from mainline actions (API/payload/checklist jargon) and replaced with business-operational language.

2. Rollout guardrails formalized for `NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER`.
- `shadow`:
  - flag on for internal operators only; monitor `console_tenants_endpoint_latency`, e2e/a11y deterministic lane.
- `canary`:
  - expand to controlled platform-admin subset; stop-the-line on p95 breach or deterministic lane failure.
- `full`:
  - switch default on after canary stability window.
- rollback:
  - set `NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER=0`; keep backend read-model cache backward-compatible.

3. Validation after continuation changes.
- Backend:
  - `pytest -q truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py` -> `70 passed`
  - `ruff check ...` (console router/model/tests/perf script) -> pass
  - `python3 truffles-api/scripts/generate_openapi.py --check` -> pass
- Frontend:
  - `corepack pnpm -C console-web run lint` -> pass
  - `corepack pnpm -C console-web run build` -> pass
  - `PLAYWRIGHT_BASE_URL=http://localhost:3100 CI=1 E2E_DETERMINISTIC_AUTH=1 ... platform-admin.spec.ts` -> `17 passed`
  - `PLAYWRIGHT_BASE_URL=http://localhost:3100 CI=1 E2E_DETERMINISTIC_AUTH=1 A11Y_FAIL_ON_THRESHOLDS=1 ... tenants-a11y.spec.ts` -> `2 passed`

## Wave 4 async refresh continuation (2026-02-23, UTC)
1. Added async stale-while-refresh for fleet cache hit near expiry.
- `list_clients(include_summary)` and `list_fleet_attention` now schedule background refresh when cached entry is close to TTL end.
- Added inflight dedupe guard to prevent thread storms per cache key (`cache_type:scope_key`).
- Refresh is fail-open and non-blocking for request path.

2. Fleet attention cache key contract hardened.
- Added `limit` into attention cache scope key to avoid cross-limit cache collisions.

3. Shared compute path extracted for attention.
- Added helper that builds fleet attention response from active clients and reused it for:
  - request miss path,
  - background refresh path.

4. Validation.
- `pytest -q truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py` -> `72 passed`
- Added explicit tests:
  - `cache hit -> schedule async refresh` for `clients summary`,
  - `cache hit -> schedule async refresh` for `fleet attention`.

## Wave 4 event-driven invalidation continuation (2026-02-23, UTC)
1. Added write-path invalidation for fleet cache.
- Introduced `_invalidate_tenants_fleet_cache_scope` (best-effort nested transaction guard) to clear `fleet_summary` and `fleet_attention` cache slices without blocking tenant writes.

2. Hooked invalidation into mutation endpoints that change fleet aggregates.
- `update_company`
- `create_client`, `update_client`, `archive_client`, `restore_client`
- `create_branch`, `update_branch`
- `approve/reject/waive branch go-live`
- integrations execute paths: `integration_reconcile` and `provider_ops`

3. Validation.
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py` -> `89 passed`
- `ruff check truffles-api/app/routers/console.py truffles-api/tests/test_console_admin_provisioning.py` -> pass
- `python3 truffles-api/scripts/generate_openapi.py --check` -> pass

## Wave 4 scope-aware invalidation continuation (2026-02-23, UTC)
1. Extended cache schema with scope metadata.
- Added `scope_company_id` and `scope_client_id` to `tenants_fleet_cache` via migration `039`.
- Updated ORM model `TenantsFleetCache` accordingly.

2. Moved invalidation from full wipe to targeted-by-company delete.
- `_invalidate_tenants_fleet_cache_scope` now supports `company_ids` and deletes:
  - global rows (`scope_company_id IS NULL`)
  - rows for affected companies only.
- Summary cache writes now persist `scope_company_id` so company-scoped entries become addressable.

3. Endpoint hooks now pass affected company scope.
- `update_company`, `create/update/archive/restore client`,
- `create/update branch`,
- `branch go-live approve/reject/waive`,
- integrations execute paths (`integration_reconcile`, `provider_ops`).

4. Validation.
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_access_admin_pr2.py` -> `133 passed`
- `ruff check truffles-api/app/routers/console.py truffles-api/tests/test_console_admin_provisioning.py truffles-api/app/models/tenants_fleet_cache.py` -> pass
- `python3 truffles-api/scripts/generate_openapi.py --check` -> pass

## Wave 4 targeted prewarm continuation (2026-02-23, UTC)
1. Added post-commit targeted prewarm for affected company scopes.
- `_invalidate_tenants_fleet_cache_scope` now queues affected `company_ids` in session info (`tenants_fleet_cache_prewarm_company_ids`) after successful invalidation.
- `after_commit` hook consumes queued ids and starts async summary prewarm worker per affected company scope.
- Prewarm worker reuses existing summary refresh pipeline (`_refresh_fleet_summary_cache_worker`) with scope key based on `company_id + active clients hash`.

2. Transaction safety and behavior guarantees.
- Prewarm is launched strictly `after_commit`, so it cannot race on uncommitted tenant mutations.
- Rollback clears pending prewarm queue via `after_rollback`.
- Flow remains fail-open for write path (best-effort; no mutation blocking).

3. Validation.
- `pytest -q truffles-api/tests/test_console_tenants_list.py -k "prewarm or invalidate_tenants_fleet_cache_scope_queues_company_prewarm or on_console_session_after_commit"` -> `3 passed`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_access_admin_pr2.py` -> `136 passed`
- `ruff check truffles-api/app/routers/console.py truffles-api/tests/test_console_tenants_list.py` -> pass

4. CI/infra note.
- PR run `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/22301196048` was cancelled as infra-stuck (`core-eval` pending without progress >10m) per stop-the-line policy; continuation runs on next pushed commit.

## Post-merge canary verification (2026-02-23, UTC)
1. Authenticated perf baseline on deployed API captured (platform_admin scope).
- Command:
  - `PLAYWRIGHT_BASE_URL=https://console.truffles.kz PLAYWRIGHT_WEB_SERVER=0 E2E_DETERMINISTIC_AUTH=0 E2E_USERNAME=admin E2E_PASSWORD=admin corepack pnpm -C console-web exec node - <<'NODE' ... NODE`
- Result artifact:
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-authenticated-perf-baseline-20260223.json`
- Summary:
  - `portfolio p95=979.35ms`
  - `company_cockpit (company scope) p95=268.05ms`
  - `branches (company scope) p95=73.1ms`
  - `company_cockpit (client scope) p95=245.25ms`
  - all status codes `200`.

2. Runtime SLO snapshot after auth load captured from Prometheus metrics.
- Command:
  - `python3 ops/console_tenants_perf_snapshot.py --metrics-url https://api.truffles.kz/metrics --pretty --output /tmp/tenants_perf_snapshot_20260223_after_authload.json`
- Result artifact:
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-perf-snapshot-after-authload-20260223.json`
- Summary:
  - `portfolio p95=1000ms` (`samples=25`, SLO `<1200ms` pass)
  - `company_cockpit p95=250ms` (`samples=45`, SLO `<1000ms` pass)
  - `branches GET p95=100ms` (`samples=22`, SLO `<800ms` pass)
  - overall `status=pass`.

3. Live fail-closed a11y lane recheck on deployed `console.truffles.kz` is green.
- Command:
  - `PLAYWRIGHT_BASE_URL=https://console.truffles.kz PLAYWRIGHT_WEB_SERVER=0 E2E_DETERMINISTIC_AUTH=0 E2E_USERNAME=admin E2E_PASSWORD=admin A11Y_FAIL_ON_THRESHOLDS=1 corepack pnpm -C console-web exec playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1 --reporter=line`
- Result:
  - `3 passed (setup + desktop + mobile)`.
- Updated artifacts:
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-desktop-axe.json`
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-mobile-axe.json`
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-desktop.png`
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-mobile.png`

4. Live canary build/runtime stamp captured for rollout evidence.
- Build artifact:
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-live-build-20260223.json`
  - captured value: `Build: 93824a4 | 2026-02-23T07:17:01Z`.
- Runtime health artifact:
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-runtime-health-20260223.json`
  - current status: `healthy`.

5. Interpretation.
- Wave 6 canary evidence is now complete for this rollout slice: deterministic e2e/a11y lanes are green, deployed build is verified, and runtime SLO snapshot is within thresholds.

## Post-merge perf recheck (2026-02-24, UTC)
1. Runtime tenants perf snapshot refreshed after latest merge.
- Command:
  - `python3 ops/console_tenants_perf_snapshot.py --metrics-url https://api.truffles.kz/metrics --pretty --output /tmp/tenants_perf_snapshot_20260224_postmerge.json`
- Artifact:
  - `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-perf-snapshot-after-merge-20260224.json`

2. Current p95/p99 status from Prometheus histogram.
- `portfolio`: `p95=1000ms`, `p99=1000ms`, SLO `<1200ms` pass (`samples=2`).
- `company_cockpit`: `p95=250ms`, `p99=250ms`, SLO `<1000ms` pass (`samples=1`).
- `branches GET`: `p95=2500ms`, `p99=2500ms`, SLO `<800ms` fail (`samples=3`).
- Overall script result: `status=fail`, `required_slo_failed=true`.

3. Interpretation.
- Wave 1 contract alignment is complete, but Wave 4 runtime performance work remains open because `branches` p95/p99 exceeds target in latest snapshot and requires branch-list path optimization / targeted runtime profiling.
