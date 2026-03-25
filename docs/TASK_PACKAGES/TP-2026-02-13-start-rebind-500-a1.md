# TP-2026-02-13-start-rebind-500-a1

- Название/цель: Убрать `Internal Server Error` при `Start Rebind` в Console provider ops execute и закрыть регрессию тестом на legacy onboarding contract payload.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW по Console Plane onboarding/support), `STRATEGY/REQUIREMENTS.md`.

- Invariant:
  - Provider ops execute остаётся fail-closed по доступу/confirmation.
  - Контракт `OnboardingContractPayload` остаётся строгим (`extra=forbid`) для API входов.
  - Go-live/onboarding scorecard поведение не меняется.

- Scope:
  - Точечный backend fix в ветке provider ops execute (`provider_start_rebind`).
  - Unit test на legacy payload с extra keys.

- Out of scope:
  - Редизайн UX страниц `Integrations` / `Company Workspace`.
  - Изменение схемы onboarding contract.
  - Массовая миграция старых контрактов в БД.

- Touch-list:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_integrations_registry.py`

- Plan:
  1. Заменить unhandled `OnboardingContractPayload.model_validate(...)` в execute-пути на безопасную валидацию с нормализацией payload.
  2. Добавить тест-кейс `provider_start_rebind execute` с legacy extra полями в `payload_json`.
  3. Прогнать целевые тесты и зафиксировать evidence.

- DoD:
  - `Start Rebind` не отдаёт 500 из-за legacy extra полей в stored payload.
  - Ошибки валидации возвращаются контролируемо как `ConsoleAPIError`.
  - Новый тест воспроизводит legacy-case и проходит.

- Checks:
  - `pytest -q truffles-api/tests/test_console_integrations_registry.py -q`
  - `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py -q`

- Evidence:
  - Локальный прогон указанных pytest команд в этой сессии.
  - Diff с изменениями в `console.py` и новом тесте.

- Rollback:
  - Откатить коммит ветки (revert) и вернуть прежнюю логику в `run_integration_reconcile_for_branch`.

- No-go:
  - Не ослаблять schema contract (`extra=forbid`) глобально.
  - Не добавлять хардкод под конкретного клиента.

- Риски/блокеры:
  - В БД могут оставаться другие legacy payload варианты, которые падали в других endpoints и требуют отдельного remediation плана.
