# TP-2026-02-17-console-onboarding-wave12-a88

- Название/цель: Реализовать wave `1+2` для enterprise onboarding: синхронизировать autopilot intake contract/UI и добавить `Document Ingestion Gate` в server scorecard/go-live prerequisites.
- Canon refs: `AGENTS.md`, `STATE.md` (Console Plane onboarding), `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant:
  - Не ослаблять `GO_LIVE_GATE_REQUIRED` и existing onboarding prerequisites.
  - Не менять webhook runtime decision semantics.
  - Сохранять backward compatibility (`document_ingestion` optional в scorecard API).
- Scope:
  - Backend: `onboarding_state` + scorecard serialization + schema.
  - Contract: `contracts/console_api/openapi.v1.yaml` + regenerated TS types.
  - UI: `ProvisioningWizard` render для `intake.field_states/question_queue` и `scorecard.document_ingestion`.
- Out of scope:
  - Новый ingestion parser v2.
  - Миграции БД.
  - Изменение live-outbound transport логики.
- Touch-list:
  - `truffles-api/app/services/onboarding_state.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_onboarding_state.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/types/api.generated.ts`
  - `console-web/src/components/ProvisioningWizard.tsx`
- Plan:
  1) Добавить `document_ingestion` вычисление в onboarding inputs/scorecard.
  2) Привязать gate к GO_NO_GO missing (`document_ingestion_invalid`).
  3) Расширить scorecard schema/serializer.
  4) Синхронизировать OpenAPI и frontend types.
  5) Отрендерить новые intake поля и document ingestion status в Console Plane.
  6) Закрыть тестами и сборкой.
- DoD:
  - `/onboarding/scorecard` возвращает `document_ingestion` payload.
  - GO/No-Go учитывает `document_ingestion_invalid` при `knowledge_upload=true`.
  - `ProvisioningWizard` отображает `field_states`, `question_queue`, `document_ingestion`.
  - Все целевые проверки зеленые.
- Checks:
  - `python3 -m py_compile truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py`
  - `ruff check truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_state.py`
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or onboarding_autopilot"`
  - `pytest -q truffles-api/tests/test_onboarding_intake_service.py`
  - `pytest -q truffles-api/tests/test_minimum_data_contract.py truffles-api/tests/test_safe_mode_gate.py`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
  - `npm --prefix console-web run generate:api`
  - `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx`
  - `npm --prefix console-web run build`
- Evidence:
  - `docs/REPORTS/2026-02-17-console-onboarding-wave12-a88.md`
- Rollback:
  - `git revert 0a792a84`
- No-go:
  - Не вводить go-live bypass при `document_ingestion_invalid`.
  - Не оставлять backend/frontend contract drift.
