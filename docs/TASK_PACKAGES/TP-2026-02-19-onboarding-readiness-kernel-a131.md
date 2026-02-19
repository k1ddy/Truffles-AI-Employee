# TP-2026-02-19-onboarding-readiness-kernel-a131

- Название/цель: Реализовать единый `Onboarding Readiness Kernel v1` в Control Plane как источник истины для готовности запуска: read-only scorecard readiness, shadow hard-gate и флаг включения enforcement без хардкода.
- Canon refs: `AGENTS.md`, `STATE.md` (GAP: onboarding/go-live ложные зелёные статусы), `SPECS/CONTROL_PLANE.md`, `SPECS/VERTICAL_PACK_KIT.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant:
  - Не ослаблять существующий fail-closed `GO_LIVE_GATE_REQUIRED`.
  - Не менять runtime decision semantics webhook/booking.
  - Не добавлять niche-specific hardcode (вся логика через deterministic codes).
- Scope:
  - Добавить readiness kernel read-model в onboarding scorecard API:
    - blocker codes,
    - next_action codes,
    - auto_questions,
    - shadow hard-gate статус.
  - Добавить shadow hard-gate logic в `go-live`/`branch_activate` путь.
  - Добавить feature flag для включения hard-gate enforcement.
  - Покрыть тестами сериализацию и gate behavior.
- Out of scope:
  - UI redesign `ProvisioningWizard`.
  - DB migrations.
  - Изменение transport/provider routing.
- Touch-list:
  - `truffles-api/app/services/onboarding_state.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_onboarding_state.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `docs/REPORTS/2026-02-19-onboarding-readiness-kernel-a131.md`
- Plan:
  1) Добавить в `onboarding_state` deterministic readiness kernel (dimensions/blockers/actions/questions + shadow gate blockers).
  2) Расширить API schema/serializer для scorecard readiness payload.
  3) Встроить feature-flagged hard-gate enforcement в go-live/activate путь (`shadow` по умолчанию, `enforced` только при flag=on).
  4) Обновить тесты на scorecard payload и gate behavior.
  5) Синхронизировать OpenAPI контракт и прогнать target checks.
- DoD:
  - `/console/v1/onboarding/scorecard` возвращает readiness kernel с codes/actions/questions и shadow hard-gate.
  - При выключенном flag поведение блокировки не меняется (shadow-only).
  - При включенном flag hard-gate блокирует по readiness blocker codes.
  - Ошибка `GO_LIVE_GATE_REQUIRED` содержит readiness детали для диагностики.
  - Таргетные проверки зелёные.
- Checks:
  - `python3 -m py_compile truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_state.py`
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or go_live or require_branch_scorecard"`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
  - `ruff check truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py`
- Evidence:
  - Test outputs for target pytest set.
  - OpenAPI drift check output.
  - `docs/REPORTS/2026-02-19-onboarding-readiness-kernel-a131.md`.
- Rollback:
  - `git revert SHA_ONBOARDING_READINESS_KERNEL_A131`.
- No-go:
  - Не включать hard-gate enforcement по умолчанию.
  - Не дублировать бизнес-логику в нескольких местах (единый readiness kernel).
  - Не подменять blocker codes текстовыми эвристиками.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-19-onboarding-readiness-kernel-a131`
  - Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-readiness-kernel-a131`
  - Base: `origin/main`
  - Merge policy: merge commit via PR (no rebase)
  - Cleanup: `scripts/session_end.sh --status done` в финальном рабочем коммите; удалить worktree/branch после merge.
- Риски/блокеры:
  - Риск contract drift при расширении scorecard schema.
  - Неправильные thresholds delivery-health могут дать шум; mitigation: shadow mode by default + env-flagged enforcement.
