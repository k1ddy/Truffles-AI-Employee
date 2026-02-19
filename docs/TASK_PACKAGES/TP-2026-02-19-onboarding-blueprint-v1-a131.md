# TP-2026-02-19-onboarding-blueprint-v1-a131

- Название/цель: Реализовать `Onboarding Blueprint v1` как единый backend source-of-truth для шаблонов ниш (`domain_slug`) и авто-вопросов, чтобы убрать хардкод шаблонов из UI и ускорить onboarding новых ниш без изменений core-логики.
- Canon refs: `AGENTS.md`, `STATE.md` (GAP: onboarding cross-niche scaling + false-green risks), `SPECS/CONTROL_PLANE.md`, `SPECS/VERTICAL_PACK_KIT.md`, `docs/PROCESSES.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant:
  - Не ослаблять fail-closed go-live gate (`GO_LIVE_GATE_REQUIRED`).
  - Не вводить demo/client-specific hardcode.
  - Не менять runtime webhook decision semantics.
- Scope:
  - Добавить backend реестр onboarding blueprints (domain templates + question templates + go-live profile metadata).
  - Добавить Console API endpoint для чтения blueprints (platform/owner/admin/support read).
  - Интегрировать `ProvisioningWizard` с API blueprints вместо локального `DOMAIN_TEMPLATE_PRESETS` хардкода.
  - Добавить deterministic fallback в UI только на случай недоступности API (без изменения бизнес-логики payload).
  - Покрыть backend/frontend тестами и обновить OpenAPI.
- Out of scope:
  - Включение hard-gate enforcement в production env.
  - Изменение delivery remediation loop.
  - DB миграции.
- Touch-list:
  - `truffles-api/app/services/onboarding_blueprints.py` (new)
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
  - `truffles-api/tests/test_console_onboarding_state.py` (если потребуется)
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/types/api.ts`
  - `docs/REPORTS/2026-02-19-onboarding-blueprint-v1-a131.md`
- Plan:
  1) Реализовать backend blueprint registry (typed, deterministic, domain-scoped) + сервисные функции получения.
  2) Добавить API endpoint и schema response в console backend.
  3) Подключить wizard к endpoint и заменить использование локального hardcoded template list.
  4) Добавить/обновить тесты backend и frontend type/lint checks.
  5) Обновить OpenAPI, прогнать target checks, собрать evidence report.
- DoD:
  - UI template selector получает данные из backend endpoint.
  - Применение шаблона в wizard работает как раньше по функционалу, но без source-of-truth хардкода в UI.
  - Endpoint возвращает минимум `beauty/clinic/legal/ecom` и machine-readable поля шаблона.
  - Таргетные тесты/линтеры/OpenAPI check зелёные.
- Checks:
  - `python3 -m py_compile truffles-api/app/services/onboarding_blueprints.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py`
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding"`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
  - `ruff check truffles-api/app/services/onboarding_blueprints.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py truffles-api/tests/test_console_access_admin_pr2.py`
  - `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx --file src/lib/api-client.ts`
  - `npm --prefix console-web run build`
- Evidence:
  - Вывод целевых команд checks.
  - Diff по backend+frontend.
  - `docs/REPORTS/2026-02-19-onboarding-blueprint-v1-a131.md`.
- Rollback:
  - `git revert SHA_ONBOARDING_BLUEPRINT_V1_A131`.
- No-go:
  - Не добавлять niche rules через `if domain_slug == ...` в роутере.
  - Не оставлять дублирующий источник шаблонов между backend и frontend как primary truth.
  - Не менять контракты go-live gate без тестов.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-19-onboarding-blueprint-v1-a131`
  - Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-blueprint-v1-a131`
  - Base: `origin/main`
  - Merge policy: merge commit via PR (no rebase)
  - Cleanup: `scripts/session_end.sh --status done` в финальном рабочем коммите; удалить worktree/branch после merge.
- Риски/блокеры:
  - Риск UI contract drift при обновлении типов API; mitigation: OpenAPI check + build.
  - Риск регрессии wizard apply; mitigation: сохранить payload contract и добавить тестовые проверки endpoint + UI wiring.
