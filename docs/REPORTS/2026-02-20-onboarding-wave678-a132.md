# REPORT-2026-02-20-onboarding-wave678-a132

- TP: `docs/TASK_PACKAGES/TP-2026-02-20-onboarding-wave678-a132.md`
- Scope: Step 6 + Step 7 + Step 8 (single-operator onboarding flow, evidence-closed incident remediation, onboarding throughput metrics).
- Branch/worktree: `feat/2026-02-20-onboarding-wave678-a132` / `/home/zhan/worktrees/2026-02-20-onboarding-wave678-a132`

## Что реализовано

1) Step 6 (Single-Operator flow consolidation)
- `console-web/src/components/ProvisioningWizard.tsx`:
  - добавлен Execution Hub блок;
  - добавлен CTA `Продолжить в Workspace`;
  - добавлен перенос контекста `company/client/branch` в storage перед переходом в `/company-workspace`.
- `console-web/src/app/tenants/page.tsx` и `console-web/src/app/settings/page.tsx`:
  - добавлены явные UX-подсказки, что remediation/go-live выполняются в `Company Workspace`.

2) Step 7 (Evidence-closed remediation)
- `truffles-api/app/routers/console.py`:
  - для `incident_state=resolved` в `incident_state` job добавлен backend hard-check:
    - обязательны `evidence_confirmed=true` и `evidence_summary`.
  - evidence-поля добавляются в payload и audit metadata.
- `truffles-api/tests/test_console_ops_jobs.py`:
  - добавлены тесты:
    - блокировка resolve без evidence (`INCIDENT_EVIDENCE_REQUIRED`);
    - успешный resolve с evidence и проверка metadata.
- `console-web/src/components/OpsPage.tsx`:
  - добавлен post-check evidence блок на карточке инцидента;
  - baseline/current/delta по метрикам;
  - checklist перед закрытием инцидента;
  - кнопка `Закрыть` блокируется до полного checklist + note;
  - при resolve в job отправляются `evidence_confirmed` + `evidence_summary`.

3) Step 8 (Onboarding throughput metrics)
- `truffles-api/app/schemas/console.py`:
  - добавлена схема `ConsoleOnboardingThroughputMetrics`;
  - в `ConsoleFleetSummary` добавлено поле `onboarding_throughput`.
- `truffles-api/app/routers/console.py`:
  - добавлен расчёт throughput-метрик в summary:
    - `time_to_go_live_median_hours`,
    - `blocker_age_p95_hours`,
    - `first_pass_go_live_rate_pct`,
    - `incident_reopen_rate_24h_pct`;
  - добавлены служебные вычисления percentile/median и first-pass/reopen логика.
- `truffles-api/tests/test_console_tenants_list.py`:
  - добавлены тесты на расчёт throughput-метрик и default поведение на пустом scope.
- `contracts/console_api/openapi.v1.yaml` и `console-web/src/types/api.generated.ts`:
  - синхронизированы контракты/типы под новое поле summary.
- `console-web/src/app/tenants/page.tsx`:
  - добавлена панель `Onboarding Throughput` в KPI-блок.
- `console-web/src/app/company-workspace/page.tsx`:
  - добавлен блок `Скорость онбординга` с теми же 4 KPI.

## Проверки

- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_ops_jobs.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_access_admin_pr2.py` -> PASS
- `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_ops_jobs.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_access_admin_pr2.py` -> PASS
- `pytest -q truffles-api/tests/test_console_ops_jobs.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_access_admin_pr2.py` -> PASS (`90 passed`)
- `python3 truffles-api/scripts/generate_openapi.py --check` -> PASS
- `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/OpsPage.tsx --file src/app/tenants/page.tsx --file src/app/company-workspace/page.tsx --file src/app/settings/page.tsx --file src/types/api.generated.ts` -> PASS
- `npm --prefix console-web run build` -> PASS

## Evidence

- UI:
  - `data-testid="onboarding-execution-hub"`
  - `data-testid="onboarding-open-workspace"`
  - `data-testid="ops-incident-postcheck-<incident_id>"`
  - `data-testid="tenants-onboarding-throughput"`
  - `data-testid="company-workspace-throughput"`
- Backend:
  - `INCIDENT_EVIDENCE_REQUIRED` contract guard in `incident_state` job.
  - Throughput metrics delivered via `summary.onboarding_throughput` in `/admin/clients?include_summary=true`.

