# TP-2026-02-12-onboarding-fleet-remediation-a33

- Название/цель: Закрыть операционный разрыв по onboarding readiness для active branches (domain/contract/payment), добавить fleet-check gate в ops/CI и ввести multi-domain quality smoke вне `demo_salon`.

- Canon refs:
  - `AGENTS.md` (one-issue flow, stop-the-line, Local-first validation, P0/P1/P2 fitness)
  - `STATE.md` NOW/GAP: onboarding + minimum data contract + scorecard hard-stop, gap по полноте onboarding данных на active branches
  - `SPECS/SYSTEM_REFERENCE.md` (evidence/check protocol)
  - `TECH.md` (CI/workflow run policy)

- Invariant:
  - Не ослаблять tenant isolation и go-live hard gates.
  - Не обходить scorecard вручную; только fail-closed поведение.
  - Не ломать существующие console onboarding endpoints/контракты.

- Scope:
  - Ops remediation tool для active branches: report + controlled backfill (`domain_slug` / onboarding contract / payment flag).
  - Fleet readiness check command с `--fail-on-active-missing`.
  - Nightly/workflow gate для fleet-check.
  - Multi-domain onboarding quality smoke command (beauty baseline + clinic/legal/ecom smoke) и тесты.

- Out of scope:
  - Редизайн onboarding UI.
  - Новые бизнес-политики billing/finance.
  - Изменение core webhook decision/runtime orchestration.

- Touch-list (files/tables):
  - `ops/diagnose.py`
  - `.github/workflows/*` (новый или обновлённый workflow с nightly fleet-check)
  - `truffles-api/tests/*` (targeted deterministic tests for new diagnose commands)
  - `docs/runbooks/*` (при необходимости короткий SOP)
  - Runtime DB tables (только через controlled remediation run, без ручной чистки):
    - `branches`
    - `client_capabilities`
    - `client_onboarding_contracts`
    - `reference_packs`

- Plan:
  1. Добавить в `ops/diagnose.py` команды:
     - `onboarding-fleet-check` (report/exit-code gate),
     - `onboarding-fleet-remediate` (controlled backfill with explicit flags),
     - `onboarding-quality-smoke` (multi-domain deterministic smoke).
  2. Добавить тесты на новую CLI-логику (parser + core decision paths + fail-on-active-missing semantics).
  3. Добавить nightly/workflow запуск `onboarding-fleet-check --fail-on-active-missing`.
  4. Выполнить remediation на текущем окружении в controlled режиме и зафиксировать SQL evidence.
  5. Прогнать локальные проверки и собрать evidence bundle для handoff.

- DoD:
  - Есть deterministic ops-команда, которая валидирует onboarding readiness по active branches и даёт non-zero при missing.
  - Есть controlled remediation path для `domain_slug` + contract/payment backfill без unsafe defaults.
  - Nightly/dispatch workflow запускает fleet-check gate.
  - Multi-domain smoke (beauty/clinic/legal/ecom) запускается отдельной командой и даёт machine-readable summary.
  - Тесты на новую логику зелёные.
  - Текущее active branch состояние после remediation: scorecard missing не содержит `reference_pack_domain`.

- Checks:
  - `pytest -q truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_onboarding_intake_service.py truffles-api/tests/test_reference_pack_integrity.py truffles-api/tests/test_console_onboarding_contract_api.py`
  - `python3 ops/diagnose.py onboarding-fleet-check --json --fail-on-active-missing`
  - `python3 ops/diagnose.py onboarding-quality-smoke --domains beauty,clinic,legal,ecom --json`
  - `python3 -m py_compile ops/diagnose.py`

- Evidence:
  - Command outputs for fleet-check before/after remediation.
  - SQL snapshots для active branches (`cap_domain`, `contract_domain`, payment/status).
  - Workflow file diff + local parser/test outputs.
  - Session log + `git diff --stat`.

- Rollback:
  - Code rollback: revert commit/PR.
  - Data rollback: remediation пишет только upsert/update для конкретных записей; откат через point-in-time backup или reverse update по logged IDs.

- No-go:
  - Не делать manual SQL cleanup ради “красивых” отчётов.
  - Не менять webhook core behavior.
  - Не вводить hardcoded domain guesses без явного флага/inputs.

- Риски/блокеры:
  - Для remediation нужен валидный mapping branch->domain (если отсутствует, фиксируется как unresolved, без авто-угадывания).
  - Nightly workflow может требовать секреты/доступ к окружению; fallback — workflow_dispatch + артефакты.

- Branch / Worktree / Base / Merge policy / Cleanup:
  - Branch: `feat/2026-02-12-onboarding-fleet-remediation-a33`
  - Worktree: `/home/zhan/worktrees/2026-02-12-onboarding-fleet-remediation-a33`
  - Base ref: `origin/main`
  - Merge policy: normal PR merge to `main` (no rebase)
  - Cleanup: Brain/Top Architect after merge (remove worktree + branch)
