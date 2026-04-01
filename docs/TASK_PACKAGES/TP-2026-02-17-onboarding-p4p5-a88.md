# TP-2026-02-17-onboarding-p4p5-a88

- Название/цель: Реализовать объединённый контур `P4+P5` для enterprise onboarding: policy-pack compile report из реального клиентского документа + quality matrix с baseline/replay регрессией, и вывести результат в Console Plane onboarding.
- Canon refs: `AGENTS.md`, `STATE.md` (Console onboarding + quality gates), `SPECS/VERTICAL_PACK_KIT.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant:
  - Не ослаблять `GO_LIVE_GATE_REQUIRED` и mandatory minimum data gate.
  - Не менять webhook runtime decision semantics.
  - Не вводить demo-specific хардкоды в runtime-core.
- Scope:
  - Добавить сервис `onboarding_pack_quality` для compile+quality сводки из intake payload.
  - Добавить diagnose-команду для document-driven quality summary и baseline compare.
  - Расширить `onboarding_autopilot` ответ API полями compile/quality.
  - Добавить UI-блок в `ProvisioningWizard` с compile status и quality matrix.
- Out of scope:
  - Полный LLM runtime replay внутри autopilot запроса.
  - Изменение схемы БД/миграции.
  - Изменение live outbound transport flow.
- Touch-list:
  - `truffles-api/app/services/onboarding_pack_quality.py`
  - `truffles-api/app/services/onboarding_intake_service.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_onboarding_pack_quality.py`
  - `truffles-api/tests/test_diagnose_onboarding_fleet.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
  - `ops/diagnose.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/types/api.generated.ts`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `docs/REPORTS/2026-02-17-onboarding-p4p5-a88.md`
- Plan:
  1) Вынести compile+quality расчёт в отдельный сервис и покрыть unit тестами.
  2) Добавить CLI `ops/diagnose.py onboarding-pack-quality` (input document/json, baseline compare, JSON summary).
  3) Подключить compile/quality summary в `onboarding_autopilot` response.
  4) Синхронизировать OpenAPI/TS types и отрисовать блок в `ProvisioningWizard`.
  5) Закрыть целевыми тестами backend/API/diagnose/frontend.
- DoD:
  - Есть единый compile+quality summary с `infra_valid`/`semantic_valid`, matrix dims и compile errors.
  - `onboarding_autopilot` возвращает `intake.compile` и `intake.quality_matrix`.
  - `ProvisioningWizard` отображает compile status и quality dimensions.
  - Diagnose-команда умеет baseline compare и `--fail-on-regression`.
  - Все целевые проверки зелёные.
- Checks:
  - `python3 -m py_compile truffles-api/app/services/onboarding_pack_quality.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py ops/diagnose.py`
  - `ruff check truffles-api/app/services/onboarding_pack_quality.py truffles-api/app/services/onboarding_intake_service.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_onboarding_pack_quality.py truffles-api/tests/test_diagnose_onboarding_fleet.py truffles-api/tests/test_console_access_admin_pr2.py`
  - `pytest -q truffles-api/tests/test_onboarding_pack_quality.py`
  - `pytest -q truffles-api/tests/test_diagnose_onboarding_fleet.py`
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_autopilot or onboarding_scorecard"`
  - `pytest -q truffles-api/tests/test_onboarding_intake_service.py truffles-api/tests/test_console_onboarding_state.py`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
  - `npm --prefix console-web run generate:api`
  - `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx`
  - `npm --prefix console-web run build`
- Evidence:
  - `docs/REPORTS/2026-02-17-onboarding-p4p5-a88.md`
  - JSON summary from `ops/diagnose.py onboarding-pack-quality`
- Rollback:
  - `git revert --no-edit HEAD`
- No-go:
  - Не считать synthetic smoke достаточным без document-driven compile/quality.
  - Не допускать API/UI contract drift.
  - Не вводить bypass go-live для compile/quality fail.
