# TP-2026-02-19-onboarding-any-niche-acceptance-a131

- Название/цель: Закрыть `TP-2026-02-19-onboarding-any-niche-end2end-tz.md` по пункту 1 (acceptance contour): собрать и зафиксировать полный evidence-пакет contract/runtime/ops для уже реализованных этапов (domain required fields + readiness kernel + onboarding blueprint v1).
- Canon refs: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-end2end-tz.md`, `AGENTS.md`, `STATE.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- Invariant:
  - Не менять core runtime semantics webhook/decision.
  - Не вводить demo/client-specific hardcode.
  - Приемка только по фактам (команды/JSON/логи), без ручных DB bypass.
- Scope:
  - Прогнать обязательный acceptance-набор из раздела `2.5 A/B/C` целевого ТЗ.
  - Для runtime acceptance зафиксировать фактические ответы scorecard/autopilot/go-live gate (shadow/enforced)
  - Для ops acceptance собрать вывод diagnose-команд и обозначить pass/fail по критериям.
  - Обновить/добавить report + session docs для приемки.
- Out of scope:
  - Реализация этапа 4 (Delivery Contour Stabilization).
  - Реализация этапа 5 (Reference Branch Normalization).
  - Новые функциональные фичи вне необходимых фиксов для прохождения acceptance.
- Touch-list:
  - `docs/REPORTS/2026-02-19-onboarding-any-niche-acceptance-a131.md` (new)
  - `docs/SESSIONS/SESSION-2026-02-19-onboarding-any-niche-acceptance-a131.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md` (только если требуется фиксация фактов)
  - Код/тесты только при выявленной блокирующей регрессии на acceptance-командах.
- Plan:
  1) Поднять session/worktree и подготовить deterministic входные данные для ops/pack-quality.
  2) Прогнать contract acceptance (`py_compile`, `ruff`, `openapi --check`, обязательные pytest наборы).
  3) Прогнать runtime acceptance: scorecard + shadow/enforced gate + autopilot intake, зафиксировать JSON evidence.
  4) Прогнать ops acceptance: fleet-check, quality-smoke, pack-quality, зафиксировать summary.
  5) Сформировать report с фактическим verdict по каждому пункту ТЗ и открыть PR.
- DoD:
  - Для каждого пункта `2.5 A/B/C` есть фактический результат (PASS/BLOCKED/FAIL) с командами и выводом.
  - Runtime evidence включает минимум: `onboarding/scorecard` JSON, `GO_LIVE_GATE_REQUIRED` payload в enforced-path, `autopilot intake` summary.
  - Ops evidence включает минимум: `onboarding-fleet-check`, `onboarding-quality-smoke`, `onboarding-pack-quality`.
  - PR содержит report и, при необходимости, минимальные кодовые фиксы с тестами.
- Checks:
  - `python3 -m py_compile truffles-api/app/services/onboarding_state.py truffles-api/app/services/onboarding_intake_service.py truffles-api/app/services/knowledge_validation.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py ops/diagnose.py`
  - `ruff check truffles-api/app/services/onboarding_state.py truffles-api/app/services/onboarding_intake_service.py truffles-api/app/services/knowledge_validation.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py ops/diagnose.py`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
  - `pytest -q truffles-api/tests/test_console_onboarding_state.py`
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or onboarding_autopilot or go_live or require_branch_scorecard"`
  - `pytest -q truffles-api/tests/test_onboarding_intake_service.py`
  - `pytest -q truffles-api/tests/test_knowledge_validation.py`
  - `pytest -q truffles-api/tests/test_reference_pack_integrity.py`
  - `pytest -q truffles-api/tests/test_diagnose_onboarding_fleet.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`
  - `python3 ops/diagnose.py onboarding-fleet-check --fail-on-active-missing --json`
  - `python3 ops/diagnose.py onboarding-quality-smoke --domains beauty,clinic,legal,ecom --fail-on-regression --json`
  - `python3 ops/diagnose.py onboarding-pack-quality --domain-slug beauty --require-booking auto --client-data-text-file /tmp/onboarding_any_niche_acceptance_client_data.txt --save-summary /tmp/onboarding_any_niche_acceptance_pack_quality.json --json`
- Evidence:
  - Report: `docs/REPORTS/2026-02-19-onboarding-any-niche-acceptance-a131.md`
  - Raw command outputs/JSON snapshots saved under `/tmp/onboarding_any_niche_acceptance_a131/`.
  - При core/behavior изменениях: обновление `STATE.md` с фактами до merge.
- Rollback:
  - Если только docs/evidence: `git revert COMMIT_SHA`.
  - Если есть код: отдельный revert-коммит по конкретному фиксу.
- No-go:
  - Не подгонять результат через ручное редактирование БД/runtime state.
  - Не ослаблять gate или тесты ради прохождения acceptance.
  - Не расширять scope на этапы 4/5 в этом TP.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-19-onboarding-any-niche-acceptance-a131`
  - Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-any-niche-acceptance-a131`
  - Base: `origin/main`
  - Merge policy: merge commit via PR (no rebase)
  - Cleanup: `scripts/session_end.sh --status done` в финальном коммите; удалить worktree/branch после merge.
- Риски/блокеры:
  - Некоторые ops/runtime команды могут зависеть от локального окружения/ключей/контейнеров; фиксировать как `BLOCKED` только при подтвержденной инфраструктурной причине.
