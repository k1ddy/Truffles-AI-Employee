# TP-2026-02-17-onboarding-p6p7-enterprise-loop-a88

- Название/цель: Реализовать `P6+P7` для enterprise onboarding: усилить SLA/escalation control loop и операционный onboarding pipeline в Console Plane без конфликтов с уже смерженным `P4+P5`.
- Canon refs: `AGENTS.md`, `STATE.md` (Console Plane onboarding / enterprise readiness), `SPECS/CONTROL_PLANE.md`, `SPECS/MULTI_TENANT.md`, `STRATEGY/REQUIREMENTS.md`, `docs/REPORTS/2026-02-17-demo-salon-v2-enterprise-readiness-v1.md`.
- Invariant:
  - Не ослаблять existing go-live hard gates и fail-closed логику.
  - Не менять runtime decision semantics webhook/booking.
  - Сохранить backward compatibility API (`optional` новые поля).
- Scope:
  - Backend read models: SLA/escalation loop summary + onboarding operational pipeline summary.
  - Console API schema/contracts: новые поля в onboarding scorecard/autopilot payload.
  - Console Plane UI: визуализация enterprise SLA control loop и pipeline этапов/блокеров.
  - Deterministic diagnostics: CLI summary для enterprise onboarding ops.
- Out of scope:
  - Миграции БД и прод-деплой.
  - Переписывание escalation engine/runtime маршрутизации.
  - Изменение provider transport протокола.
- Touch-list:
  - `truffles-api/app/services/onboarding_state.py`
  - `truffles-api/app/services/onboarding_intake_service.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `ops/diagnose.py`
  - `truffles-api/tests/test_console_onboarding_state.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
  - `truffles-api/tests/test_diagnose_onboarding_fleet.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/types/api.generated.ts`
  - `console-web/src/components/ProvisioningWizard.tsx`
- Plan:
  1) Аудитнуть текущую реализацию P6/P7 surfaces и определить точные gaps по API/UI.
  2) Добавить backend summary для SLA/escalation control loop (breach/risk/recent incidents/coverage).
  3) Добавить backend summary для operational onboarding pipeline (стадии, blockers, next actions, owner lane).
  4) Синхронизировать OpenAPI + generated TS types.
  5) Обновить Console Plane (`ProvisioningWizard`) для новых блоков P6/P7.
  6) Закрыть тестами (backend + contracts + frontend build/lint) и диагностикой.
- DoD:
  - Console API возвращает enterprise SLA control loop summary с вычислимым `status` и actionable fields.
  - Console API возвращает operational onboarding pipeline stage model с blocker list и next actions.
  - `ProvisioningWizard` показывает P6/P7 статусы и блокеры без регрессии существующих секций.
  - Целевые тесты и проверки зелёные.
- Checks:
  - `python3 -m py_compile truffles-api/app/services/onboarding_state.py truffles-api/app/services/onboarding_intake_service.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py ops/diagnose.py`
  - `ruff check truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py ops/diagnose.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py truffles-api/tests/test_diagnose_onboarding_fleet.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_state.py`
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or onboarding_autopilot"`
  - `pytest -q truffles-api/tests/test_diagnose_onboarding_fleet.py`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
  - `npm --prefix console-web run generate:api`
  - `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx`
  - `npm --prefix console-web run build`
- Evidence:
  - `docs/REPORTS/2026-02-17-onboarding-p6p7-enterprise-loop-a88.md`
  - test outputs + command transcripts (key lines)
- Rollback:
  - `git revert SHA_коммита_P6P7` для отката P6/P7 после merge.
- No-go:
  - Не вводить поля, которые требуют DB migrations.
  - Не ломать существующий контракт onboarding/autopilot scorecard.
  - Не маскировать missing data как green status.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-17-onboarding-p6p7-enterprise-loop-a88`
  - Worktree: `/home/zhan/worktrees/2026-02-17-onboarding-p6p7-enterprise-loop-a88`
  - Base: `origin/main`
  - Merge policy: merge commit через PR, без rebase
  - Cleanup: `scripts/session_end.sh --status done` в финальном рабочем коммите; cleanup ветки/worktree после merge
- Риски/блокеры:
  - Источник SLA метрик ограничен текущими read-model полями (без новых таблиц).
  - Возможен API/UI contract drift без regenerate + build checks.
